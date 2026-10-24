"""Tenant isolation, grounding, publication state, event replay and OAuth recovery."""

import hashlib
import hmac
import json
import time
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from seo_optimizer.application_models import ProjectCreate, ProjectSpec
from seo_optimizer.connectors import oauth
from seo_optimizer.connectors.events import handle, signature
from seo_optimizer.connectors.jobs import schedule
from seo_optimizer.connectors.models import (
    CollectionRequest,
    ConnectionInput,
    ImportRequest,
    Platform,
    ProposalInput,
)
from seo_optimizer.connectors.service import ConnectorService
from seo_optimizer.connectors.transport import ConnectorError
from seo_optimizer.contracts import TrustedFact, utc_now
from seo_optimizer.settings import Settings
from seo_optimizer.store import PrivateState, Store
from seo_optimizer.web import create_app


@pytest.fixture
def workspace(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        database_url=f"sqlite:///{tmp_path / 'control.db'}",
        secret_key="fixture-control-secret",
        allow_private_network=False,
    )
    store = Store(settings)
    owner, token = store.create_user("owner@example.test", "fixture-hash")
    other, other_token = store.create_user("other@example.test", "fixture-hash-other")
    project = store.create_project(
        owner.id,
        ProjectCreate(
            spec=ProjectSpec(
                name="Fixture lighting",
                website_url="https://example.test/",
                publishing_platform="website",
            )
        ),
    )
    yield store, settings, owner, token, other, other_token, project
    store.close()


@pytest.fixture
def publisher(workspace, monkeypatch):
    store, _, _, _, _, _, project = workspace
    monkeypatch.setattr("seo_optimizer.crawler.Crawler.check_url", lambda *args: ["93.184.216.34"])
    native = {
        "id": 1,
        "title": {"raw": "Desk lamps"},
        "content": {"raw": "Handmade desk lamps."},
        "status": "publish",
        "meta": {"seo_title": "", "seo_description": "Handmade desk lamps."},
        "modified_gmt": "revision-1",
        "link": "https://example.test/lamps/",
    }
    calls = []
    fail = {"write": False}

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            if fail["write"]:
                raise httpx.ReadTimeout("fixture-private-token", request=request)
            native["meta"].update(json.loads(request.content)["meta"])
            native["modified_gmt"] = "revision-" + str(len(calls))
        return httpx.Response(200, json=native if request.url.path.endswith("/1") else [native])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = ConnectorService(store, project, client)
    service.configure(
        ConnectionInput(
            platform="wordpress",
            resource="https://example.test",
            options={"seo_title_field": "seo_title", "seo_description_field": "seo_description"},
            credentials={
                "username": "fixture-user",
                "application_password": "fixture-private-token",
            },
            allow_writes=True,
        )
    )
    yield service, native, calls, fail
    client.close()


def proposal_for(service):
    result = service.collect(Platform.WORDPRESS, CollectionRequest())
    return service.propose(
        Platform.WORDPRESS,
        ProposalInput(
            resource_id="1",
            changes={"seo_title": "Desk lamps"},
            reason="Use the observed product title.",
            evidence_ids=[result["evidence_id"]],
        ),
    )


def test_credentials_encrypted_never_returned_and_tenant_scoped(workspace, publisher):
    store, settings, owner, token, other, other_token, project = workspace
    service, _, _, _ = publisher
    public = service.public(Platform.WORDPRESS)
    assert "fixture-private-token" not in json.dumps(public)
    with store.sessions() as session:
        encrypted = session.scalar(
            select(PrivateState.body).where(PrivateState.key == service.key(Platform.WORDPRESS))
        )
        assert "fixture-private-token" not in encrypted
    with TestClient(create_app(settings, store)) as api:
        path = f"/api/v1/projects/{project.id}/connectors"
        assert api.get(path).status_code == 401
        assert api.get(path, headers={"Authorization": "Bearer " + other_token}).status_code == 404
        response = api.get(path, headers={"Authorization": "Bearer " + token})
        assert response.status_code == 200 and len(response.json()["connections"]) == 22
        assert "fixture-private-token" not in response.text
        assert (
            api.put(
                path + "/wordpress",
                json={"platform": "wordpress", "resource": "https://evil.test"},
                headers={"Authorization": "Bearer " + token},
            ).status_code
            == 422
        )
    service.disconnect(Platform.WORDPRESS)
    assert not service.state(Platform.WORDPRESS)[0]


