"""Managed account policy, verified Firebase identity and GitHub App connections."""

import secrets
import time
from datetime import UTC, datetime
from typing import Any, Literal, cast
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse

from seo_optimizer.application_models import (
    ProjectCreate,
    ProjectSecrets,
    ProjectSpec,
    ProviderConfig,
)
from seo_optimizer.contracts import ProviderCapabilities
from seo_optimizer.github import GitHubClient
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store, User, token_hash


def firebase_user(token: str, settings: Settings, store: Store) -> User | None:
    import firebase_admin  # type: ignore[import-untyped]
    from firebase_admin import auth

    name = "your-optimiser-" + settings.firebase_project
    try:
        application = firebase_admin.get_app(name)
    except ValueError:
        application = firebase_admin.initialize_app(
            options={"projectId": settings.firebase_project}, name=name
        )
    try:
        claims = auth.verify_id_token(token, app=application, check_revoked=True)
        if not claims.get("email_verified") or not claims.get("email"):
            return None
        uid = str(claims["uid"])
        key = "identity:" + token_hash(uid)
        value, version = store.state(key)
        if value:
            return store.user(id=value["tenant"])
        # UID is the durable identity. A new UID must not inherit a former account
        # merely because a deleted/reassigned email address now verifies again.
        email = str(claims["email"]).lower()
        email_key = "identity-email:" + token_hash(email)
        binding, binding_version = store.state(email_key)
        account = store.user(email=email)
        if binding and binding.get("uid") != uid:
            return None
        if account is not None and not binding:
            return None  # Legacy accounts require an explicit operator migration.
        if not binding:
            if not store.save_state(email_key, {"uid": uid}, binding_version):
                binding, _ = store.state(email_key)
                if binding.get("uid") != uid:
                    return None
        if account is None:
            try:
                account, _ = store.create_user(email, "!federated-only")
            except Exception:
                account = store.user(email=email)
                if account is None:
                    raise
        if not store.save_state(key, {"tenant": account.id}, version):
            value, _ = store.state(key)
            return store.user(id=value["tenant"])
        return account
    except (
        ValueError,
        auth.InvalidIdTokenError,
        auth.RevokedIdTokenError,
        auth.UserDisabledError,
        auth.UserNotFoundError,
        auth.CertificateFetchError,
    ):
        return None


def managed_spec(spec: ProjectSpec, settings: Settings) -> ProjectSpec:
    """Server-side defaults are authoritative, including non-UI API clients."""
    if spec.local_path or (spec.publishing_platform == "github" and not spec.repository):
        raise HTTPException(400, "Connect a GitHub repository for the hosted workspace")
    if not settings.managed_key:
        raise HTTPException(503, "Managed inference has not been configured")
    return spec.model_copy(
        update={
            "provider": ProviderConfig(
                kind=cast(
                    Literal["rules", "ollama", "openai", "anthropic", "google"],
                    settings.managed_provider,
                ),
                model=settings.managed_model,
                max_output_tokens=8192,
                capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
            ),
            "max_pages": min(spec.max_pages, 25),
            "max_files_changed": min(spec.max_files_changed, 5),
            "max_tool_steps": min(spec.max_tool_steps, 6),
            "max_cost_usd": min(spec.max_cost_usd, 2),
            "max_job_seconds": min(spec.max_job_seconds, 480),
            "reconcile_seconds": max(spec.reconcile_seconds, 86400),
            "auto_merge": False,
        }
    )


def grant_token(store: Store, tenant: str, settings: Settings) -> str:
    key = "github-grant:" + tenant
    grant, version = store.state(key)
    if not grant:
        raise HTTPException(409, "Connect GitHub first")
    if grant.get("expires", 0) > time.time() + 60:
        return str(grant["token"])
    if not grant.get("refresh") or grant.get("refresh_expires", 0) < time.time():
        raise HTTPException(409, "Reconnect GitHub to refresh repository access")
    with httpx.Client(timeout=20) as client:
        result = client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": grant["refresh"],
            },
        )
        result.raise_for_status()
        body = result.json()
    if not body.get("access_token"):
        raise HTTPException(409, "GitHub access expired; reconnect")
    grant.update(
        token=body["access_token"],
        expires=time.time() + int(body.get("expires_in", 28800)),
        refresh=body.get("refresh_token", ""),
        refresh_expires=time.time() + int(body.get("refresh_token_expires_in", 0)),
    )
    if not store.save_state(key, grant, version):
        raise HTTPException(409, "Connection changed; retry")
    return str(grant["token"])


