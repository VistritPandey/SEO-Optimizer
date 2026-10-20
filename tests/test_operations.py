"""Exercise publishing and recovery boundaries with controlled observations/transports."""

import gzip
import json
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from seo_optimizer.application_models import (
    FileChange,
    ProjectCreate,
    ProjectSecrets,
    ProjectSpec,
    ProviderConfig,
)
from seo_optimizer.contracts import Evidence, ProviderCapabilities, utc_now
from seo_optimizer.crawler import Crawler
from seo_optimizer.execution import apply_changes, without_metadata
from seo_optimizer.github import GitHubClient
from seo_optimizer.llm import ModelClient, ProviderError
from seo_optimizer.remote import RemoteStore
from seo_optimizer.scanner import affected_urls, context
from seo_optimizer.settings import Settings
from seo_optimizer.store import Job, SchemaVersion, Store
from seo_optimizer.web import create_app, hash_password
from seo_optimizer.worker import Worker

HEALTHY = (
    '<html><head><title>Observed guide</title><meta name="description" content="Real guide">'
    "</head><body><h1>Observed guide</h1></body></html>"
)


def make_store(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        database_url=f"sqlite:///{tmp_path}/control.sqlite",
        secret_key="fixture-long-secret-key",
        allowed_repo_roots=(tmp_path,),
    )
    return Store(settings), settings


def page(html=HEALTHY, status=200, url="https://example.test/"):
    return Evidence.model_validate(
        {
            "id": "after",
            "tenant_id": "tenant",
            "project_id": "project",
            "environment": "production",
            "kind": "http",
            "url": url,
            "observation": "Controlled deployed response",
            "collected_at": utc_now(),
            "data": {"html": html, "status_code": status},
        }
    )


def test_outbound_remote_worker_claim_credentials_and_lease(tmp_path):
    store, settings = make_store(tmp_path)
    account, token = store.create_user("worker@example.test", hash_password("fixture-password-123"))
    project = store.create_project(
        account.id,
        ProjectCreate(
            spec=ProjectSpec(name="Site", website_url="https://example.test/"),
            credentials=ProjectSecrets(provider_key="controlled-secret"),
        ),
    )
    remote = RemoteStore(settings, "http://127.0.0.1:8000", token)
    remote.client.close()
    with TestClient(create_app(settings, store)) as client:
        client.headers["Authorization"] = "Bearer " + token
        remote.client = client
        claimed = remote.claim("local-worker")
        assert claimed.project_id == project.id
        assert remote.project(account.id, project.id).id == project.id
        assert (
            remote.secrets(remote.project(account.id, project.id)).provider_key
            == "controlled-secret"
        )
        assert remote.project("other-tenant", project.id) is None
        assert remote.remember_findings(account.id, project.id, [], []) == 0
        remote.progress(account.id, claimed.id, "local-worker", "Collecting evidence")
        assert store.job(account.id, claimed.id).events[-1]["message"] == "Collecting evidence"
        remote.finish(account.id, claimed.id, "local-worker", "complete", {"summary": "Observed"})
        assert store.job(account.id, claimed.id).status == "complete"
        assert remote.claim("local-worker") is None
    store.engine.dispose()


@pytest.mark.parametrize("kind", ["script", "private", "directives", "redirect"])
def test_metadata_cannot_change_scripts_privacy_or_redirect(tmp_path, kind):
    (tmp_path / "web").mkdir()
    source = tmp_path / "web/index.html"
    source.write_text(HEALTHY)
    spec = ProjectSpec(
        name="Site",
        website_url="https://example.test/",
        allowed_paths=["web"],
        route_map={"/": "web/index.html"},
    )
    after = "<head><script>window.location='https://other.test'</script>"
    if kind == "private":
        spec.page_intents = {"https://example.test/": False}
        after = "<head><title>More words</title>"
    elif kind == "directives":
        after = '<head><meta name="robots" content="noindex">'
    elif kind == "redirect":
        after = '<head><meta http-equiv="refresh" content="0;url=https://other.test">'
    change = FileChange(
        path="web/index.html",
        before="<head>",
        after=after,
        reason="Controlled attempt",
        check_id="tech.title",
        evidence_ids=["page"],
    )
    with pytest.raises(ValueError):
        apply_changes(tmp_path, spec, [change], {"page"}, {"tech.title"})
    assert source.read_text() == HEALTHY


