"""Structural assessment gates. These do not authorize or execute real mutations."""

from pathlib import PurePosixPath

from seo_optimizer.contracts import (
    ActionKind,
    Assessment,
    AuditRequest,
    BenchmarkCase,
    EvidenceStrength,
    FindingStatus,
    ProviderCapabilities,
)
from seo_optimizer.knowledge import KnowledgePackage


def _allowed_path(target: str, roots: list[str]) -> bool:
    path = PurePosixPath(target)
    if path.is_absolute() or ".." in path.parts or "\\" in target:
        return False
    return any(path == PurePosixPath(root) or path.is_relative_to(root) for root in roots)


def validate_request(case: AuditRequest, package: KnowledgePackage) -> list[str]:
    errors: list[str] = []
    envs = {env.name for env in case.project.environments}
    if case.environment not in envs:
        errors.append("unknown case environment")
    ids = [evidence.id for evidence in case.evidence]
    if len(ids) != len(set(ids)):
        errors.append("duplicate evidence identifiers")
    for evidence in case.evidence:
        if (evidence.tenant_id, evidence.project_id) != (
            case.project.tenant_id,
            case.project.project_id,
        ):
            errors.append(f"{evidence.id}: evidence crosses tenant/project boundary")
        if evidence.environment != case.environment:
            errors.append(f"{evidence.id}: evidence belongs to a different environment")
    if len(case.allowed_check_ids) != len(set(case.allowed_check_ids)):
        errors.append("duplicate allowed checks")
    for check_id in case.allowed_check_ids:
        if check_id not in package.checks:
            errors.append(f"unknown allowed check {check_id}")
    return errors


def validate_case(case: BenchmarkCase, package: KnowledgePackage) -> list[str]:
    errors = validate_request(case, package)
    ids = [evidence.id for evidence in case.evidence]
    keys = [(item.check_id, item.status) for item in case.expected_findings]
    if len(keys) != len(set(keys)):
        errors.append("duplicate expected findings")
    for expected in case.expected_findings:
        if expected.check_id not in case.allowed_check_ids:
            errors.append(f"expected finding {expected.check_id} is outside allowed checks")
        if not set(expected.required_evidence_ids).issubset(ids):
            errors.append("expected finding references unknown evidence")
        check = package.checks.get(expected.check_id)
        if check and not set(expected.allowed_actions).issubset(check.allowed_actions):
            errors.append("expected action is unsupported by the check")
    return errors


def validate_assessment(
    assessment: Assessment,
    case: AuditRequest,
    package: KnowledgePackage,
    capabilities: ProviderCapabilities,
) -> list[str]:
    errors = validate_request(case, package)
    project = case.project
    if (assessment.tenant_id, assessment.project_id, assessment.environment) != (
        project.tenant_id,
        project.project_id,
        case.environment,
    ):
        errors.append("assessment crosses tenant/project/environment boundary")
    evidence_by_id = {item.id: item for item in case.evidence}
    facts = {item.id: item for item in project.trusted_facts}
    for capability in case.required_capabilities:
        if not getattr(capabilities, capability):
            errors.append(f"unsupported required capability: {capability}")
    call_ids = [call.id for call in assessment.tool_calls]
    result_ids = [result.call_id for result in assessment.tool_results]
    if len(call_ids) != len(set(call_ids)) or len(result_ids) != len(set(result_ids)):
        errors.append("duplicate tool call/result identifiers")
    if assessment.tool_calls and not capabilities.tool_calling:
        errors.append("provider lacks tool calling capability")
    if set(result_ids) != set(call_ids):
        errors.append("tool calls and results must correspond exactly in completed replay")
    for call in assessment.tool_calls:
        if call.name == "apply_patch" and ActionKind.PROPOSE_PATCH not in project.permitted_actions:
            errors.append("patch tool outside project policy")
        if call.name in {"read_file", "apply_patch"}:
            target = call.arguments.get("path")
            if not isinstance(target, str) or not _allowed_path(target, project.allowed_paths):
                errors.append("tool path outside project policy")
    tool_failed = any(not result.success for result in assessment.tool_results)
    seen: set[tuple[str, FindingStatus, tuple[str, ...]]] = set()
    for finding in assessment.findings:
        key = (finding.check_id, finding.status, tuple(sorted(finding.evidence_ids)))
        if key in seen:
            errors.append(f"duplicate finding {finding.check_id}/{finding.status}")
        seen.add(key)
        check = package.checks.get(finding.check_id)
        if check is None:
            errors.append(f"unknown check {finding.check_id}")
            continue
        if finding.check_id not in case.allowed_check_ids:
            errors.append(f"check {finding.check_id} is outside requested audit scope")
        if not set(project.website_types).intersection(check.website_types):
            errors.append(f"check {finding.check_id} is not applicable to this website")
        if not set(finding.source_ids).issubset(check.source_ids):
            errors.append(f"finding {finding.check_id} has unknown or unrelated sources")
        if not set(finding.evidence_ids).issubset(evidence_by_id):
            errors.append(f"finding {finding.check_id} has unknown evidence references")
        if not set(finding.action.fact_ids).issubset(facts):
            errors.append("action references unknown trusted facts")
        if finding.action.kind not in check.allowed_actions:
            errors.append(f"action not supported by check {finding.check_id}")
        if finding.action.kind != ActionKind.NONE and (
            finding.action.kind not in project.permitted_actions
        ):
            errors.append("action outside project policy")
        for target in finding.action.target_paths:
            if not _allowed_path(target, project.allowed_paths):
                errors.append("action target outside project paths")
        for bot, intent in finding.action.crawler_changes.items():
            if project.crawler_preferences.get(bot, "unchanged") != intent:
                errors.append(f"crawler change conflicts with configured preference: {bot}")
        for url, indexable in finding.action.indexability_changes.items():
            # Mutating an unconfigured URL is never inferred from environment defaults.
            if project.page_intents.get(url) != indexable:
                errors.append("indexability change lacks explicit matching URL intent")
        unresolved_experiment = (
            finding.status == FindingStatus.UNRESOLVED
            and finding.action.kind == ActionKind.NONE
            and not finding.action.automatic
            and bool(finding.dependencies)
        )
        if (
            check.assessment == "experimental"
            and not unresolved_experiment
            and (
                finding.status != FindingStatus.EXPERIMENT
                or finding.evidence_strength != EvidenceStrength.HYPOTHESIS
            )
        ):
            errors.append("research tactic presented as established repair")
        if finding.action.automatic:
            supporting = [
                evidence_by_id[item] for item in finding.evidence_ids if item in evidence_by_id
            ]
            if not supporting or all(item.kind == "screenshot" for item in supporting):
                errors.append("automatic change lacks non-visual corroboration")
            if tool_failed:
                errors.append("automatic action after a failed tool")
            if finding.action.kind == ActionKind.PUBLISH_CONTENT:
                if not finding.action.fact_ids:
                    errors.append("automatic content publication lacks trusted facts")
                newest = max((item.collected_at for item in supporting), default=None)
                for fact_id in finding.action.fact_ids:
                    fact = facts.get(fact_id)
                    if fact and fact.valid_until and newest and fact.valid_until < newest:
                        errors.append("automatic publication uses expired business facts")
    return errors
