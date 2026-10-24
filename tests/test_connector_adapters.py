"""Provider wire contracts with controlled HTTP responses, not claims of live access."""

import base64
import json
from datetime import timedelta

import httpx
import pytest

from seo_optimizer.connectors import measurements, publishing, repositories, visibility
from seo_optimizer.connectors.catalog import catalog
from seo_optimizer.connectors.models import CollectionRequest, ConnectionInput, Platform
from seo_optimizer.connectors.transport import ConnectorError, Transport
from seo_optimizer.contracts import utc_now


@pytest.fixture
def cms(monkeypatch):
    monkeypatch.setattr("seo_optimizer.crawler.Crawler.check_url", lambda *args: ["93.184.216.34"])
    fields = {"seo_title": "", "seo_description": "Original description"}
    requests = []

    def handler(request):
        requests.append(request)
        host, path = request.url.host, request.url.path
        payload = (
            json.loads(request.content)
            if request.content and "json" in request.headers.get("content-type", "")
            else {}
        )
        row = {
            "id": 1,
            "title": {"raw": "Desk lamps"},
            "content": {"raw": "Original description"},
            "status": "publish",
            "meta": {
                "seo_title": fields["seo_title"],
                "seo_description": fields["seo_description"],
            },
            "modified_gmt": str(len(requests)),
            "link": "https://example.test/lamps/",
        }
        if host == "example.test":
            if request.method in {"POST", "PUT"}:
                fields.update(payload.get("meta", {}))
            row["meta"] = dict(fields)
            if "wc/v3" in path:
                row = {
                    "id": 1,
                    "name": "Desk lamps",
                    "description": "Original description",
                    "short_description": "Short copy",
                    "status": "publish",
                    "permalink": "https://example.test/lamps/",
                }
            return httpx.Response(200, json=row if path.endswith("/1") else [row])
        if host.endswith("myshopify.com"):
            if "mutation" in payload.get("query", ""):
                fields.update(
                    {"seo_" + k: v for k, v in payload["variables"]["product"]["seo"].items()}
                )
                return httpx.Response(
                    200,
                    json={
                        "data": {
                            "productUpdate": {
                                "product": {"id": "gid://shopify/Product/1"},
                                "userErrors": [],
                            }
                        }
                    },
                )
            product = {
                "id": "gid://shopify/Product/1",
                "title": "Desk lamps",
                "descriptionHtml": "Original description",
                "seo": {"title": fields["seo_title"], "description": fields["seo_description"]},
                "updatedAt": "revision",
                "onlineStoreUrl": "https://example.test/lamps/",
            }
            return httpx.Response(
                200,
                json={"data": {"product": product}}
                if "id" in payload.get("variables", {})
                else {
                    "data": {"products": {"nodes": [product], "pageInfo": {"hasNextPage": False}}}
                },
            )
        if host == "api.webflow.com":
            if request.method == "PUT":
                fields.update({"seo_" + k: v for k, v in payload["seo"].items()})
            row = {
                "id": "page1",
                "title": "Desk lamps",
                "seo": {"title": fields["seo_title"], "description": fields["seo_description"]},
                "lastUpdated": "revision",
            }
            return httpx.Response(
                200,
                json=row
                if path.endswith("page1")
                else {"pages": [row], "pagination": {"total": 1}},
            )
        if host.endswith("sanity.io"):
            if request.method == "POST":
                assert payload["mutations"][0]["patch"]["ifRevisionID"] == "revision"
                fields.update(payload["mutations"][0]["patch"]["set"])
                return httpx.Response(200, json={"results": []})
            # This API version defaults to published content, even with an
            # authorized token. Existing drafts require an explicit perspective.
            if request.url.params.get("perspective") != "raw":
                return httpx.Response(
                    200, json={"result": None if "$id" in request.url.params else []}
                )
            row = {"_id": "drafts.page1", "_rev": "revision", "title": "Desk lamps", **fields}
            return httpx.Response(
                200, json={"result": row if "$id" in request.url.params else [row]}
            )
        if host == "api.contentful.com":
            if request.method == "PUT":
                assert request.headers["X-Contentful-Version"] == "2"
                assert payload["fields"]["unrelated"] == {"en-US": "Keep this"}
                fields.update(
                    {k: v["en-US"] for k, v in payload["fields"].items() if k.startswith("seo_")}
                )
            row = {
                "sys": {"id": "page1", "version": 2},
                "fields": {
                    "title": {"en-US": "Desk lamps"},
                    "unrelated": {"en-US": "Keep this"},
                    **{k: {"en-US": v} for k, v in fields.items()},
                },
            }
            return httpx.Response(
                200, json=row if path.endswith("page1") else {"items": [row], "total": 1}
            )
        if host == "api.squarespace.com":
            if request.method == "POST":
                assert payload["seoData"]["present"]
                fields.update({"seo_" + k: v for k, v in payload["seoData"]["value"].items()})
            row = {
                "id": "page1",
                "name": "Desk lamps",
                "description": "Original description",
                "seoOptions": {
                    "title": fields["seo_title"],
                    "description": fields["seo_description"],
                },
                "modifiedOn": "revision",
                "url": "https://example.test/lamps/",
            }
            return httpx.Response(
                200, json={"products": [row], "pagination": {"hasNextPage": False}}
            )
        if host == "www.wixapis.com":
            return httpx.Response(200, json={"tags": [{"type": "title", "children": "Desk lamps"}]})
        raise AssertionError((host, path, payload))

    return fields, requests, httpx.Client(transport=httpx.MockTransport(handler))


