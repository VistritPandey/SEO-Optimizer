"""Exercise workspace UI in a disposable browser with fictional identity and API fixtures.

Bundles the actual components with test-only auth/navigation adapters in a temporary
folder. No auth bypass or preview route is added to the production application.
"""

import json
import subprocess
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "frontend"


def fixtures():
    report = {
        "score": 85,
        "pages": 4,
        "evaluated_checks": 2,
        "total_checks": 4,
        "coverage": [
            {
                "check_id": "tech.title",
                "title": "Descriptive titles",
                "module": "technical",
                "state": "healthy",
            },
            {
                "check_id": "tech.links",
                "title": "Internal links",
                "module": "technical",
                "state": "defect",
            },
            {
                "check_id": "geo.crawlers",
                "title": "Crawler policy",
                "module": "geo",
                "state": "needs_data",
                "reason": "Search and training access require separate owner preferences.",
                "dependencies": ["Confirm the policy for each crawler"],
                "method": "deterministic",
                "evidence_urls": ["https://example.test/robots.txt"],
            },
            {
                "check_id": "perf.field",
                "title": "Field performance",
                "module": "performance",
                "state": "not_checked",
            },
        ],
        "page_summaries": [
            {
                "url": "https://example.test/shop",
                "title": "Workshop lighting",
                "excerpt": "Original workshop lighting guide.",
                "evidence_id": "response",
            }
        ],
        "model_runtime_ms": 12345,
        "usage": {"input_tokens": 4000, "output_tokens": 1000, "api_cost_usd": None},
        "tool_trace": [
            {"name": "read_file", "success": True, "runtime_ms": 21},
            {"name": "run_checks", "success": False, "runtime_ms": 30},
        ],
    }
    project = {
        "id": "site",
        "spec": {
            "name": "Cedar Workshop",
            "website_url": "https://example.test",
            "repository": "fictional/site",
            "branch": "main",
            "enabled": True,
            "auto_fix": True,
        },
        "last_report": report,
    }
    jobs = [
        {
            "id": "blocked",
            "kind": "audit",
            "status": "blocked",
            "created_at": 1792450000,
            "updated_at": 1792450010,
            "events": [{"time": 1792450010, "message": "Build verification needs configuration"}],
            "result": {
                "summary": "Build verification needs configuration",
                "error_type": "ValueError",
            },
        },
        {
            "id": "done",
            "kind": "push",
            "status": "complete",
            "created_at": 1792440000,
            "updated_at": 1792440040,
            "events": [{"time": 1792440040, "message": "Observed four pages"}],
            "result": {
                "summary": "Audited 4 pages; 2 new findings",
                "report": report,
                "verified_fixes": 0,
                "pr": {"url": "https://github.com/fictional/site/pull/1", "number": 1},
                "evidence": [
                    {
                        "id": "response",
                        "url": "https://example.test/shop",
                        "observation": "Collected destination response",
                        "collected_at": "2026-10-19T12:00:00Z",
                        "data": {"status_code": 404},
                    }
                ],
            },
        },
    ]
    jobs.append(
        {
            "id": "reused",
            "kind": "audit",
            "status": "complete",
            "events": [
                {
                    "time": 1792450010,
                    "message": "Assessment complete; no source changes will be published",
                }
            ],
            "result": {
                "summary": "Unchanged website assessed",
                "report": {
                    **report,
                    "assessment_reused": True,
                    "tool_trace": [],
                    "model_runtime_ms": None,
                    "usage": {"input_tokens": 0, "output_tokens": 0, "api_cost_usd": 0},
                },
            },
        }
    )
    findings = [
        {
            "id": "broken",
            "active": True,
            "details": {
                "check_id": "tech.links",
                "summary": "A collection link returns 404",
                "severity": "high",
                "status": "defect",
                "evidence_strength": "confirmed",
                "url": "https://example.test/shop",
                "evidence_ids": ["response"],
                "action": {"rationale": "Use the existing collection destination"},
                "verification_criteria": ["Fetch the repaired link and verify status 200"],
            },
        },
        {
            "id": "intent",
            "active": True,
            "details": {
                "check_id": "tech.indexability",
                "summary": "Confirm account page visibility",
                "severity": "info",
                "status": "unresolved",
                "evidence_strength": "hypothesis",
                "dependencies": ["Owner-confirmed page intent"],
            },
        },
    ]
    return project, {"jobs": jobs, "findings": findings}