def test_framework_metadata_preserves_body_and_requires_checks(tmp_path):
    original = 'export const metadata = {title: "Old"};\nexport default function Page(){return 1;}'
    updated = original.replace('"Old"', '"Observed"')
    assert without_metadata(original) == without_metadata(updated)
    with pytest.raises(ValueError, match="executable"):
        without_metadata(original.replace('"Old"', "process.exit()"))
    (tmp_path / "app").mkdir()
    (tmp_path / "app/page.tsx").write_text(original)
    spec = ProjectSpec(name="Site", website_url="https://example.test/", allowed_paths=["app"])
    change = FileChange(
        path="app/page.tsx",
        before='"Old"',
        after='"Observed"',
        check_id="tech.title",
        evidence_ids=["page"],
        reason="Actual heading",
    )
    with pytest.raises(ValueError, match="build"):
        apply_changes(tmp_path, spec, [change], {"page"}, {"tech.title"})
    spec.check_commands = [["python", "-m", "compileall", "/workspace"]]
    assert apply_changes(tmp_path, spec, [change], {"page"}, {"tech.title"})


@pytest.mark.parametrize(
    "observation,outcome,rollback",
    [
        ("healthy", "complete", False),
        ("broken", "blocked", True),
        ("regression", "blocked", True),
        ("unavailable", "blocked", False),
    ],
)
def test_deployed_verification_and_guarded_rollback(tmp_path, observation, outcome, rollback):
    store, settings = make_store(tmp_path)
    worker = Worker(store, settings)
    github = Mock()
    github.revert.return_value = "reverted"
    spec = ProjectSpec(name="Site", website_url="https://example.test/", repository="owner/site")
    html = HEALTHY
    if observation == "broken":
        html = html.replace("<title>Observed guide</title>", "")
    if observation == "regression":
        html = html.replace('<meta name="description" content="Real guide">', "")
    result = {
        "revision": "before",
        "merged_sha": "after",
        "fixed_checks": ["tech.title"],
        "fixed_targets": [{"check_id": "tech.title", "url": "https://example.test/"}],
        "before_defects": [{"check_id": "tech.title", "url": "https://example.test/"}],
        "audited_urls": ["https://example.test/"],
    }
    status, report, _ = worker.verify_deployment(
        spec, result, [page(html, 503 if observation == "unavailable" else 200)], github
    )
    assert status == outcome
    assert github.revert.called is rollback
    if status == "complete":
        assert report["verified_fixes"] == 1 and report["revision"] == "after"
    store.engine.dispose()


def test_existing_unfixed_page_is_not_attributed_to_new_fix(tmp_path):
    store, settings = make_store(tmp_path)
    worker = Worker(store, settings)
    second = page(
        HEALTHY.replace("<title>Observed guide</title>", ""), url="https://example.test/other"
    )
    second.id = "other"
    result = {
        "revision": "before",
        "merged_sha": "after",
        "fixed_checks": ["tech.title"],
        "fixed_targets": [{"check_id": "tech.title", "url": "https://example.test/"}],
        "before_defects": [{"check_id": "tech.title", "url": "https://example.test/other"}],
        "audited_urls": ["https://example.test/", "https://example.test/other"],
    }
    status, _, _ = worker.verify_deployment(
        ProjectSpec(name="Site", website_url="https://example.test/"),
        result,
        [page(), second],
        None,
    )
    assert status == "complete"
    store.engine.dispose()


def test_rollback_refuses_newer_branch_revision():
    calls = []

    def transport(request):
        calls.append(request.method)
        return httpx.Response(200, json={"object": {"sha": "newer"}})

    client = GitHubClient(
        ProjectSecrets(github_token="fixture"),
        httpx.Client(transport=httpx.MockTransport(transport)),
    )
    with pytest.raises(ValueError, match="newer"):
        client.revert("owner/site", "main", "merged", "previous")
    assert calls == ["GET"]


def test_malformed_json_regeneration_is_bounded_and_explicit():
    requests = []

    def transport(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": "```json\n{}\n```"
                    if len(requests) == 1
                    else '{"findings":[],"changes":[],"summary":"Observed"}'
                }
            },
        )

    client = ModelClient(
        ProviderConfig(
            kind="ollama", model="fixture", capabilities=ProviderCapabilities(json_schema=True)
        ),
        client=httpx.Client(transport=httpx.MockTransport(transport)),
    )
    result = client.complete("Return JSON", {}, [], lambda n, a: {}, max_steps=2)
    assert result.decision.summary == "Observed"
    assert "No Markdown" in requests[1]["messages"][-1]["content"]
    assert len(requests) == 2


