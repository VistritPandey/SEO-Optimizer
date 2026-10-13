"""Actual isolated Git/HTTP publication and scoped dashboard/API research flow."""

import threading
from functools import partial
from http.server import ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient
from test_growth import PASSAGE, setup

from seo_optimizer.application_models import ProjectCreate
from seo_optimizer.execution import run_git
from seo_optimizer.growth import Workspace, plan
from seo_optimizer.repair_benchmark import QuietHandler
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import create_app, hash_password
from seo_optimizer.worker import Worker


def make_store(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{tmp_path}/db.sqlite",
        secret_key="controlled-long-secret",
        allowed_repo_roots=(tmp_path,),
    )
    settings.data_dir.mkdir()
    store = Store(settings)
    owner, token = store.create_user("owner@example.test", hash_password("fixture-password-123"))
    return store, settings, owner, token


def test_workspace_api_isolation_validation_and_strategy_job(tmp_path):
    store, settings, owner, token = make_store(tmp_path)
    other, other_token = store.create_user(
        "other@example.test", hash_password("fixture-password-456")
    )
    spec, workspace = setup()
    project = store.create_project(owner.id, ProjectCreate(spec=spec))
    endpoint = f"/api/v1/projects/{project.id}/workspace"
    with TestClient(create_app(settings, store)) as client:
        headers = {"Authorization": "Bearer " + token}
        assert client.get(endpoint).status_code == 401
        assert (
            client.get(endpoint, headers={"Authorization": "Bearer " + other_token}).status_code
            == 404
        )
        assert (
            client.put(
                endpoint, json=workspace.model_dump(mode="json"), headers=headers
            ).status_code
            == 200
        )
        assert store.workspace(owner.id, project.id).materials[0].id == "notebook"
        with pytest.raises(ValueError, match="Project not found"):
            store.workspace(other.id, project.id)
        bad = workspace.model_dump(mode="json")
        bad["materials"][0]["fact_ids"] = ["invented"]
        assert client.put(endpoint, json=bad, headers=headers).status_code == 400
        assert client.get(f"/projects/{project.id}/research", headers=headers).status_code == 200
        response = client.get(f"/api/v1/projects/{project.id}/strategy", headers=headers)
        assert response.json()["opportunities"][0]["brief"]["ready"]
        assert (
            client.post(f"/api/v1/projects/{project.id}/strategy", headers=headers).status_code
            == 202
        )
        job = next(j for j in store.jobs(owner.id) if j.kind == "strategy")
        status, result, _ = Worker(store, settings).process(project, job)
        assert status == "complete" and result["strategy"]["opportunities"][0]["synthetic"]
        assert store.workspace(owner.id, project.id).model_dump() == workspace.model_dump()
    store.engine.dispose()


@pytest.mark.integration
@pytest.mark.enable_socket
@pytest.mark.allow_hosts(["127.0.0.1"])
def test_autonomous_original_refresh_served_verification_and_repeat(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    (repository / "web/guide").mkdir(parents=True)
    (repository / "web/index.html").write_text(
        "<html><head><title>Lighting</title>"
        '<meta name="description" content="Lighting guide"></head>'
        '<body><main><a href="/guide/">Guide</a></main></body></html>'
    )
    page = repository / "web/guide/index.html"
    page.write_text(
        '<html><head><title>Desk guide</title><meta name="description" content="Desk '
        'guide"></head><body><main><h1>Desk setup</h1></main></body></html>'
    )
    run_git(repository, "init", "-b", "main")
    run_git(repository, "add", ".")
    run_git(
        repository,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@localhost",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "Add fixture",
    )
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(repository / "web"))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    store, settings, owner, _ = make_store(tmp_path)
    spec, workspace = setup(f"http://127.0.0.1:{server.server_port}")
    spec.route_map = {"/": "web/index.html", "/guide/": "web/guide/index.html"}
    spec.local_path = str(repository)
    spec.auto_content_refresh = True
    project = store.create_project(owner.id, ProjectCreate(spec=spec))
    store.save_workspace(owner.id, project.id, workspace)

    # Controlled build adapter. Git, HTTP, policy, publication and served checks are real;
    # actual Docker execution is exercised separately in the recorded live demonstration.
    def check(root, configured, files):
        assert PASSAGE in (root / "web/guide/index.html").read_text()
        return [{"passed": True, "source": "controlled build adapter"}]

    monkeypatch.setattr("seo_optimizer.worker.verify_workspace", check)
    worker = Worker(store, settings)
    try:
        assert worker.tick(owner.id)  # Audit automatically schedules strategy.
        assert worker.tick(owner.id)  # Strategy automatically schedules supported content.
        assert worker.tick(owner.id)  # Content passes source/policy, merge, served verification.
        content = next(j for j in store.jobs(owner.id) if j.kind == "content")
        assert content.status == "complete" and content.result["content_verified"]
        assert PASSAGE in page.read_text()
        merged = run_git(repository, "rev-parse", "HEAD")
        opportunity = plan(spec, workspace).opportunities[0]
        store.enqueue(owner.id, project.id, "content", "repeat", {"opportunity_id": opportunity.id})
        assert worker.tick(owner.id)
        assert run_git(repository, "rev-parse", "HEAD") == merged
        assert page.read_text().count(PASSAGE) == 1
        assert not worker.tick(owner.id)
    finally:
        server.shutdown()
        server.server_close()
        store.engine.dispose()


def test_unknown_owner_fact_cannot_be_persisted(tmp_path):
    store, _, owner, _ = make_store(tmp_path)
    spec, workspace = setup()
    project = store.create_project(owner.id, ProjectCreate(spec=spec))
    workspace.materials[0].fact_ids = ["unknown"]
    with pytest.raises(ValueError, match="unknown"):
        store.save_workspace(owner.id, project.id, workspace)
    assert store.workspace(owner.id, project.id) == Workspace()
    store.engine.dispose()