def test_source_conflict_blocks_write_and_healthy_change_does_nothing(publisher):
    service, native, calls, _ = publisher
    proposal = proposal_for(service)
    native["modified_gmt"] = "concurrent-human-edit"
    with pytest.raises(ConnectorError, match="Source changed"):
        service.publish(Platform.WORDPRESS, proposal["id"])
    assert all(r.method == "GET" for r in calls)
    assert service.state(Platform.WORDPRESS)[0]["lease_until"] == 0


def test_publish_readback_idempotence_and_safe_restore(publisher):
    service, native, calls, _ = publisher
    proposed = proposal_for(service)
    result = service.publish(Platform.WORDPRESS, proposed["id"])
    assert result["status"] == "verified"
    assert result["verification"]["provider_readback"]
    assert result["verification"]["deployed_site"] == "unverified"
    assert native["meta"]["seo_title"] == "Desk lamps"
    written = sum(r.method == "POST" for r in calls)
    service.publish(Platform.WORDPRESS, proposed["id"])
    assert sum(r.method == "POST" for r in calls) == written
    restored = service.publish(Platform.WORDPRESS, proposed["id"], rollback=True)
    assert restored["status"] == "rolled_back" and native["meta"]["seo_title"] == ""
    assert (
        native["status"] == "publish"
        and native["meta"]["seo_description"] == "Handmade desk lamps."
    )


def test_uncertain_write_cannot_be_automatically_retried(publisher):
    service, _, calls, fail = publisher
    proposed = proposal_for(service)
    fail["write"] = True
    with pytest.raises(ConnectorError) as error:
        service.publish(Platform.WORDPRESS, proposed["id"])
    assert error.value.code == "write_uncertain"
    assert service.public(Platform.WORDPRESS)["proposals"][0]["status"] == "write_uncertain"
    with pytest.raises(ConnectorError, match="cannot be safely repeated"):
        service.publish(Platform.WORDPRESS, proposed["id"])
    assert sum(r.method == "POST" for r in calls) == 1


def test_grounding_rejects_invented_claims_unknown_evidence_and_expired_facts(publisher):
    service, _, _, _ = publisher
    result = service.collect(Platform.WORDPRESS, CollectionRequest())
    base = {
        "resource_id": "1",
        "reason": "Unsupported invented claim.",
        "evidence_ids": [result["evidence_id"]],
    }
    with pytest.raises(ConnectorError, match="claims require"):
        service.propose(
            Platform.WORDPRESS,
            ProposalInput(**base, changes={"seo_title": "The world's best lamps with 500 reviews"}),
        )
    with pytest.raises(ConnectorError, match="Unknown evidence"):
        service.propose(
            Platform.WORDPRESS,
            ProposalInput(
                **{**base, "evidence_ids": ["invented"]}, changes={"seo_title": "Desk lamps"}
            ),
        )
    service.spec.facts = [
        TrustedFact(
            id="stale",
            name="Claim",
            value="Best lamps",
            source="owner",
            verified_at=utc_now() - timedelta(days=5),
            valid_until=utc_now() - timedelta(days=1),
        )
    ]
    with pytest.raises(ConnectorError, match="expired facts"):
        service.propose(
            Platform.WORDPRESS,
            ProposalInput(**base, changes={"seo_title": "Best lamps"}, fact_ids=["stale"]),
        )
    with pytest.raises(ConnectorError, match="unsupported fields"):
        service.propose(Platform.WORDPRESS, ProposalInput(**base, changes={"status": "publish"}))


def test_schema_rejects_privilege_escalation_and_untrusted_log_fields(workspace):
    service = ConnectorService(workspace[0], workspace[-1])
    with pytest.raises(ValueError):
        ConnectionInput(platform="wordpress", auto_apply=True)
    with pytest.raises(ConnectorError, match="read-only"):
        service.configure(ConnectionInput(platform="ga4", resource="123", allow_writes=True))
    service.configure(ConnectionInput(platform="server_logs", resource="https://example.test/"))
    row = {
        "path": "/",
        "status": 200,
        "user_agent": "GPTBot",
        "occurred_at": (utc_now() - timedelta(minutes=1)).isoformat(),
    }
    value = ImportRequest(kind="crawler", source="fixture log export", records=[row])
    evidence = service.import_records(Platform.SERVER_LOGS, value)
    assert not evidence["collection"]["records"][0]["fields"]["identity_verified"]
    with pytest.raises(ValueError):
        service.import_records(
            Platform.SERVER_LOGS,
            value.model_copy(update={"records": [{**row, "ip": "private visitor"}]}),
        )
    assert service.state(Platform.SERVER_LOGS)[0]["lease_until"] == 0


