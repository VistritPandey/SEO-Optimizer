import json
from pathlib import Path

import pytest

from seo_optimizer.audit import SUPPORTED_CHECKS, audit
from seo_optimizer.cli import main
from seo_optimizer.contracts import BenchmarkCase
from seo_optimizer.knowledge import KnowledgePackage

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "case_id",
    [
        "public-missing-title",
        "public-healthy-title",
        "private-untitled",
        "preview-untitled",
        "accidental-noindex",
        "intentional-noindex",
        "header-noindex",
        "healthy-indexable",
        "canonical-conflict",
        "canonical-missing-not-defect",
        "canonical-equivalent",
        "broken-internal-link",
        "redirect-link-is-valid",
        "unobserved-link",
        "external-link-outside-baseline",
        "failed-response-not-healthy",
        "offer-price-conflict",
        "offer-consistent",
        "page-injection",
    ],
)
def test_baseline_against_raw_observations(
    case_id: str,
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    case = cases[case_id]
    result = audit(case, knowledge)
    assert not result.unsupported_checks
    assert {(item.check_id, item.status) for item in result.assessment.findings} == {
        (item.check_id, item.status) for item in case.expected_findings
    }


def test_unsupported_scanner_is_explicit(
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["hreflang-one-way"]
    result = audit(case, knowledge)
    assert result.unsupported_checks == ["intl.hreflang"]
    assert not result.evaluated_checks


def test_no_response_evidence_is_unresolved(
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["public-missing-title"].model_copy(update={"evidence": []})
    result = audit(case, knowledge)
    assert result.assessment.findings[0].status == "unresolved"


def test_baseline_cannot_cross_project_boundary(
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["public-missing-title"].model_copy(deep=True)
    case.evidence[0].project_id = "another-project"
    with pytest.raises(ValueError, match="boundary"):
        audit(case, knowledge)


def test_missing_optional_headers_do_not_crash(
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["public-missing-title"].model_copy(deep=True)
    del case.evidence[0].data["headers"]
    assert audit(case, knowledge).assessment.findings


def test_equivalent_offer_format_is_not_a_defect(
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["offer-consistent"].model_copy(deep=True)
    case.evidence[0].data["visible_offer"] = {
        "price": 25,
        "priceCurrency": "usd",
        "availability": "https://schema.org/InStock",
    }
    assert not audit(case.to_request(), knowledge).assessment.findings


def test_missing_offer_observation_remains_unresolved(
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["offer-consistent"].model_copy(deep=True)
    del case.evidence[0].data["visible_offer"]
    assert audit(case.to_request(), knowledge).assessment.findings[0].status == "unresolved"


def test_fragment_navigation_does_not_require_http_destination(
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["unobserved-link"].model_copy(deep=True)
    case.evidence[0].data["html"] = '<title>Guide</title><a href="#section">Section</a>'
    assert not audit(case.to_request(), knowledge).assessment.findings


def test_missing_status_is_not_assumed_successful(
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    case = cases["public-healthy-title"].model_copy(deep=True)
    del case.evidence[0].data["status_code"]
    assert audit(case.to_request(), knowledge).assessment.findings[0].status == "unresolved"


def test_baseline_refuses_to_silently_collapse_multiple_pages(
    cases: dict[str, BenchmarkCase],
    knowledge: KnowledgePackage,
) -> None:
    request = cases["public-missing-title"].to_request().model_copy(deep=True)
    second = request.evidence[0].model_copy(update={"id": "second-page"})
    request.evidence.append(second)
    with pytest.raises(ValueError, match="one HTTP page"):
        audit(request, knowledge)


def test_validate_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "passed"


def test_evaluate_cli_writes_report(tmp_path: Path) -> None:
    output = tmp_path / "nested/report.json"
    assert (
        main(
            [
                "evaluate",
                "--cases",
                str(FIXTURES / "cases.json"),
                "--responses",
                str(FIXTURES / "reference-responses.json"),
                "--split",
                "all",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(output.read_text())["counts"]["passed"] == 41


def test_missing_responses_returns_incomplete_exit_code(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text("[]")
    assert (
        main(
            [
                "evaluate",
                "--cases",
                str(FIXTURES / "cases.json"),
                "--responses",
                str(empty),
                "--output",
                str(tmp_path / "report.json"),
            ]
        )
        == 2
    )


def test_rules_cli_preserves_coverage(tmp_path: Path) -> None:
    output = tmp_path / "rules.json"
    assert (
        main(
            [
                "rules",
                "--cases",
                str(FIXTURES / "cases.json"),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    records = json.loads(output.read_text())
    for record in records:
        assert record["provider"] == "rules"
        assert record["usage"]["api_cost_usd"] is None
    assert len(records) < 41  # Other catalog checks have no scanner yet.
    assert len(SUPPORTED_CHECKS) == 5
