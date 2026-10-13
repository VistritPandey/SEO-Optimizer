"""An irrelevant merge does not invalidate the next full-audit model cache."""

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from seo_optimizer.application_models import (
    AgentDecision,
    ProjectCreate,
    ProjectSpec,
    ProviderConfig,
)
from seo_optimizer.contracts import ProviderCapabilities, Usage
from seo_optimizer.execution import run_git
from seo_optimizer.llm import Inference
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.worker import Worker


@pytest.mark.integration
@pytest.mark.enable_socket
@pytest.mark.allow_hosts(["127.0.0.1"])
def test_irrelevant_merge_then_periodic_audit_reuses_identical_model_inputs(tmp_path, monkeypatch):
    repo = tmp_path / "website"
    (repo / "web").mkdir(parents=True)
    (repo / "web/index.html").write_text(
        '<html><head><title>Example</title><meta name="description" content="Example"></head><body><h1>Example</h1></body></html>'
    )
    run_git(repo, "init", "-b", "main")
    run_git(repo, "add", ".")

    def commit(message):
        run_git(
            repo,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@localhost",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            message,
        )

    commit("Add page")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(repo / "web"))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    store = Store(
        Settings(
            tmp_path / "data",
            f"sqlite:///{tmp_path / 'state.db'}",
            "secret",
            allowed_repo_roots=(repo,),
        )
    )
    owner, _ = store.create_user("owner@example.test", "hash")
    site = store.create_project(
        owner.id,
        ProjectCreate(
            spec=ProjectSpec(
                name="Example",
                website_url=f"http://127.0.0.1:{server.server_port}",
                local_path=str(repo),
                allowed_paths=["web"],
                provider=ProviderConfig(
                    kind="ollama",
                    model="fixture",
                    capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
                ),
            )
        ),
    )
    calls = []

    class Model:
        def __init__(self, *args, **kwargs):
            pass

        def close(self):
            pass

        def complete(self, *args, **kwargs):
            calls.append(True)
            return Inference(decision=AgentDecision(), usage=Usage(), model="fixture", runtime_ms=1)

    monkeypatch.setattr("seo_optimizer.worker.ModelClient", Model)
    worker = Worker(store, store.settings)
    try:
        assert worker.tick(owner.id)
        assert len(calls) == 1
        before = store.project(owner.id, site.id).last_report["source_revision"]
        (repo / "README.md").write_text("Documentation only")
        run_git(repo, "add", "README.md")
        commit("Update documentation")
        store.enqueue(owner.id, site.id, "push", "docs", {})
        assert worker.tick(owner.id)
        store.enqueue(owner.id, site.id, "audit", "periodic", {})
        assert worker.tick(owner.id)
        assert len(calls) == 1
        report = store.project(owner.id, site.id).last_report
        assert report["source_revision"] == before
        assert report["model_cache_hit"]
        (repo / "web/index.html").write_text(
            (repo / "web/index.html").read_text().replace("Example</title>", "Updated</title>")
        )
        run_git(repo, "add", "web/index.html")
        commit("Update website")
        store.enqueue(owner.id, site.id, "audit", "changed-source", {})
        assert worker.tick(owner.id)
        assert len(calls) == 2
    finally:
        server.shutdown()
        server.server_close()
        store.close()