def verified_repositories(store: Store, tenant: str, settings: Settings) -> dict[str, Any]:
    """Refresh repository grants from GitHub; never extend an old cached permission."""
    token = grant_token(store, tenant, settings)
    result = []
    with GitHubConnectionClient(token) as client:
        installations = client.get("/user/installations", "installations")
        for installation in installations:
            if str(installation.get("app_id")) != settings.github_app_id or installation.get(
                "suspended_at"
            ):
                continue
            for repo in client.get(
                f"/user/installations/{installation['id']}/repositories", "repositories"
            ):
                if repo.get("archived") or not repo.get("permissions", {}).get("push"):
                    continue
                key = "github-repo:" + tenant + ":" + repo["full_name"]
                _, version = store.state(key)
                store.save_state(
                    key,
                    {
                        "installation": installation["id"],
                        "repo_id": repo["id"],
                        "until": time.time() + 300,
                    },
                    version,
                )
                result.append(
                    {
                        "repository": repo["full_name"],
                        "branch": repo["default_branch"],
                        "private": repo["private"],
                    }
                )
    return {"repositories": result}


def connected_create(
    value: ProjectCreate, tenant: str, store: Store, settings: Settings
) -> ProjectCreate:
    spec = managed_spec(value.spec, settings)
    if spec.publishing_platform != "github":
        if spec.repository:
            raise HTTPException(400, "Choose one publishing platform per project")
        return ProjectCreate(spec=spec)
    grant_token(store, tenant, settings)  # A cached repository cannot revive a disconnected grant.
    connection, _ = store.state("github-repo:" + tenant + ":" + spec.repository)
    if not connection or connection.get("until", 0) < time.time():
        try:
            refreshed = verified_repositories(store, tenant, settings)
        except httpx.HTTPError:
            raise HTTPException(
                502, "GitHub access could not be verified. Please try again shortly."
            ) from None
        if not any(row["repository"] == spec.repository for row in refreshed["repositories"]):
            raise HTTPException(
                409,
                "GitHub no longer grants access to this repository. "
                "Check the app installation and repository permissions.",
            )
        connection, _ = store.state("github-repo:" + tenant + ":" + spec.repository)
        if not connection or connection.get("until", 0) < time.time():
            raise HTTPException(
                409, "Repository access changed. Refresh repositories and try again."
            )
    credentials = ProjectSecrets(github_installation_id=str(connection["installation"]))
    return ProjectCreate(spec=spec, credentials=credentials)


