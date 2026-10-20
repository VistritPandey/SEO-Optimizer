import hashlib
import hmac
import json
import re
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from seo_optimizer.application_models import ProjectCreate
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import create_app, hash_password


@pytest.fixture
def application(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path,
        database_url=f"sqlite:///{tmp_path}/db.sqlite",
        secret_key="fixture-secret-key-which-is-long-enough",
        allowed_repo_roots=(tmp_path,),
    )
    store = Store(settings)
    alice, token = store.create_user("alice@example.test", hash_password("fixture-password-123"))
    bob, bob_token = store.create_user("bob@example.test", hash_password("fixture-password-456"))
    with TestClient(create_app(settings, store)) as client:
        yield client, store, alice, token, bob, bob_token
    store.engine.dispose()


def project_value() -> dict:
    return {
        "spec": {
            "name": "Fixture project",
            "website_url": "https://example.test/",
            "repository": "owner/site",
        },
        "credentials": {
            "github_token": "fixture-private-value",
            "webhook_secret": "webhook-fixture-secret",
        },
    }


def test_registration_login_csrf_and_secret_exports(application):
    client, store, alice, token, _, _ = application
    page = client.get("/login")
    csrf = re.search(r'name="csrf" value="([^"]+)"', page.text)[1]
    assert (
        client.post(
            "/login", data={"email": alice.email, "password": "fixture-password-123"}
        ).status_code
        == 403
    )
    login = client.post(
        "/login", data={"csrf": csrf, "email": alice.email, "password": "fixture-password-123"}
    )
    assert login.status_code == 200 and "Your websites" in login.text
    assert client.post("/api/v1/projects", json=project_value()).status_code == 403
    response = client.post(
        "/api/v1/projects", headers={"Authorization": "Bearer " + token}, json=project_value()
    )
    assert response.status_code == 201
    assert "fixture-private-value" not in response.text
    assert "credentials" not in response.json()
    project = store.project(alice.id, response.json()["id"])
    assert "fixture-private-value" not in project.credentials
    assert store.secrets(project).github_token == "fixture-private-value"


def test_cross_tenant_access_and_worker_scope(application):
    client, store, alice, token, bob, bob_token = application
    project = store.create_project(alice.id, ProjectCreate.model_validate(project_value()))
    headers = {"Authorization": "Bearer " + bob_token}
    assert client.get(f"/api/v1/projects/{project.id}", headers=headers).status_code == 404
    assert (
        client.patch(
            f"/api/v1/projects/{project.id}", headers=headers, json=project.spec
        ).status_code
        == 404
    )
    assert client.get("/api/v1/projects", headers=headers).json() == []
    assert (
        client.post(
            "/api/v1/worker/claim", headers=headers, json={"worker_id": "bob-worker"}
        ).json()
        is None
    )
    job = store.jobs(alice.id)[0]
    assert client.get(f"/api/v1/jobs/{job.id}", headers=headers).status_code == 404
    own = client.post(
        "/api/v1/worker/claim",
        headers={"Authorization": "Bearer " + token},
        json={"worker_id": "alice-worker"},
    )
    assert own.json()["credentials"]["github_token"] == "fixture-private-value"
    assert (
        client.post(
            f"/api/v1/worker/jobs/{job.id}/finish",
            headers=headers,
            json={"worker_id": "alice-worker", "status": "complete", "result": {}},
        ).status_code
        == 409
    )


def test_webhook_signature_replay_branch_and_repository(application):
    client, store, alice, _, _, _ = application
    project = store.create_project(alice.id, ProjectCreate.model_validate(project_value()))
    payload = {
        "repository": {"full_name": "owner/site"},
        "ref": "refs/heads/main",
        "after": "a" * 40,
        "before": "b" * 40,
    }
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"webhook-fixture-secret", body, hashlib.sha256).hexdigest()
    path = f"/webhooks/github/{project.id}"
    assert client.post(path, content=body, headers={"x-github-event": "push"}).status_code == 403
    headers = {"x-github-event": "push", "x-hub-signature-256": signature}
    first = client.post(path, content=body, headers=headers)
    second = client.post(path, content=body, headers=headers)
    assert first.json()["job_id"] == second.json()["job_id"]
    assert len(store.jobs(alice.id)) == 2


def test_job_claim_lease_and_wrong_worker(application, monkeypatch):
    _, store, alice, _, _, _ = application
    store.create_project(alice.id, ProjectCreate.model_validate(project_value()))
    claimed = store.claim("first", alice.id)
    assert claimed is not None
    assert store.claim("second", alice.id) is None
    with pytest.raises(ValueError, match="lease"):
        store.finish(alice.id, claimed.id, "second", "complete", {})
    expired = time.time() + 901
    monkeypatch.setattr("seo_optimizer.store.time.time", lambda: expired)
    recovered = store.claim("second", alice.id)
    assert recovered.id == claimed.id and recovered.attempts == 2
    store.finish(alice.id, recovered.id, "second", "complete", {"summary": "Recovered"})
    assert store.job(alice.id, claimed.id).status == "complete"


