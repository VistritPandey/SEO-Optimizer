"""Publish only reviewed original owner passages; never invent claims to fill a brief."""

import html
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from seo_optimizer.application_models import FileChange, ProjectSpec
from seo_optimizer.contracts import (
    ActionKind,
    Evidence,
    EvidenceStrength,
    Finding,
    FindingStatus,
    ProposedAction,
    Severity,
    utc_now,
)
from seo_optimizer.execution import confined
from seo_optimizer.growth import Workspace, plan
from seo_optimizer.knowledge import KnowledgePackage


def prepare_content(
    root: Path,
    spec: ProjectSpec,
    workspace: Workspace,
    opportunity_id: str,
    tenant: str,
    project: str,
    knowledge: KnowledgePackage,
) -> tuple[FileChange | None, Evidence, Finding | None]:
    if not (spec.auto_fix and spec.allow_content_publication and spec.check_commands):
        raise ValueError(
            "Content publication requires automatic fixes, permission and build checks"
        )
    opportunity = next(
        (o for o in plan(spec, workspace).opportunities if o.id == opportunity_id), None
    )
    if opportunity is None or opportunity.action != "refresh" or not opportunity.brief.ready:
        raise ValueError("Content opportunity needs current supporting evidence")
    brief = opportunity.brief
    path = spec.route_map[urlparse(str(brief.target_url)).path]
    target = confined(root, path, spec.allowed_paths)
    text = target.read_text()
    if target.suffix.lower() != ".html" or text.count("</main>") != 1:
        raise ValueError("Automatic original passages currently require an existing HTML main")
    item = Evidence(
        id=str(uuid4()),
        tenant_id=tenant,
        project_id=project,
        environment=spec.environment,
        kind="source",
        source_file=path,
        url=brief.target_url,
        collected_at=utc_now(),
        observation="Read source and verified original owner passages for this content brief",
        data={"brief": brief.model_dump(mode="json"), "text": text},
    )
    # Repeat jobs do not duplicate content already present in the source.
    paragraphs = [p for p in brief.paragraphs if html.escape(p) not in text]
    if not paragraphs:
        return None, item, None
    marker = f'<section data-optimizer-topic="{brief.id}">'
    if marker in text:
        raise ValueError("Existing managed passage changed; collect fresh editorial evidence")
    section = marker + "\n" + "\n".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)
    section += "\n</section>\n</main>"
    check = knowledge.checks["content.originality"]
    finding = Finding(
        check_id=check.id,
        summary="Reviewed original owner evidence is absent from the target page",
        severity=Severity.LOW,
        status=FindingStatus.DEFECT,
        evidence_strength=EvidenceStrength.SUPPORTED,
        evidence_ids=[item.id],
        source_ids=check.source_ids,
        action=ProposedAction(
            kind=ActionKind.PUBLISH_CONTENT,
            rationale="Publish supported original passages for an observed need",
        ),
        verification_criteria=["Observe each supported original passage on the served target page"],
    )
    change = FileChange(
        path=path,
        before="</main>",
        after=section,
        reason="Add reviewed original passages without generating new factual claims",
        check_id=check.id,
        evidence_ids=[item.id],
        fact_ids=brief.fact_ids,
    )
    return change, item, finding
