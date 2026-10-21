"""Check responsive public navigation, keyboard use and appearance in a real browser."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3002")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/public-header-qa.json")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    passed, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chromium")
        page = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base + "/blog", wait_until="networkidle")
        panel = page.locator("#public-navigation")
        links = panel.get_by_role("link")
        toggle = page.locator(".public-menu-toggle")
        for width in (1440, 1280, 1101, 1100, 1024, 768, 640, 390, 320):
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            assert page.locator(".public-header").bounding_box()["height"] <= 90, width
            if width > 1100:
                expect(toggle).to_be_hidden()
                expect(panel).to_be_visible()
                assert links.count() == 6
                boxes = [links.nth(i).bounding_box() for i in range(6)]
                assert max(box["y"] for box in boxes) - min(box["y"] for box in boxes) < 2
                assert all(box["height"] < 36 and box["x"] + box["width"] <= width for box in boxes)
                passed.append(f"{width}px: all desktop links stay on one aligned row")
                continue
            expect(toggle).to_be_visible()
            expect(panel).to_be_hidden()
            expect(toggle).to_have_attribute("aria-expanded", "false")
            toggle.focus()
            page.keyboard.press("Enter")
            expect(toggle).to_have_attribute("aria-expanded", "true")
            expect(panel).to_be_visible()
            assert links.count() == 6
            for index in range(6):
                expect(links.nth(index)).to_be_visible()
            page.keyboard.press("Tab")
            expect(links.first).to_be_focused()
            page.keyboard.press("Escape")
            expect(panel).to_be_hidden()
            expect(toggle).to_be_focused()
            toggle.click()
            page.mouse.click(width - 5, 880)
            expect(panel).to_be_hidden()
            toggle.click()
            links.first.click()
            expect(page).to_have_url(base + "/how-it-works")
            expect(toggle).to_have_attribute("aria-expanded", "false")
            page.goto(base + "/blog", wait_until="networkidle")
            passed.append(
                f"{width}px: complete menu, keyboard, Escape, outside click and link dismissal"
            )

        for theme in ("light", "dark"):
            toggle.click()
            page.get_by_role("group", name="Appearance").get_by_role(
                "button", name=theme.title(), exact=True
            ).click()
            expect(page.locator("html")).to_have_attribute("data-theme", theme)
            page.add_script_tag(path=str(ROOT / "frontend/node_modules/axe-core/axe.min.js"))
            violations = page.evaluate(
                "async () => (await axe.run(document, "
                "{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations"
            )
            assert not violations, [{"id": item["id"]} for item in violations]
            page.screenshot(path=str(ROOT / f".data/header-menu-{theme}.png"))
            page.keyboard.press("Escape")
            passed.append(f"Open {theme} menu passes automated A/AA accessibility checks")

        toggle.click()
        page.set_viewport_size({"width": 1440, "height": 900})
        expect(panel).to_have_attribute("data-open", "false")
        expect(panel).to_be_visible()
        page.set_viewport_size({"width": 390, "height": 900})
        expect(panel).to_be_hidden()
        expect(toggle).to_have_attribute("aria-expanded", "false")
        passed.append("Resizing between desktop and compact layouts resets the menu safely")

        toggle.click()
        page.get_by_role("group", name="Appearance").get_by_role(
            "button", name="System", exact=True
        ).focus()
        page.keyboard.press("Tab")
        expect(panel).to_be_hidden()
        passed.append("Tab can leave the disclosure; navigation never traps keyboard focus")

        context = browser.new_context(
            java_script_enabled=False, viewport={"width": 390, "height": 900}
        )
        fallback = context.new_page()
        fallback.goto(base + "/blog", wait_until="networkidle")
        fallback_links = fallback.get_by_role("navigation", name="Main navigation").get_by_role(
            "link"
        )
        assert fallback_links.count() == 6
        expect(fallback_links.first).to_be_visible()
        expect(fallback_links.last).to_be_visible()
        passed.append("All navigation destinations remain available without JavaScript")
        browser.close()
    assert not errors, errors
    report = {"environment": base, "passed": passed, "browser_errors": errors, "failed": []}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