def test_findings_deduplicate_and_resolve(application):
    _, store, alice, _, _, _ = application
    project = store.create_project(alice.id, ProjectCreate.model_validate(project_value()))
    finding = {"check_id": "tech.title", "url": "https://example.test/", "summary": "Missing title"}
    assert store.remember_findings(alice.id, project.id, [finding], [finding["url"]]) == 1
    assert store.remember_findings(alice.id, project.id, [finding], [finding["url"]]) == 0
    store.remember_findings(alice.id, project.id, [], [finding["url"]])
    assert not store.findings(alice.id, project.id)[0].active


def test_html_views_escape_untrusted_project_names(application):
    client, store, alice, token, _, _ = application
    value = project_value()
    value["spec"]["name"] = '<script>alert("x")</script>'
    project = store.create_project(alice.id, ProjectCreate.model_validate(value))
    page = client.get(f"/projects/{project.id}", headers={"Authorization": "Bearer " + token})
    assert page.status_code == 200
    assert '<script>alert("x")</script>' not in page.text
    assert "&lt;script&gt;" in page.text
    assert "fixture-private-value" not in page.text


def test_public_host_disables_local_repositories(application):
    client, store, alice, token, _, _ = application
    settings = store.settings
    from dataclasses import replace

    app = create_app(replace(settings, allow_local_repositories=False), store)
    with TestClient(app) as hosted:
        value = project_value()
        value["spec"]["repository"] = ""
        value["spec"]["local_path"] = "/tmp/private"
        assert (
            hosted.post(
                "/api/v1/projects", headers={"Authorization": "Bearer " + token}, json=value
            ).status_code
            == 400
        )


def test_registration_creates_separate_workspace(application):
    client, store, _, _, _, _ = application
    page = client.get("/register")
    csrf = re.search(r'name="csrf" value="([^"]+)"', page.text)[1]
    response = client.post(
        "/register",
        data={"csrf": csrf, "email": "new@example.test", "password": "new-password-1234"},
    )
    assert response.status_code == 200 and "Connect your first website" in response.text
    assert store.user(email="new@example.test") is not None


def test_reconcile_is_scoped(application):
    client, store, alice, token, bob, _ = application
    a = store.create_project(alice.id, ProjectCreate.model_validate(project_value()))
    b = store.create_project(bob.id, ProjectCreate.model_validate(project_value()))
    from seo_optimizer.store import Project

    with store.sessions.begin() as session:
        session.execute(update(Project).where(Project.id.in_([a.id, b.id])).values(next_audit=0))
    result = client.post("/api/v1/reconcile", headers={"Authorization": "Bearer " + token})
    assert result.json()["scheduled"] == 1
    assert len(store.jobs(alice.id)) == 2 and len(store.jobs(bob.id)) == 1


def test_live_progress_scoped_bounded_and_requires_active_lease(application, monkeypatch):
    client, store, alice, token, bob, bob_token = application
    project = store.create_project(alice.id, ProjectCreate.model_validate(project_value()))
    job = store.claim("first", alice.id)
    endpoint = f"/api/v1/worker/jobs/{job.id}/progress"
    payload = {"worker_id": "first", "message": "Collecting page evidence"}
    headers = {"Authorization": "Bearer " + token}
    assert client.post(endpoint, json=payload).status_code == 401
    assert (
        client.post(
            endpoint, headers={"Authorization": "Bearer " + bob_token}, json=payload
        ).status_code
        == 409
    )
    assert (
        client.post(endpoint, headers=headers, json={**payload, "worker_id": "other"}).status_code
        == 409
    )
    assert client.post(endpoint, headers=headers, json={**payload, "message": 1}).status_code == 400
    assert client.post(endpoint, headers=headers, json=payload).status_code == 200
    for index in range(105):
        store.progress(alice.id, job.id, "first", f"Observation {index}")
    updated = store.job(alice.id, job.id)
    assert len(updated.events) == 100
    assert updated.events[-1]["message"] == "Observation 104"
    assert updated.events[-1]["time"] >= job.created_at
    assert updated.status == "running" and updated.lease_until == job.lease_until
    assert store.claim("second", alice.id) is None
    expired = time.time() + 901
    monkeypatch.setattr("seo_optimizer.store.time.time", lambda: expired)
    with pytest.raises(ValueError, match="lease"):
        store.progress(alice.id, job.id, "first", "Expired")
    recovered = store.claim("second", alice.id)
    store.finish(alice.id, recovered.id, "second", "complete", {})
    with pytest.raises(ValueError, match="lease"):
        store.progress(alice.id, recovered.id, "second", "Already complete")
    assert store.project(alice.id, project.id).id == project.id
