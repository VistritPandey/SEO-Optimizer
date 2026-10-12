import json

import httpx

from seo_optimizer.performance import collect_performance


def test_official_measurements_keep_lab_and_missing_field_separate(monkeypatch):
    monkeypatch.setattr(
        "seo_optimizer.crawler.socket.getaddrinfo",
        lambda *args: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    requests = []

    def transport(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "analysisUTCTimestamp": "2026-10-12T12:00:00Z",
                "lighthouseResult": {
                    "lighthouseVersion": "fixture",
                    "finalUrl": "https://example.test/",
                    "categories": {"performance": {"score": 0.72}},
                    "audits": {"largest-contentful-paint": {"numericValue": 2700}},
                },
            },
        )

    evidence = collect_performance(
        "https://example.test/",
        "tenant",
        "project",
        "production",
        "controlled-private-key",
        client=httpx.Client(transport=httpx.MockTransport(transport)),
    )
    assert evidence.data["lab_score"] == 0.72
    assert evidence.data["lab"]["largest-contentful-paint"] == 2700
    assert evidence.data["field_url"] is None and evidence.data["field_origin"] is None
    assert requests[0].url.host == "www.googleapis.com"
    assert "controlled-private-key" not in json.dumps(evidence.model_dump(mode="json"))


def test_failed_diagnostic_records_dependency_and_hides_credentials(monkeypatch):
    monkeypatch.setattr(
        "seo_optimizer.crawler.socket.getaddrinfo",
        lambda *args: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    evidence = collect_performance(
        "https://example.test/",
        "tenant",
        "project",
        "production",
        "controlled-private-key",
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(429))),
    )
    assert evidence.data["collection_error"] == "ValueError"
    assert "controlled-private-key" not in evidence.model_dump_json()


def test_private_diagnostic_never_calls_external_service():
    requests = []
    client = httpx.Client(transport=httpx.MockTransport(lambda request: requests.append(request)))
    evidence = collect_performance(
        "http://127.0.0.1/", "tenant", "project", "production", client=client
    )
    assert evidence.data["collection_error"] and not requests
