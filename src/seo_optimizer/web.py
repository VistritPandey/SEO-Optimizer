"""Authenticated management API and server-rendered dashboard."""

import hashlib
import hmac
import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import HttpUrl, ValidationError
from sqlalchemy.exc import IntegrityError
from starlette.middleware.sessions import SessionMiddleware

from seo_optimizer.application_models import (
    ProjectCreate,
    ProjectSecrets,
    ProjectSpec,
    Registration,
)
from seo_optimizer.contracts import WebsiteType
from seo_optimizer.github import verify_signature
from seo_optimizer.growth import CitationProbe, Workspace, plan
from seo_optimizer.settings import Settings
from seo_optimizer.store import Job, Project, Store, User, open_store

ASSETS = Path(__file__).parent / "ui"


def hash_password(value: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(value.encode(), salt=salt, n=16384, r=8, p=1, maxmem=64 * 1024 * 1024)
    return salt.hex() + ":" + digest.hex()


def check_password(value: str, encoded: str) -> bool:
    try:
        salt, expected = encoded.split(":")
        actual = hashlib.scrypt(
            value.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, maxmem=64 * 1024 * 1024
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def public_report(report: dict[str, Any], hosted: bool = False) -> dict[str, Any]:
    if not hosted:
        return report
    return {
        **{
            key: value
            for key, value in report.items()
            if key not in {"model", "model_summary", "model_cache_hit", "cacheable_model_result"}
        },
        **(
            {"assessment_reused": report["model_cache_hit"] is True}
            if "model_cache_hit" in report
            else {}
        ),
    }


def project_json(project: Project, hosted: bool = False) -> dict[str, Any]:
    spec = dict(project.spec)
    if hosted:
        spec.pop("provider", None)
    return {
        "id": project.id,
        "spec": spec,
        "last_report": public_report(project.last_report, hosted),
        "last_revision": project.last_revision,
        "updated_at": project.updated_at,
    }


def job_json(job: Job, hosted: bool = False) -> dict[str, Any]:
    result = dict(job.result)
    if hosted:
        for key in ("report", "after_report"):
            if isinstance(result.get(key), dict):
                result[key] = public_report(result[key], hosted=True)
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "project_id": job.project_id,
        "kind": job.kind,
        "status": job.status,
        "result": result,
        "events": job.events,
        "payload": job.payload,
        "attempts": job.attempts,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def create_app(settings: Settings | None = None, store: Store | None = None) -> FastAPI:
    configuration = settings or Settings.from_env()
    storage = store or open_store(configuration)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        if store is None:
            storage.close()

    app = FastAPI(
        title="Your Optimiser API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if configuration.production else "/api/docs",
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
    )
    app.state.store, app.state.settings = storage, configuration
    app.add_middleware(
        SessionMiddleware,
        secret_key=configuration.secret_key,
        same_site="lax",
        https_only=configuration.production,
        max_age=604800,
    )
    app.mount("/static", StaticFiles(directory=ASSETS / "static"), name="static")
    templates = Jinja2Templates(directory=ASSETS / "templates")

    @app.get("/guide", response_class=HTMLResponse, include_in_schema=False)
    def guide(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request=request, name="guide.html", context={})

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Any:
        if (
            configuration.hosted
            and request.method != "GET"
            and not request.url.path.startswith(("/api/v1/", "/webhooks/"))
        ):
            return JSONResponse({"detail": "Use the hosted dashboard"}, status_code=403)
        if request.method in {"POST", "PATCH", "PUT"}:
            body = await request.body()
            if len(body) > 2_000_000:
                return JSONResponse({"detail": "Request body exceeds the limit"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; frame-ancestors 'none'; form-action 'self'"
        )
        if not request.url.path.startswith("/static"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def user(request: Request, required: bool = True) -> User | None:
        authorization = request.headers.get("authorization", "")
        authenticated = (
            storage.user(token=authorization[7:])
            if authorization.startswith("Bearer ")
            else storage.user(id=request.session.get("user_id"))
        )
        if authenticated is None and configuration.hosted and authorization.startswith("Bearer "):
            from seo_optimizer.hosted import firebase_user

            authenticated = firebase_user(authorization[7:], configuration, storage)
        if authenticated is None and required:
            raise HTTPException(401, "Sign in to continue")
        return authenticated

    def require_user(request: Request) -> User:
        if configuration.hosted and request.url.path.startswith("/api/v1/worker/"):
            raise HTTPException(403, "Managed worker access is reserved for service identity")
        value = user(request)
        assert value is not None
        return value

    def csrf(request: Request, value: str | None = None) -> None:
        if request.headers.get("authorization", "").startswith("Bearer "):
            return
        expected = request.session.get("csrf", "")
        actual = value or request.headers.get("x-csrf-token", "")
        if not expected or not hmac.compare_digest(expected, actual):
            raise HTTPException(403, "Request verification failed; reload the page")

    def render(
        request: Request, name: str, values: dict[str, Any] | None = None, status: int = 200
    ) -> HTMLResponse:
        request.session.setdefault("csrf", secrets.token_urlsafe(32))
        return templates.TemplateResponse(
            request=request,
            name=name,
            context={
                "user": user(request, False),
                "csrf": request.session["csrf"],
                **(values or {}),
            },
            status_code=status,
        )

    def owned(request: Request, id: str) -> Project:
        account = require_user(request)
        value = storage.project(account.id, id)
        if value is None:
            raise HTTPException(404, "Project not found")
        return value

    def validate_host_policy(spec: ProjectSpec) -> None:
        if spec.local_path and not configuration.allow_local_repositories:
            raise HTTPException(400, "This host accepts GitHub repositories only")
        if spec.local_path and not any(
            Path(spec.local_path).resolve().is_relative_to(root)
            for root in configuration.allowed_repo_roots
        ):
            raise HTTPException(400, "Local repository is outside configured roots")

    @app.exception_handler(ValueError)
    async def value_error(request: Request, error: ValueError) -> JSONResponse:
        message = str(error)
        allowed = {"Monthly free audit/job limit reached", "Project limit reached"}
        return JSONResponse(
            {"detail": message if message in allowed else "Request validation failed"},
            status_code=429 if message in allowed else 400,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> Any:
        if request.url.path.startswith(("/api", "/webhooks")):
            return JSONResponse({"detail": error.detail}, status_code=error.status_code)
        if error.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        return render(request, "error.html", {"message": error.detail}, error.status_code)

    @app.get("/api/v1/health", include_in_schema=False)
    @app.get("/healthz")
    def health() -> dict[str, str]:
        storage.health()
        return {"status": "ready", "version": "1.0.0"}

    @app.get("/login")
    def login(request: Request) -> Any:
        return render(request, "auth.html", {"register": False})

    @app.get("/register")
    def register(request: Request) -> Any:
        if configuration.hosted or not configuration.registration_enabled:
            raise HTTPException(403, "Registration is disabled")
        return render(request, "auth.html", {"register": True})

    @app.post("/register")
    async def registration_form(request: Request) -> Any:
        form = await request.form()
        csrf(request, str(form.get("csrf", "")))
        if configuration.hosted or not configuration.registration_enabled:
            raise HTTPException(403, "Registration is disabled")
        try:
            value = Registration(
                email=str(form.get("email", "")), password=str(form.get("password", ""))
            )
            account, _ = storage.create_user(value.email, hash_password(value.password))
        except (ValidationError, IntegrityError):
            return render(
                request,
                "auth.html",
                {
                    "register": True,
                    "error": (
                        "Use a valid email and at least 12 password characters. "
                        "The email must be available."
                    ),
                },
                400,
            )
        request.session.clear()
        request.session["user_id"] = account.id
        return RedirectResponse("/", status_code=303)

    @app.post("/login")
    async def login_form(request: Request) -> Any:
        form = await request.form()
        csrf(request, str(form.get("csrf", "")))
        email = str(form.get("email", "")).strip().lower()
        host = request.client.host if request.client else "unknown"
        if not storage.throttle(host + ":" + email):
            raise HTTPException(429, "Too many sign-in attempts; try again later")
        account = storage.user(email=email)
        if not account or not check_password(str(form.get("password", "")), account.password_hash):
            return render(
                request,
                "auth.html",
                {"register": False, "error": "Email or password is incorrect."},
                400,
            )
        request.session.clear()
        request.session["user_id"] = account.id
        return RedirectResponse("/", status_code=303)

    @app.post("/logout")
    async def logout(request: Request) -> Any:
        form = await request.form()
        csrf(request, str(form.get("csrf", "")))
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    @app.get("/")
    def dashboard(request: Request) -> Any:
        account = require_user(request)
        projects = storage.projects(account.id)
        jobs = storage.jobs(account.id)
        lookup = {project.id: project.spec["name"] for project in projects}
        repairs: dict[str, int] = {}
        for job in jobs:
            key = job.result.get("pr", {}).get("url") or job.id
            repairs[key] = max(repairs.get(key, 0), job.result.get("verified_fixes", 0))
        return render(
            request,
            "dashboard.html",
            {
                "projects": projects,
                "jobs": jobs[:8],
                "lookup": lookup,
                "active": sum(
                    job.status in {"queued", "running", "waiting_checks", "waiting_deployment"}
                    for job in jobs
                ),
                "verified": sum(repairs.values()),
            },
        )

    @app.get("/projects/new")
    def new_project(request: Request) -> Any:
        require_user(request)
        return render(
            request, "project_form.html", {"local_allowed": configuration.allow_local_repositories}
        )

    @app.post("/projects/new")
    async def new_project_form(request: Request) -> Any:
        account = require_user(request)
        form = await request.form()
        csrf(request, str(form.get("csrf", "")))
        try:
            from seo_optimizer.application_models import ProviderConfig
            from seo_optimizer.contracts import ProviderCapabilities

            provider = str(form.get("provider", "rules"))
            spec = ProjectSpec(
                name=str(form.get("name", "")),
                website_url=HttpUrl(str(form.get("website_url", ""))),
                repository=str(form.get("repository", "")).strip(),
                local_path=str(form.get("local_path", "")).strip() or None,
                provider=ProviderConfig(
                    kind=cast(Any, provider),
                    model=str(form.get("model", "")).strip(),
                    base_url=str(form.get("base_url", "")).strip() or None,
                    capabilities=ProviderCapabilities(
                        tool_calling=provider != "rules", json_schema=provider == "ollama"
                    ),
                ),
                website_types=[WebsiteType(str(form.get("website_type", "generic")))],
            )
            validate_host_policy(spec)
            value = storage.create_project(
                account.id,
                ProjectCreate(
                    spec=spec,
                    credentials=ProjectSecrets(
                        github_token=str(form.get("github_token", "")),
                        provider_key=str(form.get("provider_key", "")),
                        webhook_secret=str(form.get("webhook_secret", ""))
                        or secrets.token_urlsafe(32),
                    ),
                ),
            )
        except (ValueError, ValidationError):
            return render(
                request,
                "project_form.html",
                {
                    "error": "Check the website URL, repository, model and selected project type.",
                    "local_allowed": configuration.allow_local_repositories,
                },
                400,
            )
        return RedirectResponse("/projects/" + value.id, status_code=303)

    @app.get("/projects/{id}")
    def project_page(request: Request, id: str) -> Any:
        project = owned(request, id)
        return render(
            request,
            "project.html",
            {
                "project": project,
                "jobs": storage.jobs(project.tenant_id, id),
                "findings": storage.findings(project.tenant_id, id),
                "configuration": json.dumps(project.spec, indent=2),
                "webhook_url": configuration.public_url.rstrip("/") + "/webhooks/github/" + id,
                "strategy": plan(
                    ProjectSpec.model_validate(project.spec),
                    storage.workspace(project.tenant_id, id),
                ),
            },
        )

    @app.get("/projects/{id}/research")
    def research_page(request: Request, id: str) -> Any:
        project = owned(request, id)
        workspace = storage.workspace(project.tenant_id, id)
        return render(
            request,
            "research.html",
            {
                "project": project,
                "workspace": workspace.model_dump_json(indent=2),
                "strategy": plan(ProjectSpec.model_validate(project.spec), workspace),
            },
        )

    @app.post("/projects/{id}/research")
    async def research_save(request: Request, id: str) -> Any:
        project = owned(request, id)
        form = await request.form()
        csrf(request, str(form.get("csrf", "")))
        try:
            value = Workspace.model_validate_json(str(form.get("workspace", "")))
            storage.save_workspace(project.tenant_id, id, value)
        except ValueError:
            raise HTTPException(
                400, "Research contracts or project fact references are invalid"
            ) from None
        return RedirectResponse(f"/projects/{id}/research", status_code=303)

    @app.post("/projects/{id}/content/{opportunity_id}")
    async def content_run(request: Request, id: str, opportunity_id: str) -> Any:
        project = owned(request, id)
        form = await request.form()
        csrf(request, str(form.get("csrf", "")))
        job = storage.enqueue(
            project.tenant_id,
            id,
            "content",
            "content:" + str(uuid4()),
            {"opportunity_id": opportunity_id},
        )
        return RedirectResponse("/jobs/" + job.id, status_code=303)

    @app.get("/api/v1/projects/{id}/workspace")
    def api_workspace(request: Request, id: str) -> Any:
        project = owned(request, id)
        return storage.workspace(project.tenant_id, id).model_dump(mode="json")

    @app.put("/api/v1/projects/{id}/workspace")
    def api_save_workspace(request: Request, id: str, value: Workspace) -> Any:
        project = owned(request, id)
        csrf(request)
        try:
            storage.save_workspace(project.tenant_id, id, value)
        except ValueError:
            raise HTTPException(400, "Research contains invalid project references") from None
        return value.model_dump(mode="json")

    @app.get("/api/v1/projects/{id}/strategy")
    def api_strategy(request: Request, id: str) -> Any:
        project = owned(request, id)
        return plan(
            ProjectSpec.model_validate(project.spec), storage.workspace(project.tenant_id, id)
        ).model_dump(mode="json")

    @app.post("/api/v1/projects/{id}/search-console")
    def api_search_console(request: Request, id: str, start: date, end: date) -> Any:
        from seo_optimizer.search_console import collect_search

        project = owned(request, id)
        csrf(request)
        try:
            observations, coverage = collect_search(
                str(project.spec["website_url"]),
                start,
                end,
                storage.secrets(project).search_console_access_token,
            )
            workspace = storage.workspace(project.tenant_id, id)
            replacement_ids = {row.id for row in observations}
            workspace = Workspace.model_validate(
                {
                    **workspace.model_dump(),
                    "search": [row for row in workspace.search if row.id not in replacement_ids]
                    + observations,
                }
            )
            storage.save_workspace(project.tenant_id, id, workspace)
        except ValueError:
            raise HTTPException(
                400,
                "Search Console import needs valid OAuth access, dates "
                "and nonoverlapping project observations",
            ) from None
        return coverage

    @app.post("/api/v1/projects/{id}/citations")
    def api_citation_probe(request: Request, id: str, value: CitationProbe) -> Any:
        from seo_optimizer.citations import collect_citation

        project = owned(request, id)
        csrf(request)
        spec = ProjectSpec.model_validate(project.spec)
        if spec.provider.kind != "google":
            raise HTTPException(
                400,
                "Search-grounded API collection needs a Google provider; "
                "other engine observations can be imported",
            )
        storage.reserve_job(project.tenant_id, "citation:" + str(uuid4()))
        try:
            observation, transcript = collect_citation(
                value.query,
                spec.provider.model,
                storage.secrets(project).provider_key,
                value.experiment,
                value.market,
                value.arm,
            )
            workspace = storage.workspace(project.tenant_id, id)
            workspace = Workspace.model_validate(
                {
                    **workspace.model_dump(),
                    "citations": [*workspace.citations, observation],
                }
            )
            storage.save_workspace(project.tenant_id, id, workspace)
        except ValueError:
            raise HTTPException(
                400, "Citation collection failed or reached the observation limit"
            ) from None
        return {"observation": observation.model_dump(mode="json"), "transcript": transcript}

    @app.post("/api/v1/projects/{id}/strategy", status_code=202)
    def api_strategy_run(request: Request, id: str) -> Any:
        project = owned(request, id)
        csrf(request)
        return job_json(
            storage.enqueue(project.tenant_id, id, "strategy", "strategy:" + str(uuid4()), {})
        )

    @app.post("/api/v1/projects/{id}/content/{opportunity_id}", status_code=202)
    def api_content_run(request: Request, id: str, opportunity_id: str) -> Any:
        project = owned(request, id)
        csrf(request)
        return job_json(
            storage.enqueue(
                project.tenant_id,
                id,
                "content",
                "content:" + str(uuid4()),
                {"opportunity_id": opportunity_id},
            )
        )

    @app.post("/projects/{id}/run")
    async def project_run(request: Request, id: str) -> Any:
        project = owned(request, id)
        form = await request.form()
        csrf(request, str(form.get("csrf", "")))
        job = storage.enqueue(project.tenant_id, id, "audit", "manual:" + str(uuid4()), {})
        return RedirectResponse("/jobs/" + job.id, status_code=303)

    @app.post("/projects/{id}/settings")
    async def project_settings(request: Request, id: str) -> Any:
        project = owned(request, id)
        form = await request.form()
        csrf(request, str(form.get("csrf", "")))
        try:
            spec = ProjectSpec.model_validate_json(str(form.get("configuration", "")))
            validate_host_policy(spec)
            storage.update_project(project.tenant_id, id, spec)
        except (ValueError, ValidationError):
            raise HTTPException(400, "Project configuration is invalid") from None
        return RedirectResponse("/projects/" + id, status_code=303)

    @app.get("/jobs/{id}")
    def job_page(request: Request, id: str) -> Any:
        account = require_user(request)
        job = storage.job(account.id, id)
        if job is None:
            raise HTTPException(404, "Job not found")
        return render(
            request,
            "job.html",
            {"job": job, "project": storage.project(account.id, job.project_id)},
        )

    @app.post("/projects/{id}/credentials")
    async def project_credentials(request: Request, id: str) -> Any:
        project = owned(request, id)
        form = await request.form()
        csrf(request, str(form.get("csrf", "")))
        credentials = storage.secrets(project).model_dump()
        for name in credentials:
            value = str(form.get(name, "")).strip()
            if value:
                credentials[name] = value
        storage.update_project(
            project.tenant_id,
            id,
            ProjectSpec.model_validate(project.spec),
            ProjectSecrets.model_validate(credentials),
        )
        return RedirectResponse("/projects/" + id, status_code=303)

    @app.get("/settings")
    def settings_page(request: Request) -> Any:
        require_user(request)
        return render(request, "settings.html")

    @app.post("/settings/token")
    async def rotate_token(request: Request) -> Any:
        account = require_user(request)
        form = await request.form()
        csrf(request, str(form.get("csrf", "")))
        return render(request, "settings.html", {"token": storage.rotate_token(account.id)})

    @app.get("/api/v1/projects")
    def api_projects(request: Request) -> Any:
        account = require_user(request)
        return [
            project_json(project, hosted=configuration.hosted)
            for project in storage.projects(account.id)
        ]

    @app.post("/api/v1/projects", status_code=201)
    def api_create_project(request: Request, value: ProjectCreate) -> Any:
        account = require_user(request)
        csrf(request)
        validate_host_policy(value.spec)
        if configuration.hosted:
            from seo_optimizer.hosted import connected_create

            value = connected_create(value, account.id, storage, configuration)
        project = storage.create_project(account.id, value)
        from seo_optimizer.followups import register_project

        register_project(storage, project)
        return project_json(project, hosted=configuration.hosted)

    @app.get("/api/v1/projects/{id}")
    def api_project(request: Request, id: str) -> Any:
        return project_json(owned(request, id), hosted=configuration.hosted)

    @app.patch("/api/v1/projects/{id}")
    def api_update_project(request: Request, id: str, spec: ProjectSpec) -> Any:
        project = owned(request, id)
        csrf(request)
        validate_host_policy(spec)
        if configuration.hosted:
            from seo_optimizer.hosted import managed_spec

            if spec.repository != project.spec.get("repository"):
                raise HTTPException(400, "Connect a new project to change repository access")
            spec = managed_spec(spec, configuration)
            credentials = storage.secrets(project)
            if spec.enabled and (
                not project.spec.get("enabled") or not credentials.github_installation_id
            ):
                from seo_optimizer.followups import register_project
                from seo_optimizer.hosted import connected_create

                connection = connected_create(
                    ProjectCreate(spec=spec), project.tenant_id, storage, configuration
                )
                credentials.github_installation_id = connection.credentials.github_installation_id
                storage.update_project(project.tenant_id, id, spec, credentials)
                updated = storage.project(project.tenant_id, id)
                assert updated is not None
                register_project(storage, updated)
                return project_json(updated, hosted=configuration.hosted)
        storage.update_project(project.tenant_id, id, spec)
        updated = storage.project(project.tenant_id, id)
        assert updated is not None
        return project_json(updated, hosted=configuration.hosted)

    @app.put("/api/v1/projects/{id}/credentials")
    def api_credentials(request: Request, id: str, value: ProjectSecrets) -> Any:
        project = owned(request, id)
        csrf(request)
        if configuration.hosted:
            raise HTTPException(403, "Hosted credentials are managed by the service")
        storage.update_project(
            project.tenant_id, id, ProjectSpec.model_validate(project.spec), value
        )
        return {"status": "configured"}

    @app.post("/api/v1/projects/{id}/jobs", status_code=202)
    def api_run(request: Request, id: str) -> Any:
        project = owned(request, id)
        csrf(request)
        return job_json(
            storage.enqueue(project.tenant_id, id, "audit", "manual:" + str(uuid4()), {}),
            hosted=configuration.hosted,
        )

    @app.get("/api/v1/jobs/{id}")
    def api_job(request: Request, id: str) -> Any:
        account = require_user(request)
        job = storage.job(account.id, id)
        if job is None:
            raise HTTPException(404, "Job not found")
        return job_json(job, hosted=configuration.hosted)

    @app.post("/api/v1/worker/claim")
    def api_claim(request: Request, value: dict[str, str]) -> Any:
        account = require_user(request)
        if not request.headers.get("authorization", "").startswith("Bearer "):
            raise HTTPException(403, "Worker requires a scoped API token")
        worker = value.get("worker_id", "")
        if not re_worker_id(worker):
            raise HTTPException(400, "Invalid worker identifier")
        job = storage.claim(worker, account.id)
        if job is None:
            return None
        project = storage.project(account.id, job.project_id)
        assert project is not None
        return {
            "job": job_json(job),
            "project": project_json(project),
            "credentials": storage.secrets(project).model_dump(),
        }

    @app.post("/api/v1/worker/jobs/{id}/progress")
    def api_progress(request: Request, id: str, value: dict[str, Any]) -> Any:
        account = require_user(request)
        if not request.headers.get("authorization", "").startswith("Bearer "):
            raise HTTPException(403, "Worker requires a scoped API token")
        worker, message = value.get("worker_id"), value.get("message")
        if not isinstance(worker, str) or not re_worker_id(worker):
            raise HTTPException(400, "Invalid worker identifier")
        if not isinstance(message, str) or not message or len(message) > 200:
            raise HTTPException(400, "Invalid progress message")
        try:
            storage.progress(account.id, id, worker, message)
        except ValueError:
            raise HTTPException(409, "Job lease is not owned by this worker") from None
        return {"status": "recorded"}

    @app.post("/api/v1/worker/jobs/{id}/finish")
    def api_finish(request: Request, id: str, value: dict[str, Any]) -> Any:
        account = require_user(request)
        if not request.headers.get("authorization", "").startswith("Bearer "):
            raise HTTPException(403, "Worker requires a scoped API token")
        if value.get("status") not in {
            "complete",
            "queued",
            "failed",
            "blocked",
            "canceled",
            "superseded",
            "waiting_checks",
            "waiting_deployment",
        }:
            raise HTTPException(400, "Invalid job status")
        try:
            storage.finish(
                account.id,
                id,
                value["worker_id"],
                value["status"],
                value["result"],
                min(3600, max(0, float(value.get("delay", 0)))),
            )
        except (ValueError, KeyError):
            raise HTTPException(409, "Job lease is not owned by this worker") from None
        return {"status": "recorded"}

    @app.post("/api/v1/worker/findings")
    def api_findings(request: Request, value: dict[str, Any]) -> Any:
        account = require_user(request)
        if not request.headers.get("authorization", "").startswith("Bearer "):
            raise HTTPException(403, "Worker requires a scoped API token")
        if storage.project(account.id, value["project_id"]) is None:
            raise HTTPException(404, "Project not found")
        fresh = storage.remember_findings(
            account.id, value["project_id"], value["findings"], value["audited_urls"]
        )
        return {"fresh": fresh}

    @app.post("/api/v1/worker/enqueue")
    def worker_enqueue(request: Request, value: dict[str, Any]) -> Any:
        account = require_user(request)
        if not request.headers.get("authorization", "").startswith("Bearer "):
            raise HTTPException(403, "Worker requires a scoped API token")
        if storage.project(account.id, value["project_id"]) is None:
            raise HTTPException(404, "Project not found")
        if value.get("kind") not in {"audit", "push", "strategy", "content"}:
            raise HTTPException(400, "Invalid job kind")
        return job_json(
            storage.enqueue(
                account.id,
                value["project_id"],
                value["kind"],
                value["key"],
                value.get("payload", {}),
            )
        )

    @app.post("/api/v1/reconcile")
    def api_reconcile(request: Request) -> Any:
        account = require_user(request)
        csrf(request)
        return {"scheduled": storage.reconcile(account.id)}

    @app.post("/webhooks/github/{id}")
    async def webhook(request: Request, id: str) -> Any:
        project = storage.webhook_project(id)
        if project is None:
            raise HTTPException(404, "Project not found")
        raw = await request.body()
        if not verify_signature(
            storage.secrets(project).webhook_secret,
            raw,
            request.headers.get("x-hub-signature-256", ""),
        ):
            raise HTTPException(403, "Webhook signature is invalid")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            raise HTTPException(400, "Webhook body is invalid") from None
        if not isinstance(payload, dict):
            raise HTTPException(400, "Invalid webhook payload")
        from seo_optimizer.followups import handle_event

        return handle_event(
            storage,
            project,
            request.headers.get("x-github-event", ""),
            payload,
            request.headers.get("x-github-delivery", ""),
        )

    from seo_optimizer.hosted import install_routes

    install_routes(app, storage, configuration, require_user)
    from seo_optimizer.followups import install_webhook

    install_webhook(app, storage, configuration)
    from seo_optimizer.task_dispatch import install as install_tasks

    install_tasks(app, storage, configuration)
    return app


def re_worker_id(value: str) -> bool:
    import re

    return bool(re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value))


def re_sha(value: str) -> bool:
    import re

    return bool(re.fullmatch(r"[0-9a-f]{40,64}", value))