def main():
    project, activity = fixtures()
    results = []
    output = ROOT / ".data/workspace-qa"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="optimiser-workspace-qa-") as folder:
        folder = Path(folder)
        (folder / "auth.mjs").write_text(
            'export const user={uid:"fictional-user",'
            'email:"tester@example.test",emailVerified:true,'
            'getIdToken:async()=>"fixture-token"};'
            "export const onAuthStateChanged=(_,fn)=>{queueMicrotask(()=>fn(user));return()=>{}};"
            "export const sendEmailVerification=async()=>{};export const signOut=async()=>{};"
        )
        (folder / "firebase.mjs").write_text(
            'import {user} from "./auth.mjs"; export const firebaseAuth=()=>({currentUser:user});'
        )
        (folder / "navigation.mjs").write_text(
            "const router={replace:()=>{},push:()=>{}};export const useRouter=()=>router;"
        )
        (folder / "link.jsx").write_text(
            'import React from "react";export default function '
            "Link({children,...props}){return <a {...props}>{children}</a>}"
        )
        (folder / "image.jsx").write_text(
            'import React from "react";export default function '
            "Image({preload,...props}){return <img {...props}/>}"
        )
        (folder / "motion.mjs").write_text(
            'import React from "react";export const '
            'm={main:({initial,animate,transition,children,...props})=>React.createElement("main",props,children)};'
        )
        (folder / "entry.jsx").write_text(
            'import React from "react";import {createRoot} from "react-dom/client";import '
            "{Dashboard} from "
            + json.dumps(str(WEB / "components/Dashboard.tsx"))
            + ';createRoot(document.getElementById("root")).render(<Dashboard/>);'
        )
        args = [
            "npx",
            "--yes",
            "--package=esbuild@0.25.12",
            "esbuild",
            str(folder / "entry.jsx"),
            "--bundle",
            "--jsx=automatic",
            "--outfile=" + str(folder / "app.js"),
            "--alias:@=" + str(WEB),
            "--alias:react=" + str(WEB / "node_modules/react"),
            "--alias:react-dom=" + str(WEB / "node_modules/react-dom"),
        ]
        for name, target in {
            "firebase/auth": "auth.mjs",
            "@/lib/firebase": "firebase.mjs",
            "next/navigation": "navigation.mjs",
            "next/link": "link.jsx",
            "next/image": "image.jsx",
            "motion/react": "motion.mjs",
        }.items():
            args.append("--alias:" + name + "=" + str(folder / target))
        subprocess.run(args, check=True, text=True)
        import shutil

        shutil.copytree(WEB / "public/brand", folder / "brand")
        (folder / "style.css").write_text(
            (WEB / "app/globals.css").read_text() + ":root{--font-sans:Arial;--font-serif:Georgia}"
        )
        (folder / "index.html").write_text(
            '<!doctype html><html lang="en"><head><meta charset="UTF-8">'
            "<title>Workspace fixture QA</title><meta "
            'name="viewport" content="width=device-width, initial-scale=1"><link '
            'rel="stylesheet" href="/style.css"></head><body><div id="root"></div><script '
            'src="/app.js"></script></body></html>'
        )
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(folder))
        )
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as runtime:
                browser = runtime.chromium.launch(channel="chromium")
                page = browser.new_page(viewport={"width": 1440, "height": 1080})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                state = {"account_calls": 0, "mode": "normal", "mutations": 0}

                def respond(route):
                    path = route.request.url.split("/api/backend/", 1)[1]
                    if path == "account":
                        state["account_calls"] += 1
                        if state["mode"] == "fail" or state["account_calls"] == 1:
                            route.fulfill(
                                status=502,
                                content_type="text/html",
                                body="<h1>Temporary gateway error</h1>",
                            )
                            return
                        data = {
                            "email": "tester@example.test",
                            "tier": "free",
                            "jobs_used": 2,
                            "job_limit": 100,
                            "project_limit": 3,
                            "github_connection": {"status": "connected", "login": "fictional"},
                        }
                    elif path == "projects":
                        data = [project]
                    elif path == "projects/site/activity":
                        data = activity
                    elif path == "projects/site":
                        if route.request.method == "PATCH":
                            project["spec"].update(route.request.post_data_json)
                        data = project
                    elif path.endswith("/workspace"):
                        data = {}
                    elif path.endswith("/strategy"):
                        data = {"opportunities": [], "dependencies": []}
                    elif path.endswith("/jobs"):
                        state["mutations"] += 1
                        data = {"id": "new-job", "status": "queued"}
                    else:
                        route.fulfill(status=404, json={"detail": "Fixture endpoint absent"})
                        return
                    route.fulfill(status=200, json=data)

                page.route("**/api/backend/**", respond)
                page.goto(f"http://127.0.0.1:{server.server_port}")
                page.get_by_role("heading", name="Your search visibility,").wait_for()
                assert state["account_calls"] == 2
                assert page.get_by_text("Retry connection", exact=True).count() == 0
                results.append("HTML gateway read recovers; normal loading never shows retry")
                page.get_by_role("button", name="Take the tour", exact=True).click()
                tour = page.get_by_role("dialog")
                expect(tour).to_be_visible()
                expect(tour.get_by_role("heading", name="Connect the website")).to_be_visible()
                tour.get_by_role("button", name="Next").click()
                expect(tour.get_by_role("heading", name="Start with evidence")).to_be_visible()
                tour.get_by_role("button", name="Next").click()
                page.screenshot(path=str(output / "tour.png"))
                tour.get_by_role("button", name="Back").click()
                expect(tour.get_by_role("heading", name="Start with evidence")).to_be_visible()
                page.keyboard.press("Escape")
                expect(tour).not_to_be_visible()
                expect(page.get_by_role("button", name="Take the tour", exact=True)).to_have_count(
                    0
                )
                assert state["mutations"] == 0
                results.append(
                    "Tutorial navigation, Escape and remembered dismissal without audit writes"
                )
                page.get_by_role("button", name="Monitoring Cedar Workshop").click()
                page.get_by_role("heading", name="Health over time").wait_for()
                assert page.get_by_role("img", name="out of 100").count() == 1
                sidebar = page.get_by_role("navigation", name="Selected website navigation")
                sidebar.get_by_role("button", name="Pages inspected").click()
                expect(page.get_by_role("heading", name="Workshop lighting")).to_be_visible()
                sidebar.get_by_role("button", name="Website overview").click()
                page.get_by_role("button", name="Pause monitoring", exact=True).click()
                page.get_by_role("button", name="Resume monitoring", exact=True).click()
                expect(
                    page.get_by_role("button", name="Pause monitoring", exact=True)
                ).to_be_visible()
                page.get_by_role("button", name="How it works A quick guided tour").click()
                expect(page.get_by_role("dialog")).to_be_visible()
                for _ in range(4):
                    page.get_by_role("dialog").get_by_role("button", name="Next").click()
                page.get_by_role("dialog").get_by_role("button", name="Finish tour").click()
                expect(page.get_by_role("dialog")).not_to_be_visible()
                results.append("Sidebar sections, replayable tour and saved monitoring responses")
                page.screenshot(path=str(output / "overview.png"), full_page=True)
                page.locator(".audit-coverage > details").filter(has_text="Crawler policy").locator(
                    ":scope > summary"
                ).click()
                page.get_by_text("Crawler policy", exact=True).click()
                expect(
                    page.get_by_text(
                        "Search and training access require separate owner preferences.", exact=True
                    )
                ).to_be_visible()
                expect(
                    page.get_by_text("Confirm the policy for each crawler", exact=True)
                ).to_be_visible()
                assert (
                    page.get_by_role("link", name="https://example.test/robots.txt").get_attribute(
                        "href"
                    )
                    == "https://example.test/robots.txt"
                )
                results.append(
                    "Coverage exposes per-check reasons, dependencies and collected URLs"
                )
                theme = page.get_by_role("group", name="Appearance")
                theme.get_by_role("button", name="Dark", exact=True).click()
                expect(page.locator("html")).to_have_attribute("data-theme", "dark")
                page.screenshot(path=str(output / "overview-dark.png"), full_page=True)
                page.reload()
                page.get_by_role("button", name="Monitoring Cedar Workshop").click()
                expect(page.locator("html")).to_have_attribute("data-theme", "dark")
                expect(theme.get_by_role("button", name="Dark", exact=True)).to_have_attribute(
                    "aria-pressed", "true"
                )
                page.emulate_media(color_scheme="dark")
                theme.get_by_role("button", name="System", exact=True).click()
                expect(page.locator("html")).to_have_attribute("data-theme", "dark")
                page.emulate_media(color_scheme="light")
                expect(page.locator("html")).to_have_attribute("data-theme", "light")
                theme.get_by_role("button", name="Light", exact=True).click()
                page.emulate_media(color_scheme="dark")
                expect(page.locator("html")).to_have_attribute("data-theme", "light")
                results.append("Light/dark/system appearance, reload persistence and OS changes")

                page.get_by_role("tab", name="Findings").click()
                page.get_by_label("Filter findings").select_option("unresolved")
                page.get_by_text("Confirm account page visibility", exact=True).click()
                expect(page.get_by_text("Owner-confirmed page intent", exact=True)).to_be_visible()
                assert page.get_by_text("A collection link returns 404", exact=True).count() == 0
                page.get_by_label("Filter findings").select_option("defect")
                page.get_by_text("A collection link returns 404", exact=True).click()
                expect(
                    page.get_by_text("Collected destination response", exact=True)
                ).to_be_visible()
                page.get_by_label("Search findings").fill("no-match")
                expect(page.get_by_role("heading", name="No findings in this view")).to_be_visible()
                results.append(
                    "Findings filter and search; independent strength, dependencies and evidence"
                )
                page.get_by_role("tab", name="AI audits & logs").click()
                page.get_by_text("Audited 4 pages; 2 new findings", exact=True).click()
                expect(page.get_by_text("Read source file", exact=False).first).to_be_visible()
                expect(
                    page.locator(".audit-run[open]").get_by_text(
                        "API cost was not supplied.", exact=False
                    )
                ).to_be_visible()
                assert (
                    page.get_by_role("link", name="Review pull request #1").get_attribute("href")
                    == "https://github.com/fictional/site/pull/1"
                )
                page.get_by_text("Unchanged website assessed", exact=True).click()
                expect(page.get_by_text("Reused assessment", exact=True)).to_be_visible()
                expect(page.get_by_text("Inputs were unchanged.", exact=False)).to_be_visible()
                expect(
                    page.get_by_text("No pull request was opened for this audit.", exact=True)
                ).to_be_visible()
                results.append(
                    "Reused assessments and no-PR outcomes explain model and publication decisions"
                )
                page.get_by_label("Job status").select_option("blocked")
                expect(
                    page.get_by_text("Build verification needs configuration", exact=True).first
                ).to_be_visible()
                assert page.get_by_text("Audited 4 pages; 2 new findings", exact=True).count() == 0
                results.append("Audit history, failed checks, job filters and PR destination")
                page.get_by_role("tab", name="Pages", exact=True).click()
                expect(page.get_by_role("heading", name="Workshop lighting")).to_be_visible()
                page.get_by_role("button", name="Run audit").click()
                expect(page.get_by_text("Audit queued.", exact=True)).to_be_visible()
                assert state["mutations"] == 1
                results.append("Page observations and single audit submission")
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                menu = page.get_by_role("button", name="Workspace menu", exact=True)
                expect(menu).to_have_attribute("aria-expanded", "false")
                menu.click()
                expect(
                    page.get_by_role("navigation", name="Selected website navigation")
                ).to_be_visible()
                page.get_by_role("navigation", name="Selected website navigation").get_by_role(
                    "button", name="Website overview", exact=True
                ).click()
                expect(menu).to_have_attribute("aria-expanded", "false")
                page.screenshot(path=str(output / "mobile.png"), full_page=True)
                results.append("390px viewport without horizontal overflow")
                page.set_viewport_size({"width": 1440, "height": 1080})
                page.get_by_role("tab", name="Overview", exact=True).click()
                page.add_script_tag(path=str(WEB / "node_modules/axe-core/axe.min.js"))
                page.get_by_role("button", name="How it works A quick guided tour").click()
                tour_violations = page.evaluate(
                    "async()=> (await axe.run(document,{runOnly:{type:'tag',"
                    "values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>v.id)"
                )
                assert not tour_violations, tour_violations
                page.keyboard.press("Shift+Tab")
                assert page.get_by_role("dialog").evaluate(
                    "element => element.contains(document.activeElement)"
                )
                page.keyboard.press("Escape")
                results.append("Tutorial dialog accessibility and focus trapping")
                violations = page.evaluate(
                    "async()=> (await "
                    "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.length}))"
                )
                assert not violations, violations
                results.append("Workspace overview accessibility checks")
                page.get_by_role("group", name="Appearance").get_by_role(
                    "button", name="Dark", exact=True
                ).click()
                dark_violations = page.evaluate(
                    "async()=> (await axe.run(document,{runOnly:{type:'tag',"
                    "values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>({id:v.id,"
                    "nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))"
                )
                assert not dark_violations, dark_violations
                page.get_by_role("button", name="How it works A quick guided tour").click()
                dark_tour = page.evaluate(
                    "async()=> (await axe.run(document,{runOnly:{type:'tag',"
                    "values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>v.id)"
                )
                assert not dark_tour, dark_tour
                page.keyboard.press("Escape")
                results.append("Dark workspace and tour accessibility checks")

                state["mode"] = "fail"
                page.reload()
                page.get_by_role("heading", name="Your workspace couldn’t be loaded").wait_for()
                expect(page.get_by_role("button", name="Reload workspace")).to_be_visible()
                state["mode"] = "normal"
                page.get_by_role("button", name="Reload workspace").click()
                page.get_by_role("heading", name="Your search visibility,").wait_for()
                results.append("Persistent connection failure has actionable recovery")
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
    (output / "results.json").write_text(
        json.dumps({"passed": results, "fixture_only": True}, indent=2)
    )
    print(json.dumps({"passed": results}, indent=2))


if __name__ == "__main__":
    main()
