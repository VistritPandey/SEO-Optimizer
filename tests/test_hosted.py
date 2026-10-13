"""Managed policy and authenticated GitHub flows without external credentials."""

import hashlib
import hmac
import json
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from seo_optimizer.application_models import ProjectCreate, ProjectSecrets, ProjectSpec
from seo_optimizer.followups import handle_event, register_project
from seo_optimizer.github import GitHubClient
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import create_app


@pytest.fixture
def hosted(tmp_path: Path):
    settings = Settings(
        tmp_path,
        f"sqlite:///{tmp_path / 'test.db'}",
        "test-encryption-key" * 3,
        hosted=True,
        firebase_project="demo-your-optimiser",
        managed_key="managed-test-key",
        github_app_id="123",
        github_app_slug="example-app",
        github_client_id="client",
        github_client_secret="example-client-secret",
        github_private_key="example-pem",
        github_webhook_secret="example-webhook-secret",
    )
    store = Store(settings)
    account, token = store.create_user("owner@example.test", "!federated-only")
    client = TestClient(create_app(settings, store))
    yield settings, store, account, token, client
    store.close()


def test_managed_creation_and_tenant_isolation(hosted) -> None:
    settings, store, account, token, client = hosted
    headers = {"Authorization": "Bearer " + token}
    value = {
        "spec": {
            "name": "Example",
            "website_url": "https://example.test",
            "repository": "example/site",
            "provider": {"kind": "ollama", "base_url": "http://127.0.0.1:11434"},
            "auto_merge": True,
            "max_pages": 100,
        },
        "credentials": {"provider_key": "injected-key", "github_installation_id": "999"},
    }
    assert client.post("/api/v1/projects", json=value, headers=headers).status_code == 409
    store.save_state(
        "github-repo:" + account.id + ":example/site",
        {"installation": 456, "until": time.time() + 300},
        0,
    )
    response = client.post("/api/v1/projects", json=value, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["spec"]["provider"]["kind"] == "google"
    assert body["spec"]["provider"]["base_url"] is None
    assert not body["spec"]["auto_merge"]
    assert body["spec"]["max_pages"] == 25
    assert "managed-test-key" not in response.text and "injected-key" not in response.text
    project = store.project(account.id, body["id"])
    assert store.secrets(project).github_installation_id == "456"
    assert store.secrets(project).provider_key == settings.managed_key
    assert "managed-test-key" not in settings.cipher.decrypt(project.credentials.encode()).decode()
    assert (
        client.put(
            f"/api/v1/projects/{project.id}/credentials", json={}, headers=headers
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/worker/claim", json={"worker_id": "worker"}, headers=headers
        ).status_code
        == 403
    )
    assert client.post("/projects/new", data={}).status_code == 403
    other, other_token = store.create_user("other@example.test", "!federated-only")
    assert (
        client.get(
            f"/api/v1/projects/{project.id}/activity",
            headers={"Authorization": "Bearer " + other_token},
        ).status_code
        == 404
    )
    assert store.projects(other.id) == []


def test_oauth_callback_is_tenant_bound_single_use_and_private(hosted, monkeypatch) -> None:
    _, store, account, token, client = hosted
    result = client.post("/api/v1/github/connect", headers={"Authorization": "Bearer " + token})
    assert result.status_code == 200
    from urllib.parse import parse_qs, urlparse

    state = parse_qs(urlparse(result.json()["url"]).query)["state"][0]
    original = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("access_token"):
            return httpx.Response(
                200,
                json={
                    "access_token": "private-github-access",
                    "expires_in": 28800,
                    "refresh_token": "private-refresh",
                    "refresh_token_expires_in": 100000,
                },
            )
        return httpx.Response(200, json={"login": "example-owner"})

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler))
    )
    response = client.get(
        "/api/v1/github/callback",
        params={"code": "example-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].endswith("/dashboard?github=connected")
    grant, _ = store.state("github-grant:" + account.id)
    assert grant["token"] == "private-github-access"
    assert "private-github-access" not in response.text
    assert (
        client.get(
            "/api/v1/github/callback", params={"code": "example-code", "state": state}
        ).status_code
        == 400
    )


def connected_project(store, tenant: str):
    return store.create_project(
        tenant,
        ProjectCreate(
            spec=ProjectSpec(
                name="Site", website_url=HttpUrl("https://example.test"), repository="example/site"
            ),
            credentials=ProjectSecrets(
                github_token="test-token",
                github_installation_id="456",
                webhook_secret="example-webhook-secret",
            ),
        ),
    )


def test_central_webhooks_dedupe_push_and_revoke_installation(hosted) -> None:
    settings, store, account, _, client = hosted
    project = connected_project(store, account.id)
    register_project(store, project)
    payload = {
        "installation": {"id": 456},
        "repository": {"full_name": "example/site"},
        "ref": "refs/heads/main",
        "after": "a" * 40,
        "before": "b" * 40,
    }

    def deliver(event: str, body: dict):
        raw = json.dumps(body).encode()
        signature = (
            "sha256="
            + hmac.new(settings.github_webhook_secret.encode(), raw, hashlib.sha256).hexdigest()
        )
        return client.post(
            "/webhooks/github",
            content=raw,
            headers={"x-github-event": event, "x-hub-signature-256": signature},
        )

    first = deliver("push", payload).json()["results"][0]
    assert deliver("push", payload).json()["results"][0]["job_id"] == first["job_id"]
    assert client.post("/webhooks/github", json=payload).status_code == 403
    assert (
        deliver("installation", {"installation": {"id": 456}, "action": "deleted"}).status_code
        == 200
    )
    current = store.project(account.id, project.id)
    assert not current.spec["enabled"]
    assert not store.secrets(current).github_installation_id


def test_followup_requires_collaborator_and_tracked_same_repo_pr(hosted, monkeypatch) -> None:
    _, store, account, _, _ = hosted
    project = connected_project(store, account.id)
    claimed = store.claim("worker", account.id)
    store.finish(
        account.id,
        claimed.id,
        "worker",
        "complete",
        {"pr": {"number": 7, "head_sha": "a" * 40, "base_sha": "b" * 40}},
    )
    permission = "read"

    def request(self, method, path, **kwargs):
        if path.endswith("/permission"):
            return {"permission": permission}
        return {
            "state": "open",
            "head": {
                "sha": "a" * 40,
                "ref": "optimizer/example",
                "repo": {"full_name": "example/site"},
            },
        }

    monkeypatch.setattr(GitHubClient, "request", request)
    payload = {
        "repository": {"full_name": "example/site"},
        "action": "created",
        "issue": {"number": 7, "pull_request": {}},
        "comment": {"body": "Please recheck the canonical."},
        "sender": {"login": "example-reviewer", "type": "User"},
    }
    # Presence, not truthiness, of issue.pull_request identifies a PR issue.
    payload["issue"]["pull_request"] = {"url": "https://api.github.com/repos/example/site/pulls/7"}
    assert (
        handle_event(store, project, "issue_comment", payload, "delivery-one")["status"]
        == "unauthorized_reviewer"
    )
    permission = "write"
    first = handle_event(store, project, "issue_comment", payload, "delivery-one")
    assert first["status"] == "queued"
    assert (
        handle_event(store, project, "issue_comment", payload, "delivery-one")["job_id"]
        == first["job_id"]
    )
    assert store.job(account.id, first["job_id"]).kind == "followup"


def test_hosted_monthly_quota_is_atomic_and_local_is_unlimited(hosted) -> None:
    from dataclasses import replace

    _, store, account, _, _ = hosted
    store.settings = replace(store.settings, free_jobs_per_month=2)
    project = connected_project(store, account.id)
    store.enqueue(account.id, project.id, "audit", "one", {})
    with pytest.raises(ValueError, match="Monthly free"):
        store.enqueue(account.id, project.id, "audit", "two", {})
    store.settings = replace(store.settings, hosted=False)
    assert store.enqueue(account.id, project.id, "audit", "local", {}).status == "queued"
