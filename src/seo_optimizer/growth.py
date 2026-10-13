"""Evidence-backed strategy, content briefs and citation observations, independent of AI."""

import hashlib
from datetime import date
from typing import Literal, Self
from urllib.parse import urljoin, urlparse

from pydantic import AwareDatetime, Field, HttpUrl, model_validator

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.contracts import Contract, utc_now


class Material(Contract):
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=20000)
    origin: Literal["owner", "primary_research", "competitor"]
    source: str = Field(min_length=1, max_length=1000)
    collected_at: AwareDatetime
    reviewed: bool = False
    original: bool = False
    fact_ids: list[str] = Field(default_factory=list, max_length=30)
    target_path: str | None = Field(default=None, max_length=1000)
    valid_until: AwareDatetime | None = None

    @model_validator(mode="after")
    def trust(self) -> Self:
        if self.original and self.origin != "owner":
            raise ValueError("Original contribution must come from owner material")
        if self.valid_until and self.valid_until < self.collected_at:
            raise ValueError("Material expires before collection")
        if self.collected_at > utc_now():
            raise ValueError("Material collection cannot be in the future")
        return self


class SearchObservation(Contract):
    id: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=500)
    page: HttpUrl
    start: date
    end: date
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    position: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    source: str = Field(min_length=1, max_length=1000)
    market: str = Field(default="unspecified", max_length=100)
    device: str = Field(default="all", max_length=30)
    business_relevance: Literal["confirmed", "unknown", "irrelevant"] = "unknown"
    synthetic: bool = False

    @model_validator(mode="after")
    def period(self) -> Self:
        if self.end < self.start or self.end > utc_now().date():
            raise ValueError("Invalid search measurement period")
        if self.clicks > self.impressions:
            raise ValueError("Clicks exceed impressions")
        return self


class CitationObservation(Contract):
    id: str = Field(min_length=1, max_length=100)
    experiment: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=500)
    engine: str = Field(min_length=1, max_length=100)
    engine_version: str = Field(min_length=1, max_length=100)
    arm: Literal["baseline", "treatment", "holdout"]
    observed_at: AwareDatetime
    market: str = Field(min_length=1, max_length=100)
    answer: str = Field(max_length=20000)
    cited_urls: list[HttpUrl] = Field(default_factory=list, max_length=100)
    source: str = Field(min_length=1, max_length=1000)
    retrieval_enabled: bool
    citation_accuracy: Literal["supported", "unsupported", "unreviewed"] = "unreviewed"
    synthetic: bool = False

    @model_validator(mode="after")
    def valid_observation(self) -> Self:
        if self.observed_at > utc_now():
            raise ValueError("Citation observation cannot be in the future")
        if self.cited_urls and not self.retrieval_enabled:
            raise ValueError("Retrieval-disabled observations cannot establish search citations")
        return self


class CitationProbe(Contract):
    query: str = Field(min_length=1, max_length=500)
    experiment: str = Field(min_length=1, max_length=100)
    market: str = Field(min_length=1, max_length=100)
    arm: Literal["baseline", "treatment", "holdout"] = "baseline"


class Workspace(Contract):
    version: Literal["1"] = "1"
    materials: list[Material] = Field(default_factory=list, max_length=100)
    search: list[SearchObservation] = Field(default_factory=list, max_length=1000)
    citations: list[CitationObservation] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        for records in (self.materials, self.search, self.citations):
            if len({item.id for item in records}) != len(records):
                raise ValueError("Duplicate record IDs")
        # Overlapping rows of the same slice would inflate apparent demand.
        slices: dict[tuple[str, str, str, str, bool], list[SearchObservation]] = {}
        for row in self.search:
            key = (row.query.casefold(), str(row.page), row.market, row.device, row.synthetic)
            for prior in slices.get(key, []):
                if row.start <= prior.end and prior.start <= row.end:
                    raise ValueError("Overlapping search observation periods")
            slices.setdefault(key, []).append(row)
        return self


class Brief(Contract):
    id: str
    query: str
    target_url: HttpUrl
    source_ids: list[str]
    fact_ids: list[str]
    paragraphs: list[str]
    distinctive_contribution: str
    dependencies: list[str]
    ready: bool
    success_metric: str = "Compare query/page clicks after a comparable observation window"


class Opportunity(Contract):
    id: str
    query: str
    target_url: HttpUrl
    observation_ids: list[str]
    action: Literal["refresh", "collect_evidence", "preserve"]
    impressions: int
    clicks: int
    priority: int
    explanation: str
    synthetic: bool
    brief: Brief


class StrategyReport(Contract):
    version: Literal["1"] = "1"
    generated_at: AwareDatetime
    opportunities: list[Opportunity]
    dependencies: list[str]
    citation_groups: list[dict[str, str | int | float | None]]
    attribution: str = (
        "Priority is an operational heuristic, not estimated search uplift. Citation observations "
        "are separate from rankings, clicks and conversions; before/after does not prove causation."
    )


