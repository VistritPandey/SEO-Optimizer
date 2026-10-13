from pathlib import Path

import pytest
from pydantic import HttpUrl

from seo_optimizer.application_models import FileChange, ProjectSpec
from seo_optimizer.contracts import Evidence, utc_now
from seo_optimizer.patch_grounding import ground_patch


def fixture(tmp_path: Path):
    (tmp_path / "web").mkdir()
    text = "<html><head><title>Example</title></head></html>"
    (tmp_path / "web/index.html").write_text(text)
    spec = ProjectSpec(
        name="Site", website_url=HttpUrl("https://example.test"), allowed_paths=["web"]
    )
    source = Evidence(
        id="source",
        tenant_id="tenant",
        project_id="site",
        environment="production",
        kind="source",
        source_file="web/index.html",
        collected_at=utc_now(),
        observation="Successful source read",
        data={"text": text},
    )
    http = Evidence(
        id="http",
        tenant_id="tenant",
        project_id="site",
        environment="production",
        kind="http",
        url=HttpUrl("https://example.test"),
        collected_at=utc_now(),
        observation="Page response",
        data={"status_code": 200},
    )
    patch = FileChange(
        path="web/index.html",
        before="</title>",
        after='</title><meta name="description" content="Example">',
        reason="Describe the observed page",
        check_id="tech.metadata",
        evidence_ids=["http"],
    )
    return spec, source, http, patch


def test_real_source_read_is_attached_without_inventing_evidence(tmp_path):
    spec, source, http, patch = fixture(tmp_path)
    result = ground_patch(patch, [source, http], tmp_path, spec, "tenant", "site")
    assert result.evidence_ids == ["http", "source"]
    assert patch.evidence_ids == ["http"]


def test_missing_stale_cross_tenant_and_invented_reads_are_rejected(tmp_path):
    spec, source, http, patch = fixture(tmp_path)
    with pytest.raises(ValueError, match="Read the same"):
        ground_patch(patch, [http], tmp_path, spec, "tenant", "site")
    foreign = source.model_copy(update={"tenant_id": "other"})
    with pytest.raises(ValueError, match="Read the same"):
        ground_patch(patch, [foreign, http], tmp_path, spec, "tenant", "site")
    invalid = patch.model_copy(update={"evidence_ids": ["invented"]})
    with pytest.raises(ValueError, match="outside"):
        ground_patch(invalid, [source, http], tmp_path, spec, "tenant", "site")
    (tmp_path / "web/index.html").write_text("new revision")
    with pytest.raises(ValueError, match="stale"):
        ground_patch(patch, [source, http], tmp_path, spec, "tenant", "site")