def config(platform, **updates):
    resource = {
        "wordpress": "https://example.test",
        "woocommerce": "https://example.test",
        "shopify": "fixture.myshopify.com",
        "webflow": "site1",
        "sanity": "project1",
        "contentful": "space1",
        "squarespace": "https://example.test",
        "wix": "site1",
    }.get(platform, "account1")
    return ConnectionInput(
        platform=platform,
        resource=resource,
        credentials={
            "access_token": "fixture-token",
            "username": "fixture",
            "application_password": "fixture-app-pass",
            "consumer_key": "fixture-key",
            "consumer_secret": "fixture-secret",
        },
        options={"seo_title_field": "seo_title", "seo_description_field": "seo_description"},
        **updates,
    )


@pytest.mark.parametrize(
    "platform",
    [
        "wordpress",
        "woocommerce",
        "shopify",
        "webflow",
        "sanity",
        "contentful",
        "squarespace",
        "wix",
    ],
)
def test_content_wire_contracts_preserve_other_values(platform, cms):
    fields, requests, client = cms
    t = Transport(config(platform), client)
    observed = publishing.collect(t, CollectionRequest())
    assert observed.records and observed.records[0].kind
    if platform not in {"wix", "woocommerce"}:
        current = observed.records[0]
        publishing.write(t, current, {"seo_title": "Desk lamps"})
        after = publishing.collect(t, CollectionRequest(resource_id=current.id, limit=1)).records[0]
        assert after.fields["seo_title"] == "Desk lamps"
        assert after.fields["seo_description"] == "Original description"
        assert fields["seo_description"] == "Original description"
        assert not any("publish" in r.url.path for r in requests)
    if platform == "woocommerce":
        publishing.write(t, observed.records[0], {"short_description": "Short copy"})
        assert "price" not in json.loads(requests[-1].content)
    if platform == "wix":
        with pytest.raises(ConnectorError, match="unsupported|supported"):
            publishing.write(t, observed.records[0], {"seo_title": "Desk lamps"})


