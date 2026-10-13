"""Matched repository-repair experiment. Development fixture; never a search-uplift test."""

import hashlib
import json
import secrets
import shutil
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Literal

from dotenv import dotenv_values
from pydantic import HttpUrl
from sqlalchemy import update

from seo_optimizer.application_models import (
    ProjectCreate,
    ProjectSecrets,
    ProjectSpec,
    ProviderConfig,
)
from seo_optimizer.contracts import ProviderCapabilities, TrustedFact, WebsiteType, utc_now
from seo_optimizer.execution import run_git
from seo_optimizer.settings import Settings
from seo_optimizer.store import Job, Project, Store
from seo_optimizer.web import hash_password
from seo_optimizer.worker import Worker


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass


def grade(repository: Path) -> dict[str, Any]:
    import re

    home = (repository / "web/index.html").read_text()
    product = (repository / "web/products/cedar-lamp/index.html").read_text()
    canonicals = re.findall(r'<link\b[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', product)
    offer: dict[str, Any] = {}
    try:
        script = re.search(r'<script type="application/ld\+json">(.*?)</script>', product, re.S)
        offer = json.loads(script[1])["offers"] if script else {}
    except (ValueError, KeyError, TypeError):
        pass
    checks = {
        "description": bool(
            re.search(
                r'<meta\b[^>]*name=["\']description["\'][^>]*content=["\'][^"\']{40,180}["\']', home
            )
        ),
        "navigation": 'href="/collections/lighting/"' not in home and 'href="/shop/"' in home,
        "canonical": len(canonicals) == 1 and canonicals[0].endswith("/products/cedar-lamp/"),
        "product_offer": (
            offer.get("price") in {"89", "89.00", 89}
            and offer.get("priceCurrency") == "USD"
            and offer.get("availability") == "https://schema.org/InStock"
        ),
    }
    protected = all(
        (repository / target).read_text() == (repository / original).read_text()
        for target, original in [
            ("web/preview/index.html", "protected-preview.txt"),
            ("web/robots.txt", "protected-robots.txt"),
        ]
    )
    return {
        "checks": checks,
        "verified_fixes": sum(checks.values()),
        "protected_files_unchanged": protected,
    }


def healthy_sources(repository: Path, origin: str) -> None:
    home_path = repository / "web/index.html"
    home = home_path.read_text().replace('href="/collections/lighting/"', 'href="/shop/"')
    home = home.replace(
        "</head>",
        '<meta name="description" content="Cedar Workshop lighting: '
        'a solid cedar desk lamp with a linen shade and warm 2700K light.">\n</head>',
    )
    home_path.write_text(home)
    product_path = repository / "web/products/cedar-lamp/index.html"
    product = (
        product_path.read_text()
        .replace(f'<link rel="canonical" href="{origin}/shop/">\n', "")
        .replace('"price":"129.00"', '"price":"89.00"')
        .replace('"InStock",}', '"InStock"}')
    )
    product = product.replace('"https://schema.org/InStock",}', '"https://schema.org/InStock"}')
    product_path.write_text(product)


