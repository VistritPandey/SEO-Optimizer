"""Staged verification must test the proposed files without mutating publication input."""

import pytest

from seo_optimizer.application_models import FileChange, ProjectSpec
from seo_optimizer.execution import verify_proposals

ORIGINAL = "<html><head><title>Cedar Workshop</title></head><body><h1>Lighting</h1></body></html>"


def fixture(tmp_path):
    root = tmp_path / "repository"
    (root / "web").mkdir(parents=True)
    (root / "web/index.html").write_text(ORIGINAL)
    spec = ProjectSpec(
        name="Synthetic storefront",
        website_url="https://example.test/",
        allowed_paths=["web"],
        route_map={"/": "web/index.html"},
    )
    change = FileChange(
        path="web/index.html",
        before="</title>",
        after='</title><meta name="description" content="Cedar lighting">',
        reason="Describe visible lighting products",
        check_id="tech.metadata",
        evidence_ids=["source"],
    )
    return root, spec, change


def test_checks_read_staged_files_and_original_stays_unchanged(tmp_path, monkeypatch):
    root, spec, change = fixture(tmp_path)
    seen = []

    def inspect(preview, policy, files):
        assert preview != root
        assert 'content="Cedar lighting"' in (preview / change.path).read_text()
        assert files[change.path] == (preview / change.path).read_text()
        assert (root / change.path).read_text() == ORIGINAL
        seen.append(preview)
        return [{"name": "staged metadata", "passed": True}]

    monkeypatch.setattr("seo_optimizer.execution.verify_workspace", inspect)
    result = verify_proposals(root, spec, [change], {"source"}, {"tech.metadata"})
    assert result[0]["passed"]
    assert not seen[0].exists()
    assert (root / change.path).read_text() == ORIGINAL


def test_failed_staged_checks_preserve_original_and_remove_preview(tmp_path, monkeypatch):
    root, spec, change = fixture(tmp_path)

    def reject(preview, policy, files):
        assert 'content="Cedar lighting"' in (preview / change.path).read_text()
        raise ValueError("Build rejected proposal")

    monkeypatch.setattr("seo_optimizer.execution.verify_workspace", reject)
    with pytest.raises(ValueError, match="Build rejected"):
        verify_proposals(root, spec, [change], {"source"}, {"tech.metadata"})
    assert (root / change.path).read_text() == ORIGINAL
    assert not list(tmp_path.glob("proposal-*"))


def test_private_patch_is_rejected_before_verification(tmp_path, monkeypatch):
    root, spec, change = fixture(tmp_path)
    spec.page_intents = {"/": False}
    called = []
    monkeypatch.setattr(
        "seo_optimizer.execution.verify_workspace", lambda *args: called.append(args)
    )
    with pytest.raises(ValueError, match="private"):
        verify_proposals(root, spec, [change], {"source"}, {"tech.metadata"})
    assert not called
    assert (root / change.path).read_text() == ORIGINAL
