"""Versioned application contracts; provider output is always validated locally."""

from datetime import date, datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    JsonValue,
    field_validator,
    model_validator,
)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class WebsiteType(StrEnum):
    SAAS = "saas"
    DOCS = "docs"
    PUBLISHING = "publishing"
    LOCAL = "local"
    ECOMMERCE = "ecommerce"
    GENERIC = "generic"


class Module(StrEnum):
    TECHNICAL = "technical"
    PERFORMANCE = "performance"
    CONTENT = "content"
    GEO = "geo"
    LOCAL = "local"
    ECOMMERCE = "ecommerce"
    INTERNATIONAL = "international"
    OPERATIONS = "operations"


class ActionKind(StrEnum):
    NONE = "none"
    INVESTIGATE = "investigate"
    COLLECT_EVIDENCE = "collect_evidence"
    PROPOSE_PATCH = "propose_patch"
    PUBLISH_CONTENT = "publish_content"
    CHANGE_CRAWLER_POLICY = "change_crawler_policy"
    UPDATE_BUSINESS_PROFILE = "update_business_profile"
    MERGE = "merge"
    DEPLOY = "deploy"
    EXPERIMENT = "experiment"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EvidenceStrength(StrEnum):
    CONFIRMED = "confirmed"
    SUPPORTED = "supported"
    HYPOTHESIS = "hypothesis"


class FindingStatus(StrEnum):
    DEFECT = "defect"
    UNRESOLVED = "unresolved"
    EXPERIMENT = "experiment"


class Scope(Contract):
    tenant_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)


class Environment(Contract):
    name: str = Field(min_length=1)
    base_url: HttpUrl
    intended_indexable: bool


class TrustedFact(Contract):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    value: JsonValue
    source: str = Field(min_length=1)
    verified_at: AwareDatetime
    valid_until: AwareDatetime | None = None

    @model_validator(mode="after")
    def valid_window(self) -> Self:
        if self.valid_until and self.valid_until < self.verified_at:
            raise ValueError("fact expiry precedes verification")
        return self


class ProjectContext(Scope):
    schema_version: Literal["1.0"] = "1.0"
    website_types: list[WebsiteType] = Field(min_length=1)
    environments: list[Environment] = Field(min_length=1)
    # Exact URL intent overrides environment defaults. Preserve private routes.
    page_intents: dict[str, bool] = Field(default_factory=dict)
    trusted_facts: list[TrustedFact] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    crawler_preferences: dict[str, Literal["allow", "block", "unchanged"]] = Field(
        default_factory=dict
    )
    permitted_actions: list[ActionKind] = Field(
        default_factory=lambda: [ActionKind.INVESTIGATE, ActionKind.COLLECT_EVIDENCE]
    )
    allowed_paths: list[str] = Field(default_factory=list)

    @field_validator("allowed_paths")
    @classmethod
    def confined_paths(cls, values: list[str]) -> list[str]:
        from pathlib import PurePosixPath

        for value in values:
            path = PurePosixPath(value)
            if (
                not value
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in value
                or str(path) == "."
            ):
                raise ValueError("allowed paths must be named relative repository roots")
        return values

    @model_validator(mode="after")
    def unique_context(self) -> Self:
        for values in (
            [env.name for env in self.environments],
            [fact.id for fact in self.trusted_facts],
        ):
            if len(values) != len(set(values)):
                raise ValueError("duplicate environment or trusted fact identifier")
        if len(self.website_types) != len(set(self.website_types)):
            raise ValueError("duplicate website type")
        return self


class Evidence(Scope):
    id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    kind: Literal["source", "http", "dom", "screenshot", "field_metric", "research", "tool"]
    observation: str = Field(min_length=1)
    collected_at: AwareDatetime
    url: HttpUrl | None = None
    source_file: str | None = None
    screenshot: str | None = None
    data: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def has_locator(self) -> Self:
        if not self.url and not self.source_file:
            raise ValueError("evidence requires a URL or source file")
        if self.kind == "screenshot" and not self.screenshot:
            raise ValueError("screenshot evidence requires an artifact locator")
        return self


class ProposedAction(Contract):
    kind: ActionKind
    rationale: str = Field(min_length=1)
    automatic: bool = False
    target_paths: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)
    # Declared effects allow the application to enforce policy outside prose.
    crawler_changes: dict[str, Literal["allow", "block"]] = Field(default_factory=dict)
    indexability_changes: dict[str, bool] = Field(default_factory=dict)


class Finding(Contract):
    check_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    status: FindingStatus
    severity: Severity
    evidence_strength: EvidenceStrength
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(min_length=1)
    action: ProposedAction
    verification_criteria: list[str] = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def justified_state(self) -> Self:
        if self.status == FindingStatus.UNRESOLVED:
            if not self.dependencies:
                raise ValueError("unresolved findings require recorded dependencies")
            if self.action.kind not in {
                ActionKind.NONE,
                ActionKind.INVESTIGATE,
                ActionKind.COLLECT_EVIDENCE,
            }:
                raise ValueError("unresolved findings cannot propose a fix or publish")
        elif not self.evidence_ids:
            raise ValueError("defects and experiments require evidence")
        if self.status == FindingStatus.EXPERIMENT:
            if self.evidence_strength != EvidenceStrength.HYPOTHESIS:
                raise ValueError("experimental findings must retain hypothesis strength")
            if self.action.kind not in {ActionKind.NONE, ActionKind.EXPERIMENT}:
                raise ValueError("experiment must not masquerade as a required repair")
        if self.action.automatic and (
            self.status != FindingStatus.DEFECT
            or self.evidence_strength != EvidenceStrength.CONFIRMED
            or self.dependencies
        ):
            raise ValueError("automatic action requires a confirmed defect without dependencies")
        return self


