"""Native provider replay with real Git, HTTP and the production Docker check runner.

Responses are scripted: these cases prove execution/policy, never model quality.
Enable with OPT_TEST_SANDBOX=1; no provider credentials or network access needed.
"""

import json
import os
import threading
from functools import partial

import httpx
import pytest
from test_growth_integration import make_store

from seo_optimizer.application_models import ProjectCreate, ProjectSpec, ProviderConfig
from seo_optimizer.contracts import ProviderCapabilities
from seo_optimizer.execution import run_git
from seo_optimizer.llm import ModelClient
from seo_optimizer.repair_benchmark import QuietHandler, ThreadingHTTPServer
from seo_optimizer.worker import Worker

CASES = {
    "description": (
        "tech.metadata",
        '<meta name="description" content="">',
        '<meta name="description" content="Cedar lamps with replaceable shades.">',
    ),
    "canonical": ("tech.canonical", '<link rel="canonical" href="/wrong">', ""),
    "indexability": (
        "tech.indexability",
        '<meta name="robots" content="noindex">',
        '<meta name="robots" content="index,follow">',
    ),
    "navigation": ("tech.links", 'href="/missing"', 'href="/about/"'),
    "crawler_policy": (
        "geo.crawlers",
        "User-agent: GPTBot\nDisallow:\n",
        "User-agent: GPTBot\nDisallow: /\n",
    ),
    "failed_checks": (
        "tech.metadata",
        '<meta name="description" content="">',
        '<meta name="description" content="Cedar lamps with replaceable shades.">',
    ),
}


