import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from seo_optimizer.contracts import (
    Assessment,
    BenchmarkCase,
    Evidence,
    Finding,
    ProjectContext,
    ProviderCapabilities,
    ResponseRecord,
    ToolResult,
    Usage,
    schema_models,
)
from seo_optimizer.evaluation import save_schemas
from seo_optimizer.providers import parse_assessment


def test_json_schemas_are_valid_and_example_matches(
    tmp_path: Path, records: dict[str, ResponseRecord]
) -> None:
    save_schemas(tmp_path)
    for name in schema_models():
        schema = json.loads((tmp_path / f"{name}.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
        published = Path(__file__).parents[1] / "schemas" / f"{name}.schema.json"
        assert json.loads(published.read_text()) == schema
    schema = json.loads((tmp_path / "Assessment.schema.json").read_text())
    Draft202012Validator(schema).validate(json.loads(records["public-missing-title"].raw_response))


def test_evidence_requires_locator(cases: dict[str, BenchmarkCase]) -> None:
    raw = cases["public-missing-title"].evidence[0].model_dump()
    raw.update(url=None, source_file=None)
    with pytest.raises(ValidationError):
        Evidence.model_validate(raw)


def test_evidence_requires_timezone(cases: dict[str, BenchmarkCase]) -> None:
    raw = cases["public-missing-title"].evidence[0].model_dump()
    raw["collected_at"] = "2026-10-12T12:00:00"
    with pytest.raises(ValidationError):
        Evidence.model_validate(raw)


def test_extra_provider_claims_are_rejected(records: dict[str, ResponseRecord]) -> None:
    raw = json.loads(records["public-missing-title"].raw_response)
    raw["verified_fix"] = True
    with pytest.raises(ValidationError):
        Assessment.model_validate(raw)


def test_raw_provider_output_cannot_coerce_boolean_policy_fields(
    records: dict[str, ResponseRecord],
) -> None:
    raw = json.loads(records["public-missing-title"].raw_response)
    raw["findings"][0]["action"]["automatic"] = "false"
    with pytest.raises(ValidationError):
        parse_assessment(json.dumps(raw))


@pytest.mark.parametrize(
    "change",
    [
        {"dependencies": []},
        {"action": {"kind": "propose_patch", "rationale": "Guess a fix"}},
    ],
)
def test_unresolved_findings_cannot_hide_dependencies_or_propose_repairs(
    records: dict[str, ResponseRecord], change: dict[str, object]
) -> None:
    finding = json.loads(records["unknown-business-hours"].raw_response)["findings"][0]
    finding.update(change)
    with pytest.raises(ValidationError):
        Finding.model_validate(finding)


def test_hypothesis_cannot_be_automatic(records: dict[str, ResponseRecord]) -> None:
    finding = json.loads(records["bounded-citation-experiment"].raw_response)["findings"][0]
    finding["action"]["automatic"] = True
    with pytest.raises(ValidationError):
        Finding.model_validate(finding)


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_costs_rejected(value: float) -> None:
    with pytest.raises(ValidationError):
        Usage(api_cost_usd=value)


def test_missing_cost_is_unknown_and_measured_zero_is_zero() -> None:
    assert Usage(api_cost_usd=0).total_cost() is None
    assert Usage(api_cost_usd=0, electricity_cost_usd=0, hardware_cost_usd=0).total_cost() == 0


def test_capabilities_are_independent() -> None:
    flags = ProviderCapabilities(tool_calling=True)
    assert flags.tool_calling and not flags.vision and not flags.json_schema


@pytest.mark.parametrize("root", ["..", "/", ".", "../secrets", "web/../../secrets"])
def test_policy_roots_cannot_escape_repo(
    root: str,
    cases: dict[str, BenchmarkCase],
) -> None:
    project = cases["public-missing-title"].project.model_dump()
    project["allowed_paths"] = [root]
    with pytest.raises(ValidationError):
        ProjectContext.model_validate(project)


@pytest.mark.parametrize(
    "raw",
    [
        {"call_id": "1", "success": False},
        {"call_id": "1", "success": True, "error": "failed"},
    ],
)
def test_tool_results_cannot_claim_contradictory_success(raw: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ToolResult.model_validate(raw)
