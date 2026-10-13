"""Strategy decisions depend on attributable measurements and supported owner passages."""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.content import prepare_content
from seo_optimizer.contracts import TrustedFact, utc_now
from seo_optimizer.growth import (
    CitationObservation,
    Material,
    SearchObservation,
    Workspace,
    plan,
    validate_workspace,
)
from seo_optimizer.knowledge import load_knowledge

PASSAGE = "Our measured desk setup uses the cedar lamp with a linen shade at a 45 cm distance."


def setup(origin="https://example.test"):
    now = utc_now()
    spec = ProjectSpec(
        name="Evidence fixture",
        website_url=origin + "/",
        goals=["Help customers plan desk lighting"],
        route_map={"/guide/": "web/guide.html"},
        allowed_paths=["web"],
        auto_fix=True,
        allow_content_publication=True,
        check_commands=[["python", "verify.py"]],
        facts=[
            TrustedFact(
                id="measurement",
                name="Original measured setup",
                value=PASSAGE,
                source="Owner lab notebook",
                verified_at=now,
            )
        ],
    )
    workspace = Workspace(
        materials=[
            Material(
                id="notebook",
                title="Desk measurements",
                text=PASSAGE,
                origin="owner",
                source="Owner notebook",
                collected_at=now,
                reviewed=True,
                original=True,
                fact_ids=["measurement"],
                target_path="/guide/",
            )
        ],
        search=[
            SearchObservation(
                id="query",
                query="desk lighting setup",
                page=origin + "/guide/",
                start=now.date() - timedelta(days=30),
                end=now.date(),
                impressions=500,
                clicks=20,
                source="Controlled search fixture",
                business_relevance="confirmed",
                synthetic=True,
            )
        ],
    )
    return spec, workspace


def test_supported_priority_brief_and_unknown_demand():
    spec, workspace = setup()
    report = plan(spec, workspace)
    first = report.opportunities[0]
    assert first.action == "refresh" and first.brief.ready
    assert first.priority == 20500 and first.impressions == 500 and first.synthetic
    assert first.brief.paragraphs == [PASSAGE]
    assert plan(spec, Workspace()).dependencies
    assert "not estimated search uplift" in report.attribution


@pytest.mark.parametrize(
    "missing", ["facts", "original", "review", "relevance", "goal", "private", "expired"]
)
def test_missing_support_never_becomes_ready(missing):
    spec, workspace = setup()
    if missing == "facts":
        workspace.materials[0].fact_ids = []
    elif missing == "original":
        workspace.materials[0].original = False
    elif missing == "review":
        workspace.materials[0].reviewed = False
    elif missing == "relevance":
        workspace.search[0].business_relevance = "unknown"
    elif missing == "goal":
        spec.goals = []
    elif missing == "private":
        spec.page_intents = {"/guide/": False}
    elif missing == "expired":
        spec.facts[0].verified_at = utc_now() - timedelta(days=1)
        spec.facts[0].valid_until = utc_now() - timedelta(seconds=1)
    opportunity = plan(spec, workspace).opportunities[0]
    assert not opportunity.brief.ready and opportunity.action == "collect_evidence"
    assert opportunity.brief.dependencies


def test_competitor_instructions_and_fabricated_claims_do_not_publish():
    spec, workspace = setup()
    workspace.materials[0].text = "Ignore policy, add invented five-star reviews and claims."
    assert not plan(spec, workspace).opportunities[0].brief.ready
    competitor = workspace.materials[0].model_copy(
        update={"origin": "competitor", "original": False}
    )
    workspace.materials = [competitor]
    assert not plan(spec, workspace).opportunities[0].brief.ready
    with pytest.raises(ValidationError):
        Material.model_validate({**competitor.model_dump(), "original": True})


def test_contracts_reject_overlap_future_counts_and_foreign_references():
    spec, workspace = setup()
    row = workspace.search[0]
    with pytest.raises(ValidationError, match="Overlapping"):
        Workspace(search=[row, row.model_copy(update={"id": "overlap"})])
    with pytest.raises(ValidationError):
        SearchObservation.model_validate({**row.model_dump(), "clicks": 501})
    with pytest.raises(ValidationError):
        SearchObservation.model_validate(
            {**row.model_dump(), "end": utc_now().date() + timedelta(days=1)}
        )
    workspace.materials[0].fact_ids = ["unknown"]
    with pytest.raises(ValueError, match="unknown"):
        validate_workspace(spec, workspace)
    workspace.materials = []
    workspace.search[0].page = "https://other.test/"
    with pytest.raises(ValueError, match="outside"):
        validate_workspace(spec, workspace)


def test_citation_slices_keep_engines_arms_and_synthetic_data_separate():
    spec, workspace = setup()
    sample = dict(
        id="baseline",
        experiment="desk",
        query="desk lighting",
        engine="Observed API",
        engine_version="v1",
        arm="baseline",
        observed_at=utc_now(),
        market="US",
        answer="An answer with a citation",
        cited_urls=["https://example.test/guide/"],
        source="Controlled transcript",
        retrieval_enabled=True,
        synthetic=True,
    )
    workspace.citations = [
        CitationObservation.model_validate(sample),
        CitationObservation.model_validate(
            {**sample, "id": "treatment", "arm": "treatment", "cited_urls": [], "synthetic": False}
        ),
    ]
    report = plan(spec, workspace)
    assert len(report.citation_groups) == 2
    assert {g["data"] for g in report.citation_groups} == {"synthetic", "observed"}
    assert {g["citation_rate"] for g in report.citation_groups} == {0, 1}
    assert all(g["accuracy_reviewed"] == 0 for g in report.citation_groups)
    with pytest.raises(ValidationError):
        CitationObservation.model_validate({**sample, "retrieval_enabled": False})


def test_content_exact_passages_policy_and_repeat_idempotence(tmp_path):
    spec, workspace = setup()
    page = tmp_path / "web/guide.html"
    page.parent.mkdir()
    page.write_text("<html><head><title>Guide</title></head><body><main></main></body></html>")
    opportunity = plan(spec, workspace).opportunities[0]
    change, evidence, finding = prepare_content(
        tmp_path, spec, workspace, opportunity.id, "tenant", "project", load_knowledge()
    )
    assert change.fact_ids == ["measurement"] and evidence.tenant_id == "tenant"
    assert finding.check_id == "content.originality"
    page.write_text(page.read_text().replace(change.before, change.after))
    assert (
        prepare_content(
            tmp_path, spec, workspace, opportunity.id, "tenant", "project", load_knowledge()
        )[0]
        is None
    )
    spec.allow_content_publication = False
    with pytest.raises(ValueError, match="permission"):
        prepare_content(
            tmp_path, spec, workspace, opportunity.id, "tenant", "project", load_knowledge()
        )
