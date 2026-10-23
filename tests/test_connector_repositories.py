"""New-host PR adapters backed by a real temporary Git repository, with simulated provider HTTP."""

import base64
import json
from email.parser import BytesParser
from email.policy import default

import httpx
import pytest

from seo_optimizer.application_models import ProjectCreate, ProjectSpec
from seo_optimizer.connectors.models import CollectionRequest, ConnectionInput, Platform
from seo_optimizer.connectors.service import ConnectorService
from seo_optimizer.execution import run_git
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store


@pytest.mark.parametrize("platform", ["gitlab", "bitbucket"])
def test_observe_generate_metadata_repair_commit_branch_and_open_pr(tmp_path, platform):
    root = tmp_path / "repository"
    (root / "web").mkdir(parents=True)
    original = "<html><head></head><body><h1>Desk lamps</h1><p>Original content.</p></body></html>"
    (root / "web/index.html").write_text(original)
    run_git(root, "init", "-b", "main")
    run_git(root, "add", "web/index.html")
    run_git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@localhost",
        "commit",
        "-m",
        "Add page",
    )
    initial = run_git(root, "rev-parse", "main")
    requests = []
    pulls = []

    def handler(request):
        requests.append(request)
        path = request.url.path
        if request.method == "GET":
            if platform == "gitlab":
                return httpx.Response(
                    200,
                    json={
                        "content": base64.b64encode(original.encode()).decode(),
                        "last_commit_id": initial,
                    },
                )
            if "/refs/branches/" in path:
                return httpx.Response(200, json={"target": {"hash": initial}})
            return httpx.Response(200, text=original)
        if path.endswith("/merge_requests"):
            pulls.append(json.loads(request.content))
            return httpx.Response(
                201,
                json={"web_url": "https://gitlab.com/fixture/site/-/merge_requests/1", "iid": 1},
            )
        if path.endswith("/pullrequests"):
            pulls.append(json.loads(request.content))
            return httpx.Response(
                201,
                json={
                    "id": 1,
                    "links": {
                        "html": {"href": "https://bitbucket.org/fixture/site/pull-requests/1"}
                    },
                },
            )
        if path.endswith("/refs/branches"):
            payload = json.loads(request.content)
            run_git(root, "branch", payload["name"], initial)
        else:
            if platform == "gitlab":
                payload = json.loads(request.content)
                branch = payload["branch"]
                assert payload["actions"][0]["last_commit_id"] == initial
                content = payload["actions"][0]["content"]
                run_git(root, "branch", branch, initial)
            else:
                assert request.headers["content-type"].startswith("multipart/form-data")
                message = BytesParser(policy=default).parsebytes(
                    b"Content-Type: "
                    + request.headers["content-type"].encode()
                    + b"\r\n\r\n"
                    + request.content
                )
                fields = {
                    part.get_param("name", header="content-disposition"): part.get_payload(
                        decode=True
                    ).decode()
                    for part in message.iter_parts()
                }
                branch = fields["branch"]
                content = fields["web/index.html"]
                assert fields["parents"] == initial
            run_git(root, "checkout", branch)
            (root / "web/index.html").write_text(content)
            run_git(root, "add", "web/index.html")
            run_git(
                root,
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@localhost",
                "commit",
                "-m",
                "Fix title",
            )
            run_git(root, "checkout", "main")
        return httpx.Response(201, json={"id": "fixture-write"})

    settings = Settings(
        data_dir=tmp_path,
        database_url=f"sqlite:///{tmp_path / 'control.db'}",
        secret_key="fixture-control-secret",
    )
    store = Store(settings)
    owner, _ = store.create_user("owner@example.test", "fixture-hash")
    project = store.create_project(
        owner.id,
        ProjectCreate(
            spec=ProjectSpec(
                name="Fixture", website_url="https://example.test/", publishing_platform=platform
            )
        ),
    )
    try:
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            service = ConnectorService(store, project, client)
            service.configure(
                ConnectionInput(
                    platform=platform,
                    resource="fixture/site",
                    credentials={"access_token": "fixture-access-token"},
                    allow_writes=True,
                )
            )
            result = service.collect(
                Platform(platform), CollectionRequest(resource_id="web/index.html", limit=1)
            )
            proposals = service.auto_propose(Platform(platform), result["evidence_id"])
            assert len(proposals) == 1
            published = service.publish(Platform(platform), proposals[0]["id"])
            assert published["status"] == "pr_opened" and len(pulls) == 1
            assert published["verification"] == {
                "source_checked": True,
                "build_ci": "unverified",
                "deployed_site": "unverified",
            }
            branch = published["pr"]["branch"]
            repaired = run_git(root, "show", branch + ":web/index.html")
            assert (
                "<title>Desk lamps</title>" in repaired and "<p>Original content.</p>" in repaired
            )
            assert run_git(root, "rev-parse", "main") == initial
            assert (root / "web/index.html").read_text() == original
            service.publish(Platform(platform), proposals[0]["id"])
            assert len(pulls) == 1
    finally:
        store.close()