def install_routes(app: FastAPI, store: Store, settings: Settings, authenticate: Any) -> None:
    @app.get("/api/v1/account")
    def account(request: Request) -> dict[str, Any]:
        user = authenticate(request)
        month = datetime.now(UTC).strftime("%Y-%m")
        usage, _ = store.state(f"usage:{user.id}:{month}")
        grant, _ = store.state("github-grant:" + user.id)
        connection = "not_connected"
        if grant.get("token"):
            renewable = grant.get("refresh") and grant.get("refresh_expires", 0) > time.time()
            connection = (
                "connected"
                if grant.get("expires", 0) > time.time() + 60 or renewable
                else "reconnect_required"
            )
        return {
            "email": user.email,
            "mode": "hosted" if settings.hosted else "local",
            "tier": "free" if settings.hosted else "self-hosted",
            "month": month,
            "jobs_used": len(usage.get("jobs", [])),
            "job_limit": settings.free_jobs_per_month if settings.hosted else None,
            "project_limit": settings.free_projects if settings.hosted else 20,
            "github_connection": {
                "status": connection,
                "login": grant.get("login") if connection != "not_connected" else None,
            },
            "github_install_url": "https://github.com/apps/"
            + settings.github_app_slug
            + "/installations/new"
            if settings.github_app_slug
            else None,
        }

    @app.get("/api/v1/projects/{id}/activity")
    def activity(request: Request, id: str) -> dict[str, Any]:
        user = authenticate(request)
        if store.project(user.id, id) is None:
            raise HTTPException(404, "Project not found")
        from seo_optimizer.web import job_json

        return {
            "jobs": [job_json(job, hosted=settings.hosted) for job in store.jobs(user.id, id)],
            "findings": [
                {"id": finding.id, "active": finding.active, "details": finding.details}
                for finding in store.findings(user.id, id)
            ],
        }

    def begin_connection(request: Request, installation: bool = False) -> dict[str, str]:
        user = authenticate(request)
        if not settings.github_client_id or not settings.github_client_secret:
            raise HTTPException(503, "GitHub App OAuth is not configured")
        if installation and not settings.github_app_slug:
            raise HTTPException(503, "GitHub App installation is not configured")
        state = secrets.token_urlsafe(32)
        store.save_state(
            "oauth:" + token_hash(state), {"tenant": user.id, "until": time.time() + 600}, 0
        )
        if installation:
            return {
                "url": "https://github.com/apps/"
                + settings.github_app_slug
                + "/installations/new?"
                + urlencode({"state": state})
            }
        return {
            "url": "https://github.com/login/oauth/authorize?"
            + urlencode(
                {
                    "client_id": settings.github_client_id,
                    "state": state,
                    "redirect_uri": settings.public_url.rstrip("/") + "/api/v1/github/callback",
                }
            )
        }

    @app.post("/api/v1/github/connect")
    def connect(request: Request) -> dict[str, str]:
        return begin_connection(request)

    @app.post("/api/v1/github/install")
    def install(request: Request) -> dict[str, str]:
        return begin_connection(request, installation=True)

    @app.get("/api/v1/github/callback")
    def callback(code: str = "", state: str = "") -> RedirectResponse:
        key = "oauth:" + token_hash(state)
        record, version = store.state(key)
        if not record or record.get("until", 0) < time.time() or not code:
            raise HTTPException(400, "Connection expired; start again")
        if not store.save_state(key, {}, version):
            raise HTTPException(409, "Connection callback was already used")
        with httpx.Client(timeout=20) as client:
            response = client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.public_url.rstrip("/") + "/api/v1/github/callback",
                },
            )
            response.raise_for_status()
            body = response.json()
            if not body.get("access_token"):
                raise HTTPException(400, "GitHub did not grant access")
            identity = client.get(
                "https://api.github.com/user",
                headers={"Authorization": "Bearer " + body["access_token"]},
            )
            identity.raise_for_status()
        grant_key = "github-grant:" + record["tenant"]
        _, grant_version = store.state(grant_key)
        store.save_state(
            grant_key,
            {
                "token": body["access_token"],
                "refresh": body.get("refresh_token", ""),
                "expires": time.time() + int(body.get("expires_in", 28800)),
                "refresh_expires": time.time() + int(body.get("refresh_token_expires_in", 0)),
                "login": identity.json()["login"],
            },
            grant_version,
        )
        return RedirectResponse(
            settings.frontend_url + "/dashboard?github=connected", status_code=303
        )

    @app.get("/api/v1/github/repositories")
    def repositories(request: Request) -> dict[str, Any]:
        user = authenticate(request)
        return verified_repositories(store, user.id, settings)

    @app.delete("/api/v1/github/connect")
    def disconnect(request: Request) -> dict[str, str]:
        user = authenticate(request)
        key = "github-grant:" + user.id
        _, version = store.state(key)
        store.save_state(key, {}, version)
        for project in store.projects(user.id):
            spec = ProjectSpec.model_validate(project.spec)
            if spec.repository:
                spec.enabled = False
                credentials = store.secrets(project)
                credentials.github_installation_id = ""
                credentials.github_token = ""
                store.update_project(user.id, project.id, spec, credentials)
                repo_key = "github-repo:" + user.id + ":" + spec.repository
                _, repo_version = store.state(repo_key)
                store.save_state(repo_key, {}, repo_version)
        return {"status": "disconnected", "projects": "paused"}


class GitHubConnectionClient:
    def __init__(self, token: str):
        self.client = GitHubClient(ProjectSecrets(github_token=token))

    def __enter__(self) -> "GitHubConnectionClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.client.close()

    def get(self, path: str, field: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for page in range(1, 11):
            body = self.client.request("GET", path, params={"per_page": 100, "page": page})
            result.extend(body.get(field, []))
            if len(body.get(field, [])) < 100:
                return result
        raise HTTPException(
            409, "Connection is too broad; select fewer repositories in the GitHub App"
        )