def test_consumer_answers_remain_separate_from_api_experiments(workspace):
    service = ConnectorService(workspace[0], workspace[-1])
    service.configure(ConnectionInput(platform="ai_visibility", resource="example.test"))
    evidence = service.import_records(
        Platform.AI_VISIBILITY,
        ImportRequest(
            kind="consumer_observation",
            source="Owner recorded browser observation",
            records=[
                {
                    "query": "Which lamps?",
                    "engine": "Perplexity consumer product",
                    "market": "United States",
                    "answer": "Desk lamps",
                    "cited_urls": ["https://example.test/", "javascript:alert(1)"],
                    "observed_at": (utc_now() - timedelta(minutes=1)).isoformat(),
                }
            ],
        ),
    )
    assert evidence["collection"]["measurement"] == "consumer_observation"
    assert evidence["collection"]["records"][0]["fields"]["cited_urls"] == ["https://example.test/"]


def test_scheduled_syncs_are_deduplicated_and_paid_experiments_are_explicit(workspace):
    service = ConnectorService(workspace[0], workspace[-1])
    service.configure(
        ConnectionInput(
            platform="ga4", resource="123", credentials={"access_token": "fixture-token"}
        )
    )
    service.configure(ConnectionInput(platform="dataforseo", resource="example.test"))
    service.configure(ConnectionInput(platform="ai_visibility", resource="example.test"))
    assert schedule(workspace[0], workspace[-1]) == 1
    assert schedule(workspace[0], workspace[-1]) == 0
    connectors = [j for j in workspace[0].jobs(workspace[2].id) if j.kind == "connector"]
    assert len(connectors) == 1 and connectors[0].payload["platform"] == "ga4"


def event_headers(secret, body):
    stamp = str(int(time.time()))
    return {"x-optimiser-timestamp": stamp, "x-optimiser-signature": signature(secret, stamp, body)}


def test_deployment_events_check_signatures_origin_scope_replays_and_order(workspace):
    service = ConnectorService(workspace[0], workspace[-1])
    service.configure(
        ConnectionInput(
            platform="deployment",
            resource="fixture-project",
            credentials={"webhook_secret": "fixture-event-secret"},
        )
    )
    event = {
        "event_id": "event-1",
        "resource": "fixture-project",
        "environment": "production",
        "revision": "fixture-sha",
        "url": "https://example.test/",
        "occurred_at": utc_now().isoformat(),
        "status": "succeeded",
        "changed_paths": ["web/index.html"],
    }
    raw = json.dumps(event).encode()
    headers = event_headers("fixture-event-secret", raw)
    with pytest.raises(ConnectorError, match="signature"):
        handle(service, Platform.DEPLOYMENT, {}, raw)
    result = handle(service, Platform.DEPLOYMENT, headers, raw)
    assert result["queued"]
    assert handle(service, Platform.DEPLOYMENT, headers, raw) == {"duplicate": True}
    for changed, expected in [
        ({"event_id": "other-env", "environment": "preview"}, "ignored"),
        ({"event_id": "backend-only", "changed_paths": ["backend/jobs.py"]}, "ignored"),
        (
            {"event_id": "old", "occurred_at": (utc_now() - timedelta(minutes=1)).isoformat()},
            "ignored",
        ),
    ]:
        body = json.dumps({**event, **changed}).encode()
        assert expected in handle(
            service, Platform.DEPLOYMENT, event_headers("fixture-event-secret", body), body
        )
    body = json.dumps({**event, "event_id": "bad-origin", "url": "https://evil.test/"}).encode()
    with pytest.raises(ConnectorError, match="origin"):
        handle(service, Platform.DEPLOYMENT, event_headers("fixture-event-secret", body), body)


