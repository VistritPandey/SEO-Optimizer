"""Exercise the actual Next UI, Firebase identity, Firestore and offline SEO worker.

Requires the documented loopback emulators, API :8791 and Next development :3001.
All data belongs to a fictional local fixture. No GitHub or paid-model requests.
"""

import json
import os
import secrets
import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
from firebase_admin import auth, get_app, initialize_app
from playwright.sync_api import sync_playwright

from seo_optimizer.application_models import ProjectCreate, ProjectSpec
from seo_optimizer.execution import run_git
from seo_optimizer.firestore_store import FirestoreStore
from seo_optimizer.hosted import firebase_user
from seo_optimizer.settings import Settings
from seo_optimizer.worker import Worker

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    assert os.getenv("FIRESTORE_EMULATOR_HOST") == "127.0.0.1:8089"
    assert os.getenv("FIREBASE_AUTH_EMULATOR_HOST") == "127.0.0.1:9099"
    settings = Settings.from_env()
    assert settings.firebase_project == "demo-your-optimiser" and not settings.production
    store = FirestoreStore(settings)
    email, password = "demo-owner@example.test", secrets.token_urlsafe(24)
    app_name = "your-optimiser-demo-your-optimiser"
    try:
        application = get_app(app_name)
    except ValueError:
        application = initialize_app(
            options={"projectId": settings.firebase_project}, name=app_name
        )
    try:
        account = auth.get_user_by_email(email, app=application)
        auth.update_user(account.uid, password=password, email_verified=True, app=application)
    except auth.UserNotFoundError:
        account = auth.create_user(
            email=email, password=password, email_verified=True, app=application
        )
    with httpx.Client() as client:
        response = client.post(
            "http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=example",
            json={"email": email, "password": password, "returnSecureToken": True},
        )
        response.raise_for_status()
        owner = firebase_user(response.json()["idToken"], settings, store)
    assert owner is not None
    fixture = settings.data_dir / "fixture"
    if fixture.exists():
        shutil.rmtree(fixture)
    shutil.copytree(ROOT / "tests/fixtures/agent_site", fixture)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(fixture / "web"))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    for page in (fixture / "web").rglob("*.html"):
        page.write_text(page.read_text().replace("__ORIGIN__", origin))
    run_git(fixture, "init", "-b", "main")
    run_git(fixture, "add", ".")
    run_git(
        fixture,
        "-c",
        "user.name=Fixture Owner",
        "-c",
        "user.email=owner@example.test",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "Add fixture",
    )
    project = store.create_project(
        owner.id,
        ProjectCreate(
            spec=ProjectSpec(
                name="Cedar Workshop · local fixture",
                website_url=origin,
                local_path=str(fixture),
                allowed_paths=["web"],
                page_intents={"/preview/": False},
                auto_fix=False,
                website_types=["generic", "ecommerce"],
            )
        ),
    )
    settings = Settings(**{**settings.__dict__, "allowed_repo_roots": (fixture,)})
    assert Worker(store, settings).tick(owner.id)
    job = store.jobs(owner.id, project.id)[0]
    assert job.status == "complete", job.result
    output = ROOT / ".data/hosted-ui/capture"
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    checks = []
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            record_video_dir=str(output / "raw"),
            record_video_size={"width": 1440, "height": 1000},
        )
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://localhost:3001")
        page.get_by_role("heading", name="A better website.").wait_for()
        page.screenshot(path=str(output / "landing.png"), full_page=True)
        page.get_by_role("tab", name="03 Change & test").click()
        assert "Stage precise replacements" in page.get_by_role("tabpanel").inner_text()
        checks.append("interactive landing workflow")
        page.goto("http://localhost:3001/login")
        page.get_by_label("Email", exact=True).fill(email)
        page.get_by_label("Password", exact=True).fill(password)
        page.get_by_role("button", name="Sign in ↗", exact=True).click()
        page.get_by_role("heading", name="Your websites,").wait_for()
        page.get_by_role("button", name="Cedar Workshop · local fixture").last.click()
        page.get_by_role("heading", name="Findings & evidence").wait_for()
        page.get_by_text("tech.canonical", exact=True).first.wait_for()
        page.screenshot(path=str(output / "findings.png"), full_page=True)
        checks.extend(
            [
                "real Firebase sign-in",
                "tenant-scoped API and Firestore project",
                "actual rules audit findings",
            ]
        )
        page.get_by_role("tab", name="activity", exact=True).click()
        page.get_by_text("Activity & pull requests", exact=True).wait_for()
        page.locator("details").first.locator("summary").click()
        page.screenshot(path=str(output / "activity.png"), full_page=True)
        page.get_by_role("tab", name="research", exact=True).click()
        page.get_by_label("Research workspace JSON").wait_for()
        page.get_by_role("button", name="Save evidence ↗").click()
        page.get_by_role("status").filter(has_text="Research saved").wait_for()
        checks.append("research save reaches existing contract API")
        page.get_by_role("tab", name="policy", exact=True).click()
        page.get_by_label("Project settings JSON").wait_for()
        page.get_by_role("button", name="＋ Connect website").click()
        page.get_by_role("heading", name="Give your website").wait_for()
        assert page.get_by_label("Verified repository").is_visible()
        assert page.get_by_label("Directories to monitor").is_visible()
        page.screenshot(path=str(output / "onboarding.png"), full_page=True)
        checks.append("guided repository onboarding")
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto("http://localhost:3001")
        page.screenshot(path=str(output / "mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        checks.append("mobile landing without horizontal overflow")
        video = page.video
        context.close()
        video.save_as(str(output / "workspace.webm"))
        browser.close()
    server.shutdown()
    server.server_close()
    store.close()
    assert not errors, errors
    report = {
        "status": "passed",
        "checks": checks,
        "page_errors": errors,
        "environment": "local Next + Firebase emulators + Firestore + actual rules worker",
        "model_requests": 0,
        "github_requests": 0,
        "cloud_execution": "unverified",
        "worker_status": job.status,
        "worker_summary": job.result["summary"],
    }
    (ROOT / "reports/hosted-ui.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
