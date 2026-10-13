"""Model latency cannot consume the following deployment-observation budget."""

import httpx

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.crawler import Crawler


def test_new_collection_gets_a_fresh_budget_after_long_inference(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("seo_optimizer.crawler.time.monotonic", lambda: clock[0])

    def respond(request):
        body = "<html><head><title>Cedar Workshop</title></head><body>Lighting</body></html>"
        if request.url.path == "/robots.txt":
            body = "User-agent: *\nAllow: /"
        return httpx.Response(200, text=body, headers={"Content-Type": "text/html"})

    client = httpx.Client(transport=httpx.MockTransport(respond))
    crawler = Crawler("http://127.0.0.1/", allow_private=True, client=client)
    spec = ProjectSpec(name="Synthetic storefront", website_url="http://127.0.0.1/")
    before = crawler.collect("tenant", "project", spec)
    clock[0] = 2000.0
    after = crawler.collect("tenant", "project", spec)
    assert before[0].data["status_code"] == after[0].data["status_code"] == 200
    assert crawler.deadline == 2120
    assert crawler.requests == 3
    client.close()