def test_google_refresh_updates_encrypted_credentials(workspace):
    service = ConnectorService(workspace[0], workspace[-1])
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "fixture-new-token"})
        if request.headers.get("authorization") == "Bearer fixture-old-token":
            return httpx.Response(401, json={})
        return httpx.Response(200, json={"rows": [], "rowCount": 0})

    service.configure(
        ConnectionInput(
            platform="ga4",
            resource="123",
            credentials={
                "access_token": "fixture-old-token",
                "refresh_token": "fixture-refresh-token",
                "client_id": "fixture-client",
                "client_secret": "fixture-client-secret",
            },
        )
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service.client = client
        service.collect(Platform.GA4, CollectionRequest())
    assert len(requests) == 3
    assert (
        service.state(Platform.GA4)[0]["config"]["credentials"]["access_token"]
        == "fixture-new-token"
    )
    assert "fixture-new-token" not in json.dumps(service.public(Platform.GA4))


def test_oauth_state_is_single_use_project_bound_and_expiring(workspace, monkeypatch):
    store, _, owner, _, _, _, project = workspace
    monkeypatch.setenv("OPT_CONNECTOR_GOOGLE_CLIENT_ID", "fixture-client")
    monkeypatch.setenv("OPT_CONNECTOR_GOOGLE_CLIENT_SECRET", "fixture-client-secret")
    service = ConnectorService(store, project)
    service.configure(ConnectionInput(platform="ga4", resource="123"))
    url = oauth.begin(store, owner.id, project.id, Platform.GA4)
    query = parse_qs(urlparse(url).query)
    assert query["code_challenge_method"] == ["S256"] and "analytics.readonly" in query["scope"][0]
    state = query["state"][0]
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200,
                json={
                    "access_token": "fixture-oauth-token",
                    "refresh_token": "fixture-refresh-token",
                },
            )
        )
    ) as client:
        assert oauth.complete(store, state, "fixture-code", client) == (
            owner.id,
            project.id,
            Platform.GA4,
        )
        with pytest.raises(ConnectorError, match="already used"):
            oauth.complete(store, state, "fixture-code", client)
    url = oauth.begin(store, owner.id, project.id, Platform.GA4)
    state = parse_qs(urlparse(url).query)["state"][0]
    key = "connector-oauth:" + hashlib.sha256(state.encode()).hexdigest()
    saved, version = store.state(key)
    saved["expires"] = time.time() - 1
    store.save_state(key, saved, version)
    with pytest.raises(ConnectorError, match="expired"):
        oauth.complete(store, state, "fixture-code")


@pytest.mark.parametrize("platform", ["vercel", "netlify"])
def test_native_hosting_signatures_and_preview_filter(workspace, platform):
    import jwt

    from seo_optimizer.connectors.events import native_deployment

    service = ConnectorService(workspace[0], workspace[-1])
    p = Platform(platform)
    service.configure(
        ConnectionInput(
            platform=p,
            resource="hosting1",
            credentials={"webhook_secret": "fixture-native-hook-secret-32-bytes-long"},
        )
    )
    if platform == "vercel":
        event = {
            "id": "evt1",
            "type": "deployment.promoted",
            "createdAt": int(time.time() * 1000),
            "payload": {
                "project": {"id": "hosting1"},
                "target": "production",
                "deployment": {"id": "deployment1", "meta": {"githubCommitSha": "fixture-sha"}},
            },
        }
        raw = json.dumps(event).encode()
        headers = {
            "x-vercel-signature": hmac.new(
                b"fixture-native-hook-secret-32-bytes-long", raw, hashlib.sha1
            ).hexdigest()
        }
    else:
        event = {
            "id": "deploy1",
            "site_id": "hosting1",
            "state": "ready",
            "context": "production",
            "published_at": utc_now().isoformat(),
            "commit_ref": "fixture-sha",
        }
        raw = json.dumps(event).encode()
        headers = {
            "x-webhook-signature": jwt.encode(
                {"iss": "netlify", "sha256": hashlib.sha256(raw).hexdigest()},
                "fixture-native-hook-secret-32-bytes-long",
                algorithm="HS256",
            )
        }
    assert native_deployment(service, p, headers, raw)["queued"]
    assert native_deployment(service, p, headers, raw) == {"duplicate": True}
    with pytest.raises(ConnectorError, match="signature"):
        native_deployment(service, p, headers, raw + b" ")


