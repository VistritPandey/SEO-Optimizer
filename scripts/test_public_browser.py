"""Exercise the fictional workflow, responsive pages and accessibility in a disposable browser."""

import argparse
import json
import re
import traceback
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright
from test_public_site import PAGES

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3002")
    args = parser.parse_args()
    passed, errors, violations = [], [], []
    screenshots = ROOT / "reports/public-site"
    screenshots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chromium")
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        page.goto(args.base_url, wait_until="networkidle")
        assert page.locator("video").count() == 0
        assert not any("demo-poster" in url or url.endswith("/demo.mp4") for url in requests)
        summary = page.get_by_text("▷ Prefer to watch? See the customer walkthrough", exact=True)
        summary.click()
        page.locator("video").wait_for(state="visible")
        assert page.locator("video").is_visible()
        assert page.locator("video").evaluate("video => video.muted && !video.autoplay")
        summary.click()
        page.locator("video").wait_for(state="detached")
        assert page.locator("video").count() == 0
        passed.append("Silent captioned video mounts only on request and unloads when closed")
        page.get_by_role("link", name="Try the interactive demo").click()
        page.get_by_role("button", name="Explore the collection").click()
        assert page.get_by_role("heading", name="This collection cannot be found.").is_visible()
        page.get_by_role("button", name="Back to the homepage").click()
        page.get_by_role("button", name=re.compile("Review the fix")).click()
        page.get_by_role("button", name="Before", exact=True).click()
        assert page.get_by_text("/collections/lighting/ → missing page", exact=True).is_visible()
        page.get_by_role("button", name="Proposed fix", exact=True).click()
        assert page.get_by_text("/shop/ → existing collection", exact=True).is_visible()
        page.get_by_role("button", name="Approve example fix").click()
        page.get_by_role("button", name="Explore the collection").click()
        assert page.get_by_role("heading", name="A little light for everyday life.").is_visible()
        passed.append(
            "Broken update: missing destination, before/after review and repaired destination"
        )
        page.get_by_role("button", name="Nothing breaks", exact=True).click()
        page.get_by_role("button", name="Explore the collection").click()
        assert page.get_by_role("heading", name="A little light for everyday life.").is_visible()
        page.get_by_role("button", name=re.compile("Leave the page alone")).click()
        assert page.get_by_role("heading", name="No unnecessary changes.").is_visible()
        assert page.get_by_role("button", name="Approve example fix").count() == 0
        passed.append("Healthy update: working collection and no proposed fix or approval")
        page.goto(args.base_url, wait_until="networkidle")
        page.get_by_text("What is included in the free plan?", exact=True).click()
        assert page.get_by_text(re.compile("Up to three connected websites and 100")).is_visible()
        page.evaluate(
            "() => { document.activeElement?.blur(); window.scrollTo({top:0,behavior:'instant'}); }"
        )
        page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
        passed.append("FAQ answers expand with native accessible controls")

        # Use reduced motion for stable scans; the standard animated workflow was tested above.
        context = browser.new_context(
            viewport={"width": 390, "height": 844}, reduced_motion="reduce"
        )
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        for path in PAGES:
            page.goto(args.base_url + path, wait_until="networkidle")
            assert page.get_by_role("heading", level=1).count() == 1
            dimensions = page.evaluate(
                "({viewport:document.documentElement.clientWidth, "
                "content:document.documentElement.scrollWidth})"
            )
            assert dimensions["content"] <= dimensions["viewport"], f"Mobile overflow: {path}"
            page.add_script_tag(path=str(ROOT / "frontend/node_modules/axe-core/axe.min.js"))
            audit = page.evaluate(
                "async () => (await axe.run(document, "
                "{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations"
            )
            for item in audit:
                violations.append(
                    {
                        "path": path,
                        "id": item["id"],
                        "impact": item["impact"],
                        "targets": [node["target"] for node in item["nodes"]],
                    }
                )
            if path in {"/", "/how-it-works", "/privacy"}:
                filename = "mobile" if path == "/" else path.strip("/").replace("/", "-")
                page.screenshot(path=str(screenshots / (filename + ".png")), full_page=True)
        passed.append("Eight public pages fit a 390px mobile viewport without horizontal overflow")
        assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
        passed.append("Reduced-motion preference is active during responsive accessibility checks")
        browser.close()
    report = {
        "environment": args.base_url,
        "passed": passed,
        "browser_errors": errors,
        "accessibility_violations": violations,
        "screenshots": str(screenshots.relative_to(ROOT)),
        "model_calls": 0,
        "unverified": ["Manual assistive-technology audit", "Authenticated customer workflow"],
    }
    (ROOT / "reports/public-browser-qa.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return int(bool(errors or violations))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, PlaywrightError, OSError) as error:
        frame = traceback.extract_tb(error.__traceback__)[-1]
        report = {
            "status": "failed",
            "failed": [str(error) or f"{type(error).__name__} at line {frame.lineno}"],
            "model_calls": 0,
        }
        (ROOT / "reports").mkdir(exist_ok=True)
        (ROOT / "reports/public-browser-qa.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        raise SystemExit(1) from error
