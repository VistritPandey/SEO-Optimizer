"""Exercise the served contact form while intercepting every Formspree submission.

Synthetic requests never leave the browser fixture or generate support messages.
Inbox delivery and Formspree account configuration are separate live checks.
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://formspree.io/f/xdoqkdpy"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3002")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/contact-form-qa.json")
    args = parser.parse_args()
    passed = []
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="chromium")
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        pending = []
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route(ENDPOINT, lambda route: pending.append(route))
        page.clock.install()
        page.goto(args.base_url + "/contact", wait_until="networkidle")
        form = page.get_by_role("form", name="Contact Your Optimiser")
        expect(form).to_have_attribute("action", ENDPOINT)
        expect(form).to_have_attribute("method", "POST")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        form.get_by_role("button", name="Send message").click()
        assert not pending
        page.get_by_label("Your name", exact=True).fill("Demo visitor")
        page.get_by_label("Email address", exact=True).fill("invalid-email")
        page.get_by_label("Your message", exact=True).fill("A fictional support question.")
        form.get_by_role("button", name="Send message").click()
        assert not pending
        passed.append("Native required-field and email validation prevent invalid submissions")

        def send():
            page.get_by_label("Your name", exact=True).fill("Demo visitor")
            page.get_by_label("Email address", exact=True).fill("demo@example.invalid")
            page.get_by_label("What can we help with?").select_option("Something isn’t working")
            page.get_by_label("Your message", exact=True).fill("A fictional support question.")
            form.get_by_role("button", name="Send message").click()
            expect(form.get_by_role("button", name="Sending…", exact=True)).to_be_disabled()
            expect(form).to_have_attribute("aria-busy", "true")
            assert len(pending) == 1
            route = pending.pop()
            request = route.request
            assert request.method == "POST"
            assert request.headers["accept"] == "application/json"
            assert "authorization" not in request.headers and "cookie" not in request.headers
            payload = request.post_data
            assert "demo@example.invalid" in payload and "A fictional support question." in payload
            assert 'name="_subject"' in payload and 'name="topic"' in payload
            return route

        def respond(route, status, body, content_type="application/json"):
            route.fulfill(
                status=status,
                content_type=content_type,
                headers={"Access-Control-Allow-Origin": "*"},
                body=body if isinstance(body, str) else json.dumps(body),
            )

        first = send()
        form.evaluate("f => f.requestSubmit()")
        page.clock.fast_forward(5000)
        assert not pending
        respond(first, 422, {"errors": [{"field": "message", "message": "Invalid message"}]})
        expect(form.get_by_role("alert")).to_contain_text("could not be submitted")
        expect(page.get_by_label("Your message", exact=True)).to_have_value(
            "A fictional support question."
        )
        page.clock.fast_forward(5000)
        assert not pending
        passed.append("Pending submissions cannot duplicate; rejected messages remain editable")

        for status, body, kind in [
            (200, "<html>Unexpected gateway response</html>", "text/html"),
            (200, "{invalid", "application/json"),
            (200, {"ok": False}, "application/json"),
            (200, {}, "application/json"),
            (429, {"errors": [{"message": "Limit reached"}]}, "application/json"),
        ]:
            route = send()
            respond(route, status, body, kind)
            expect(form.get_by_role("alert")).to_be_visible()
            expect(form.get_by_role("button", name="Send message")).to_be_enabled()
            expect(page.get_by_label("Email address", exact=True)).to_have_value(
                "demo@example.invalid"
            )
        passed.append("Malformed, HTML, unacknowledged and rate-limited replies never show success")
        send().abort("failed")
        expect(form.get_by_role("alert")).to_contain_text("couldn’t confirm")
        expect(page.get_by_label("Your message", exact=True)).to_have_value(
            "A fictional support question."
        )
        passed.append("Network failure preserves the message without automatic POST retries")

        success = send()
        respond(success, 200, {"ok": True, "next": "/thanks"})
        expect(form.get_by_role("status")).to_contain_text("Your message has been submitted")
        expect(page.get_by_label("Your message", exact=True)).to_have_value("")
        expect(page.get_by_label("Email address", exact=True)).to_have_value("")
        assert page.url == args.base_url + "/contact"
        passed.append("Acknowledged submissions show an inline confirmation and clear the form")

        send()
        page.clock.fast_forward(20_001)
        expect(form.get_by_role("alert")).to_contain_text("couldn’t confirm")
        expect(form.get_by_role("button", name="Send message")).to_be_enabled()
        passed.append("Timed-out submissions recover and retain the message")
        page.locator('[name="_gotcha"]').evaluate("e => { e.value = 'bot'; }")
        form.get_by_role("button", name="Send message").click()
        assert not pending
        passed.append("Honeypot submissions do not contact the provider")
        page.locator('[name="_gotcha"]').evaluate("e => { e.value = ''; }")
        form.get_by_role("button", name="Continue with secure submission").click(no_wait_after=True)
        assert len(pending) == 1
        fallback = pending.pop()
        assert fallback.request.method == "POST"
        assert fallback.request.is_navigation_request()
        assert "demo%40example.invalid" in fallback.request.post_data
        respond(fallback, 200, "<h1>Secure verification fixture</h1>", "text/html")
        expect(page.get_by_role("heading", name="Secure verification fixture")).to_be_visible()
        passed.append("Optional native submission preserves fields for provider verification")
        assert not errors, errors
        context.close()

        static = browser.new_context(java_script_enabled=False)
        page = static.new_page()
        page.goto(args.base_url + "/contact", wait_until="networkidle")
        native = page.get_by_role("form", name="Contact Your Optimiser")
        expect(native).to_have_attribute("action", ENDPOINT)
        expect(page.get_by_label("Your message", exact=True)).to_be_visible()
        assert native.locator('[type="submit"]').is_enabled()
        passed.append("Server-rendered form retains native Formspree submission without JavaScript")
        static.close()
        browser.close()
    report = {
        "environment": args.base_url,
        "passed": passed,
        "failed": [],
        "actual_provider_submissions": 0,
        "unverified": ["Live Formspree acceptance, account limits, CAPTCHA and inbox delivery"],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