def test_shared_worker_does_not_accept_custom_model_address():
    with pytest.raises(ProviderError, match="Custom"):
        ModelClient(
            ProviderConfig(kind="openai", base_url="http://169.254.169.254", model="x"),
            allow_custom_endpoint=False,
        )
    with pytest.raises(ProviderError, match="local worker"):
        ModelClient(ProviderConfig(kind="ollama", model="x"), allow_custom_endpoint=False)


def test_http_address_is_pinned_and_compressed_content_decoded(monkeypatch):
    monkeypatch.setattr(
        "seo_optimizer.crawler.socket.getaddrinfo",
        lambda *args: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    observed = []

    def transport(request):
        observed.append(request)
        return httpx.Response(
            200, headers={"content-encoding": "gzip"}, content=gzip.compress(b"observed page")
        )

    crawler = Crawler(
        "https://example.test/", client=httpx.Client(transport=httpx.MockTransport(transport))
    )
    response = crawler.fetch("https://example.test/")
    assert response.text == "observed page"
    assert observed[0].url.host == "93.184.216.34"
    assert observed[0].headers["host"] == "example.test"
    assert observed[0].extensions["sni_hostname"] == "example.test"
    assert str(response.url) == "https://example.test/"


def test_incremental_route_scope_and_private_intent():
    spec = ProjectSpec(
        name="Site",
        website_url="https://example.test/",
        route_map={"/": "web/index.html", "/guide": "web/guide.html"},
        page_intents={"/private": False},
    )
    assert context("tenant", "project", spec).page_intents["https://example.test/private"] is False
    assert affected_urls(spec, ["web/guide.html"]) == ["https://example.test/guide"]
    assert affected_urls(spec, ["tests/test_math.py"]) == []
    assert affected_urls(spec, ["src/backend/middleware.py"]) is None


def test_database_schema_version_gate(tmp_path):
    store, settings = make_store(tmp_path)
    with store.sessions.begin() as session:
        session.execute(update(SchemaVersion).values(version=99))
    store.engine.dispose()
    with pytest.raises(ValueError, match="migration"):
        Store(settings)


def test_required_check_failure_and_stale_base_block_merge(tmp_path):
    store, settings = make_store(tmp_path)
    account, _ = store.create_user("check@example.test", hash_password("fixture-password-123"))
    project = store.create_project(
        account.id,
        ProjectCreate(
            spec=ProjectSpec(
                name="Site", website_url="https://example.test/", repository="owner/site"
            )
        ),
    )
    worker = Worker(store, settings)
    github = Mock()
    job = Job(
        id="test",
        created_at=0,
        result={"pr": {"number": 1, "head_sha": "candidate", "base_sha": "before"}},
    )
    spec = ProjectSpec.model_validate(project.spec)
    github.request.return_value = {"head": {"sha": "candidate"}, "state": "open"}
    github.checks_ready.return_value = "failed"
    assert worker.finish_pr(project, job, spec, github)[0] == "blocked"
    github.merge.assert_not_called()
    github.checks_ready.return_value = "ready"
    github.head.return_value = "newer"
    assert worker.finish_pr(project, job, spec, github)[0] == "superseded"
    github.merge.assert_not_called()
    assert any(item.dedupe_key == "supersede:test" for item in store.jobs(account.id))
    store.engine.dispose()


def test_worker_recovers_merge_after_lost_response(tmp_path):
    store, settings = make_store(tmp_path)
    account, _ = store.create_user("recovery@example.test", hash_password("fixture-password-123"))
    project = store.create_project(
        account.id,
        ProjectCreate(
            spec=ProjectSpec(
                name="Site", website_url="https://example.test/", repository="owner/site"
            )
        ),
    )
    worker = Worker(store, settings)
    github = Mock()
    github.request.return_value = {
        "head": {"sha": "candidate"},
        "merged": True,
        "merge_commit_sha": "merged",
    }
    job = Job(
        id="recovery",
        created_at=0,
        result={
            "stage": "checks",
            "pr": {"number": 1, "head_sha": "candidate", "base_sha": "before"},
        },
    )
    status, result, _ = worker.finish_pr(
        project, job, ProjectSpec.model_validate(project.spec), github
    )
    assert status == "waiting_deployment" and result["merged_sha"] == "merged"
    github.merge.assert_not_called()
    store.engine.dispose()


def test_finding_memory_does_not_depend_on_model_wording(tmp_path):
    store, settings = make_store(tmp_path)
    original = {
        "check_id": "tech.title",
        "url": "https://example.test/",
        "status": "defect",
        "summary": "A title is missing",
    }
    assert store.remember_findings("tenant", "project", [original], [original["url"]]) == 1
    assert (
        store.remember_findings(
            "tenant",
            "project",
            [{**original, "summary": "This public document needs a title"}],
            [original["url"]],
        )
        == 0
    )
    assert len(store.findings("tenant", "project")) == 1
    store.engine.dispose()


def test_local_crawl_cannot_read_another_port_or_scheme():
    crawler = Crawler("http://127.0.0.1:8081/", allow_private=True)
    from seo_optimizer.crawler import CrawlError

    try:
        with pytest.raises(CrawlError, match="configured website"):
            crawler.check_url("http://127.0.0.1:11434/api/tags")
        with pytest.raises(CrawlError, match="configured website"):
            crawler.check_url("https://127.0.0.1:8081/")
    finally:
        crawler.close()


def test_owner_crawler_repair_preserves_training_opt_out(tmp_path):
    from seo_optimizer.execution import validate_robots_policy, verify_workspace

    original = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: OAI-SearchBot\nDisallow: /\n"
    updated = original.replace(
        "User-agent: OAI-SearchBot\nDisallow: /", "User-agent: OAI-SearchBot\nDisallow: "
    )
    spec = ProjectSpec(
        name="Site",
        website_url="https://example.test/",
        allowed_paths=["public"],
        crawler_preferences={"GPTBot": "block", "OAI-SearchBot": "allow"},
    )
    (tmp_path / "public").mkdir()
    (tmp_path / "public/robots.txt").write_text(original)
    change = FileChange(
        path="public/robots.txt",
        before=original,
        after=updated,
        reason="Apply explicit discovery preference",
        check_id="geo.crawlers",
        evidence_ids=["page"],
    )
    changed = apply_changes(tmp_path, spec, [change], {"page"}, {"geo.crawlers"})
    assert "User-agent: GPTBot\nDisallow: /" in changed[change.path]
    assert verify_workspace(tmp_path, spec, changed)[0]["passed"]
    with pytest.raises(ValueError, match="intent|block"):
        validate_robots_policy(
            original, updated.replace("GPTBot\nDisallow: /", "GPTBot\nDisallow: "), spec
        )


def test_unconfigured_training_preference_cannot_change():
    from seo_optimizer.execution import validate_robots_policy

    spec = ProjectSpec(
        name="Site",
        website_url="https://example.test/",
        crawler_preferences={"OAI-SearchBot": "allow"},
    )
    with pytest.raises(ValueError, match="intent"):
        validate_robots_policy(
            "User-agent: GPTBot\nDisallow: /", "User-agent: GPTBot\nDisallow: ", spec
        )


def test_content_policy_cannot_authorize_script_changes(tmp_path):
    (tmp_path / "web").mkdir()
    (tmp_path / "web/index.html").write_text(HEALTHY)
    spec = ProjectSpec(
        name="Site",
        website_url="https://example.test/",
        allowed_paths=["web"],
        allow_content_publication=True,
    )
    change = FileChange(
        path="web/index.html",
        before="<head>",
        after="<head><script>window.location='https://other.test/'</script>",
        reason="Controlled attempt",
        check_id="content.factual",
        evidence_ids=["page"],
    )
    with pytest.raises(ValueError, match="scripts"):
        apply_changes(tmp_path, spec, [change], {"page"}, {"content.factual"})
    assert (tmp_path / "web/index.html").read_text() == HEALTHY


def test_content_publication_requires_current_fact_references(tmp_path):
    from datetime import timedelta

    from seo_optimizer.contracts import TrustedFact

    (tmp_path / "web").mkdir()
    (tmp_path / "web/index.html").write_text(HEALTHY)
    fact = TrustedFact(
        id="heading",
        name="heading",
        value="Observed guide",
        source="Owner verified copy",
        verified_at=utc_now() - timedelta(days=2),
        valid_until=utc_now() - timedelta(days=1),
    )
    spec = ProjectSpec(
        name="Site",
        website_url="https://example.test/",
        allowed_paths=["web"],
        allow_content_publication=True,
        facts=[fact],
    )
    change = FileChange(
        path="web/index.html",
        before="<h1>Observed guide</h1>",
        after="<h1>A guide with unsupported claims</h1>",
        reason="Controlled attempt",
        check_id="content.factual",
        evidence_ids=["page"],
    )
    with pytest.raises(ValueError, match="referenced"):
        apply_changes(tmp_path, spec, [change], {"page"}, {"content.factual"})
    change.fact_ids = ["heading"]
    with pytest.raises(ValueError, match="expired"):
        apply_changes(tmp_path, spec, [change], {"page"}, {"content.factual"})


def test_repaired_link_does_not_require_orphaned_error_url_to_become_a_page(tmp_path):
    store, settings = make_store(tmp_path)
    spec = ProjectSpec(
        name="Example",
        website_url="https://example.test/",
        route_map={"/": "web/index.html", "/about": "web/about.html"},
    )
    orphan = page(
        '<title>Not found</title><meta name="robots" content="noindex">',
        status=404,
        url="https://example.test/typo",
    )
    orphan.id = "orphan"
    about = page(url="https://example.test/about")
    about.id = "about"
    result = {
        "revision": "before",
        "merged_sha": "after",
        "fixed_checks": ["tech.links"],
        "fixed_targets": [
            {"check_id": "tech.links", "url": "https://example.test/"},
            # Legacy proposals also referenced the already healthy destination.
            {"check_id": "tech.links", "url": "https://example.test/about"},
        ],
        "before_defects": [{"check_id": "tech.links", "url": "https://example.test/"}],
        "audited_urls": [
            "https://example.test/",
            "https://example.test/about",
            "https://example.test/typo",
        ],
        "verification_urls": ["https://example.test/", "https://example.test/about"],
    }
    worker = Worker(store, settings)
    status, report, _ = worker.verify_deployment(spec, result, [page(), about, orphan], None)
    assert status == "complete" and report["verified_fixes"] == 1
    assert report["regressions"] == 0
    assert not any(
        f["check_id"] in {"tech.metadata", "tech.indexability", "tech.status"}
        for f in report["findings"]
    )
    status, report, _ = worker.verify_deployment(spec, result, [about], None)
    assert status == "blocked" and "inconclusive" in report["summary"]
    store.close()


@pytest.mark.parametrize("check_id", ["content.factual", "geo.entities", "tech.metadata"])
def test_published_semantic_change_requires_fresh_proof_before_verified_fix(tmp_path, check_id):
    store, settings = make_store(tmp_path)
    target = {"check_id": check_id, "url": "https://example.test/"}
    result = {
        "revision": "before",
        "merged_sha": "after",
        "fixed_checks": [check_id],
        "fixed_targets": [target],
        "before_defects": [target],
        "deterministic_defects": [],
        "audited_urls": ["https://example.test/"],
    }
    github = Mock()
    status, observed, _ = Worker(store, settings).verify_deployment(
        ProjectSpec(name="Site", website_url="https://example.test/"),
        result,
        [page()],
        github,
    )
    assert status == "blocked" and observed["stage"] == "verification_pending"
    assert observed["verified_fixes"] == 0 and observed["unverified_targets"][0]["dependency"]
    assert observed["after_evidence"] and observed["regressions"] == 0
    github.revert.assert_not_called()  # Missing proof does not establish a regression.
    store.engine.dispose()


def test_partial_verification_counts_only_independently_confirmed_fix(tmp_path):
    store, settings = make_store(tmp_path)
    structural = {"check_id": "tech.metadata", "url": "https://example.test/"}
    semantic = {"check_id": "content.factual", "url": "https://example.test/"}
    result = {
        "revision": "before",
        "merged_sha": "after",
        "fixed_checks": ["tech.metadata", "content.factual"],
        "fixed_targets": [structural, semantic],
        "before_defects": [structural, semantic],
        "deterministic_defects": [structural],
        "audited_urls": ["https://example.test/"],
    }
    status, observed, _ = Worker(store, settings).verify_deployment(
        ProjectSpec(name="Site", website_url="https://example.test/"),
        result,
        [page()],
        None,
    )
    assert status == "blocked" and observed["verified_fixes"] == 1
    assert [t["check_id"] for t in observed["unverified_targets"]] == ["content.factual"]
    store.engine.dispose()


def test_followup_cannot_drop_verification_of_an_earlier_repair(tmp_path):
    store, settings = make_store(tmp_path)
    targets = [
        {"check_id": check, "url": "https://example.test/"}
        for check in ("tech.title", "tech.metadata")
    ]
    result = {
        "revision": "before",
        "merged_sha": "after",
        "fixed_checks": ["tech.metadata"],
        "fixed_targets": targets,
        "before_defects": targets,
        "audited_urls": ["https://example.test/"],
    }
    github = Mock()
    status, observed, _ = Worker(store, settings).verify_deployment(
        ProjectSpec(name="Site", website_url="https://example.test/"),
        result,
        [page(HEALTHY.replace("<title>Observed guide</title>", ""))],
        github,
    )
    assert status == "blocked" and "failed verification" in observed["summary"]
    github.revert.assert_called_once()
    store.engine.dispose()
