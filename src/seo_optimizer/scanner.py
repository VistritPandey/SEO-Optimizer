"""Live findings, evidence-aware coverage and an explicitly limited health score."""

import re
from typing import Any
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.audit import PageParser, audit
from seo_optimizer.contracts import (
    ActionKind,
    AuditRequest,
    Environment,
    Evidence,
    EvidenceStrength,
    Finding,
    FindingStatus,
    ProjectContext,
    ProposedAction,
    Severity,
)
from seo_optimizer.crawler import page_excerpt
from seo_optimizer.knowledge import KnowledgePackage


def context(tenant: str, project: str, spec: ProjectSpec) -> ProjectContext:
    actions = [ActionKind.INVESTIGATE, ActionKind.COLLECT_EVIDENCE, ActionKind.EXPERIMENT]
    if spec.auto_fix:
        actions += [ActionKind.PROPOSE_PATCH]
    if spec.allow_content_publication:
        actions += [ActionKind.PUBLISH_CONTENT]
    return ProjectContext(
        tenant_id=tenant,
        project_id=project,
        website_types=spec.website_types,
        environments=[
            Environment(
                name=spec.environment,
                base_url=spec.website_url,
                intended_indexable=spec.environment == "production",
            )
        ],
        page_intents=spec.page_intents,
        trusted_facts=spec.facts,
        goals=spec.goals,
        crawler_preferences=spec.crawler_preferences,
        permitted_actions=actions,
        allowed_paths=spec.allowed_paths,
    )