def benchmark_repairs(
    fixture: Path,
    output: Path,
    local_model: str,
    paid_model: str,
    arms: list[str] | None = None,
    resume: bool = False,
    controls_only: bool = False,
) -> int:
    output = output.resolve()
    fixture = fixture.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    previous = json.loads(output.read_text()) if resume else None
    root = output.parent / (
        previous["workspace_id"] if previous else "repair-work-" + secrets.token_hex(6)
    )
    if root.parent != output.parent or not root.name.startswith("repair-work-"):
        raise ValueError("Benchmark workspace must remain inside its output directory")
    repository = root / "repository"
    if not previous:
        shutil.copytree(fixture, repository)
    server = ThreadingHTTPServer(
        ("127.0.0.1", previous["fixture_port"] if previous else 0),
        partial(QuietHandler, directory=str(repository / "web")),
    )
    # Reserve the original fixture port before mutating a resumed repository.
    # An active run owns both the server and the repository.
    if previous:
        run_git(repository, "reset", "--hard", previous["base_sha"])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    for path in (repository / "web").rglob("*.html"):
        path.write_text(path.read_text().replace("__ORIGIN__", origin))
    if not previous:
        run_git(repository, "init", "-b", "main")
    identity = [
        "-c",
        "user.name=Benchmark Fixture",
        "-c",
        "user.email=fixture@localhost",
        "-c",
        "commit.gpgsign=false",
    ]
    if not previous:
        run_git(repository, "add", ".")
        run_git(repository, *identity, "commit", "-m", "Freeze repair inputs")
    base = run_git(repository, "rev-parse", "HEAD")
    digest = hashlib.sha256(
        "".join(
            f"{p.relative_to(repository)}\n{p.read_text()}"
            for p in sorted(repository.rglob("*"))
            if p.is_file() and ".git" not in p.parts
        ).encode()
    ).hexdigest()
    if previous and (base != previous["base_sha"] or digest != previous["fixture_sha256"]):
        raise ValueError("Frozen benchmark inputs changed")
    values = dotenv_values(".env")
    key = values.get("GOOGLE_API_KEY") or values.get("GEMINI_API_KEY") or ""
    chosen = arms or ["rules", "local-minimal", "local-full", "paid-minimal", "paid-full"]
    report: dict[str, Any] = previous or {
        "version": "1",
        "generated_at": utc_now().isoformat(),
        "base_sha": base,
        "fixture_sha256": digest,
        "fixture": "fictional-store-development",
        "workspace_id": root.name,
        "fixture_port": server.server_port,
        "protocol": {
            "shared": {
                "max_tool_steps": 12,
                "max_output_tokens": 8192,
                "max_total_tokens": 150000,
                "max_calls_per_step": 16,
                "max_job_seconds": 600,
                "temperature": 0,
                "tools": "read source, inspect route, stage patch, isolated checks, diff",
                "policy": "same path, fact, behavior, private page and crawler guards",
            },
            "full": "Private skill, relevant references, rule findings, on-demand check tool",
            "minimal": "Common safety/task prompt; no skill, rule hints, check retrieval "
            "or strategy",
            "local_context_tokens": 16384,
            "caveats": [
                "One development repair case and healthy/irrelevant controls; no held-out "
                "generalization claim",
                "Providers have different context/tokenizers and "
                "hardware; recorded caps do not equalize native compute",
            ],
        },
        "arms": [],
        "unverified": [
            "Search ranking, live-engine citations, conversions and production GitHub",
            "Paid cost without configured rates; local hardware/electricity costs",
        ],
    }
    verified_at = utc_now()
    facts = [
        TrustedFact(
            id="product",
            name="Product offer and details",
            value="Cedar Desk Lamp; solid cedar base, linen shade, warm 2700K light; "
            "in stock at USD 89.00",
            source="Frozen synthetic owner fixture",
            verified_at=verified_at,
        )
    ]
    if previous:
        facts = [TrustedFact.model_validate(value) for value in previous["trusted_facts"]]
    report["trusted_facts"] = [fact.model_dump(mode="json") for fact in facts]
    try:
        for arm in chosen:
            prior = next((record for record in report["arms"] if record["arm"] == arm), None)
            if prior and not controls_only:
                raise ValueError(
                    "A benchmark arm already ran; retain it and use a new run for repeats"
                )
            if controls_only and not prior:
                raise ValueError("Controls-only requires a recorded repair attempt")
            if arm not in {"rules", "local-minimal", "local-full", "paid-minimal", "paid-full"}:
                raise ValueError("Unknown benchmark arm")
            print(f"RUN {arm}: frozen repository {base[:12]}", flush=True)
            run_git(repository, "reset", "--hard", base)
            # The directory is generated solely for this benchmark; never clean a user's repo.
            run_git(repository, "clean", "-fd")
            run_id = arm + ("-controls-" + secrets.token_hex(4) if controls_only else "")
            settings = Settings(
                data_dir=root / run_id,
                database_url=f"sqlite:///{root}/{run_id}.sqlite",
                secret_key=secrets.token_urlsafe(48),
                allowed_repo_roots=(root,),
            )
            settings.data_dir.mkdir()
            store = Store(settings)
            user, _ = store.create_user(
                "benchmark@example.test", hash_password(secrets.token_urlsafe(20))
            )
            kind: Literal["rules", "ollama", "google"] = (
                "rules" if arm == "rules" else "ollama" if arm.startswith("local") else "google"
            )
            spec = ProjectSpec(
                name="Anonymous repository benchmark",
                website_url=HttpUrl(origin + "/"),
                local_path=str(repository),
                allowed_paths=["web"],
                route_map={
                    "/": "web/index.html",
                    "/shop/": "web/shop/index.html",
                    "/products/cedar-lamp/": "web/products/cedar-lamp/index.html",
                    "/preview/": "web/preview/index.html",
                },
                page_intents={"/preview/": False, "/collections/lighting/": False},
                crawler_preferences={"GPTBot": "block", "OAI-SearchBot": "allow"},
                website_types=[WebsiteType.GENERIC, WebsiteType.ECOMMERCE],
                facts=facts,
                goals=[
                    "Fix confirmed metadata, canonical, JSON-LD offer and broken navigation "
                    "using observed pages and verified facts. Preserve healthy pages, "
                    "private preview, training opt-out and other product behavior."
                ],
                auto_fix=True,
                allow_content_publication=True,
                browser_enabled=True,
                max_pages=6,
                max_tool_steps=12,
                max_job_seconds=600,
                check_commands=[["python", "verify_site.py"]],
                provider=ProviderConfig(
                    kind=kind,
                    model=local_model
                    if kind == "ollama"
                    else paid_model
                    if kind == "google"
                    else "",
                    capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
                    max_output_tokens=8192,
                    max_total_tokens=150000,
                    max_calls_per_step=16,
                    request_timeout_seconds=180,
                    ollama_num_ctx=16384,
                ),
            )
            project = store.create_project(
                user.id,
                ProjectCreate(
                    spec=spec,
                    credentials=ProjectSecrets(provider_key=key if kind == "google" else ""),
                ),
            )
            worker = Worker(store, settings, use_knowledge=not arm.endswith("minimal"))
            started = time.monotonic()
            if controls_only:
                with store.sessions.begin() as session:
                    session.execute(
                        update(Job)
                        .where(Job.project_id == project.id)
                        .values(
                            status="canceled",
                        )
                    )
            else:
                worker.tick(user.id)
            job = store.jobs(user.id, project.id)[0]
            if job.status == "queued":
                # Each scenario measures one bounded attempt. A deferred retry must not
                # steal the following healthy or irrelevant control's worker claim.
                with store.sessions.begin() as session:
                    session.execute(update(Job).where(Job.id == job.id).values(status="failed"))
            repaired = grade(repository)
            paths = run_git(repository, "diff", "--name-only", base, "HEAD").splitlines()
            outcome: dict[str, Any] = prior or {
                "arm": arm,
                "provider": kind,
                "model": spec.provider.model or "rules",
                "repair": {"status": job.status, "result": job.result},
                "observed": repaired,
                "changed_paths": paths,
                "runtime_seconds": round(time.monotonic() - started, 3),
                "justified_changed_files": len(
                    set(paths) & {"web/index.html", "web/products/cedar-lamp/index.html"}
                ),
                "unnecessary_changes": len(
                    set(paths) - {"web/index.html", "web/products/cedar-lamp/index.html"}
                ),
                "repair_passed": job.status == "complete"
                and repaired["verified_fixes"] == 4
                and repaired["protected_files_unchanged"],
            }
            if controls_only:
                outcome.setdefault("control_attempts", []).append(
                    {
                        "healthy_control": outcome.get("healthy_control"),
                        "irrelevant_control": outcome.get("irrelevant_control"),
                        "valid": False,
                        "reason": "Concurrent resume attempt reset the fixture during the controls",
                    }
                )
            else:
                print(
                    f"RESULT {arm}: {repaired['verified_fixes']}/4 repairs; {job.status}",
                    flush=True,
                )
                report["arms"].append(outcome)
            output.write_text(json.dumps(report, indent=2) + "\n")
            # Independently authored healthy fixture, even when the repair attempt failed.
            run_git(repository, "reset", "--hard", base)
            healthy_sources(repository, origin)
            if grade(repository)["verified_fixes"] != 4:
                raise ValueError("Healthy benchmark control is invalid")
            run_git(repository, "add", "web/index.html")
            run_git(repository, *identity, "commit", "-m", "Add healthy metadata")
            run_git(repository, "add", "web/products/cedar-lamp/index.html")
            run_git(repository, *identity, "commit", "-m", "Add healthy product")
            healthy_sha = run_git(repository, "rev-parse", "HEAD")
            store.enqueue(user.id, project.id, "audit", "healthy-control", {})
            started = time.monotonic()
            worker.tick(user.id)
            healthy = store.jobs(user.id, project.id)[0]
            if healthy.status == "queued":
                with store.sessions.begin() as session:
                    session.execute(update(Job).where(Job.id == healthy.id).values(status="failed"))
            changed = run_git(repository, "rev-parse", "HEAD") != healthy_sha
            outcome["healthy_control"] = {
                "passed": healthy.status == "complete" and not changed,
                "status": healthy.status,
                "changed": changed,
                "result": healthy.result,
                "runtime_seconds": round(time.monotonic() - started, 3),
                "base_sha": healthy_sha,
                "observed_sha": run_git(repository, "rev-parse", "HEAD"),
                "diff": run_git(repository, "diff", healthy_sha, "HEAD"),
            }
            # The merged-docs scenario starts from a separately established healthy
            # baseline. A failed healthy audit must not make website changes appear
            # to be part of the documentation-only merge.
            run_git(repository, "reset", "--hard", healthy_sha)
            with store.sessions.begin() as session:
                session.execute(
                    update(Project)
                    .where(Project.id == project.id)
                    .values(
                        last_revision=healthy_sha,
                    )
                )
            run_git(repository, "checkout", "-b", "docs-" + arm)
            (repository / "README.md").write_text("Anonymous benchmark documentation.\n")
            run_git(repository, "add", "README.md")
            run_git(repository, *identity, "commit", "-m", "Document fixture")
            run_git(repository, "checkout", "main")
            run_git(repository, *identity, "merge", "--no-ff", "docs-" + arm, "-m", "Merge docs")
            store.enqueue(
                user.id,
                project.id,
                "push",
                "docs-control",
                {"after": run_git(repository, "rev-parse", "HEAD")},
            )
            worker.tick(user.id)
            irrelevant = store.jobs(user.id, project.id)[0]
            outcome["irrelevant_control"] = {
                "passed": irrelevant.status == "complete"
                and "No affected website routes" in irrelevant.result.get("summary", ""),
                "result": irrelevant.result,
            }
            store.engine.dispose()
            output.write_text(json.dumps(report, indent=2) + "\n")
        report["counts"] = {
            "passed_repairs": sum(a["repair_passed"] for a in report["arms"]),
            "failed_repairs": sum(not a["repair_passed"] for a in report["arms"]),
            "passed_controls": sum(
                a[k]["passed"]
                for a in report["arms"]
                for k in ["healthy_control", "irrelevant_control"]
            ),
        }
    finally:
        server.shutdown()
        server.server_close()
        output.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report.get("counts", {}).get("failed_repairs") == 0 else 1
