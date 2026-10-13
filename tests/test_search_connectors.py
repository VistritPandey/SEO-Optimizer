"""Transport-controlled connector checks; no real credentials or external requests."""

from datetime import timedelta

import httpx
import pytest

from seo_optimizer.citations import normalize_interaction
from seo_optimizer.contracts import utc_now
from seo_optimizer.search_console import collect_search


def test_search_console_auth_dimensions_final_data_and_provenance():
    today = utc_now().date()

    def respond(request):
        import json

        assert request.url.host == "www.googleapis.com"
        assert request.headers["authorization"] == "Bearer controlled-oauth-token"
        body = json.loads(request.content)
        assert body["dimensions"] == ["query", "page", "country", "device"]
        assert body["dataState"] == "final"
        return httpx.Response(
            200,
            json={
                "rows": [
                    {
                        "keys": ["desk guide", "https://example.test/guide/", "usa", "MOBILE"],
                        "clicks": 3.0,
                        "impressions": 100.0,
                        "position": 8.5,
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        rows, report = collect_search(
            "https://example.test/",
            today - timedelta(days=7),
            today,
            "controlled-oauth-token",
            client,
        )
    assert rows[0].impressions == 100 and not rows[0].synthetic
    assert rows[0].business_relevance == "unknown"
    assert report["coverage"].startswith("Top rows only")


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_search_console_failure_does_not_leak_response_or_credentials(status):
    today = utc_now().date()
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(status, text="sensitive-response-and-token")
        )
    ) as client:
        with pytest.raises(ValueError, match=f"HTTP {status}") as failure:
            collect_search("https://example.test/", today, today, "controlled-oauth-token", client)
    assert "sensitive" not in str(failure.value) and "controlled-oauth-token" not in str(
        failure.value
    )


def test_search_console_requires_oauth_and_rejects_unexpected_pages():
    today = utc_now().date()
    with pytest.raises(ValueError, match="OAuth"):
        collect_search("https://example.test/", today, today, "")
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"rows": [{"keys": ["query", "https://other.test/", "usa", "MOBILE"]}]}
            )
        )
    ) as client:
        with pytest.raises(ValueError, match="unexpected"):
            collect_search("https://example.test/", today, today, "controlled", client)


def test_actual_citation_annotations_and_retrieval_are_separate_from_answer_claims():
    payload = {
        "id": "fixture",
        "steps": [
            {"type": "google_search_call"},
            {
                "type": "model_output",
                "content": [
                    {
                        "type": "text",
                        "text": "A sourced answer",
                        "annotations": [
                            {"type": "url_citation", "url": "https://example.test/guide/"}
                        ],
                    }
                ],
            },
        ],
    }
    observation = normalize_interaction(
        payload, "desk setup", "model-fixture", "experiment", "US", "baseline"
    )
    assert observation.retrieval_enabled and len(observation.cited_urls) == 1
    assert observation.citation_accuracy == "unreviewed" and not observation.synthetic
    payload["steps"].pop(0)
    with pytest.raises(ValueError, match="without"):
        normalize_interaction(
            payload, "desk setup", "model-fixture", "experiment", "US", "baseline"
        )
    empty = {
        "steps": [{"type": "model_output", "content": [{"type": "text", "text": "No search"}]}]
    }
    assert not normalize_interaction(
        empty, "desk setup", "model-fixture", "experiment", "US", "baseline"
    ).retrieval_enabled