class ToolCall(Contract):
    id: str = Field(min_length=1)
    name: Literal[
        "read_file", "get_diff", "inspect_route", "crawl_page", "apply_patch", "run_checks"
    ]
    arguments: dict[str, JsonValue]


class ToolResult(Contract):
    call_id: str = Field(min_length=1)
    success: bool
    output: JsonValue = None
    error: str | None = None

    @model_validator(mode="after")
    def result_consistency(self) -> Self:
        if self.success and self.error:
            raise ValueError("successful tool result cannot contain an error")
        if not self.success and not self.error:
            raise ValueError("failed tool result requires an error")
        return self


class Assessment(Scope):
    schema_version: Literal["1.0"] = "1.0"
    environment: str = Field(min_length=1)
    findings: list[Finding] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)


class ProviderCapabilities(Contract):
    tool_calling: bool = False
    json_schema: bool = False
    vision: bool = False
    context_tokens: int | None = Field(default=None, gt=0)


class Usage(Contract):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    api_cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    electricity_cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    hardware_cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    def total_cost(self) -> float | None:
        parts = (self.api_cost_usd, self.electricity_cost_usd, self.hardware_cost_usd)
        if any(value is None for value in parts):
            return None
        return sum(value for value in parts if value is not None)


class ExpectedFinding(Contract):
    check_id: str
    status: FindingStatus
    allowed_actions: list[ActionKind] = Field(min_length=1)
    required_evidence_ids: list[str] = Field(default_factory=list)
    automatic: bool = False


class AuditRequest(Contract):
    """Only observations and scope; benchmark answers never enter the model request."""

    project: ProjectContext
    environment: str
    evidence: list[Evidence]
    allowed_check_ids: list[str] = Field(min_length=1)
    required_capabilities: list[Literal["tool_calling", "json_schema", "vision"]] = Field(
        default_factory=list
    )


class BenchmarkCase(AuditRequest):
    id: str = Field(min_length=1)
    split: Literal["development", "held_out"]
    description: str = Field(min_length=1)
    expected_findings: list[ExpectedFinding]

    def to_request(self) -> AuditRequest:
        return AuditRequest.model_validate(self.model_dump(include=set(AuditRequest.model_fields)))


class ResponseRecord(Contract):
    case_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    capabilities: ProviderCapabilities
    raw_response: str
    runtime_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    usage: Usage = Field(default_factory=Usage)
    run_error: str | None = None


class EvaluationResult(Contract):
    case_id: str
    provider: str | None = None
    model: str | None = None
    status: Literal["passed", "failed", "skipped"]
    expected: list[ExpectedFinding]
    observed: list[Finding] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    runtime_ms: float | None = None
    usage: Usage | None = None


class EvaluationReport(Contract):
    schema_version: Literal["1.0"] = "1.0"
    generated_at: AwareDatetime
    knowledge_version: str
    split: Literal["development", "held_out", "all"]
    results: list[EvaluationResult]
    counts: dict[str, int]
    metrics: dict[str, JsonValue]
    unverified: list[str]


class Source(Contract):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    url: HttpUrl
    verified_on: date
    source_type: Literal["official", "research"]
    applicability: list[str] = Field(min_length=1)
    supports: list[str] = Field(min_length=1)
    limitations: str = Field(min_length=1)


class SourceRegistry(Contract):
    version: str
    as_of: date
    sources: list[Source] = Field(min_length=1)


class Check(Contract):
    id: str = Field(min_length=1)
    module: Module
    title: str = Field(min_length=1)
    website_types: list[WebsiteType] = Field(min_length=1)
    page_types: list[str] = Field(min_length=1)
    required_context: list[str] = Field(min_length=1)
    evidence_requirements: list[str] = Field(min_length=1)
    assessment: Literal["deterministic", "model_assisted", "experimental"]
    recommended_action: str = Field(min_length=1)
    allowed_actions: list[ActionKind] = Field(min_length=1)
    automatic_prerequisites: list[str] = Field(min_length=1)
    verification: list[str] = Field(min_length=1)
    no_op_conditions: list[str] = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    reference: str = Field(min_length=1)

    @field_validator("reference")
    @classmethod
    def local_reference(cls, value: str) -> str:
        from pathlib import PurePosixPath

        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("reference must remain inside the knowledge package")
        return value


class CheckCatalog(Contract):
    version: str
    checks: list[Check] = Field(min_length=1)


def schema_models() -> dict[str, type[BaseModel]]:
    from seo_optimizer.application_models import (
        AgentDecision,
        FileChange,
        ProjectCreate,
        ProjectSecrets,
        ProjectSpec,
        ProviderConfig,
        Registration,
    )
    from seo_optimizer.growth import (
        Brief,
        CitationObservation,
        Material,
        Opportunity,
        SearchObservation,
        StrategyReport,
        Workspace,
    )

    return {
        model.__name__: model
        for model in (
            ProjectContext,
            Evidence,
            Finding,
            Assessment,
            AuditRequest,
            ProviderCapabilities,
            ToolCall,
            ToolResult,
            ResponseRecord,
            BenchmarkCase,
            EvaluationResult,
            EvaluationReport,
            SourceRegistry,
            CheckCatalog,
            AgentDecision,
            FileChange,
            ProjectCreate,
            ProjectSecrets,
            ProjectSpec,
            ProviderConfig,
            Registration,
            Brief,
            CitationObservation,
            Material,
            Opportunity,
            SearchObservation,
            StrategyReport,
            Workspace,
        )
    }


def utc_now() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)
