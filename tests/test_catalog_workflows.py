"""All 39 collection/assessment paths; scripted reviews test workflow, not model judgment."""

from copy import deepcopy

import pytest
from pydantic import ValidationError
from workflow_fixtures import ROOT, rich_context

from seo_optimizer.application_models import CheckReview
from seo_optimizer.catalog_audit import (
    MODEL_INPUTS,
    SEMANTIC_FOLLOWUPS,
    apply_reviews,
    complete_catalog,
)
from seo_optimizer.contracts import Assessment, AuditRequest, Finding, ProviderCapabilities
from seo_optimizer.knowledge import load_knowledge
from seo_optimizer.policy import validate_assessment
from seo_optimizer.scanner import context, scan

PACKAGE = load_knowledge()
SEMANTIC = sorted(set(MODEL_INPUTS) | set(SEMANTIC_FOLLOWUPS))


def assess(spec, workspace, evidence):
    findings, report = scan(
        context("fixture-tenant", "fixture-site", spec), spec, evidence, PACKAGE
    )
    requested = complete_catalog(spec, evidence, workspace, PACKAGE, findings, report)
    return findings, report, requested


@pytest.mark.parametrize("check_id", sorted(PACKAGE.checks))
def test_every_check_reaches_a_grounded_conclusion_or_semantic_handoff(check_id):
    spec, workspace, evidence = rich_context()
    findings, report, requested = assess(spec, workspace, evidence)
    row = next(r for r in report["coverage"] if r["check_id"] == check_id)
    assert row["state"] in {"healthy", "needs_model"}
    assert row["evidence_ids"] and row["source_ids"] and row["verification"]
    if row["state"] == "needs_model":
        assert check_id in {r["id"] for r in requested}
        review = CheckReview(
            check_id=check_id,
            state="healthy",
            reason="Scripted fixture review of supplied observations; no model quality inference.",
            evidence_ids=[e.id for e in evidence],
        )
        apply_reviews(report, [review], evidence, findings, requested)
        assert next(r for r in report["coverage"] if r["check_id"] == check_id)["model_reviewed"]
    else:
        assert not any(f.check_id == check_id and f.status == "defect" for f in findings)
    assert next(r for r in report["coverage"] if r["check_id"] == check_id)["state"] == "healthy"


@pytest.mark.parametrize("check_id", SEMANTIC)
@pytest.mark.parametrize("state", ["defect", "needs_data"])
def test_every_semantic_workflow_validates_findings_or_records_blockers(check_id, state):
    spec, workspace, evidence = rich_context()
    findings, report, requested = assess(spec, workspace, evidence)
    check = PACKAGE.checks[check_id]
    experimental = check.assessment == "experimental"
    if experimental and state == "defect":
        # Experiments retain hypothesis strength; they cannot become established defects.
        finding_status, strength, action = "experiment", "hypothesis", "experiment"
    elif state == "defect":
        finding_status, strength, action = "defect", "supported", "investigate"
    else:
        finding_status, strength, action = "unresolved", "hypothesis", "collect_evidence"
        if experimental:
            action = "none"
    finding = Finding(
        check_id=check_id,
        status=finding_status,
        severity="medium",
        evidence_strength=strength,
        summary="Scripted fixture decision",
        evidence_ids=[e.id for e in evidence],
        source_ids=check.source_ids,
        action={"kind": action, "rationale": "Follow the supplied evidence"},
        verification_criteria=check.verification,
        dependencies=["Collect the missing authoritative observation"]
        if state == "needs_data"
        else [],
    )
    errors = validate_assessment(
        Assessment(
            tenant_id="fixture-tenant",
            project_id="fixture-site",
            environment="production",
            findings=[finding],
        ),
        AuditRequest(
            project=context("fixture-tenant", "fixture-site", spec),
            environment="production",
            evidence=evidence,
            allowed_check_ids=[check_id],
        ),
        PACKAGE,
        ProviderCapabilities(json_schema=True),
    )
    assert not errors
    review_state = "needs_data" if experimental else state
    review = CheckReview(
        check_id=check_id,
        state=review_state,
        reason="Scripted fixture decision",
        evidence_ids=[e.id for e in evidence],
        dependencies=["Retain experiment limitations or collect missing proof"]
        if review_state == "needs_data"
        else [],
    )
    apply_reviews(report, [review], evidence, [*findings, finding], requested)
    row = next(r for r in report["coverage"] if r["check_id"] == check_id)
    assert row["state"] == review_state and row["model_reviewed"]
    if review_state == "needs_data":
        assert row["dependencies"]
    if state == "defect" and not experimental:
        with pytest.raises(ValueError, match="conflicts"):
            apply_reviews(
                report,
                [review.model_copy(update={"state": "healthy"})],
                evidence,
                [finding],
                requested,
            )


