"""Attach application-observed source provenance; never trust model-created IDs."""

from pathlib import Path

from seo_optimizer.application_models import FileChange, ProjectSpec
from seo_optimizer.contracts import Evidence
from seo_optimizer.execution import confined


def ground_patch(
    change: FileChange,
    evidence: list[Evidence],
    root: Path,
    spec: ProjectSpec,
    tenant: str,
    project: str,
) -> FileChange:
    scoped = [
        item
        for item in evidence
        if item.tenant_id == tenant
        and item.project_id == project
        and item.environment == spec.environment
    ]
    if not set(change.evidence_ids).issubset({item.id for item in scoped}):
        raise ValueError("Patch references evidence outside the current job")
    source = next(
        (
            item
            for item in reversed(scoped)
            if item.kind == "source" and item.source_file == change.path
        ),
        None,
    )
    if source is None:
        raise ValueError("Read the same source file successfully before staging a patch")
    current = confined(root, change.path, spec.allowed_paths).read_text()
    if source.data.get("text") != current:
        raise ValueError("Source read is stale; read the current file before staging a patch")
    # This provenance is created by read_file, not inferred from the model's prose.
    return change.model_copy(
        update={"evidence_ids": list(dict.fromkeys([*change.evidence_ids, source.id]))}
    )
