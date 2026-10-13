"""Record real autonomous strategy/content publication on an anonymous local fixture."""

import difflib
import json
import secrets
import shutil
import socket
import threading
import time
from datetime import timedelta
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import uvicorn
from playwright.sync_api import sync_playwright

from seo_optimizer.application_models import ProjectCreate, ProjectSpec
from seo_optimizer.contracts import TrustedFact, utc_now
from seo_optimizer.execution import run_git
from seo_optimizer.growth import Material, SearchObservation, Workspace, plan
from seo_optimizer.repair_benchmark import QuietHandler
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import create_app, hash_password
from seo_optimizer.worker import Worker

ROOT = Path(__file__).resolve().parents[1]
PASSAGE = (
    "In our fictional desk setup study, we placed the Cedar Desk Lamp 45 cm from the reading "
    "surface. The linen shade softened the light on the page while the solid cedar base "
    "kept the lamp steady. These are owner-supplied demonstration observations, not a real "
    "lighting study or a promised health benefit."
)


def main():
    root = ROOT / ".data/growth-demo" / uuid4().hex
    repository = root / "repository"
    (repository / "web/guide").mkdir(parents=True)
    assets = ROOT / "videos/public"
    shutil.copy(ROOT / "tests/fixtures/agent_site/web/style.css", repository / "web/style.css")
    (repository / "web/index.html").write_text(
        '<html lang="en"><head><meta charset="utf-8"><title>Cedar Workshop guide</title>'
        '<meta name="description" content="Cedar Workshop original desk lighting guide">'
        '<link rel="stylesheet" href="/style.css"></head><body><header><a class="brand" href="/">'
        'Cedar Workshop</a><nav><a href="/guide/">Desk guide</a></nav></header><main><section '
        'class="hero"><div><div class="eyebrow">A useful next page</div><h1>A quieter<br>desk.</h1>'
        '<p>Plan your reading corner with original owner evidence.</p><a class="button" '
        'href="/guide/">Read the desk guide ↗</a></div></section></main></body></html>'
    )
    guide = repository / "web/guide/index.html"
    guide.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Desk lighting setup '
        '— Cedar Workshop</title><meta name="description" content="Plan a desk lighting setup '
        'with the Cedar Desk Lamp and original owner observations."><link rel="stylesheet" '
        'href="/style.css"></head><body><header><a class="brand" href="/">Cedar Workshop</a>'
        '<nav><a href="/guide/">Desk guide</a></nav></header><main><section class="hero"><div>'
        '<div class="eyebrow">DESK LIGHTING GUIDE</div><h1>Make room<br>for focus.</h1><p>A useful '
        "guide should contain evidence you can inspect. Our desk setup observations belong "
        "here.</p></div></section></main><footer>Fictional demonstration · no measured search "
        "uplift</footer></body></html>"
    )
    (repository / "verify_content.py").write_text(
        "from pathlib import Path\n"
        'text=Path("web/guide/index.html").read_text()\n'
        f"assert {PASSAGE!r} in text\n"
        'assert text.count("data-optimizer-topic") == 1\n'
        'assert "<h1>Make room<br>for focus.</h1>" in text\n'
        'assert "<script" not in text\n'
        'print("PASS: original passage, single publication, existing heading preserved")\n'
    )
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
        "Add original content fixture",
    )
    base = run_git(repository, "rev-parse", "HEAD")
    before = guide.read_text()
    site = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(repository / "web"))
    )
    threading.Thread(target=site.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{site.server_port}"
    settings = Settings(
        data_dir=root / "control",
        database_url=f"sqlite:///{root}/control.sqlite",
        secret_key=secrets.token_urlsafe(40),
        allowed_repo_roots=(root,),
    )
    settings.data_dir.mkdir()
    store = Store(settings)
    password = secrets.token_urlsafe(20)
    account, _ = store.create_user("demo@example.test", hash_password(password))
    spec = ProjectSpec(
        name="Cedar Workshop",
        website_url=origin + "/",
        local_path=str(repository),
        allowed_paths=["web"],
        route_map={"/": "web/index.html", "/guide/": "web/guide/index.html"},
        goals=["Help customers plan a reading corner with actual original owner observations"],
        facts=[
            TrustedFact(
                id="owner-study",
                name="Original desk setup notes",
                value=PASSAGE,
                source="Fictional owner notebook, explicitly synthetic",
                verified_at=utc_now(),
            )
        ],
        auto_fix=True,
        allow_content_publication=True,
        auto_content_refresh=True,
        check_commands=[["python", "verify_content.py"]],
    )
    project = store.create_project(account.id, ProjectCreate(spec=spec))
    workspace = Workspace(
        materials=[
            Material(
                id="desk-notes",
                title="Original desk setup observations",
                text=PASSAGE,
                origin="owner",
                source="Fictional owner notebook",
                collected_at=utc_now(),
                reviewed=True,
                original=True,
                fact_ids=["owner-study"],
                target_path="/guide/",
            )
        ],
        search=[
            SearchObservation(
                id="query-sample",
                query="desk lighting setup",
                page=origin + "/guide/",
                start=utc_now().date() - timedelta(days=30),
                end=utc_now().date(),
                impressions=500,
                clicks=20,
                business_relevance="confirmed",
                source="Synthetic demonstration measurements, not live Search Console",
                synthetic=True,
            )
        ],
    )
    store.save_workspace(account.id, project.id, workspace)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        dashboard_port = listener.getsockname()[1]
    dashboard = uvicorn.Server(
        uvicorn.Config(
            create_app(settings, store), host="127.0.0.1", port=dashboard_port, log_level="error"
        )
    )
    thread = threading.Thread(target=dashboard.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 20
    while not dashboard.started and time.monotonic() < deadline:
        time.sleep(0.1)
    if not dashboard.started:
        raise RuntimeError("Demo dashboard did not start")
    report = {
        "status": "running",
        "generated_at": utc_now().isoformat(),
        "synthetic": True,
        "base_sha": base,
        "source": workspace.model_dump(mode="json"),
        "github_writes": False,
    }
    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(channel="chromium")
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                record_video_dir=str(root / "raw"),
                record_video_size={"width": 1440, "height": 1000},
            )
            page = context.new_page()
            page.goto(origin + "/guide/")
            page.screenshot(path=str(assets / "growth-before.png"))
            page.wait_for_timeout(1800)
            page.goto(f"http://127.0.0.1:{dashboard_port}/login")
            page.locator('input[name="email"]').fill(account.email)
            page.locator('input[name="password"]').fill(password)
            page.locator('button[type="submit"], button.button').first.click()
            page.goto(f"http://127.0.0.1:{dashboard_port}/projects/{project.id}/research")
            page.locator("summary", has_text="Inspect the brief").click()
            page.screenshot(path=str(assets / "growth-strategy.png"))
            page.wait_for_timeout(2800)
            worker = Worker(store, settings)
            for kind, step in [
                ("audit", "Audit"),
                ("strategy", "Strategy"),
                ("content", "Original content publication"),
            ]:
                print(f"RUN {step}", flush=True)
                assert worker.tick(account.id)
                latest = next(j for j in store.jobs(account.id, project.id) if j.kind == kind)
                print(f"WORKER {latest.status}: {latest.result.get('summary', '')}", flush=True)
                assert latest.status == "complete", latest.result
            content = next(j for j in store.jobs(account.id, project.id) if j.kind == "content")
            assert content.result["content_verified"] and content.result["stage"] == "verified"
            page.goto(f"http://127.0.0.1:{dashboard_port}/jobs/{content.id}")
            page.screenshot(path=str(assets / "growth-verification.png"))
            page.wait_for_timeout(2400)
            page.goto(origin + "/guide/")
            assert PASSAGE in page.locator("main").inner_text()
            page.screenshot(path=str(assets / "growth-after.png"))
            page.wait_for_timeout(2600)
            merged = run_git(repository, "rev-parse", "HEAD")
            opportunity = plan(spec, workspace).opportunities[0]
            store.enqueue(
                account.id,
                project.id,
                "content",
                "repeat-content",
                {"opportunity_id": opportunity.id},
            )
            worker.tick(account.id)
            assert run_git(repository, "rev-parse", "HEAD") == merged
            report.update(
                status="passed",
                merged_sha=merged,
                content=content.result,
                jobs=[
                    {"kind": j.kind, "status": j.status, "summary": j.result.get("summary")}
                    for j in store.jobs(account.id, project.id)
                ],
                repeat_created_commit=False,
                model_requests=0,
                diff="\n".join(
                    difflib.unified_diff(
                        before.splitlines(),
                        guide.read_text().splitlines(),
                        fromfile="before/web/guide/index.html",
                        tofile="after/web/guide/index.html",
                        lineterm="",
                    )
                ),
            )
            video = page.video
            context.close()
            video.save_as(str(assets / "growth-workflow.webm"))
            browser.close()
            print(
                "PASS: source → strategy → Docker check → local commit → served evidence",
                flush=True,
            )
    finally:
        (assets / "growth-run.json").write_text(json.dumps(report, indent=2) + "\n")
        dashboard.should_exit = True
        thread.join(timeout=10)
        site.shutdown()
        site.server_close()
        store.engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
