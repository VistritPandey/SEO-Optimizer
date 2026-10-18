"""Cloud delivery keeps worker execution inside authenticated, retryable requests."""

from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

from seo_optimizer.application_models import ProjectCreate, ProjectSpec
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.task_dispatch import WAKE_PATH, WORK_PATH, dispatch
from seo_optimizer.web import create_app


@pytest.fixture
def service(tmp_path, monkeypatch):
    settings = Settings(
        data_dir=tmp_path,
        database_url=f"sqlite:///{tmp_path}/db.sqlite",
        secret_key="fixture-secret-with-thirty-two-characters",
    )
    store = Store(settings)
    monkeypatch.setenv("OPT_TASKS_QUEUE", "projects/demo/locations/us-central1/queues/work")
    monkeypatch.setenv("OPT_TASKS_ACCOUNT", "tasks@demo.iam.gserviceaccount.com")
    monkeypatch.setenv("OPT_TASKS_AUDIENCE", "https://example.run.app")
    verify = Mock(
        return_value={"email": "tasks@demo.iam.gserviceaccount.com", "email_verified": True}
    )
    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", verify)
    monkeypatch.setattr("google.auth.transport.requests.Request", Mock())
    send = Mock()
    monkeypatch.setattr("seo_optimizer.task_dispatch.dispatch", send)
    with TestClient(create_app(settings, store), raise_server_exceptions=False) as client:
        yield client, store, settings, verify, send
    store.close()


def test_task_identity_cannot_be_replaced_by_headers_or_customer_token(service):
    client, _, _, verify, send = service
    for path in (WORK_PATH, WAKE_PATH):
        assert client.post(path, headers={"X-CloudTasks-TaskName": "forged"}).status_code == 401
        verify.return_value = {"email": "customer@example.test", "email_verified": True}
        assert client.post(path, headers={"Authorization": "Bearer customer"}).status_code == 403
        verify.side_effect = ValueError("wrong audience")
        assert client.post(path, headers={"Authorization": "Bearer bad"}).status_code == 403
        verify.side_effect = None
    send.assert_not_called()


def test_dispatch_uses_oidc_deadline_and_future_delivery(service, monkeypatch):
    _, _, settings, _, _ = service
    sdk = MagicMock()
    monkeypatch.setattr("google.cloud.tasks_v2.CloudTasksClient", sdk)
    dispatch(settings, 30)
    call = sdk.return_value.__enter__.return_value.create_task.call_args
    request = call.kwargs["request"]
    assert request["parent"].endswith("/queues/work")
    task = request["task"]
    assert task["http_request"]["url"] == "https://example.run.app" + WORK_PATH
    assert task["http_request"]["oidc_token"]["audience"] == "https://example.run.app"
    assert task["dispatch_deadline"].total_seconds() == 1200
    assert task["schedule_time"].tzinfo is not None


def test_worker_runs_during_delivery_and_only_reschedules_pending_jobs(service, monkeypatch):
    client, store, _, _, send = service
    worker = Mock()
    worker.return_value.tick.return_value = False
    monkeypatch.setattr("seo_optimizer.worker.Worker", worker)
    header = {"Authorization": "Bearer valid-google-id-token"}
    assert client.post(WORK_PATH, headers=header).json() == {"worked": False}
    worker.return_value.tick.assert_called_once()
    send.assert_not_called()
    user, _ = store.create_user("fixture@example.test", "unused")
    project = store.create_project(
        user.id,
        ProjectCreate(
            spec=ProjectSpec(
                name="Fixture",
                website_url="https://example.test",
                auto_fix=False,
            )
        ),
    )
    assert store.has_pending_jobs()
    assert client.post(WORK_PATH, headers=header).status_code == 200
    assert send.call_args.kwargs["delay"] == 30
    job = store.jobs(user.id, project.id)[0]
    claimed = store.claim("test")
    assert claimed.id == job.id
    store.finish(user.id, job.id, "test", "complete", {})
    assert not store.has_pending_jobs()
    send.reset_mock()
    assert client.post(WAKE_PATH, headers=header).json() == {"scheduled": True}
    send.assert_called_once()


def test_dispatch_failure_is_retryable_and_never_loses_persisted_work(service, monkeypatch):
    client, store, _, _, send = service
    user, token = store.create_user("owner@example.test", "unused")
    send.side_effect = RuntimeError("queue temporarily unavailable")
    response = client.post(
        "/api/v1/projects",
        headers={"Authorization": "Bearer " + token},
        json={"spec": {"name": "Site", "website_url": "https://example.test"}},
    )
    assert response.status_code == 201
    assert store.has_pending_jobs()
    worker = Mock()
    monkeypatch.setattr("seo_optimizer.worker.Worker", worker)
    response = client.post(WORK_PATH, headers={"Authorization": "Bearer valid"})
    assert response.status_code == 500
    assert store.has_pending_jobs()
