"""Exercise real public links, top-of-page navigation, anchors and history restoration."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3002")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/navigation-qa.json")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    passed, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chromium")
        for width in (1440, 390):
            context = browser.new_context(viewport={"width": width, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base, wait_until="networkidle")
            navigation = page.get_by_role("navigation", name="Main navigation")
            expect(navigation.get_by_role("link", name="Blog", exact=True)).to_have_attribute(
                "href", "/blog"
            )
            assert navigation.get_by_role("link", name="Journal", exact=True).count() == 0
            blog_link = page.get_by_role("navigation", name="Product links").get_by_role(
                "link", name="Blog & guides", exact=True
            )
            blog_link.scroll_into_view_if_needed()
            blog_link.evaluate(
                "a => a.addEventListener('click', () => {window.__departureScroll = scrollY}, "
                "{once:true,capture:true})"
            )
            blog_link.click()
            source_scroll = page.evaluate("window.__departureScroll")
            assert source_scroll > 1000
            expect(page).to_have_url(base + "/blog")
            page.wait_for_function("scrollY === 0")
            expect(page.locator("h1")).to_be_in_viewport()
            passed.append(f"{width}px: footer link opens the separate Blog page at the top")

            page.go_back()
            expect(page).to_have_url(base + "/")
            page.wait_for_function(
                "expected => Math.abs(scrollY - expected) < 5", arg=source_scroll
            )
            passed.append(f"{width}px: Back restores the original landing-page position")

            navigation.get_by_role("link", name="Blog", exact=True).click()
            expect(page).to_have_url(base + "/blog")
            page.wait_for_function("scrollY === 0")
            card = page.locator(".journal-card h3 a").first
            card.scroll_into_view_if_needed()
            article_path = card.get_attribute("href")
            card.click()
            expect(page).to_have_url(base + article_path)
            page.wait_for_function("scrollY === 0")
            expect(page.locator("h1")).to_be_in_viewport()
            passed.append(f"{width}px: article links open at their heading")

            section = page.locator(".article-sidebar nav a").first
            target = section.get_attribute("href")
            section.click()
            expect(page).to_have_url(base + article_path + target)
            page.wait_for_function(
                "id => {const r=document.querySelector(id).getBoundingClientRect();"
                "const h=document.querySelector('.marketing-nav').getBoundingClientRect();"
                "return r.top >= h.bottom"
                " && r.top < innerHeight / 2}",
                arg=target,
            )
            passed.append(f"{width}px: article contents links reach sections below the header")

            page.get_by_role("link", name="Watch the agent work →", exact=True).click()
            expect(page).to_have_url(base + "/how-it-works#agent-demo")
            page.wait_for_function(
                "() => {const r=document.querySelector('#agent-demo').getBoundingClientRect();"
                "return r.top >= 0 && r.top < innerHeight / 2}",
            )
            passed.append(f"{width}px: cross-page video anchors retain their intended destination")

            page.get_by_role("navigation", name="Product links").get_by_role(
                "link", name="Free plan", exact=True
            ).click()
            expect(page).to_have_url(base + "/#pricing")
            page.wait_for_function(
                "() => {const r=document.querySelector('#pricing').getBoundingClientRect();"
                "return r.top >= 0 && r.top < innerHeight / 2}",
            )
            navigation.get_by_role("link", name="Blog", exact=True).click()
            expect(page).to_have_url(base + "/blog")
            page.wait_for_function("scrollY === 0")
            passed.append(f"{width}px: pricing anchors work and Blog navigation starts at the top")
            context.close()
        browser.close()
    assert not errors, errors
    report = {"environment": base, "passed": passed, "browser_errors": errors, "failed": []}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