@pytest.mark.parametrize("check_id", SEMANTIC)
def test_missing_required_context_never_becomes_a_semantic_pass(check_id):
    spec, workspace, evidence = rich_context()
    inputs = {**MODEL_INPUTS, **SEMANTIC_FOLLOWUPS}[check_id]
    missing = inputs[-1]
    if missing == "pages":
        evidence = [e for e in evidence if e.kind != "http"]
    elif missing == "dom":
        evidence = [e for e in evidence if e.kind != "dom"]
    elif missing == "facts":
        spec.facts = []
    elif missing == "goals":
        spec.goals = []
    elif missing == "route_map":
        spec.route_map = {}
    elif missing == "search":
        workspace.search = []
    elif missing == "citations":
        workspace.citations = []
    elif missing == "competitor_material":
        workspace.materials = [m for m in workspace.materials if m.origin != "competitor"]
    elif missing == "original_material":
        workspace.materials = [m for m in workspace.materials if not m.original]
    elif missing in {"media_observations", "navigation_observations", "visible_offers"}:
        key = "visible_offer" if missing == "visible_offers" else missing
        for e in evidence:
            e.data.pop(key, None)
    elif missing == "comparable_experiment":
        workspace.citations = [c for c in workspace.citations if c.arm != "holdout"]
    else:
        spec.facts = [f for f in spec.facts if f.name != missing]
    _, report, requested = assess(spec, workspace, evidence)
    assert check_id not in {r["id"] for r in requested}
    row = next(r for r in report["coverage"] if r["check_id"] == check_id)
    assert row["state"] == "needs_data" and row["dependencies"]


def test_recurring_locales_resolve_collection_notices_without_erasing_real_defects():
    spec, workspace, evidence = rich_context()
    findings, report, requested = assess(spec, workspace, evidence)
    assert "intl.hreflang" in {r["id"] for r in requested}
    assert not any(f.check_id == "intl.hreflang" and f.status == "unresolved" for f in findings)
    for e in evidence:
        if str(e.url) == ROOT + "fr/":
            e.data["html"] = e.data["html"].replace(f'href="{ROOT}"', f'href="{ROOT}wrong"')
    findings, report, requested = assess(spec, workspace, evidence)
    assert any(f.check_id == "intl.hreflang" and f.status == "defect" for f in findings)
    assert "intl.hreflang" not in {r["id"] for r in requested}


def test_failed_one_review_cannot_modify_the_original_report():
    spec, workspace, evidence = rich_context()
    findings, report, requested = assess(spec, workspace, evidence)
    before = deepcopy(report)
    with pytest.raises(ValueError, match="unknown evidence"):
        apply_reviews(
            report,
            [
                CheckReview(
                    check_id="commerce.variants",
                    state="healthy",
                    reason="No proof",
                    evidence_ids=["invented"],
                )
            ],
            evidence,
            findings,
            requested,
        )
    assert report == before


@pytest.mark.parametrize("automatic,dependencies", [(True, ["Missing baseline"]), (False, [])])
def test_experimental_unknown_cannot_authorize_action_or_hide_missing_dependency(
    automatic, dependencies
):
    spec, _, evidence = rich_context()
    check = PACKAGE.checks["geo.experiment"]
    with pytest.raises(ValidationError, match="automatic action|unresolved findings"):
        Finding(
            check_id=check.id,
            status="unresolved",
            severity="info",
            evidence_strength="hypothesis",
            summary="No comparable baseline",
            evidence_ids=[evidence[0].id],
            source_ids=check.source_ids,
            action={"kind": "none", "automatic": automatic, "rationale": "Wait for proof"},
            dependencies=dependencies,
            verification_criteria=check.verification,
        )
