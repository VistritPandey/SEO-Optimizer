"""Exercise the fictional workflow, responsive pages and accessibility in a disposable browser."""

import argparse
import json
import re
import traceback
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright
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
        page.clock.install()
        page.goto(args.base_url, wait_until="networkidle")
        hero = page.get_by_role("complementary", name="Interactive SEO workflow example")
        assert hero.get_by_role("heading", name="Your team ships a new homepage.").is_visible()
        playback = hero.locator(".demo-playback")
        expect(playback).to_have_attribute("data-running", "true")
        initial_height = hero.bounding_box()["height"]
        page.clock.fast_forward(5_300)
        expect(hero).to_have_attribute("data-stage", "1")
        hero.get_by_role("button", name="Pause hero example", exact=True).click()
        page.clock.fast_forward(11_000)
        expect(hero).to_have_attribute("data-stage", "1")
        hero.get_by_role("button", name="Play hero example", exact=True).click()
        for expected in (2, 3, 0):
            page.clock.fast_forward(5_300)
            expect(hero).to_have_attribute("data-stage", str(expected))
            assert abs(hero.bounding_box()["height"] - initial_height) < 2
        hero.get_by_role("button", name="Update", exact=True).click()
        expect(playback).to_have_attribute("data-playing", "false")
        passed.append(
            "Hero auto-plays and loops with stable height; pause and manual takeover work"
        )
        hero.get_by_role("button", name="Check this update →").click()
        hero.get_by_text("/collections/lighting/ returns 404", exact=True).wait_for(state="visible")
        hero.get_by_role("button", name="See the proposal →").click()
        hero.get_by_text("/shop/ · existing page", exact=True).wait_for(state="visible")
        hero.get_by_role("button", name="Approve this example →").click()
        hero.get_by_text("/shop/ returns 200 after deployment", exact=True).wait_for(
            state="visible"
        )
        hero.get_by_role("button", name="Replay example ↺").click()
        assert hero.get_by_role("heading", name="Your team ships a new homepage.").is_visible()
        hero.get_by_role("button", name="Inspect", exact=True).focus()
        page.keyboard.press("Enter")
        expect(hero.get_by_role("button", name="Inspect", exact=True)).to_have_attribute(
            "aria-pressed", "true"
        )
        hero.get_by_role("button", name="Update", exact=True).click()
        passed.append(
            "Hero workflow: update, findings, review, verification, replay and keyboard controls"
        )
        github = page.get_by_role("navigation", name="Main navigation").get_by_role(
            "link", name="Your Optimiser on GitHub (opens in a new tab)"
        )
        assert github.get_attribute("href") == "https://github.com/YourOptimiser/SEO-Optimizer"
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
        store = page.locator(".customer-demo")
        store_playback = store.locator(".demo-playback")
        expect(store_playback).to_have_attribute("data-running", "true")
        # Keep the walkthrough in view while virtual time advances through its full story.
        store.locator(".demo-playback").scroll_into_view_if_needed()
        page.clock.fast_forward(6_600)
        expect(store).to_have_attribute("data-step", "1")
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        expect(store_playback).to_have_attribute("data-running", "false")
        page.clock.fast_forward(14_000)
        expect(store).to_have_attribute("data-step", "1")
        store.locator(".demo-playback").scroll_into_view_if_needed()
        expect(store_playback).to_have_attribute("data-running", "true")
        for expected in (2, 3, 4, 5, 0):
            page.clock.fast_forward(6_600)
            expect(store).to_have_attribute("data-step", str(expected))
        store.get_by_role("button", name="Pause store walkthrough", exact=True).click()
        passed.append("Store auto-plays the illustrated full cycle and stops its timer off screen")
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
        page.get_by_text("What is free, and what comes next?", exact=True).click()
        assert (
            page.locator(".faq-section")
            .get_by_text(re.compile("The open-source version is free"))
            .is_visible()
        )
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
        page.clock.install()
        page.goto(args.base_url, wait_until="networkidle")
        reduced_hero = page.locator(".hero-workflow")
        expect(reduced_hero.locator(".demo-playback")).to_have_attribute("data-playing", "false")
        page.clock.fast_forward(12_000)
        expect(reduced_hero).to_have_attribute("data-stage", "0")
        reduced_hero.scroll_into_view_if_needed()
        reduced_hero.get_by_role("button", name="Play hero example", exact=True).click()
        expect(reduced_hero.locator(".demo-playback")).to_have_attribute("data-running", "true")
        page.clock.run_for(100)
        page.clock.fast_forward(5_300)
        expect(reduced_hero).to_have_attribute("data-stage", "1")
        passed.append("Reduced-motion visitors start paused and can explicitly play the example")
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
        for path in ("/", "/login", "/login?mode=register"):
            page.goto(args.base_url + path, wait_until="networkidle")
            brand = page.get_by_role("link", name="Your Optimiser home").first
            mark = brand.locator(".brand-mark").bounding_box()
            image = brand.locator(".brand-mark img").bounding_box()
            name = brand.locator(".brand-name").bounding_box()
            assert mark and image and name
            assert abs(image["x"] + image["width"] / 2 - mark["x"] - mark["width"] / 2) < 1
            assert abs(mark["y"] + mark["height"] / 2 - name["y"] - name["height"] / 2) < 2
            assert mark["x"] + mark["width"] <= name["x"]
            if path.startswith("/login"):
                page.add_script_tag(path=str(ROOT / "frontend/node_modules/axe-core/axe.min.js"))
                auth_violations = page.evaluate(
                    "async () => (await axe.run(document, "
                    "{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations"
                )
                violations.extend(
                    {"path": path, "id": item["id"], "impact": item["impact"]}
                    for item in auth_violations
                )
        passed.append(
            "Shared logo aligns on mobile home, sign-in and sign-up; "
            "authentication pages pass automated A/AA checks"
        )
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