def test_shopify_oauth_binds_shop_and_verifies_callback_hmac(workspace, monkeypatch):
    from urllib.parse import urlencode

    store, _, owner, _, _, _, project = workspace
    monkeypatch.setenv("OPT_CONNECTOR_SHOPIFY_CLIENT_ID", "fixture-shop-client")
    monkeypatch.setenv("OPT_CONNECTOR_SHOPIFY_CLIENT_SECRET", "fixture-shop-secret")
    service = ConnectorService(store, project)
    service.configure(
        ConnectionInput(platform="shopify", resource="fixture.myshopify.com", allow_writes=True)
    )
    url = oauth.begin(store, owner.id, project.id, Platform.SHOPIFY)
    assert urlparse(url).hostname == "fixture.myshopify.com"
    query = parse_qs(urlparse(url).query)
    assert query["scope"] == ["read_products,write_products"]
    callback = {
        "state": query["state"][0],
        "code": "fixture-code",
        "shop": "fixture.myshopify.com",
        "timestamp": str(int(time.time())),
    }
    message = urlencode(sorted(callback.items()))
    callback["hmac"] = hmac.new(
        b"fixture-shop-secret", message.encode(), hashlib.sha256
    ).hexdigest()
    calls = []

    def handler(request):
        calls.append(request)
        assert (
            request.url.host == "fixture.myshopify.com"
            and request.url.path == "/admin/oauth/access_token"
        )
        return httpx.Response(200, json={"access_token": "fixture-granted-token"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        oauth.complete(store, callback["state"], callback["code"], client, query=callback)
    assert len(calls) == 1
    assert "fixture-granted-token" not in json.dumps(service.public(Platform.SHOPIFY))


@pytest.mark.parametrize("platform", ["gitlab", "bitbucket", "shopify"])
def test_refresh_rotates_access_and_refresh_tokens(platform):
    from seo_optimizer.connectors.oauth import refresh_access

    config = ConnectionInput(
        platform=platform,
        resource="fixture.myshopify.com" if platform == "shopify" else "team/site",
        credentials={
            "access_token": "old-token",
            "refresh_token": "old-refresh",
            "client_id": "fixture-client",
            "client_secret": "fixture-client-secret",
        },
    )

    def handler(request):
        if platform == "bitbucket":
            assert request.headers["authorization"].startswith("Basic ")
        return httpx.Response(
            200, json={"access_token": "new-token", "refresh_token": "new-refresh"}
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        refresh_access(config, client)
    assert (
        config.credentials["access_token"] == "new-token"
        and config.credentials["refresh_token"] == "new-refresh"
    )


def test_private_pages_and_previews_never_receive_automatic_title_proposals(publisher):
    service, native, _, _ = publisher
    native["status"] = "private"
    result = service.collect(Platform.WORDPRESS, CollectionRequest())
    assert service.auto_propose(Platform.WORDPRESS, result["evidence_id"]) == []
    native["status"] = "publish"
    service.spec.environment = "preview"
    result = service.collect(Platform.WORDPRESS, CollectionRequest())
    assert service.auto_propose(Platform.WORDPRESS, result["evidence_id"]) == []


def test_repeat_collection_reuses_pending_proposal_and_refreshes_evidence(publisher):
    service, native, _, _ = publisher
    first = proposal_for(service)
    first_evidence = first["evidence_ids"]
    for _ in range(7):
        repeated = proposal_for(service)
        assert repeated["id"] == first["id"]
    assert repeated["evidence_ids"] != first_evidence
    state, _ = service.state(Platform.WORDPRESS)
    assert len(state["proposals"]) == 1
    assert set(repeated["evidence_ids"]) <= {e["id"] for e in state["evidence"]}
    applied = service.publish(Platform.WORDPRESS, repeated["id"])
    assert applied["verification"]["provider_readback"]
    assert native["meta"]["seo_title"] == "Desk lamps"


@pytest.mark.parametrize(
    "html,status,headers,expected",
    [
        ("<title>Theme title</title><h1>Desk lamps</h1>", 200, {}, False),
        ('<meta name="robots" content="noindex"><h1>Desk lamps</h1>', 200, {}, False),
        ("<h1>Desk lamps</h1>", 200, {"X-Robots-Tag": "noindex"}, False),
        ("<h1>Desk lamps</h1>", 503, {}, False),
        ("<h1>Desk lamps</h1>", 200, {}, True),
    ],
)
def test_wordpress_automatic_title_requires_live_defect_proof(
    publisher, monkeypatch, html, status, headers, expected
):
    service, _, _, _ = publisher
    monkeypatch.setattr(
        "seo_optimizer.crawler.Crawler.fetch",
        lambda self, url: httpx.Response(
            status,
            text=html,
            headers={"Content-Type": "text/html", **headers},
            request=httpx.Request("GET", url),
        ),
    )
    result = service.collect(Platform.WORDPRESS, CollectionRequest())
    proposals = service.auto_propose(Platform.WORDPRESS, result["evidence_id"])
    assert bool(proposals) is expected
    state, _ = service.state(Platform.WORDPRESS)
    proof = state["evidence"][-1]["live_observations"][0]
    assert proof["status_code"] == status
    assert proof["missing_title_confirmed"] is expected


def test_google_business_hours_require_facts_and_restore_structured_values(workspace):
    from seo_optimizer.contracts import TrustedFact

    service = ConnectorService(workspace[0], workspace[-1])
    before = {"periods": []}
    after = {
        "periods": [
            {
                "openDay": "MONDAY",
                "openTime": {"hours": 9},
                "closeDay": "MONDAY",
                "closeTime": {"hours": 17},
            }
        ]
    }
    current = {"hours": before}
    service.spec.facts = [
        TrustedFact(
            id="hours",
            name="Regular opening hours",
            value=after,
            source="Owner verified",
            verified_at=utc_now(),
        )
    ]
    service.configure(
        ConnectionInput(
            platform="business_profile",
            resource="locations/123",
            credentials={"access_token": "fixture-token"},
            allow_writes=True,
        )
    )

    def handler(request):
        if request.method == "PATCH":
            body = json.loads(request.content)
            assert set(body) == {"regularHours"}
            current["hours"] = body["regularHours"]
        return httpx.Response(
            200,
            json={
                "name": "locations/123",
                "title": "Fixture business",
                "regularHours": current["hours"],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service.client = client
        result = service.collect(Platform.BUSINESS_PROFILE, CollectionRequest())
        proposed = service.propose(
            Platform.BUSINESS_PROFILE,
            ProposalInput(
                resource_id="locations/123",
                changes={"regularHours": json.dumps(after)},
                reason="Use owner-verified regular hours.",
                evidence_ids=[result["evidence_id"]],
                fact_ids=["hours"],
            ),
        )
        assert service.publish(Platform.BUSINESS_PROFILE, proposed["id"])["verification"][
            "provider_readback"
        ]
        assert current["hours"] == after
        assert (
            service.publish(Platform.BUSINESS_PROFILE, proposed["id"], rollback=True)["status"]
            == "rolled_back"
        )
        assert current["hours"] == before


def test_connector_clock_runs_independently_of_full_site_audit_and_pauses_bad_access(workspace):
    from seo_optimizer.connectors.jobs import reconcile

    service = ConnectorService(workspace[0], workspace[-1])
    service.configure(ConnectionInput(platform="ga4", resource="123"))
    assert workspace[-1].next_audit > time.time()
    assert reconcile(workspace[0], workspace[2].id) == 1
    state, version = service.state(Platform.GA4)
    state.update(next_sync=time.time() - 1, status="credentials_required")
    service.save(Platform.GA4, state, version)
    assert workspace[0].connector_due(workspace[2].id) == []


def test_portable_worker_state_is_project_scoped_and_not_a_frontend_endpoint(workspace):
    from seo_optimizer.remote import RemoteStore

    store, settings, owner, token, other, other_token, project = workspace
    remote = RemoteStore(settings, "http://127.0.0.1:8000", token)
    remote.client.close()
    with TestClient(
        create_app(settings, store), headers={"Authorization": "Bearer " + token}
    ) as api:
        remote.client = api
        remote._projects[(owner.id, project.id)] = project
        service = ConnectorService(remote, project)
        service.configure(
            ConnectionInput(
                platform="ga4",
                resource="123",
                credentials={"access_token": "fixture-worker-access"},
            )
        )
        assert store.state(service.key(Platform.GA4))[0]["config"]["resource"] == "123"
        assert "fixture-worker-access" not in json.dumps(service.public(Platform.GA4))
        with pytest.raises(ValueError, match="confined"):
            remote.state(f"connector:{other.id}:{project.id}:ga4")
        assert (
            api.get(
                f"/api/v1/worker/connectors/{project.id}/ga4/state",
                headers={"Authorization": "Bearer " + other_token},
            ).status_code
            == 404
        )