def brief_for(spec: ProjectSpec, workspace: Workspace, query: str, url: str) -> Brief:
    now = utc_now()
    path = urlparse(url).path
    selected = [item for item in workspace.materials if item.target_path == path]
    dependencies: list[str] = []
    paragraphs: list[str] = []
    fact_ids: list[str] = []
    supported: list[str] = []
    facts = {item.id: item for item in spec.facts if not item.valid_until or item.valid_until > now}
    for material in selected:
        if not (
            material.origin == "owner"
            and material.reviewed
            and material.original
            and (not material.valid_until or material.valid_until > now)
        ):
            continue
        # Whole original passages must be explicitly backed by a current owner fact.
        if not material.fact_ids or not all(item in facts for item in material.fact_ids):
            dependencies.append(f"Material {material.id} needs current owner fact references")
            continue
        if not any(
            isinstance(facts[item].value, str)
            and material.text.strip() == str(facts[item].value).strip()
            for item in material.fact_ids
        ):
            dependencies.append(f"Material {material.id} must match an owner-verified passage")
            continue
        paragraphs.append(material.text.strip())
        supported.append(material.id)
        fact_ids.extend(material.fact_ids)
    if not spec.goals:
        dependencies.append("Configure a business goal and conversion path")
    if not paragraphs:
        dependencies.append("Supply reviewed original owner material for this target page")
    if spec.page_intents.get(path, spec.environment == "production") is False:
        dependencies.append("Target is intentionally non-indexable; preserve it")
    if (urlparse(url).scheme, urlparse(url).netloc) != (
        urlparse(str(spec.website_url)).scheme,
        urlparse(str(spec.website_url)).netloc,
    ):
        dependencies.append("Target is outside the project origin")
    if path not in spec.route_map:
        dependencies.append("Map the target route to an existing editable source file")
    return Brief(
        id=hashlib.sha256((query.casefold() + url).encode()).hexdigest()[:16],
        query=query,
        target_url=HttpUrl(url),
        source_ids=supported,
        fact_ids=sorted(set(fact_ids)),
        paragraphs=paragraphs,
        distinctive_contribution="Reviewed original owner passages",
        dependencies=dependencies,
        ready=not dependencies,
    )


def plan(spec: ProjectSpec, workspace: Workspace) -> StrategyReport:
    groups: dict[tuple[str, str, bool], list[SearchObservation]] = {}
    for row in workspace.search:
        groups.setdefault((row.query.casefold(), str(row.page), row.synthetic), []).append(row)
    opportunities: list[Opportunity] = []
    for (_, url, synthetic), rows in groups.items():
        impressions, clicks = sum(r.impressions for r in rows), sum(r.clicks for r in rows)
        query = rows[0].query
        brief = brief_for(spec, workspace, query, url)
        confirmed = all(r.business_relevance == "confirmed" for r in rows)
        irrelevant = any(r.business_relevance == "irrelevant" for r in rows)
        if not confirmed:
            brief.dependencies.append("Confirm this query serves the configured business goal")
            brief.ready = False
        action: Literal["refresh", "collect_evidence", "preserve"] = "collect_evidence"
        if irrelevant or impressions == 0:
            action = "preserve"
        elif brief.ready:
            action = "refresh"
        # Transparent queue ordering only: demonstrated demand + confirmed relevance + readiness.
        priority = (
            min(impressions, 10000) + (10000 if confirmed else 0) + (10000 if brief.ready else 0)
        )
        if action == "preserve":
            priority = 0
        opportunities.append(
            Opportunity(
                id=brief.id,
                query=query,
                target_url=HttpUrl(url),
                observation_ids=[r.id for r in rows],
                action=action,
                impressions=impressions,
                clicks=clicks,
                priority=priority,
                explanation="Observed impressions (capped at 10,000) + 10,000 for confirmed "
                "business relevance + 10,000 for a supported brief; preserve actions rank last.",
                synthetic=synthetic,
                brief=brief,
            )
        )
    citation_groups: list[dict[str, str | int | float | None]] = []
    keys = {
        (c.experiment, c.engine, c.engine_version, c.query, c.market, c.arm, c.synthetic)
        for c in workspace.citations
    }
    for experiment, engine, version, query, market, arm, synthetic in sorted(keys):
        observations = [
            c
            for c in workspace.citations
            if (c.experiment, c.engine, c.engine_version, c.query, c.market, c.arm, c.synthetic)
            == (experiment, engine, version, query, market, arm, synthetic)
        ]
        eligible = [c for c in observations if c.retrieval_enabled]
        origin = urlparse(str(spec.website_url)).netloc
        cited = [
            c for c in eligible if any(urlparse(str(u)).netloc == origin for u in c.cited_urls)
        ]
        citation_groups.append(
            {
                "experiment": experiment,
                "engine": engine,
                "version": version,
                "query": query,
                "market": market,
                "arm": arm,
                "data": "synthetic" if synthetic else "observed",
                "samples": len(observations),
                "retrieval_samples": len(eligible),
                "project_citations": len(cited),
                "citation_rate": len(cited) / len(eligible) if eligible else None,
                "accuracy_reviewed": sum(c.citation_accuracy != "unreviewed" for c in cited),
            }
        )
    return StrategyReport(
        generated_at=utc_now(),
        opportunities=sorted(opportunities, key=lambda o: (-o.priority, o.id)),
        dependencies=[] if workspace.search else ["Import dated query/page search observations"],
        citation_groups=citation_groups,
    )


def validate_workspace(spec: ProjectSpec, workspace: Workspace) -> None:
    facts = {fact.id for fact in spec.facts}
    for material in workspace.materials:
        if not set(material.fact_ids).issubset(facts):
            raise ValueError("Material references unknown project facts")
    for row in workspace.search:
        if urlparse(str(row.page)).netloc != urlparse(str(spec.website_url)).netloc:
            raise ValueError("Search page is outside the project")
    for material in workspace.materials:
        if material.target_path and not material.target_path.startswith("/"):
            raise ValueError("Material targets must be website paths")
    # Validate all URLs consistently with the production/private page policy.
    for row in workspace.search:
        brief_for(spec, workspace, row.query, urljoin(str(spec.website_url), str(row.page)))