def scan(
    project: ProjectContext,
    spec: ProjectSpec,
    evidence: list[Evidence],
    knowledge: KnowledgePackage,
) -> tuple[list[Finding], dict[str, Any]]:
    findings: list[Finding] = []
    outcomes: dict[str, str] = {}
    pages = [item for item in evidence if item.kind == "http"]

    def emit(
        id: str,
        item: Evidence,
        summary: str,
        severity: Severity = Severity.MEDIUM,
        unresolved: bool = False,
        dependencies: list[str] | None = None,
    ) -> None:
        check = knowledge.checks[id]
        findings.append(
            Finding(
                check_id=id,
                summary=summary,
                severity=severity,
                status=FindingStatus.UNRESOLVED if unresolved else FindingStatus.DEFECT,
                evidence_strength=EvidenceStrength.HYPOTHESIS
                if unresolved
                else EvidenceStrength.CONFIRMED,
                evidence_ids=[item.id],
                source_ids=check.source_ids,
                action=ProposedAction(
                    kind=ActionKind.COLLECT_EVIDENCE if unresolved else ActionKind.INVESTIGATE,
                    rationale=check.recommended_action,
                ),
                verification_criteria=check.verification,
                dependencies=(dependencies or ["Required authoritative evidence is unavailable."])
                if unresolved
                else [],
            )
        )
        outcomes[id] = "needs_data" if unresolved else "defect"

    for item in pages:
        url = str(item.url)
        if not project.page_intents.get(url, spec.environment == "production"):
            continue
        checks = ["tech.title", "tech.indexability", "tech.canonical", "tech.links"]
        if "ecommerce" in spec.website_types:
            checks.append("commerce.facts")
        baseline = audit(
            AuditRequest(
                project=project,
                environment=spec.environment,
                evidence=[item],
                allowed_check_ids=checks,
            ),
            knowledge,
        )
        findings.extend(baseline.assessment.findings)
        for id in baseline.evaluated_checks:
            outcomes.setdefault(id, "healthy")
        for finding in baseline.assessment.findings:
            outcomes[finding.check_id] = (
                "needs_data" if finding.status == FindingStatus.UNRESOLVED else "defect"
            )
        html = item.data.get("html")
        if not isinstance(html, str):
            continue
        if item.data.get("status_code") != 200:
            emit(
                "tech.status",
                item,
                "Declared public route did not serve a successful page.",
                Severity.HIGH,
            )
        else:
            outcomes.setdefault("tech.status", "healthy")
        if not re.search(r'<meta\b[^>]*name\s*=\s*["\']description["\']', html, re.I):
            emit(
                "tech.metadata",
                item,
                "Public page has no explicit description; assess a factual snippet.",
                Severity.LOW,
            )
        else:
            outcomes.setdefault("tech.metadata", "healthy")
        for script in re.findall(
            r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            re.S | re.I,
        ):
            import json

            try:
                json.loads(script)
            except json.JSONDecodeError:
                emit("geo.entities", item, "Structured data is not valid JSON.")
        raw_robots = item.data.get("robots_txt")
        if isinstance(raw_robots, str) and spec.crawler_preferences:
            rules = RobotFileParser()
            rules.parse(raw_robots.splitlines())
            mismatch = [
                bot
                for bot, preference in spec.crawler_preferences.items()
                if preference != "unchanged"
                and rules.can_fetch(bot, url) != (preference == "allow")
            ]
            if mismatch:
                emit(
                    "geo.crawlers",
                    item,
                    "Crawler rules conflict with explicit owner preferences: "
                    + ", ".join(mismatch),
                )
            else:
                outcomes.setdefault("geo.crawlers", "healthy")
        locale_links = re.findall(r'<link\b[^>]*hreflang=["\']([^"\']+)["\'][^>]*>', html, re.I)
        if locale_links:
            emit(
                "intl.hreflang",
                item,
                "Language alternatives require reciprocal-page verification.",
                Severity.INFO,
                unresolved=True,
                dependencies=["Fetch and verify equivalent locale return references."],
            )
        if "local" in spec.website_types:
            hours = next((fact for fact in spec.facts if fact.name == "hours"), None)
            if hours is None:
                emit(
                    "local.hours",
                    item,
                    "Authoritative business hours are not configured.",
                    Severity.INFO,
                    unresolved=True,
                    dependencies=["Supply current owner-verified hours for the actual location."],
                )
        outcomes.setdefault("content.factual", "needs_model")
    coverage = []
    for id, check in knowledge.checks.items():
        state = outcomes.get(
            id, "needs_model" if check.assessment != "deterministic" else "needs_data"
        )
        if not set(project.website_types).intersection(check.website_types):
            state = "not_applicable"
        coverage.append(
            {"check_id": id, "title": check.title, "module": check.module.value, "state": state}
        )
    checked = sum(item["state"] in {"healthy", "defect"} for item in coverage)
    defects = sum(item["state"] == "defect" for item in coverage)
    report = {
        "score": round(100 * (checked - defects) / checked) if checked else None,
        "score_label": "Observed audit health",
        "coverage": coverage,
        "evaluated_checks": checked,
        "total_checks": len(coverage),
        "pages": len(pages),
        "findings": len(findings),
        "unknown_metrics": [
            "Search rankings",
            "AI citation share",
            "Conversions",
            "Field Web Vitals",
        ],
        "page_summaries": [
            {
                "url": str(item.url),
                "evidence_id": item.id,
                "title": "".join(_parser(str(item.data.get("html", ""))).title),
                "excerpt": page_excerpt(str(item.data.get("html", ""))),
            }
            for item in pages
        ],
    }
    return findings, report


def _parser(html: str) -> PageParser:
    parser = PageParser()
    parser.feed(html)
    return parser


def affected_urls(spec: ProjectSpec, changed: list[str] | None) -> list[str] | None:
    if changed is None:
        return None
    if not changed:
        return []
    # Shared rendering/config/backend changes require broad inspection.
    if any(
        any(
            term in path.lower()
            for term in ("layout", "robots", "sitemap", "config", "server", "backend", "middleware")
        )
        for path in changed
    ):
        return None
    mapped = [
        urljoin(str(spec.website_url), route)
        for route, path in spec.route_map.items()
        if path in changed
    ]
    unknown = [path for path in changed if path not in spec.route_map.values()]
    if unknown and any(
        path.endswith((".html", ".tsx", ".jsx", ".js", ".py", ".md", ".mdx", ".css"))
        for path in unknown
    ):
        return None
    return mapped
