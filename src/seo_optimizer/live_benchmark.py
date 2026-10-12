"""Run the existing blinded-input decision rubric against an actual provider."""

import json
import os
import time
from pathlib import Path
from typing import Literal

from seo_optimizer.application_models import ProviderConfig
from seo_optimizer.audit import audit
from seo_optimizer.contracts import Assessment, ProviderCapabilities, ResponseRecord, Usage
from seo_optimizer.evaluation import evaluate, load_cases, save_report
from seo_optimizer.knowledge import load_knowledge
from seo_optimizer.llm import ModelClient

KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "ollama": "",
}


def benchmark(
    cases_path: Path,
    output: Path,
    provider: str,
    model: str,
    limit: int = 5,
    split: Literal["development", "held_out"] = "development",
    arm: Literal["model-only", "hybrid"] = "model-only",
) -> int:
    if limit < 1:
        raise ValueError("Benchmark limit must be positive")
    knowledge = load_knowledge()
    cases = [case for case in load_cases(cases_path, knowledge) if case.split == split][:limit]
    config = ProviderConfig.model_validate(
        {
            "kind": provider,
            "model": model,
            "max_output_tokens": 1024,
            "capabilities": {"json_schema": True},
        }
    )
    client = ModelClient(config, os.getenv(KEY_ENV[provider], ""))
    records: list[ResponseRecord] = []
    inference_cases = 0
    try:
        for case in cases:
            started = time.monotonic()
            request = case.to_request().model_dump(mode="json")
            baseline = audit(case.to_request(), knowledge) if arm == "hybrid" else None
            requested_checks = baseline.unsupported_checks if baseline else case.allowed_check_ids
            if baseline is not None and not requested_checks:
                records.append(
                    ResponseRecord(
                        case_id=case.id,
                        provider="rules+" + provider,
                        model=model,
                        capabilities=ProviderCapabilities(json_schema=True),
                        raw_response=baseline.assessment.model_dump_json(),
                        runtime_ms=(time.monotonic() - started) * 1000,
                        usage=Usage(input_tokens=0, output_tokens=0, api_cost_usd=0),
                    )
                )
                print(f"Recorded {case.id} (rules; no inference)", flush=True)
                continue
            request["allowed_check_ids"] = requested_checks
            request["project"]["permitted_actions"] = [
                "investigate",
                "collect_evidence",
                "experiment",
            ]
            request["checks"] = [
                knowledge.checks[id].model_dump(mode="json") for id in requested_checks
            ]
            instructions = (knowledge.root / "SKILL.md").read_text()
            modules = {knowledge.checks[id].module.value for id in requested_checks}
            for module in modules:
                instructions += "\n" + (knowledge.root / "references" / f"{module}.md").read_text()
            instructions += (
                "\nThis is an assessment-only evaluation. "
                "Return AgentDecision JSON with no file changes. "
                "For confirmed defects choose investigate, "
                "for unresolved context collect_evidence, "
                "for experiments experiment. "
                "A defect is an observed problem even when fixing it is not permitted. "
                "Unresolved findings require nonempty dependencies naming missing evidence. "
                "Healthy or intentionally excluded cases need no finding. "
                "Use only the provided evidence and catalog sources; do not invent observations."
            )
            try:
                inference_cases += 1
                result = client.complete(
                    instructions,
                    request,
                    [],
                    lambda name, args: {"success": False},
                    max_steps=1,
                    max_seconds=180,
                )
                assessment = Assessment(
                    tenant_id=case.project.tenant_id,
                    project_id=case.project.project_id,
                    environment=case.environment,
                    findings=(baseline.assessment.findings if baseline else [])
                    + result.decision.findings,
                )
                records.append(
                    ResponseRecord(
                        case_id=case.id,
                        provider=("rules+" if baseline else "") + provider,
                        model=result.model,
                        capabilities=ProviderCapabilities(json_schema=True),
                        raw_response=assessment.model_dump_json(),
                        runtime_ms=result.runtime_ms,
                        usage=result.usage,
                    )
                )
            except Exception as error:
                records.append(
                    ResponseRecord(
                        case_id=case.id,
                        provider=("rules+" if baseline else "") + provider,
                        model=model,
                        capabilities=ProviderCapabilities(json_schema=True),
                        raw_response="",
                        run_error=type(error).__name__ + ": " + str(error)[:1000],
                        runtime_ms=(time.monotonic() - started) * 1000,
                    )
                )
            print(f"Recorded {case.id}", flush=True)
    finally:
        client.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".responses.json").write_text(
        json.dumps([record.model_dump(mode="json") for record in records], indent=2) + "\n"
    )
    report = evaluate(cases, records, knowledge, split)
    # The generic replay warning remains: measurements are imported. This run does
    # actually use the provider, so distinguish that scope in its own report.
    report.unverified[0] = (
        f"Arm {arm}: live inference requested for {inference_cases}/{len(cases)} cases. "
        "Only selected fixture decisions were measured, not general reasoning quality."
    )
    output.with_suffix(".protocol.json").write_text(
        json.dumps(
            {
                "arm": arm,
                "provider": provider,
                "model": model,
                "inference_cases": inference_cases,
                "cases": len(cases),
                "split": split,
                "sampling_temperature": 0 if provider == "ollama" else None,
                "max_steps": 1,
                "max_seconds": 180,
                "configuration": config.model_dump(mode="json"),
                "knowledge_version": knowledge.catalog.version,
            },
            indent=2,
        )
        + "\n"
    )
    save_report(report, output)
    print(json.dumps(report.counts))
    return 1 if report.counts["failed"] else (2 if report.counts["skipped"] else 0)
