"""Source audits wait for the correct deployment and do not confuse preview success."""

import time

import pytest
from fastapi import HTTPException

from seo_optimizer.application_models import ProjectCreate, ProjectSecrets, ProjectSpec
from seo_optimizer.followups import handle_event
from seo_optimizer.github import GitHubClient
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.worker import Worker

SHA = "a" * 40


@pytest.fixture
def project(tmp_path):
    store = Store(Settings(tmp_path, f"sqlite:///{tmp_path / 'state.db'}", "fixture"))
    owner, _ = store.create_user("owner@example.test", "hash")
    site = store.create_project(
        owner.id,
        ProjectCreate(
            spec=ProjectSpec(
                name="Example",
                repository="example/site",
                website_url="https://example.test/",
                wait_for_deployment=True,
            )
        ),
    )
    yield store, site
    store.close()


@pytest.mark.parametrize(
    "state,expected",
    [
        ("success", "ready"),
        ("failure", "failed"),
        ("error", "failed"),
        ("pending", "pending"),
        ("inactive", "pending"),
        (None, "pending"),
    ],
)
def test_deployment_status_requires_exact_revision_and_environment(monkeypatch, state, expected):
    client = GitHubClient(ProjectSecrets(github_token="fixture"))
    calls = []

    def request(method, path, **kwargs):
        calls.append(path)
        if path.endswith("/deployments"):
            assert kwargs["params"]["sha"] == SHA
            return [
                {"id": 1, "sha": "b" * 40, "environment": "Production"},
                {"id": 2, "sha": SHA, "environment": "Preview"},
                {"id": 3, "sha": SHA, "environment": "Production"},
            ]
        assert path.endswith("/3/statuses")
        return [{"state": state}] if state else []

    monkeypatch.setattr(client, "request", request)
    try:
        assert client.deployment_state("example/site", SHA, "production") == expected
        assert len(calls) == 2
    finally:
        client.close()


@pytest.mark.parametrize(
    "state,expired,expected",
    [
        ("pending", False, "waiting_deployment"),
        ("failed", False, "blocked"),
        ("pending", True, "blocked"),
    ],
)
def test_worker_never_crawls_or_edits_before_source_deployment(project, state, expired, expected):
    store, site = project
    job = store.jobs(site.tenant_id, site.id)[0]
    job.kind = "push"
    job.payload = {"after": SHA}
    if expired:
        job.created_at = time.time() - 3601

    class GitHub:
        def head(self, repo, branch):
            return SHA

        def deployment_state(self, repo, revision, environment):
            assert revision == SHA and environment == "production"
            return state

    status, result, delay = Worker(store, store.settings).audit_job(
        site,
        job,
        ProjectSpec.model_validate(site.spec),
        None,
        GitHub(),
    )
    assert status == expected
    assert result["awaiting_source_deployment"] and result["pending_revision"] == SHA
    assert delay == (15 if expected == "waiting_deployment" else 0)


def test_successful_deployment_reaudits_and_duplicate_delivery_is_idempotent(project):
    store, site = project
    payload = {
        "repository": {"full_name": "example/site"},
        "deployment": {"id": 1, "sha": SHA, "environment": "Production"},
        "deployment_status": {"state": "success"},
    }
    first = handle_event(store, site, "deployment_status", payload, "first")
    second = handle_event(store, site, "deployment_status", payload, "second")
    assert first["job_id"] == second["job_id"]
    job = store.job(site.tenant_id, first["job_id"])
    assert job.payload["after"] == SHA and job.payload["trigger"] == "successful_deployment"
    payload["deployment"]["environment"] = "Preview"
    assert handle_event(store, site, "deployment_status", payload, "preview")["status"] == "ignored"
    payload["deployment"]["environment"] = "Production"
    payload["deployment"]["sha"] = "not-a-revision"
    with pytest.raises(HTTPException) as error:
        handle_event(store, site, "deployment_status", payload, "bad")
    assert error.value.status_code == 400
