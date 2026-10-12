import json
from pathlib import Path

import pytest

from seo_optimizer.contracts import (
    ActionKind,
    Assessment,
    BenchmarkCase,
    ProposedAction,
    ResponseRecord,
    TrustedFact,
    Usage,
)
from seo_optimizer.evaluation import evaluate, evaluate_case, load_responses
from seo_optimizer.knowledge import KnowledgePackage
from seo_optimizer.policy import validate_assessment, validate_case

FIXTURES = Path(__file__).parent / "fixtures"


def altered(record: ResponseRecord, assessment: Assessment) -> ResponseRecord:
    return record.model_copy(update={"raw_response": assessment.model_dump_json()})


def test_authored_reference_replays_validate(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    report = evaluate(list(cases.values()), list(records.values()), knowledge, "all")
    assert report.counts == {"passed": 41, "failed": 0, "skipped": 0}
    assert report.metrics["verified_fixes"] is None
    assert report.metrics["total_cost_usd"] is None
    assert report.unverified


@pytest.mark.parametrize(
    "case_id",
    [
        "public-missing-title",
        "accidental-noindex",
        "canonical-conflict",
        "llms-google-promise",
        "faq-obsolete-promise",
        "wrong-business-hours",
        "offer-price-conflict",
        "bounded-citation-experiment",
        "screenshot-only-evidence",
        "tool-failure-unresolved",
    ],
)
def test_adversarial_saved_outputs_fail(
    case_id: str,
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    records = {
        record.case_id: record for record in load_responses(FIXTURES / "adversarial-responses.json")
    }
    result = evaluate_case(cases[case_id], records[case_id], knowledge)
    assert result.status == "failed" and result.failures


def test_unnecessary_finding_on_healthy_page_is_false_positive(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    healthy = cases["public-healthy-title"]
    response = records["public-missing-title"].model_copy(update={"case_id": healthy.id})
    report = evaluate([healthy], [response], knowledge)
    assert report.counts["failed"] == 1
    assert report.metrics["false_positives"] == 1


def test_unknown_evidence_does_not_count_as_true_positive(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["public-missing-title"]
    record = records[case.id]
    assessment = Assessment.model_validate_json(record.raw_response)
    assessment.findings[0].evidence_ids = ["invented"]
    report = evaluate([case], [altered(record, assessment)], knowledge)
    assert report.metrics["true_positives"] == 0
    assert report.metrics["false_negatives"] == 1


def test_missing_responses_are_skipped_not_passed(
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    report = evaluate(list(cases.values()), [], knowledge)
    assert report.counts["passed"] == 0
    assert report.metrics["coverage"] == 0
    assert report.metrics["detection_recall"] is None


def test_held_out_cases_are_not_scored_by_default(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    report = evaluate(list(cases.values()), list(records.values()), knowledge)
    assert all(cases[result.case_id].split == "development" for result in report.results)


def test_mixed_runs_rejected(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    samples = list(records.values())[:2]
    samples[1] = samples[1].model_copy(update={"provider": "different-provider"})
    with pytest.raises(ValueError, match="mixed provider/model"):
        evaluate(list(cases.values()), samples, knowledge)


def test_duplicate_case_responses_rejected(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    record = records["public-missing-title"]
    with pytest.raises(ValueError, match="duplicate response"):
        evaluate(list(cases.values()), [record, record], knowledge)


@pytest.mark.parametrize("field", ["tenant_id", "project_id", "environment"])
def test_evidence_scope_rejected(
    field: str,
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["public-missing-title"].model_copy(deep=True)
    setattr(case.evidence[0], field, "wrong-scope")
    assert validate_case(case, knowledge)


def test_training_preference_preserved(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["missing-owner-bot-policy"].model_copy(deep=True)
    case.project.crawler_preferences = {"GPTBot": "block"}
    assessment = Assessment.model_validate_json(records[case.id].raw_response)
    assessment.findings[0].action.crawler_changes = {"GPTBot": "allow"}
    assert any(
        "crawler change conflicts" in failure
        for failure in validate_assessment(
            assessment, case, knowledge, records[case.id].capabilities
        )
    )


def test_private_url_cannot_be_exposed(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["accidental-noindex"].model_copy(deep=True)
    case.project.page_intents = {"https://example.test/": False}
    assessment = Assessment.model_validate_json(records[case.id].raw_response)
    assessment.findings[0].action.indexability_changes = {"https://example.test/": True}
    assert any(
        "indexability change" in failure
        for failure in validate_assessment(
            assessment, case, knowledge, records[case.id].capabilities
        )
    )


def test_publication_without_trusted_facts_rejected(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["invented-product-claim"].model_copy(deep=True)
    case.allowed_check_ids = ["content.originality"]
    assessment = Assessment.model_validate_json(records[case.id].raw_response)
    finding = assessment.findings[0]
    finding.check_id = "content.originality"
    finding.source_ids = knowledge.checks[finding.check_id].source_ids
    finding.action = ProposedAction(
        kind=ActionKind.PUBLISH_CONTENT, rationale="Unsupported publication", automatic=True
    )
    assert any(
        "lacks trusted facts" in failure
        for failure in validate_assessment(
            assessment, case, knowledge, records[case.id].capabilities
        )
    )


def test_tool_capability_is_not_assumed(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["tool-failure-unresolved"]
    record = records[case.id].model_copy(deep=True)
    record.capabilities.tool_calling = False
    assert evaluate_case(case, record, knowledge).status == "failed"


def test_vision_capability_is_not_assumed(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["screenshot-only-evidence"]
    record = records[case.id].model_copy(deep=True)
    record.capabilities.vision = False
    assert evaluate_case(case, record, knowledge).status == "failed"


def test_provider_failure_is_failed_not_skipped(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["public-missing-title"]
    record = records[case.id].model_copy(update={"run_error": "model unavailable"})
    assert evaluate_case(case, record, knowledge).status == "failed"


def test_measured_zero_cost_is_not_missing(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["public-missing-title"]
    record = records[case.id].model_copy(
        update={
            "runtime_ms": 0,
            "usage": Usage(api_cost_usd=0, electricity_cost_usd=0, hardware_cost_usd=0),
        }
    )
    report = evaluate([case], [record], knowledge)
    assert report.metrics["total_cost_usd"] == 0
    assert report.metrics["mean_runtime_ms"] == 0


def test_prose_changes_do_not_change_grade(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["public-missing-title"]
    record = records[case.id]
    assessment = Assessment.model_validate_json(record.raw_response)
    assessment.findings[0].summary = "A differently worded explanation of the same observed defect."
    assert evaluate_case(case, altered(record, assessment), knowledge).status == "passed"


def test_model_request_excludes_benchmark_answers(cases: dict[str, BenchmarkCase]) -> None:
    request = cases["public-missing-title"].to_request().model_dump()
    assert "expected_findings" not in request
    assert "split" not in request
    assert "description" not in request
    assert request["evidence"]


def test_expired_fact_cannot_support_automatic_publication(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["invented-product-claim"].model_copy(deep=True)
    case.allowed_check_ids = ["content.originality"]
    case.project.trusted_facts = [
        TrustedFact(
            id="expired-feature",
            name="feature",
            value="retired",
            source="owner record",
            verified_at="2026-01-01T00:00:00Z",
            valid_until="2026-09-01T00:00:00Z",
        )
    ]
    assessment = Assessment.model_validate_json(records[case.id].raw_response)
    finding = assessment.findings[0]
    finding.check_id = "content.originality"
    finding.source_ids = knowledge.checks[finding.check_id].source_ids
    finding.action = ProposedAction(
        kind=ActionKind.PUBLISH_CONTENT,
        rationale="Publish stale claim",
        automatic=True,
        fact_ids=["expired-feature"],
    )
    assert any(
        "expired business facts" in failure
        for failure in validate_assessment(
            assessment, case, knowledge, records[case.id].capabilities
        )
    )


def test_automatic_change_cannot_depend_only_on_screenshot(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["screenshot-only-evidence"]
    raw = json.loads(records[case.id].raw_response)
    raw["findings"][0].update(status="defect", evidence_strength="confirmed", dependencies=[])
    raw["findings"][0]["action"].update(kind="propose_patch", automatic=True)
    assessment = Assessment.model_validate(raw)
    assert any(
        "non-visual corroboration" in failure
        for failure in validate_assessment(
            assessment, case, knowledge, records[case.id].capabilities
        )
    )


def test_empty_report_partition_is_not_a_success(
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    with pytest.raises(ValueError, match="partition is empty"):
        evaluate([cases["public-missing-title"]], [], knowledge, "held_out")


def test_validation_errors_do_not_echo_private_input(
    cases: dict[str, BenchmarkCase],
    records: dict[str, ResponseRecord],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["public-missing-title"]
    raw = json.loads(records[case.id].raw_response)
    raw["confidential_extra"] = "fixture-sensitive-value"
    record = records[case.id].model_copy(update={"raw_response": json.dumps(raw)})
    result = evaluate_case(case, record, knowledge)
    assert "fixture-sensitive-value" not in str(result.failures)
