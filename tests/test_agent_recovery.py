"""The bounded agent can correct a failed proposal; failed reads never become evidence."""

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from seo_optimizer.application_models import (
    AgentDecision,
    CheckReview,
    FileChange,
    ProjectCreate,
    ProjectSpec,
    ProviderConfig,
)
from seo_optimizer.contracts import ProviderCapabilities, Usage
from seo_optimizer.execution import VerificationFailure, run_git
from seo_optimizer.llm import Inference
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import hash_password
from seo_optimizer.worker import Worker


@pytest.mark.integration
@pytest.mark.enable_socket
@pytest.mark.allow_hosts(["127.0.0.1"])
@pytest.mark.parametrize("has_source", [True, False])
@pytest.mark.parametrize("invalid_review", [True, False])
def test_failed_check_recovery_requires_successful_source_read(
    tmp_path, monkeypatch, has_source, invalid_review
):
    repository = tmp_path / "source"
    (repository / "web").mkdir(parents=True)
    original = (
        "<html><head><title>Cedar lamps</title></head><body><h1>Cedar lamps</h1></body></html>"
    )
    page = repository / "web/index.html"
    page.write_text(original)
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
    before = run_git(repository, "rev-parse", "HEAD")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(repository / "web"))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    settings = Settings(
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{tmp_path}/db",
        secret_key="fixture-secret",
        allowed_repo_roots=(tmp_path,),
    )
    store = Store(settings)
    user, _ = store.create_user("agent@localhost.test", hash_password("fixture-password-123"))
    spec = ProjectSpec(
        name="Cedar lamps",
        website_url=f"http://127.0.0.1:{server.server_port}/",
        local_path=str(repository),
        allowed_paths=["web"],
        provider=ProviderConfig(
            kind="ollama",
            model="fixture",
            capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
        ),
    )
    project = store.create_project(user.id, ProjectCreate(spec=spec))

    def check(root, policy, files):
        text = (root / "web/index.html").read_text()
        if 'content="Cedar lamps for thoughtful everyday lighting."' not in text:
            raise VerificationFailure(
                [
                    {
                        "name": "owner checks",
                        "passed": False,
                        "exit_code": 1,
                        "stderr": "Description is incomplete",
                    }
                ]
            )
        return [{"name": "owner checks", "passed": True}]

    monkeypatch.setattr("seo_optimizer.execution.verify_workspace", check)
    monkeypatch.setattr("seo_optimizer.worker.verify_workspace", check)

    class FixtureModel:
        def __init__(self, *args, **kwargs):
            pass

        def close(self):
            pass

        def complete(self, instructions, request, tools, execute, *rest):
            if request.get("mode") == "read_only_catalog_review":
                assert not tools and not execute("apply_patch", {})["success"]
                return Inference(
                    decision=AgentDecision(
                        check_reviews=[
                            CheckReview(
                                check_id="not.a.check" if invalid_review else check["id"],
                                state="needs_data",
                                reason="Fixture needs context",
                                dependencies=["Collect additional semantic observations"],
                            )
                            for check in request["requested_check_reviews"]
                        ]
                    ),
                    usage=Usage(),
                    model="fixture",
                    runtime_ms=1,
                )
            assert not request["requested_check_reviews"]
            trace = []

            def call(name, args):
                result = execute(name, args)
                trace.append({"name": name, "success": result["success"], "result": result})
                return result

            assert not call("read_file", {"path": "not-permitted"})["success"]
            initial = call("run_checks", {})
            assert not initial["success"] and initial["checks"][0]["stderr"]
            source = call("read_file", {"path": "web/index.html"}) if has_source else None
            evidence_id = source["evidence_id"] if source else request["observations"][0]["id"]
            patch = {
                "path": "web/index.html",
                "before": "</title>",
                "after": '</title><meta name="description" content="Short">',
                "check_id": "tech.metadata",
                "reason": "Describe observed lamps",
                "evidence_ids": [evidence_id],
                "fact_ids": [],
            }
            staged = call("apply_patch", patch)
            if not has_source:
                assert not staged["success"]
                assert "Read the same" in staged["error"]
                return Inference(
                    decision=AgentDecision(changes=[FileChange.model_validate(patch)]),
                    usage=Usage(),
                    model="fixture",
                    runtime_ms=1,
                    tool_trace=trace,
                )
            assert staged["success"]
            assert not call("run_checks", {})["success"]
            assert run_git(repository, "rev-parse", "HEAD") == before
            patch = {
                **patch,
                "after": '</title><meta name="description" '
                'content="Cedar lamps for thoughtful everyday lighting.">',
            }
            assert call("apply_patch", patch)["replaced_previous_proposal"]
            assert call("run_checks", {})["success"]
            return Inference(
                decision=AgentDecision(summary="Grounded proposal"),
                usage=Usage(),
                model="fixture",
                runtime_ms=1,
                tool_trace=trace,
            )

    monkeypatch.setattr("seo_optimizer.worker.ModelClient", FixtureModel)
    try:
        Worker(store, settings).tick(user.id)
        result = store.jobs(user.id, project.id)[0]
        if has_source:
            assert result.status == "complete" and result.result["stage"] == "verified"
            assert any(not item["success"] for item in result.result["report"]["tool_trace"])
            assert 'content="Cedar lamps for thoughtful everyday lighting."' in page.read_text()
            assert bool(result.result["report"].get("semantic_review_error")) == invalid_review
        else:
            assert result.status == "blocked"
            assert "Read the same" in result.result["summary"]
            assert page.read_text() == original
            assert run_git(repository, "rev-parse", "HEAD") == before
    finally:
        server.shutdown()
        server.server_close()
        store.engine.dispose()
