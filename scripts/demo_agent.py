"""Run and record a real model repair on a fictional store; no personal repository data."""

import argparse
import difflib
import importlib.metadata
import json
import secrets
import shutil
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
from playwright.sync_api import sync_playwright

import seo_optimizer.worker as worker_module
from seo_optimizer.application_models import (
    ProjectCreate,
    ProjectSecrets,
    ProjectSpec,
    ProviderConfig,
)
from seo_optimizer.contracts import ProviderCapabilities, TrustedFact, utc_now
from seo_optimizer.execution import run_git
from seo_optimizer.llm import ModelClient
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import hash_password

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["google", "ollama"], default="google")
    parser.add_argument("--model", default="gemini-3.8-flash")
    parser.add_argument("--output", type=Path, default=ROOT / "videos/public/agent-run.json")
    args = parser.parse_args()
    values = dotenv_values(ROOT / ".env")
    key = values.get("GOOGLE_API_KEY") or values.get("GEMINI_API_KEY") or ""
    if args.provider == "google" and not key:
        parser.error("GOOGLE_API_KEY or GEMINI_API_KEY is required in the ignored .env")
    assets = args.output.parent
    assets.mkdir(parents=True, exist_ok=True)
    working = ROOT / ".data/agent-demo" / uuid4().hex
    repository = working / "repository"
    shutil.copytree(ROOT / "tests/fixtures/agent_site", repository)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Handler, directory=str(repository / "web"))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    for path in (repository / "web").rglob("*.html"):
        path.write_text(path.read_text().replace("__ORIGIN__", origin))
    run_git(repository, "init", "-b", "main")
    run_git(repository, "add", ".")
    run_git(
        repository,
        "-c",
        "user.name=Demo Fixture",
        "-c",
        "user.email=fixture@localhost",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "Add synthetic store",
    )
    base_sha = run_git(repository, "rev-parse", "HEAD")
    settings = Settings(
        data_dir=working / "control",
        database_url=f"sqlite:///{working}/control.db",
        secret_key=secrets.token_urlsafe(48),
        allowed_repo_roots=(working,),
    )
    settings.data_dir.mkdir()
    store = Store(settings)
    user, _ = store.create_user(
        "synthetic@localhost.test", hash_password(secrets.token_urlsafe(24))
    )
    facts = [
        TrustedFact(
            id="brand",
            name="Store name",
            value="Cedar Workshop",
            source="Synthetic owner fixture",
            verified_at=utc_now(),
        ),
        TrustedFact(
            id="product",
            name="Product details",
            value="Cedar Desk Lamp; solid cedar base, linen shade, warm 2700K light",
            source="Synthetic owner fixture",
            verified_at=utc_now(),
        ),
        TrustedFact(
            id="price",
            name="Product offer",
            value="Cedar Desk Lamp is in stock at USD 89.00",
            source="Synthetic owner fixture",
            verified_at=utc_now(),
        ),
        TrustedFact(
            id="shop",
            name="Collection destination",
            value=origin + "/shop/",
            source="Observed working collection route",
            verified_at=utc_now(),
        ),
    ]
    spec = ProjectSpec(
        name="Cedar Workshop demonstration",
        website_url=origin + "/",
        local_path=str(repository),
        allowed_paths=["web"],
        route_map={
            "/": "web/index.html",
            "/shop/": "web/shop/index.html",
            "/products/cedar-lamp/": "web/products/cedar-lamp/index.html",
            "/preview/": "web/preview/index.html",
        },
        website_types=["generic", "ecommerce"],
        page_intents={"/preview/": False, "/collections/lighting/": False},
        crawler_preferences={"GPTBot": "block", "OAI-SearchBot": "allow"},
        facts=facts,
        goals=[
            "Repair confirmed metadata, canonical, structured-data and internal-link defects "
            "using observed pages and trusted facts. Product offer must match visible USD "
            "89.00, not the erroneous declaration. Preserve adequate content, all behavior "
            "except the evidenced broken link, intentional private preview and training "
            "opt-out. Inspect actual files, stage combined fixes and check them."
        ],
        auto_fix=False,
        auto_merge=True,
        allow_content_publication=True,
        max_pages=6,
        max_tool_steps=12,
        max_job_seconds=600,
        check_commands=[["python", "verify_site.py"]],
        sandbox_image="python:3.12-slim",
    )
    project = store.create_project(
        user.id, ProjectCreate(spec=spec, credentials=ProjectSecrets(provider_key=key))
    )
    worker = worker_module.Worker(store, settings)
    worker.tick(user.id)
    baseline = store.jobs(user.id, project.id)[0]
    assert baseline.status == "complete", baseline.result
    report = {
        "generated_at": utc_now().isoformat(),
        "fictional_site": "Cedar Workshop",
        "provider": args.provider,
        "model": args.model,
        "sdk_version": importlib.metadata.version("google-genai")
        if args.provider == "google"
        else None,
        "base_sha": base_sha,
        "baseline": baseline.result,
        "events": [],
        "requests": 0,
        "github_writes": False,
        "model_used": True,
        "status": "running",
    }
    started = time.monotonic()

    def event(text):
        print(text, flush=True)
        report["events"].append({"time": time.monotonic() - started, "text": text})

    class ObservedClient(ModelClient):
        def _post(self, path, payload, headers):
            report["requests"] += 1
            event(f"MODEL {args.model} request {report['requests']} — actual inference")
            result = super()._post(path, payload, headers)
            usage = result.get("usageMetadata", {})
            report.setdefault("request_usage", []).append(usage)
            return result

        def complete(self, instructions, request, tools, execute, *rest):
            def observed(name, arguments):
                path = arguments.get("path", arguments.get("url", ""))
                event(f"TOOL {name} {path}")
                if name == "apply_patch":
                    delta = "\n".join(
                        difflib.unified_diff(
                            arguments["before"].splitlines(),
                            arguments["after"].splitlines(),
                            fromfile="before/" + path,
                            tofile="after/" + path,
                            lineterm="",
                        )
                    )
                    event(delta)
                result = execute(name, arguments)
                event(
                    f"RESULT {name}: "
                    + json.dumps(
                        {
                            k: v
                            for k, v in result.items()
                            if k not in {"text", "html", "data", "check"}
                        }
                    )
                )
                return result

            return super().complete(instructions, request, tools, observed, *rest)

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    def film(browser, name, before):
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(working / "raw"),
            record_video_size={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.goto(origin + "/")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(assets / f"{name}-home.png"))
        page.locator("main .button").click()
        page.wait_for_timeout(1500)
        page.screenshot(path=str(assets / f"{name}-navigation.png"))
        if not before:
            assert page.url == origin + "/shop/"
            page.locator(".card").click()
            page.wait_for_timeout(1600)
        else:
            assert page.locator("body").inner_text().find("404") >= 0
            page.goto(origin + "/products/cedar-lamp/")
            page.wait_for_timeout(1200)
        page.screenshot(path=str(assets / f"{name}-product.png"))
        video = page.video
        context.close()
        video.save_as(str(assets / f"{name}.webm"))

    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="chromium")
        film(browser, "before", True)
        original_client = worker_module.ModelClient
        worker_module.ModelClient = ObservedClient
        try:
            spec.auto_fix = True
            spec.provider = ProviderConfig(
                kind=args.provider,
                model=args.model,
                capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
                max_output_tokens=8192,
                max_total_tokens=150_000,
                max_calls_per_step=16,
                request_timeout_seconds=180,
                ollama_num_ctx=16384,
            )
            store.update_project(user.id, project.id, spec)
            event("START: autonomous model repair on a synthetic local Git repository")
            store.enqueue(user.id, project.id, "audit", "model-repair", {})
            worker.tick(user.id)
            job = store.jobs(user.id, project.id)[0]
            report["repair"] = {"status": job.status, "result": job.result}
            event("WORKER " + job.status + ": " + job.result.get("summary", ""))
            save()
            assert job.status == "complete" and job.result.get("stage") == "verified", (
                job.result.get("summary")
            )
            trace = job.result["report"]["tool_trace"]
            names = {item["name"] for item in trace if item["success"]}
            assert {"read_file", "apply_patch", "run_checks"}.issubset(names)
            assert any(
                item["name"] == "run_checks" and item["result"]["scope"] == "staged_proposals"
                for item in trace
            )
            merged = run_git(repository, "rev-parse", "HEAD")
            report["merged_sha"] = merged
            report["diff"] = run_git(repository, "diff", base_sha, merged)
            report["changed_paths"] = run_git(
                repository, "diff", "--name-only", base_sha, merged
            ).splitlines()
            assert report["changed_paths"] == [
                "web/index.html",
                "web/products/cedar-lamp/index.html",
            ]
            assert (repository / "web/robots.txt").read_text() == (
                repository / "protected-robots.txt"
            ).read_text()
            assert (repository / "web/preview/index.html").read_text() == (
                repository / "protected-preview.txt"
            ).read_text()
            report["repair_requests"] = report["requests"]
            event("PUBLISHED LOCALLY: two files, one file per commit; post-merge pages verified")
            film(browser, "after", False)
            event("CONTROL: repeat the real model audit on the repaired site")
            store.enqueue(user.id, project.id, "audit", "repeat-model-audit", {})
            worker.tick(user.id)
            repeated = store.jobs(user.id, project.id)[0]
            assert repeated.status == "complete", repeated.result.get("summary")
            assert run_git(repository, "rev-parse", "HEAD") == merged
            report["repeat"] = {
                "status": repeated.status,
                "result": repeated.result,
                "created_commit": False,
            }
            event("REPEAT: model audit completed; no new edit or commit")
            run_git(repository, "checkout", "-b", "feature/docs-only")
            (repository / "README.md").write_text("Fictional storefront integration fixture.\n")
            run_git(repository, "add", "README.md")
            identity = [
                "-c",
                "user.name=Demo Fixture",
                "-c",
                "user.email=fixture@localhost",
                "-c",
                "commit.gpgsign=false",
            ]
            run_git(repository, *identity, "commit", "-m", "Document fixture")
            run_git(repository, "checkout", "main")
            run_git(
                repository,
                *identity,
                "merge",
                "--no-ff",
                "feature/docs-only",
                "-m",
                "Merge documentation branch",
            )
            requests_before = report["requests"]
            store.enqueue(
                user.id,
                project.id,
                "push",
                "merged-docs-event",
                {"after": run_git(repository, "rev-parse", "HEAD")},
            )
            worker.tick(user.id)
            irrelevant = store.jobs(user.id, project.id)[0]
            assert (
                irrelevant.status == "complete"
                and "No affected website routes" in irrelevant.result["summary"]
            )
            assert report["requests"] == requests_before
            report["merged_docs_event"] = {
                "status": irrelevant.status,
                "result": irrelevant.result,
                "inference_requests": 0,
            }
            event("MERGED DOCS BRANCH: no affected routes; zero inference requests")
            report["before_defects"] = len(baseline.result["before_defects"])
            report["after_defects"] = sum(
                item["status"] == "defect" for item in job.result["findings"]
            )
            report["protected_files_unchanged"] = True
            report["model_tool_calls"] = len(trace)
            report["runtime_seconds"] = time.monotonic() - started
            report["status"] = "passed"
            event(
                f"DEFECTS: {report['before_defects']} → {report['after_defects']}; "
                f"{len(trace)} real model tool calls"
            )
        except Exception as error:
            report["status"] = "failed"
            report["failure"] = type(error).__name__
            event("DEMO FAILED: " + type(error).__name__ + " — see preserved result")
        finally:
            worker_module.ModelClient = original_client
            browser.close()
            server.shutdown()
            server.server_close()
            store.engine.dispose()
            save()
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
