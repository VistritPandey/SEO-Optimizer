"""Load and cross-validate the private, wheel-packaged knowledge asset offline."""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from seo_optimizer.contracts import Check, CheckCatalog, Module, Source, SourceRegistry

DEFAULT_KNOWLEDGE = Path(__file__).parent / "knowledge" / "search-optimization"


@dataclass(frozen=True)
class KnowledgePackage:
    root: Path
    catalog: CheckCatalog
    registry: SourceRegistry

    @property
    def checks(self) -> dict[str, Check]:
        return {check.id: check for check in self.catalog.checks}

    @property
    def sources(self) -> dict[str, Source]:
        return {source.id: source for source in self.registry.sources}


def load_knowledge(root: Path = DEFAULT_KNOWLEDGE) -> KnowledgePackage:
    catalog = CheckCatalog.model_validate_json((root / "checks.json").read_text(), strict=True)
    registry = SourceRegistry.model_validate_json((root / "sources.json").read_text(), strict=True)
    package = KnowledgePackage(root.resolve(), catalog, registry)
    errors = validate_knowledge(package)
    if errors:
        raise ValueError("Invalid knowledge package:\n" + "\n".join(errors))
    return package


def validate_knowledge(package: KnowledgePackage) -> list[str]:
    errors: list[str] = []
    if package.catalog.version != package.registry.version:
        errors.append("catalog and registry version mismatch")
    for name, identifiers in (
        ("check", [check.id for check in package.catalog.checks]),
        ("source", [source.id for source in package.registry.sources]),
    ):
        if len(identifiers) != len(set(identifiers)):
            errors.append(f"duplicate {name} identifiers")
    if {check.module for check in package.catalog.checks} != set(Module):
        errors.append("catalog does not cover all eight modules")
    for check in package.catalog.checks:
        reference = (package.root / check.reference).resolve()
        if not reference.is_relative_to(package.root) or not reference.is_file():
            errors.append(f"{check.id}: missing or escaping reference {check.reference}")
        for source_id in check.source_ids:
            source = package.sources.get(source_id)
            if source is None:
                errors.append(f"{check.id}: unknown source {source_id}")
            elif check.id not in source.supports:
                errors.append(f"{check.id}: source {source_id} does not declare support")
        if check.assessment == "experimental" and not any(
            package.sources[source_id].source_type == "research"
            for source_id in check.source_ids
            if source_id in package.sources
        ):
            errors.append(f"{check.id}: experiment requires research provenance")
    for source in package.registry.sources:
        if source.verified_on > package.registry.as_of:
            errors.append(f"{source.id}: verification date exceeds knowledge as-of date")
        for check_id in source.supports:
            if check_id not in package.checks:
                errors.append(f"{source.id}: unknown supported check {check_id}")
            elif source.id not in package.checks[check_id].source_ids:
                errors.append(f"{source.id}: asymmetric support for {check_id}")
    entrypoint = package.root / "SKILL.md"
    if not entrypoint.is_file():
        errors.append("missing SKILL.md")
        return errors
    text = entrypoint.read_text()
    parts = text.split("---", 2)
    try:
        metadata = yaml.safe_load(parts[1]) if text.startswith("---\n") else None
        if not isinstance(metadata, dict) or not metadata.get("description"):
            errors.append("invalid skill frontmatter")
        elif metadata.get("name") != "search-optimization":
            errors.append("unexpected skill name")
    except (IndexError, yaml.YAMLError):
        errors.append("invalid skill frontmatter")
    # Follow actual local Markdown links, including links in supporting references.
    links: dict[Path, set[Path]] = {}
    for document in package.root.rglob("*.md"):
        links[document.resolve()] = set()
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text()):
            if target.startswith(("https://", "http://", "#")):
                continue
            path = (document.parent / target.split("#", 1)[0]).resolve()
            if not path.is_relative_to(package.root) or not path.is_file():
                errors.append(f"{document.name}: broken or escaping link {target}")
            else:
                links[document.resolve()].add(path)
    reachable: set[Path] = set()
    pending = [entrypoint.resolve()]
    while pending:
        document_path = pending.pop()
        if document_path in reachable:
            continue
        reachable.add(document_path)
        pending.extend(links.get(document_path, set()) - reachable)
    for check in package.catalog.checks:
        if (package.root / check.reference).resolve() not in reachable:
            errors.append(f"{check.id}: reference is not discoverable from Markdown")
    return errors
