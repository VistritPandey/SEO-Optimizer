"""Small deterministic baseline over supplied HTTP evidence, with no network access.

Only the declared supported checks are implemented here. The complete knowledge
catalog is a decision guide, not a claim that every check has an executable scanner.
"""

import json
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import cast
from urllib.parse import urljoin, urlparse

from pydantic import JsonValue

from seo_optimizer.contracts import (
    ActionKind,
    Assessment,
    AuditRequest,
    Contract,
    Evidence,
    EvidenceStrength,
    Finding,
    FindingStatus,
    ProposedAction,
    Severity,
)
from seo_optimizer.knowledge import KnowledgePackage

SUPPORTED_CHECKS = frozenset(
    {"tech.title", "tech.indexability", "tech.canonical", "tech.links", "commerce.facts"}
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: list[str] = []
        self.robots: list[str] = []
        self.canonicals: list[str] = []
        self.links: list[str] = []
        self.schemas: list[JsonValue] = []
        self._in_title = False
        self._in_schema = False
        self._schema_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and (values.get("name") or "").lower() in {"robots", "googlebot"}:
            self.robots.append(values.get("content") or "")
        elif tag == "link" and "canonical" in (values.get("rel") or "").lower().split():
            self.canonicals.append(values.get("href") or "")
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        elif tag == "script" and values.get("type") == "application/ld+json":
            self._in_schema = True
            self._schema_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._in_schema:
            try:
                self.schemas.append(cast(JsonValue, json.loads("".join(self._schema_text))))
            except json.JSONDecodeError:
                pass  # Malformed schema needs a separate check, not fabricated offer values.
            self._in_schema = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title.append(data)
        if self._in_schema:
            self._schema_text.append(data)


class RuleAuditResult(Contract):
    assessment: Assessment
    evaluated_checks: list[str]
    unsupported_checks: list[str]


def _finding(
    check_id: str,
    summary: str,
    evidence: Evidence,
    package: KnowledgePackage,
    unresolved: bool = False,
    dependencies: list[str] | None = None,
) -> Finding:
    check = package.checks[check_id]
    return Finding(
        check_id=check_id,
        summary=summary,
        status=FindingStatus.UNRESOLVED if unresolved else FindingStatus.DEFECT,
        severity=Severity.MEDIUM,
        evidence_strength=EvidenceStrength.HYPOTHESIS if unresolved else EvidenceStrength.CONFIRMED,
        evidence_ids=[evidence.id],
        source_ids=check.source_ids,
        action=ProposedAction(
            kind=ActionKind.COLLECT_EVIDENCE if unresolved else ActionKind.INVESTIGATE,
            rationale="Gather missing observations." if unresolved else check.recommended_action,
        ),
        verification_criteria=check.verification,
        dependencies=(dependencies or ["Successful HTTP evidence and page intent are required."])
        if unresolved
        else [],
    )


def _offer_value(key: str, value: JsonValue) -> str | Decimal | None:
    if key == "price":
        if isinstance(value, bool) or not isinstance(value, (str, float, int)):
            return None
        try:
            number = Decimal(str(value))
            return number if number.is_finite() and number >= 0 else None
        except InvalidOperation:
            return None
    if not isinstance(value, str):
        return None
    if key == "availability":
        return value.rstrip("/").rsplit("/", 1)[-1]
    return value.upper()


def audit(case: AuditRequest, package: KnowledgePackage) -> RuleAuditResult:
    from seo_optimizer.policy import validate_request

    errors = validate_request(case, package)
    if errors:
        raise ValueError("; ".join(errors))
    supported = sorted(
        check_id
        for check_id in set(case.allowed_check_ids) & SUPPORTED_CHECKS
        if set(case.project.website_types).intersection(package.checks[check_id].website_types)
    )
    findings: dict[str, Finding] = {}
    environment = next(env for env in case.project.environments if env.name == case.environment)
    pages = [item for item in case.evidence if item.kind == "http" and item.url]
    if len(pages) > 1:
        raise ValueError("offline baseline accepts one HTTP page per audit request")
    for evidence in pages:
        url = str(evidence.url)
        intended = case.project.page_intents.get(url, environment.intended_indexable)
        html, status = evidence.data.get("html"), evidence.data.get("status_code")
        if not intended:
            continue
        if not isinstance(html, str) or type(status) is not int or status != 200:
            for check_id in supported:
                findings[check_id] = _finding(
                    check_id,
                    "Required successful response evidence is unavailable.",
                    evidence,
                    package,
                    unresolved=True,
                )
            continue
        page = PageParser()
        page.feed(html)
        if "tech.title" in supported and not "".join(page.title).strip():
            findings["tech.title"] = _finding(
                "tech.title", "Public page has no descriptive title.", evidence, package
            )
        headers = evidence.data.get("headers")
        header_values = (
            {key.lower(): value for key, value in headers.items()}
            if isinstance(headers, dict)
            else {}
        )
        robots_values = page.robots + [str(header_values.get("x-robots-tag", ""))]
        directives = {
            word.strip().lower()
            for value in robots_values
            for word in value.replace(";", ",").split(",")
        }
        if "tech.indexability" in supported and directives & {"noindex", "none"}:
            findings["tech.indexability"] = _finding(
                "tech.indexability",
                "Declared public page has an exclusion directive.",
                evidence,
                package,
            )
        # Compare duplicate HTML declarations. Header/rendered consistency is not
        # inferred from absent evidence in this deliberately limited baseline.
        canonicals = {urljoin(url, value) for value in page.canonicals if value}
        if "tech.canonical" in supported and len(canonicals) > 1:
            findings["tech.canonical"] = _finding(
                "tech.canonical", "Response declares conflicting canonical URLs.", evidence, package
            )
        destinations = evidence.data.get("link_status")
        if "tech.links" in supported:
            destinations = destinations if isinstance(destinations, dict) else {}
            missing_observation = False
            for href in page.links:
                if href.startswith("#") or urlparse(href).scheme not in {"", "http", "https"}:
                    continue
                destination = urljoin(url, href)
                observed = destinations.get(destination)
                if urlparse(destination).netloc != urlparse(url).netloc:
                    continue
                if type(observed) is not int:
                    missing_observation = True
                if (
                    urlparse(destination).netloc == urlparse(url).netloc
                    and type(observed) is int
                    and observed in {404, 410}
                ):
                    findings["tech.links"] = _finding(
                        "tech.links",
                        "An internal link has an observed missing destination.",
                        evidence,
                        package,
                    )
            if missing_observation and "tech.links" not in findings:
                findings["tech.links"] = _finding(
                    "tech.links",
                    "Internal destination response evidence is incomplete.",
                    evidence,
                    package,
                    unresolved=True,
                    dependencies=["Observe the unresolved internal link destinations."],
                )
        if "commerce.facts" in supported:
            visible = evidence.data.get("visible_offer")
            for schema in page.schemas:
                if not isinstance(schema, dict) or schema.get("@type") != "Product":
                    continue
                offer = schema.get("offers")
                if not isinstance(offer, dict):
                    continue
                visible = visible if isinstance(visible, dict) else {}
                pairs = [
                    (_offer_value(key, offer.get(key)), _offer_value(key, visible.get(key)))
                    for key in ("price", "priceCurrency", "availability")
                ]
                if any(
                    left is not None and right is not None and left != right
                    for left, right in pairs
                ):
                    findings["commerce.facts"] = _finding(
                        "commerce.facts",
                        "Declared product offer contradicts observed visible offer.",
                        evidence,
                        package,
                    )
                elif any(left is None or right is None for left, right in pairs):
                    findings["commerce.facts"] = _finding(
                        "commerce.facts",
                        "Comparable offer observations are incomplete.",
                        evidence,
                        package,
                        unresolved=True,
                        dependencies=[
                            "Observe valid prices, currencies and availability together."
                        ],
                    )
    if not pages:
        # A requested implemented check with no HTTP evidence is unresolved, not healthy.
        for check_id in supported:
            check = package.checks[check_id]
            findings[check_id] = Finding(
                check_id=check_id,
                summary="No HTTP evidence supplied.",
                status=FindingStatus.UNRESOLVED,
                severity=Severity.INFO,
                evidence_strength=EvidenceStrength.HYPOTHESIS,
                source_ids=check.source_ids,
                action=ProposedAction(
                    kind=ActionKind.COLLECT_EVIDENCE, rationale="Collect response."
                ),
                verification_criteria=check.verification,
                dependencies=["HTTP evidence"],
            )
    return RuleAuditResult(
        assessment=Assessment(
            tenant_id=case.project.tenant_id,
            project_id=case.project.project_id,
            environment=case.environment,
            findings=list(findings.values()),
        ),
        evaluated_checks=supported,
        unsupported_checks=sorted(set(case.allowed_check_ids) - SUPPORTED_CHECKS),
    )
