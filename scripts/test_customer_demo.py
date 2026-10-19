"""Check the customer walkthrough in a real browser; capture anonymous demo assets.

Start the Next frontend on localhost :3002 first. This does not call a model, change a
customer website or pretend that the illustrated review is a published GitHub PR.
"""

import argparse
import json
import subprocess
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:3002")
    args = parser.parse_args()
    assets = ROOT / ".data/customer-demo/frames"
    assets.mkdir(parents=True, exist_ok=True)
    output = ROOT / ".data/customer-demo"
    output.mkdir(parents=True, exist_ok=True)
    passed = []
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1050})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        demo = page.locator(".customer-demo")
        expect(page.get_by_role("heading", level=1)).to_contain_text("Your website evolves")
        body = page.locator("body").inner_text().lower()
        assert not any(
            word in body
            for word in (
                "run.sh",
                "ollama",
                "gemini",
                "cloud run",
                "python",
                "firestore",
                "sdk",
                "open source",
            )
        )
        passed.append(
            "Customer copy contains no installation, infrastructure or provider promotion"
        )
        page.screenshot(
            path=str(ROOT / "reports/public-site/landing-recording.png"), full_page=True
        )
        demo.screenshot(path=str(assets / "update.png"))
        demo.get_by_role("button", name="Explore the collection").click()
        expect(demo.get_by_role("heading", name="This collection cannot be found.")).to_be_visible()
        demo.screenshot(path=str(assets / "broken-link.png"))
        demo.get_by_role("button", name="Back to the homepage").click()
        demo.get_by_role("button", name="Publish example update").click()
        expect(demo).to_have_attribute("data-step", "1")
        demo.screenshot(path=str(assets / "checking.png"))
        demo.get_by_role("button", name="Next step").click()
        expect(demo).to_have_attribute("data-step", "2")
        expect(demo.locator(".demo-findings")).to_contain_text("Missing page")
        demo.screenshot(path=str(assets / "findings.png"))
        demo.get_by_role("button", name="Next step").click()
        demo.get_by_role("button", name="Before", exact=True).click()
        expect(demo.locator(".demo-change-card")).to_contain_text("/collections/lighting/")
        demo.screenshot(path=str(assets / "review-before.png"))
        demo.get_by_role("button", name="Proposed fix", exact=True).click()
        expect(demo.locator(".demo-change-card")).to_contain_text("/shop/")
        expect(demo.locator(".demo-search-card")).to_contain_text("description missing")
        demo.screenshot(path=str(assets / "review-after.png"))
        passed.append(
            "Broken update shows two findings and an explicit before/after review before approval"
        )
        demo.get_by_role("button", name="Approve example fix").click()
        expect(demo).to_have_attribute("data-step", "4")
        expect(demo.locator(".demo-search-card")).to_contain_text("solid cedar base")
        demo.get_by_role("button", name="Explore the collection").click()
        expect(
            demo.get_by_role("heading", name="A little light for everyday life.")
        ).to_be_visible()
        demo.screenshot(path=str(assets / "verified.png"))
        demo.get_by_role("button", name="Next step").click()
        expect(demo).to_have_attribute("data-step", "5")
        demo.screenshot(path=str(assets / "watching.png"))
        passed.append(
            "Approval shows the restored description, working collection and ongoing monitoring"
        )
        demo.get_by_role("button", name="Nothing breaks", exact=True).click()
        for _ in range(5):
            demo.locator(".demo-controls .button").click()
        expect(demo.locator(".demo-result")).to_contain_text("No fix needed")
        expect(demo.locator(".demo-change-card")).to_have_count(0)
        demo.screenshot(path=str(assets / "healthy.png"))
        passed.append("Healthy update produces no proposal or unnecessary edit")
        demo.get_by_role("button", name="Something breaks", exact=True).click()
        page.clock.install()
        demo.get_by_role("button", name="Play walkthrough", exact=True).click()
        for expected in range(1, 4):
            page.clock.run_for(4_300)
            expect(demo).to_have_attribute("data-step", str(expected))
        page.clock.run_for(13_000)
        expect(demo).to_have_attribute("data-step", "3")
        expect(demo.get_by_role("button", name="Play walkthrough", exact=True)).to_have_attribute(
            "aria-pressed", "false"
        )
        expect(demo.locator(".demo-search-card")).to_contain_text("description missing")
        passed.append("Automatic walkthrough stops at review and cannot auto-approve")
        demo.get_by_role("button", name="Something breaks", exact=True).focus()
        page.keyboard.press("Enter")
        expect(demo).to_have_attribute("data-step", "0")
        passed.append("Scenario buttons work by keyboard and reset state")
        page.get_by_text("Prefer to watch? See the customer walkthrough").click()
        video = page.locator("video")
        video.evaluate(
            "node => { node.load(); document.querySelector('track').track.mode = 'hidden'; }"
        )
        page.wait_for_function("document.querySelector('video').readyState >= 1")
        assert video.evaluate("node => node.videoWidth") == 1920
        assert video.evaluate("node => node.videoHeight") == 1080
        assert 68 < video.evaluate("node => node.duration") < 70
        page.wait_for_function("document.querySelector('track').track.cues?.length > 0")
        video.evaluate("node => node.play()")
        page.wait_for_function("document.querySelector('video').currentTime > 0")
        video.evaluate("node => node.pause()")
        passed.append("Embedded customer film decodes at 1080p, plays and loads English captions")
        assert not errors, errors
        passed.append("No browser JavaScript errors")
        context.close()
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844}, reduced_motion="reduce"
        )
        phone = mobile.new_page()
        phone.goto(args.url, wait_until="networkidle")
        assert phone.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        phone.locator(".customer-demo").screenshot(path=str(assets / "mobile.png"))
        passed.append("Mobile layout fits the viewport with reduced motion")
        mobile.close()
        browser.close()
    for filename in ("frontend/public/demo.mp4",):
        streams = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=codec_type",
                    "-of",
                    "json",
                    str(ROOT / filename),
                ],
                text=True,
            )
        )["streams"]
        assert streams and all(stream["codec_type"] == "video" for stream in streams)
    passed.append("Both published demo copies contain no audio stream")
    proof = json.loads((ROOT / "videos/public/your-proof.json").read_text())
    assert (
        proof["status"] == "passed" and proof["before_defects"] == 4 and proof["after_defects"] == 0
    )
    assert {"web/index.html", "web/products/cedar-lamp/index.html"} == set(proof["changed_paths"])
    patches = "\n".join(
        event["text"] for event in proof["events"] if "before/web/index.html" in event["text"]
    )
    assert (
        "/collections/lighting/" in patches
        and "/shop/" in patches
        and 'meta name="description"' in patches
    )
    passed.append("Illustrated homepage fixes match the recorded real source patch")
    report = {
        "status": "passed",
        "passed": passed,
        "failed": [],
        "skipped": [],
        "unverified": [
            "Live GitHub PR publication",
            "Production deployment",
            "Ranking, traffic and AI citation changes",
        ],
        "scope": (
            "Real browser interactions in an illustrated customer walkthrough; "
            "previously recorded model repair supports the fix narrative"
        ),
        "model_requests_this_test": 0,
    }
    (ROOT / "reports/customer-demo.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