@pytest.mark.parametrize(
    "platform,response,resource",
    [
        (
            "search_console",
            {
                "rows": [
                    {
                        "keys": ["lamps", "https://example.test/lamps/", "usa", "DESKTOP"],
                        "clicks": 3,
                        "impressions": 10,
                        "position": 2.2,
                    }
                ]
            },
            "https://example.test/",
        ),
        (
            "ga4",
            {
                "rows": [
                    {"dimensionValues": [{"value": "/lamps/"}], "metricValues": [{"value": "3"}]}
                ],
                "rowCount": 1,
            },
            "1234",
        ),
        ("bing", {"d": [{"Query": "lamps", "Clicks": 3}]}, "https://example.test/"),
        (
            "business_profile",
            {"name": "locations/123", "title": "Fixture lighting", "regularHours": {"periods": []}},
            "locations/123",
        ),
        (
            "vercel",
            {
                "deployments": [
                    {"uid": "d1", "url": "example.test", "state": "READY", "target": "production"}
                ]
            },
            "project1",
        ),
        (
            "netlify",
            [
                {
                    "id": "d1",
                    "ssl_url": "https://example.test",
                    "state": "ready",
                    "context": "production",
                }
            ],
            "site1",
        ),
        (
            "cloudflare",
            {
                "data": {
                    "viewer": {
                        "zones": [
                            {
                                "httpRequestsAdaptiveGroups": [
                                    {
                                        "count": 2,
                                        "dimensions": {
                                            "clientRequestPath": "/lamps/",
                                            "edgeResponseStatus": 200,
                                        },
                                    }
                                ]
                            }
                        ]
                    }
                }
            },
            "zone1",
        ),
        (
            "dataforseo",
            {
                "status_code": 20000,
                "cost": 0.01,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "type": "organic",
                                        "rank_group": 3,
                                        "url": "https://example.test/lamps/",
                                        "title": "Desk lamps",
                                    }
                                ]
                            }
                        ],
                    }
                ],
            },
            "example.test",
        ),
    ],
)
def test_measurement_wire_contracts_and_limits(platform, response, resource):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/sitemaps"):
            return httpx.Response(200, json={"sitemap": []})
        return httpx.Response(200, json=response)

    c = ConnectionInput(
        platform=platform,
        resource=resource,
        credentials={
            "access_token": "fixture-token",
            "api_key": "fixture-key",
            "username": "fixture-user",
            "password": "fixture-password",
        },
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = measurements.collect(Transport(c, client), CollectionRequest(query="desk lamps"))
    assert result.records and result.platform == platform
    assert len(calls) <= 2
    if platform == "dataforseo":
        assert result.cost_usd == 0.01 and result.records[0].fields["target_match"]
    if platform == "ga4":
        assert (
            json.loads(calls[0].content)["dimensionFilter"]["filter"]["stringFilter"]["value"]
            == "Organic Search"
        )


@pytest.mark.parametrize("platform", ["gitlab", "bitbucket"])
def test_git_reads_and_prs_do_not_merge_or_deploy(platform):
    calls = []

    def handler(request):
        calls.append(request)
        path = request.url.path
        if path.endswith("/merge_requests"):
            return httpx.Response(
                201, json={"web_url": "https://gitlab.com/team/site/-/merge_requests/1", "iid": 1}
            )
        if path.endswith("/pullrequests"):
            return httpx.Response(
                201,
                json={
                    "links": {"html": {"href": "https://bitbucket.org/team/site/pull-requests/1"}},
                    "id": 1,
                },
            )
        if request.method == "POST":
            return httpx.Response(201, json={"id": "fixture-commit"})
        if "/refs/branches/" in path:
            return httpx.Response(200, json={"target": {"hash": "fixture-sha"}})
        if platform == "gitlab":
            return httpx.Response(
                200,
                json={
                    "content": base64.b64encode(b"<head><title>Before</title></head>").decode(),
                    "last_commit_id": "fixture-sha",
                },
            )
        return httpx.Response(200, text="<head><title>Before</title></head>")

    c = ConnectionInput(
        platform=platform, resource="team/site", credentials={"access_token": "fixture-token"}
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        t = Transport(c, client)
        file = repositories.collect(t, CollectionRequest(resource_id="web/index.html")).records[0]
        pr = repositories.write(
            t,
            file,
            {"content": "<head><title>After</title></head>"},
            "optimizer/fixture",
            "Fix metadata",
            "Observed defect",
        )
    assert pr["number"] == 1 and not pr["merged"]
    assert not any("merge" == r.url.path.split("/")[-1] or "deploy" in r.url.path for r in calls)
    commit = next(
        r
        for r in calls
        if r.method == "POST" and (r.url.path.endswith("/commits") or r.url.path.endswith("/src"))
    )
    if platform == "gitlab":
        assert json.loads(commit.content)["actions"][0]["last_commit_id"] == "fixture-sha"
    else:
        assert b"fixture-sha" in commit.content


@pytest.mark.parametrize("engine", ["openai", "anthropic", "perplexity"])
def test_visibility_records_annotated_citations_not_guessed_links(engine):
    response = (
        {
            "content": [
                {"type": "web_search_tool_result", "content": []},
                {
                    "type": "text",
                    "text": "A grounded answer mentioning https://uncited.test/",
                    "citations": [
                        {"type": "web_search_result_location", "url": "https://example.test/"}
                    ],
                },
            ]
        }
        if engine == "anthropic"
        else {
            "status": "completed",
            "output": [
                {"type": "web_search_call" if engine == "openai" else "search_results"},
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "A grounded answer mentioning https://uncited.test/",
                            "annotations": [
                                {"type": "url_citation", "url": "https://example.test/"}
                            ],
                        }
                    ],
                },
            ],
            "usage": {"input_tokens": 1, "output_tokens": 2},
        }
    )

    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == "explicit-test-model"
        if engine == "perplexity":
            assert request.url.path == "/v1/agent"
        return httpx.Response(200, json=response)

    c = ConnectionInput(
        platform="ai_visibility",
        resource="example.test",
        credentials={engine + "_key": "fixture-key"},
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = visibility.collect(
            Transport(c, client),
            CollectionRequest(query="Which lamps?", model="explicit-test-model", engine=engine),
        )
    assert result.measurement == "api_experiment"
    assert result.records[0].fields["cited_urls"] == ["https://example.test/"]
    assert result.records[0].fields["target_cited"]
    assert "consumer" in result.warnings[0].lower()


def test_google_visibility_uses_existing_grounded_adapter(monkeypatch):
    from seo_optimizer.growth import CitationObservation

    observation = CitationObservation(
        id="fixture",
        experiment="visibility",
        query="Lamps?",
        engine="Google Search-grounded API",
        engine_version="explicit-test-model",
        arm="baseline",
        observed_at=utc_now(),
        market="United States",
        answer="Desk lamps",
        cited_urls=["https://example.test/"],
        source="controlled fixture",
        retrieval_enabled=True,
        citation_accuracy="unreviewed",
    )
    monkeypatch.setattr(
        "seo_optimizer.citations.collect_citation",
        lambda *args: (observation, {"usage": {"total_tokens": 3}}),
    )
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as client:
        result = visibility.collect(
            Transport(
                ConnectionInput(
                    platform="ai_visibility",
                    resource="example.test",
                    credentials={"google_key": "fixture-key"},
                ),
                client,
            ),
            CollectionRequest(query="Lamps?", model="explicit-test-model"),
        )
    assert result.measurement == "api_experiment" and result.records[0].fields["retrieval_enabled"]


def test_catalog_covers_every_promised_platform():
    names = {entry["platform"] for entry in catalog()}
    assert names == {p.value for p in Platform}
    assert len(names) == 22
    assert all(
        not entry["live_verified"] and entry["source"].startswith("https://") for entry in catalog()
    )


@pytest.mark.parametrize("status", [401, 403, 409, 412, 429, 500, 302])
def test_provider_failures_are_sanitized_and_writes_never_retry(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status,
            text="fixture-secret-should-not-escape",
            headers={"Retry-After": "30", "Location": "https://evil.test/"},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ConnectorError) as error:
            Transport(config("shopify"), client).request(
                "POST", "https://api.webflow.com/v2/pages/a", read_only=False
            )
    assert len(calls) == 1 and "fixture-secret" not in str(error.value)


def test_timeout_and_invalid_json_do_not_appear_successful():
    def handler(request):
        raise httpx.ReadTimeout("fixture-secret", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ConnectorError) as error:
            Transport(config("shopify"), client).request(
                "POST", "https://api.webflow.com/v2/pages/a", read_only=False
            )
        assert error.value.code == "write_uncertain" and "fixture-secret" not in str(error.value)
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text="<html>gateway</html>"))
    ) as client:
        with pytest.raises(ConnectorError, match="invalid JSON"):
            Transport(config("shopify"), client).request(
                "GET", "https://api.webflow.com/v2/pages/a"
            )


def test_measurement_window_and_body_budget():
    with pytest.raises(ValueError):
        CollectionRequest(start=utc_now().date(), end=utc_now().date() + timedelta(days=1))
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"x" * 2_000_001))
    ) as client:
        with pytest.raises(ConnectorError, match="2 MB"):
            Transport(config("shopify"), client).request(
                "GET", "https://api.webflow.com/v2/pages/a"
            )
