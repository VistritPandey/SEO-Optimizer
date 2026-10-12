import json
import shutil
from pathlib import Path

import pytest

from seo_optimizer.knowledge import KnowledgePackage, load_knowledge


def copy_package(knowledge: KnowledgePackage, tmp_path: Path) -> Path:
    root = tmp_path / "search-optimization"
    shutil.copytree(knowledge.root, root)
    return root


def test_catalog_source_integrity(knowledge: KnowledgePackage) -> None:
    assert len(knowledge.checks) == 39
    assert len(knowledge.sources) == 30
    assert all(
        source.verified_on <= knowledge.registry.as_of for source in knowledge.registry.sources
    )


def test_deleted_reference_fails_validation(knowledge: KnowledgePackage, tmp_path: Path) -> None:
    root = copy_package(knowledge, tmp_path)
    (root / "references/technical.md").unlink()
    with pytest.raises(ValueError, match="missing or escaping reference"):
        load_knowledge(root)


def test_unknown_source_fails_validation(knowledge: KnowledgePackage, tmp_path: Path) -> None:
    root = copy_package(knowledge, tmp_path)
    path = root / "checks.json"
    catalog = json.loads(path.read_text())
    catalog["checks"][0]["source_ids"] = ["missing-source"]
    path.write_text(json.dumps(catalog))
    with pytest.raises(ValueError, match="unknown source"):
        load_knowledge(root)


def test_source_support_is_bidirectional(knowledge: KnowledgePackage, tmp_path: Path) -> None:
    root = copy_package(knowledge, tmp_path)
    path = root / "sources.json"
    registry = json.loads(path.read_text())
    registry["sources"][0]["supports"] = ["not-a-real-check"]
    path.write_text(json.dumps(registry))
    with pytest.raises(ValueError, match="unknown supported check"):
        load_knowledge(root)


def test_future_verification_date_fails_validation(
    knowledge: KnowledgePackage, tmp_path: Path
) -> None:
    root = copy_package(knowledge, tmp_path)
    path = root / "sources.json"
    registry = json.loads(path.read_text())
    registry["sources"][0]["verified_on"] = "2027-01-01"
    path.write_text(json.dumps(registry))
    with pytest.raises(ValueError, match="verification date exceeds"):
        load_knowledge(root)


def test_broken_markdown_link_fails_validation(knowledge: KnowledgePackage, tmp_path: Path) -> None:
    root = copy_package(knowledge, tmp_path)
    entrypoint = root / "SKILL.md"
    entrypoint.write_text(entrypoint.read_text() + "\n[Missing](references/missing.md)\n")
    with pytest.raises(ValueError, match="broken or escaping link"):
        load_knowledge(root)


def test_reference_path_traversal_rejected(knowledge: KnowledgePackage, tmp_path: Path) -> None:
    root = copy_package(knowledge, tmp_path)
    path = root / "checks.json"
    catalog = json.loads(path.read_text())
    catalog["checks"][0]["reference"] = "../outside.md"
    path.write_text(json.dumps(catalog))
    with pytest.raises(ValueError):
        load_knowledge(root)


def test_orphan_reference_is_not_considered_discoverable(
    knowledge: KnowledgePackage,
    tmp_path: Path,
) -> None:
    root = copy_package(knowledge, tmp_path)
    entry = root / "SKILL.md"
    entry.write_text(
        entry.read_text().replace("[technical](references/technical.md)", "technical guidance")
    )
    (root / "orphan.md").write_text("[Hidden](references/technical.md)")
    with pytest.raises(ValueError, match="not discoverable"):
        load_knowledge(root)
