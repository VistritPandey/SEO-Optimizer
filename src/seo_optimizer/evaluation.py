"""Evaluate saved decisions, not prose similarity; preserve missing measurements."""

import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import JsonValue, TypeAdapter, ValidationError

from seo_optimizer.contracts import (
    BenchmarkCase,
    EvaluationReport,
    EvaluationResult,
    FindingStatus,
    ResponseRecord,
    utc_now,
)
from seo_optimizer.knowledge import KnowledgePackage
from seo_optimizer.policy import validate_assessment, validate_case
from seo_optimizer.providers import parse_assessment


def load_cases(path: Path, package: KnowledgePackage) -> list[BenchmarkCase]:
    cases = TypeAdapter(list[BenchmarkCase]).validate_json(path.read_text(), strict=True)
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("duplicate benchmark case identifiers")
    for case in cases:
        errors = validate_case(case, package)
        if errors:
            raise ValueError(f"{case.id}: " + "; ".join(errors))
    return cases


def load_responses(path: Path) -> list[ResponseRecord]:
    return TypeAdapter(list[ResponseRecord]).validate_json(path.read_text(), strict=True)


def evaluate_case(
    case: BenchmarkCase,
    record: ResponseRecord | None,
    package: KnowledgePackage,
) -> EvaluationResult:
    base = EvaluationResult(
        case_id=case.id,
        status="skipped",
        expected=case.expected_findings,
        failures=["no saved response supplied"],
    )
    if record is None:
        return base
    base.provider, base.model = record.provider, record.model
    base.runtime_ms, base.usage = record.runtime_ms, record.usage
    base.failures = []
    if record.run_error:
        base.status = "failed"
        base.failures = [f"provider/tool run failed: {record.run_error}"]
        return base
    try:
        assessment = parse_assessment(record.raw_response)
    except ValidationError as error:
        base.status = "failed"
        # Validation locations/types are useful; raw input may contain sensitive data.
        base.failures = [
            f"invalid assessment: {item['loc']} ({item['type']})"
            for item in error.errors(include_input=False)
        ]
        return base
    base.observed = assessment.findings
    base.failures.extend(validate_assessment(assessment, case, package, record.capabilities))
    expected = {(item.check_id, item.status): item for item in case.expected_findings}
    observed = {(item.check_id, item.status): item for item in assessment.findings}
    for key in expected.keys() - observed.keys():
        base.failures.append(f"missing expected finding {key[0]}/{key[1]}")
    for key in observed.keys() - expected.keys():
        base.failures.append(f"unexpected finding {key[0]}/{key[1]}")
    for key in expected.keys() & observed.keys():
        actual, wanted = observed[key], expected[key]
        if actual.action.kind not in wanted.allowed_actions:
            base.failures.append(f"incorrect action for {key[0]}")
        if actual.action.automatic != wanted.automatic:
            base.failures.append(f"incorrect automatic-action decision for {key[0]}")
        if not set(wanted.required_evidence_ids).issubset(actual.evidence_ids):
            base.failures.append(f"missing required supporting evidence for {key[0]}")
    base.status = "failed" if base.failures else "passed"
    return base


def evaluate(
    cases: list[BenchmarkCase],
    records: list[ResponseRecord],
    package: KnowledgePackage,
    split: Literal["development", "held_out", "all"] = "development",
) -> EvaluationReport:
    known = {case.id for case in cases}
    if any(record.case_id not in known for record in records):
        raise ValueError("response references an unknown case")
    if len({record.case_id for record in records}) != len(records):
        raise ValueError("duplicate response records; evaluate each provider/model run separately")
    identities = {(record.provider, record.model) for record in records}
    if len(identities) > 1:
        raise ValueError("mixed provider/model runs would make aggregate comparisons misleading")
    selected = [case for case in cases if split == "all" or case.split == split]
    if not selected:
        raise ValueError("selected benchmark partition is empty")
    by_id = {record.case_id: record for record in records}
    results = [evaluate_case(case, by_id.get(case.id), package) for case in selected]
    counts = dict.fromkeys(("passed", "failed", "skipped"), 0)
    counts.update(Counter(result.status for result in results))
    tp = fp = fn = 0
    for result in results:
        if result.status == "skipped":
            continue
        wanted = {item.check_id for item in result.expected if item.status == FindingStatus.DEFECT}
        found = {item.check_id for item in result.observed if item.status == FindingStatus.DEFECT}
        # Invalid grounding cannot count as a true positive even with the right check ID.
        if result.status == "failed" and any(
            marker in failure
            for failure in result.failures
            for marker in (
                "unknown evidence",
                "unrelated sources",
                "boundary",
                "invalid assessment",
            )
        ):
            tp += 0
            fp += len(found)
            fn += len(wanted)
        else:
            tp += len(wanted & found)
            fp += len(found - wanted)
            fn += len(wanted - found)
    completed = [result for result in results if result.status != "skipped"]
    measured = [result.usage.total_cost() for result in completed if result.usage is not None]
    complete_cost = (
        bool(completed)
        and len(measured) == len(completed)
        and all(value is not None for value in measured)
    )
    runtimes = [result.runtime_ms for result in completed if result.runtime_ms is not None]
    metrics: dict[str, JsonValue] = {
        "evaluated_cases": len(completed),
        "coverage": len(completed) / len(selected),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "detection_precision": tp / (tp + fp) if tp + fp else None,
        "detection_recall": tp / (tp + fn) if tp + fn else None,
        "decision_pass_rate": counts["passed"] / len(completed) if completed else None,
        "unnecessary_actions": sum(
            finding.action.kind != "none"
            for result in completed
            for finding in result.observed
            if (finding.check_id, finding.status)
            not in {(expected.check_id, expected.status) for expected in result.expected}
        ),
        "mean_runtime_ms": sum(runtimes) / len(runtimes) if runtimes else None,
        "runtime_measured_cases": len(runtimes),
        "total_cost_usd": sum(value for value in measured if value is not None)
        if complete_cost
        else None,
        "cost_measured_cases": sum(value is not None for value in measured),
        "verified_fixes": None,
        "regressions": None,
        "cost_per_verified_fix_usd": None,
    }
    return EvaluationReport(
        generated_at=utc_now(),
        knowledge_version=package.catalog.version,
        split=split,
        results=results,
        counts=counts,
        metrics=metrics,
        unverified=[
            "Live provider capability and reasoning quality (saved responses are replay inputs).",
            "GitHub authentication, webhooks, writes, merges, and deployment verification.",
            "Verified fixes, regressions, search visibility, traffic, and conversion outcomes.",
            "Imported runtime and cost measurements are not independently attested.",
        ],
    )


def save_report(report: EvaluationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2) + "\n")


def save_schemas(path: Path) -> None:
    from seo_optimizer.contracts import schema_models

    path.mkdir(parents=True, exist_ok=True)
    for name, model in schema_models().items():
        (path / f"{name}.schema.json").write_text(
            json.dumps(model.model_json_schema(), indent=2) + "\n"
        )
