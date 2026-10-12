"""Doc delivery and the new rendered-heading repair boundary."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.contracts import Evidence, utc_now
from seo_optimizer.knowledge import load_knowledge
from seo_optimizer.scanner import context, scan
from seo_optimizer.settings import Settings
from seo_optimizer.web import create_app
from seo_optimizer.worker import builtin_changes


def test_public_guide_assets_have_no_project_or_private_skill_data(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        database_url=f"sqlite:///{tmp_path}/db.sqlite",
        secret_key="guide-fixture-secret",
    )
    with TestClient(create_app(settings)) as client:
        page = client.get("/guide")
        assert page.status_code == 200 and "A working partner" in page.text
        assert 'src="/static/guide.js"' in page.text
        assert "script-src 'self'" in page.headers["content-security-policy"]
        assert client.get("/static/guide.js").status_code == 200
        assert client.get("/static/guide.css").status_code == 200
        assert "Search optimization\n" not in page.text
        assert client.get("/static/../knowledge/search-optimization/SKILL.md").status_code == 404


@pytest.mark.parametrize("mismatch", [None, "url", "tenant", "project", "environment", "unsettled"])
def test_spa_title_uses_only_settled_same_page_scoped_dom(tmp_path: Path, mismatch):
    (tmp_path / "public").mkdir()
    (tmp_path / "public/index.html").write_text(
        '<html><head></head><body><div id="root"></div></body></html>'
    )
    spec = ProjectSpec(
        name="SPA",
        website_url="https://example.test/",
        allowed_paths=["public"],
        route_map={"/": "public/index.html"},
    )
    http = Evidence.model_validate(
        {
            "id": "http",
            "tenant_id": "owner",
            "project_id": "site",
            "environment": "production",
            "kind": "http",
            "url": str(spec.website_url),
            "observation": "Rendered shell",
            "collected_at": utc_now(),
            "data": {
                "status_code": 200,
                "html": '<html><head></head><body><div id="root"></div></body></html>',
            },
        }
    )
    dom = http.model_copy(deep=True)
    dom.id, dom.kind = "dom", "dom"
    dom.data = {
        "html": "<html><body><h1>Observed <span>portfolio</span></h1></body></html>",
        "render_settled": True,
    }
    if mismatch == "url":
        from pydantic import HttpUrl

        dom.url = HttpUrl("https://example.test/other")
    if mismatch in {"tenant", "project", "environment"}:
        setattr(
            dom,
            {"tenant": "tenant_id", "project": "project_id", "environment": "environment"}[
                mismatch
            ],
            "other",
        )
    if mismatch == "unsettled":
        dom.data["render_settled"] = False
    knowledge = load_knowledge()
    findings, _ = scan(context("owner", "site", spec), spec, [http], knowledge)
    changes = builtin_changes(tmp_path, spec, findings, [http, dom])
    if mismatch is None:
        assert len(changes) == 1
        assert "<title>Observed portfolio</title>" in changes[0].after
        assert changes[0].evidence_ids == ["http", "dom"]
    else:
        assert changes == []