@pytest.mark.integration
@pytest.mark.enable_socket
@pytest.mark.allow_hosts(["127.0.0.1"])
@pytest.mark.skipif(
    os.getenv("OPT_TEST_SANDBOX") != "1", reason="Enable real Docker sandbox checks"
)
@pytest.mark.parametrize("scenario", CASES)
def test_native_replay_repairs_commit_and_served_verification(tmp_path, monkeypatch, scenario):
    check_id, old, new = CASES[scenario]
    repository = tmp_path / "repository"
    web = repository / "web"
    (web / "about").mkdir(parents=True)
    (web / "private").mkdir()
    healthy = (
        "<html><head><title>Cedar lamps</title>"
        '<meta name="description" content="Cedar lamps with replaceable shades.">'
        '<link rel="canonical" href="/">'
        '</head><body><main><h1>Cedar lamps</h1><a href="/about/">About</a></main>'
        '<footer><a href="/about/">Company</a></footer></body></html>'
    )
    original = healthy
    if scenario in {"description", "failed_checks"}:
        original = healthy.replace(new, old)
    elif scenario in {"canonical", "indexability"}:
        original = healthy.replace("</head>", old + "</head>")
    elif scenario == "navigation":
        original = healthy.replace(new, old, 1)
    path = "web/robots.txt" if scenario == "crawler_policy" else "web/index.html"
    (web / "index.html").write_text(original)
    (web / "about/index.html").write_text(healthy.replace('href="/"', 'href="/about/"'))
    private = '<html><head><meta name="robots" content="noindex"></head><body>Private</body></html>'
    (web / "private/index.html").write_text(private)
    robots = "User-agent: *\nAllow: /\nUser-agent: GPTBot\nDisallow: /\n"
    if scenario == "crawler_policy":
        robots = robots.replace(new, old)
    (web / "robots.txt").write_text(robots)
    expected = (robots if path.endswith("robots.txt") else original).replace(old, new)
    verification = (
        "from pathlib import Path\n"
        f"assert Path({path!r}).read_text() == {expected!r}\n"
        f"assert Path('web/private/index.html').read_text() == {private!r}\n"
        "assert not Path('/workspace/.env').exists()\n"
    )
    if scenario == "failed_checks":
        verification += "assert False, 'Owner check rejects this proposal'\n"
    (repository / "verify.py").write_text(verification)
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
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(web)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    store, settings, owner, _ = make_store(tmp_path)
    spec = ProjectSpec(
        name="Fictional lamps",
        website_url=f"http://127.0.0.1:{server.server_port}/",
        local_path=str(repository),
        allowed_paths=["web"],
        page_intents={"/": True, "/private/": False},
        route_map={"/": "web/index.html", "/about/": "web/about/index.html"},
        crawler_preferences={"GPTBot": "block", "OAI-SearchBot": "allow"},
        check_commands=[["python", "verify.py"]],
        provider=ProviderConfig(
            kind="ollama",
            model="scripted-fixture",
            capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
        ),
    )
    project = store.create_project(owner.id, ProjectCreate(spec=spec))
    requests = []
    clients = []

    def transport(request):
        payload = json.loads(request.content)
        task = json.loads(payload["messages"][1]["content"])
        requests.append(task.get("mode", "repair"))
        tool_messages = [m for m in payload["messages"] if m["role"] == "tool"]
        if task.get("mode") == "read_only_catalog_review" or not task.get("repair_targets"):
            decision = {
                "check_reviews": [
                    {
                        "check_id": row["id"],
                        "state": "needs_data",
                        "reason": "Scripted replay",
                        "dependencies": ["Real semantic inference is outside this workflow test"],
                    }
                    for row in task["requested_check_reviews"]
                ]
            }
            message = {"role": "assistant", "content": json.dumps(decision)}
        else:
            assert any(t["check_id"] == check_id for t in task["repair_targets"])
            step = len(tool_messages)
            if step == 0:
                name, arguments = "read_file", {"path": path}
            elif step == 1:
                source = json.loads(tool_messages[0]["content"])
                assert source["success"] and old in source["text"]
                name, arguments = (
                    "apply_patch",
                    {
                        "path": path,
                        "before": old,
                        "after": new,
                        "check_id": check_id,
                        "evidence_ids": [
                            source["evidence_id"],
                            *[
                                evidence_id
                                for target in task["repair_targets"]
                                if target["check_id"] == check_id
                                for evidence_id in target["evidence_ids"]
                            ],
                        ],
                        "reason": "Repair the observed defect",
                    },
                )
            elif step == 2:
                assert json.loads(tool_messages[-1]["content"])["success"], tool_messages[-1]
                name, arguments = "run_checks", {}
            else:
                assert scenario == "failed_checks", json.loads(tool_messages[-1]["content"])
                assert not json.loads(tool_messages[-1]["content"])["success"]
                return httpx.Response(
                    200,
                    json={
                        "message": {
                            "role": "assistant",
                            "content": json.dumps({"summary": "Owner check failed"}),
                        }
                    },
                )
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": name, "arguments": arguments}}],
            }
        return httpx.Response(
            200, json={"message": message, "prompt_eval_count": 100, "eval_count": 20}
        )

    def client(config, key="", **kwargs):
        http = httpx.Client(transport=httpx.MockTransport(transport))
        clients.append(http)
        return ModelClient(config, key, client=http, **kwargs)

    monkeypatch.setattr("seo_optimizer.worker.ModelClient", client)
    try:
        assert Worker(store, settings).tick(owner.id)
        job = store.jobs(owner.id, project.id)[0]
        if scenario == "failed_checks":
            assert job.status == "blocked", job.result
            assert run_git(repository, "rev-parse", "HEAD") == before
            assert (web / "index.html").read_text() == original
        else:
            assert job.status == "complete" and job.result["stage"] == "verified", job.result
            assert job.result["verified_fixes"] == len(job.result["fixed_targets"])
            assert job.result["verified_fixes"] > 0 and job.result["regressions"] == 0
            assert job.result["report"]["finalized_from_tools"]
            assert [t["name"] for t in job.result["report"]["tool_trace"]] == [
                "read_file",
                "apply_patch",
                "run_checks",
            ]
            assert all(c["passed"] for c in job.result["verification"])
            assert (repository / path).read_text() == expected
            assert run_git(repository, "diff", "--name-only", before, "HEAD") == path
            assert len(run_git(repository, "rev-list", before + "..HEAD").splitlines()) == 1
            assert job.result["after_evidence"]
            merged = run_git(repository, "rev-parse", "HEAD")
            repeat = store.enqueue(owner.id, project.id, "audit", "repeat-healthy", {})
            assert Worker(store, settings).tick(owner.id)
            assert store.job(owner.id, repeat.id).status == "complete"
            assert run_git(repository, "rev-parse", "HEAD") == merged
            assert not store.job(owner.id, repeat.id).result.get("proposals")
        assert (web / "private/index.html").read_text() == private
        assert (web / "robots.txt").read_text().endswith("User-agent: GPTBot\nDisallow: /\n")
        assert requests
    finally:
        for http in clients:
            http.close()
        server.shutdown()
        server.server_close()
        store.engine.dispose()
