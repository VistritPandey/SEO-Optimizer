"""Execute every catalog check or record its exact unmet evidence dependencies.

Conclusive model reviews are a separate contract from repairs. Missing context,
missing reviews and failed tools never become passes. Results describe sampled
observations, not indexing, rankings or an assurance about unobserved pages.
"""

import json
import math
import re
from html.parser import HTMLParser
from typing import Any, cast
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

from seo_optimizer.application_models import CheckReview, ProjectSpec
from seo_optimizer.contracts import (
    ActionKind,
    Evidence,
    EvidenceStrength,
    Finding,
    FindingStatus,
    ProposedAction,
    Severity,
    utc_now,
)
from seo_optimizer.growth import Workspace
from seo_optimizer.knowledge import KnowledgePackage

VERSION = "2"
BASELINE = {"tech.title", "tech.indexability", "tech.canonical", "tech.links", "tech.status"}
MODEL_INPUTS: dict[str, tuple[str, ...]] = {
    "tech.metadata": ("pages",),
    "tech.rendering": ("pages", "dom"),
    "tech.migration": ("migration_map", "migration_observations"),
    "perf.media": ("pages", "dom", "media_observations"),
    "perf.navigation": ("dom", "navigation_observations"),
    "content.strategy": ("pages", "goals", "facts", "search"),
    "content.competitors": ("pages", "goals", "competitor_material"),
    "content.factual": ("pages", "facts"),
    "content.originality": ("pages", "goals", "original_material"),
    "content.refresh": ("pages", "facts", "search", "change_history"),
    "geo.google-llms": ("pages",),
    "geo.google-faq": ("pages",),
    "geo.entities": ("pages", "facts"),
    "geo.visibility": ("citations",),
    "local.identity": ("pages", "business_identity", "business_profile"),
    "local.relevance": ("pages", "service_footprint", "goals"),
    "commerce.variants": ("pages", "variants", "dom"),
    "commerce.navigation": ("pages", "category_policy", "route_map"),
    "commerce.merchants": ("pages", "merchant_observations", "merchant_policy"),
    "intl.localization": ("pages", "locale_map", "localized_facts"),
    "ops.incremental": ("incremental_trace",),
    "ops.verification": ("verification_observations",),
}
# Deterministic contradictions take precedence; richer comparisons require a
# semantic review once the authoritative facts and rendered observations exist.
SEMANTIC_FOLLOWUPS: dict[str, tuple[str, ...]] = {
    "local.hours": ("pages", "dom", "hours", "business_identity"),
    "local.schema": ("pages", "dom", "business_identity"),
    "commerce.facts": ("pages", "dom", "offer_facts", "visible_offers"),
    "intl.hreflang": ("pages", "locale_map", "localized_facts"),
    "geo.experiment": ("citations", "experiment_protocol", "comparable_experiment"),
}
DETERMINISTIC = BASELINE | {
    "tech.robots",
    "tech.sitemap",
    "perf.cwv",
    "geo.crawlers",
    "geo.google-inclusion",
    "local.hours",
    "local.schema",
    "commerce.facts",
    "intl.hreflang",
    "ops.metrics",
    "ops.indexnow",
    "geo.experiment",
}


class Document(HTMLParser):
    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.language = ""
        self.alternates: dict[str, str] = {}
        self.schemas: list[dict[str, Any]] = []
        self.description = ""
        self.robots: list[str] = []
        self.canonical = ""
        self.visible: list[str] = []
        self.invalid_schema = False
        self._script = False
        self._hidden = 0
        self._text: list[str] = []
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "html":
            self.language = data.get("lang") or ""
        if tag == "meta" and (data.get("name") or "").casefold() in {
            "robots",
            "googlebot",
            "bingbot",
        }:
            self.robots.extend(re.split(r"[,\s]+", (data.get("content") or "").casefold()))
        if tag == "link" and "canonical" in (data.get("rel") or "").lower().split():
            self.canonical = data.get("href") or ""
        if tag == "meta" and (data.get("name") or "").lower() == "description":
            self.description = data.get("content") or ""
        if (
            tag == "link"
            and "alternate" in (data.get("rel") or "").lower().split()
            and data.get("hreflang")
            and data.get("href")
        ):
            self.alternates[str(data["hreflang"])] = str(data["href"])
        if tag in {"script", "style"}:
            self._hidden += 1
        if tag == "script" and data.get("type") == "application/ld+json":
            self._script = True
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._script:
            self._text.append(data)
        if not self._hidden:
            self.visible.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._script:
            self._script = False
            try:
                parsed = json.loads("".join(self._text))
                self.schemas.extend(schema_nodes(parsed))
            except (ValueError, TypeError):
                self.invalid_schema = True
        if tag in {"script", "style"}:
            self._hidden = max(0, self._hidden - 1)


def schema_nodes(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [node for item in value for node in schema_nodes(item)]
    if isinstance(value, dict):
        return [value, *schema_nodes(value.get("@graph", []))]
    return []


def normalized_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(path=parsed.path or "/", fragment="").geturl()


def header_noindex(headers: Any) -> bool:
    if not isinstance(headers, dict):
        return False
    return any(
        str(key).casefold() == "x-robots-tag"
        and bool({"noindex", "none"}.intersection(re.split(r"[,\s]+", str(value).casefold())))
        for key, value in headers.items()
    )


def inventory(
    spec: ProjectSpec, evidence: list[Evidence], workspace: Workspace
) -> tuple[dict[str, Any], list[Evidence], dict[str, Document]]:
    now = utc_now()
    # Expired/future-dated owner facts and synthetic research cannot establish readiness.
    facts = {
        f.name: f.value
        for f in spec.facts
        if f.verified_at <= now and (not f.valid_until or f.valid_until > now)
    }
    pages = [
        e
        for e in evidence
        if e.kind == "http"
        and e.data.get("status_code") == 200
        and spec.page_intents.get(urlparse(str(e.url)).path or "/", True)
    ]
    docs = {str(e.url): Document(str(e.data.get("html", ""))) for e in pages}
    dom = [e for e in evidence if e.kind == "dom" and e.data.get("render_settled") is True]
    data = {
        **facts,
        "pages": pages,
        "dom": dom,
        "facts": facts,
        "goals": spec.goals,
        "route_map": spec.route_map,
        "search": [s for s in workspace.search if not s.synthetic],
        "citations": [c for c in workspace.citations if not c.synthetic],
        "competitor_material": [
            m
            for m in workspace.materials
            if m.origin == "competitor"
            and m.reviewed
            and (not m.valid_until or m.valid_until > now)
        ],
        "original_material": [
            m
            for m in workspace.materials
            if m.original
            and m.reviewed
            and m.origin == "owner"
            and m.fact_ids
            and (not m.valid_until or m.valid_until > now)
        ],
        "media_observations": [e for e in dom if e.data.get("media_observations") is not None],
        "visible_offers": [e for e in dom if e.data.get("visible_offer")],
        "comparable_experiment": (
            {"baseline", "treatment", "holdout"}.issubset(
                {c.arm for c in workspace.citations if not c.synthetic}
            )
            and len(
                {
                    (c.engine, c.engine_version, c.market, c.query)
                    for c in workspace.citations
                    if not c.synthetic
                }
            )
            >= 2
            and all(c.citation_accuracy != "unreviewed" for c in workspace.citations)
        ),
        "navigation_observations": [
            e for e in dom if e.data.get("navigation_observations") is not None
        ],
    }
    return data, pages, docs


def complete_catalog(
    spec: ProjectSpec,
    evidence: list[Evidence],
    workspace: Workspace,
    package: KnowledgePackage,
    findings: list[Finding],
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    if len({(e.tenant_id, e.project_id, e.environment) for e in evidence}) > 1 or any(
        e.environment != spec.environment for e in evidence
    ):
        raise ValueError("Catalog evidence crosses a project or environment boundary")
    if set(package.checks) != DETERMINISTIC | set(MODEL_INPUTS):
        raise ValueError("Catalog check has no executable assessment path")
    data, pages, docs = inventory(spec, evidence, workspace)
    prior = {row["check_id"]: row for row in report.get("coverage", [])}
    rows, requests = [], []
    scoped = [e for e in evidence if e.kind in {"http", "dom", "tool"}]
    for id, check in package.checks.items():
        row: dict[str, Any] = {
            "check_id": id,
            "title": check.title,
            "module": check.module.value,
            "state": "needs_data",
            "method": check.assessment,
            "reason": "Required observations have not been collected.",
            "dependencies": [],
            "evidence_ids": [],
            "evidence_urls": [],
            "source_ids": check.source_ids,
            "verification": check.verification,
            "assessment_path": "model_review" if id in MODEL_INPUTS else "deterministic",
        }
        if not set(spec.website_types).intersection(check.website_types):
            row.update(
                state="not_applicable",
                reason="This check does not apply to the configured website type.",
            )
        elif id in BASELINE:
            row.update(
                state=prior.get(id, {}).get("state", "needs_data"),
                evidence_ids=[e.id for e in scoped if e.kind == "http"],
                reason=(
                    "Assessed response status, directives, title, canonical or "
                    "observed links on the collected page sample. Unobserved pages are"
                    " outside this result."
                ),
            )
            if not pages:
                row.update(state="needs_data", dependencies=["Successful public page responses"])
        elif id in MODEL_INPUTS:
            missing = [name for name in MODEL_INPUTS[id] if not data.get(name)]
            row.update(
                dependencies=["Supply or collect: " + name.replace("_", " ") for name in missing]
            )
            if missing:
                row["reason"] = "The assessment was attempted; authoritative inputs are missing."
            else:
                row.update(
                    state="needs_model",
                    reason="Evidence is available; a grounded semantic review is required.",
                    evidence_ids=[e.id for e in scoped],
                )
                requests.append(
                    {
                        **check.model_dump(mode="json"),
                        "supporting_evidence_ids": row["evidence_ids"],
                    }
                )
        else:
            deterministic(id, row, spec, evidence, workspace, data, pages, docs)
        if id in SEMANTIC_FOLLOWUPS and row["state"] == "needs_data":
            missing = [name for name in SEMANTIC_FOLLOWUPS[id] if not data.get(name)]
            if not missing:
                row.update(
                    state="needs_model",
                    method="model_assisted",
                    assessment_path="model_review",
                    reason="Required observations exist; a grounded semantic comparison is needed.",
                    dependencies=[],
                    evidence_ids=[e.id for e in scoped],
                )
                requests.append(
                    {
                        **check.model_dump(mode="json"),
                        "supporting_evidence_ids": row["evidence_ids"],
                    }
                )
            else:
                row["dependencies"] = list(
                    dict.fromkeys(
                        [
                            *row["dependencies"],
                            *("Supply or collect: " + name.replace("_", " ") for name in missing),
                        ]
                    )
                )
        current = [f for f in findings if f.check_id == id]
        if any(f.status == "defect" for f in current) and row["state"] != "not_applicable":
            row.update(
                state="defect",
                reason="; ".join(f.summary for f in current if f.status == "defect"),
                evidence_ids=list(
                    dict.fromkeys(
                        ref for f in current if f.status == "defect" for ref in f.evidence_ids
                    )
                ),
            )
        elif current and row["state"] == "needs_data":
            row.update(
                state="needs_data",
                reason="; ".join(f.summary for f in current),
                dependencies=list(dict.fromkeys(d for f in current for d in f.dependencies)),
            )
        if row["state"] == "needs_data" and not row["dependencies"]:
            row["dependencies"] = check.evidence_requirements + check.required_context
        row["evidence_urls"] = sorted(
            {str(e.url) for e in scoped if e.id in row["evidence_ids"] and e.url}
        )
        if row["state"] in {"healthy", "defect"}:
            # Replace the preliminary scanner's missing-context notice when richer
            # observations actually resolve it. Confirmed defects are never removed.
            findings[:] = [f for f in findings if f.check_id != id or f.status != "unresolved"]
        rows.append(row)
        if row["state"] == "defect" and not any(
            f.check_id == id and f.status == "defect" for f in findings
        ):
            findings.append(
                Finding(
                    check_id=id,
                    summary=row["reason"],
                    status=FindingStatus.DEFECT,
                    severity=Severity.MEDIUM,
                    evidence_strength=EvidenceStrength.CONFIRMED,
                    evidence_ids=row["evidence_ids"],
                    source_ids=check.source_ids,
                    action=ProposedAction(
                        kind=ActionKind.INVESTIGATE, rationale=check.recommended_action
                    ),
                    verification_criteria=check.verification,
                )
            )
    report.update(coverage=rows, coverage_version=VERSION)
    summarize(report)
    return [
        request
        for request in requests
        if next(row for row in rows if row["check_id"] == request["id"])["state"] == "needs_model"
    ]


def deterministic(
    id: str,
    row: dict[str, Any],
    spec: ProjectSpec,
    evidence: list[Evidence],
    workspace: Workspace,
    data: dict[str, Any],
    pages: list[Evidence],
    docs: dict[str, Document],
) -> None:
    def result(
        state: str,
        reason: str,
        refs: list[Evidence] | None = None,
        dependencies: list[str] | None = None,
    ) -> None:
        row.update(
            state=state,
            reason=reason,
            evidence_ids=[e.id for e in (refs or [])],
            dependencies=dependencies or [],
        )

    if id in {"tech.robots", "geo.crawlers"}:
        prefs = spec.crawler_preferences
        if id == "tech.robots":
            prefs = {
                bot: value
                for bot, value in prefs.items()
                if bot.casefold() in {"googlebot", "bingbot"}
            }
        if not prefs or all(value == "unchanged" for value in prefs.values()):
            result(
                "needs_data",
                (
                    "Crawl access is checked separately from indexing; no explicit "
                    "crawler policy was supplied."
                ),
                dependencies=["Owner preferences for the individual search/training crawlers"],
            )
            return
        for page in pages:
            raw = page.data.get("robots_txt")
            if not isinstance(raw, str) or not raw:
                result("needs_data", "No successful robots observation is available.")
                return
            if re.search(r"(?:Allow|Disallow)\s*:[^\n]*[\*$]", raw, re.I):
                result(
                    "needs_data",
                    "Wildcard rules need engine-specific matching, not a generic robots parser.",
                )
                return
            rules = RobotFileParser()
            rules.parse(raw.splitlines())
            if any(
                rules.can_fetch(bot, str(page.url)) != (policy == "allow")
                for bot, policy in prefs.items()
                if policy != "unchanged"
            ):
                result(
                    "defect",
                    "Observed crawler access conflicts with an explicit owner preference.",
                    [page],
                )
                return
        if pages:
            result(
                "healthy",
                (
                    "Observed URLs match the configured crawler policies. Unconfigured"
                    " bots remain unchanged."
                ),
                pages,
            )
    elif id == "tech.sitemap":
        raw = next((e.data.get("sitemap_xml") for e in pages if e.data.get("sitemap_xml")), None)
        if not isinstance(raw, str):
            result(
                "needs_data", "No sitemap was collected. Absence alone is not an indexing defect."
            )
            return
        try:
            if "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
                raise ValueError("Unsupported XML declarations")
            tree = ElementTree.fromstring(raw)
            urls = [
                node.text.strip()
                for node in tree.iter()
                if node.tag.rsplit("}", 1)[-1] == "loc" and node.text
            ]
        except (ValueError, ElementTree.ParseError):
            result(
                "defect",
                "Observed sitemap XML is malformed or uses unsupported declarations.",
                pages[:1],
            )
            return
        if tree.tag.rsplit("}", 1)[-1] == "sitemapindex":
            result(
                "needs_data",
                "A sitemap index was found; its child sitemap inventories must be collected.",
            )
            return
        if tree.tag.rsplit("}", 1)[-1] != "urlset" or not urls:
            result("defect", "Sitemap must contain a URL inventory.", pages[:1])
            return
        observed = {str(e.url): e for e in evidence if e.kind == "http"}
        invalid = [
            url
            for url in urls
            if url in observed
            and (
                observed[url].data.get("status_code") != 200
                or spec.page_intents.get(urlparse(url).path or "/") is False
                or bool(
                    {"noindex", "none"}.intersection(
                        Document(str(observed[url].data.get("html", ""))).robots
                    )
                )
                or header_noindex(observed[url].data.get("headers"))
                or (
                    bool(Document(str(observed[url].data.get("html", ""))).canonical)
                    and normalized_url(
                        urljoin(url, Document(str(observed[url].data.get("html", ""))).canonical)
                    )
                    != normalized_url(url)
                )
            )
        ]
        if invalid:
            result(
                "defect",
                "Sitemap includes observed unsuccessful, excluded or noncanonical URLs.",
                [observed[url] for url in invalid],
            )
            return
        missing = [url for url in urls if url not in observed]
        if missing:
            result(
                "needs_data",
                "Sitemap parsed, but some listed destinations have not been observed.",
                pages[:1],
                ["Collect sitemap destinations: " + ", ".join(missing[:10])],
            )
            return
        result(
            "healthy",
            (
                "All collected sitemap entries have successful public responses. "
                "Lastmod accuracy and unlisted inventory need revision history."
            ),
            pages,
        )
    elif id == "perf.cwv":
        measures = [e for e in evidence if e.data.get("provider") == "pagespeed"]
        if not measures:
            result(
                "needs_data",
                (
                    "Performance measurement was not collected; page HTML does not "
                    "establish Core Web Vitals."
                ),
                dependencies=[
                    "Enable performance diagnostics and collect URL-scoped field measurements"
                ],
            )
            return
        field = measures[0].data.get("field_url")
        metrics: dict[str, Any] = (
            cast(dict[str, Any], field.get("metrics", {}))
            if isinstance(field, dict) and isinstance(field.get("metrics"), dict)
            else {}
        )
        names = {
            "LARGEST_CONTENTFUL_PAINT_MS": 2500,
            "INTERACTION_TO_NEXT_PAINT": 200,
            "CUMULATIVE_LAYOUT_SHIFT_SCORE": 10,
        }
        if (
            not isinstance(field, dict)
            or field.get("id") != str(measures[0].url)
            or measures[0].data.get("collection_error")
            or measures[0].data.get("runtime_error")
            or not all(
                isinstance(metrics.get(name), dict)
                and type(metrics[name].get("percentile")) in {int, float}
                and math.isfinite(metrics[name]["percentile"])
                and metrics[name]["percentile"] >= 0
                for name in names
            )
        ):
            result(
                "needs_data",
                (
                    "Lab diagnostics or origin averages cannot establish this URL's "
                    "field LCP, INP and CLS."
                ),
                measures,
                ["URL field percentiles for LCP, INP and CLS, with collection scope/window"],
            )
            return
        bad = any(metrics[name]["percentile"] > threshold for name, threshold in names.items())
        result(
            "defect" if bad else "healthy",
            (
                "Compared the URL's reported field percentiles with "
                "good-experience thresholds; this does not establish a ranking "
                "effect."
            ),
            measures,
        )
    elif id == "geo.google-inclusion":
        control = data.get("google_ai_inclusion")
        observation = [e for e in evidence if e.data.get("provider") == "search_console_control"]
        if control is None or not observation:
            result(
                "needs_data",
                "Repository access does not reveal the property's Google AI inclusion control.",
                dependencies=[
                    "Verified owner inclusion preference",
                    "Authorized property-control observation",
                ],
            )
            return
        actual = observation[0].data.get("included")
        result(
            "healthy" if actual == control else "defect",
            "Compared the authorized property observation with the configured preference.",
            observation,
        )
    elif id in {"local.hours", "local.schema"}:
        nodes = [
            (e, node)
            for e in pages
            for node in docs[str(e.url)].schemas
            if "LocalBusiness" in str(node.get("@type", ""))
        ]
        if id == "local.hours":
            hours = data.get("hours")
            if hours is None or not nodes:
                result(
                    "needs_data",
                    (
                        "Owner hours and applicable visible/structured location "
                        "observations are required."
                    ),
                )
                return
            contradictory = [
                (e, node)
                for e, node in nodes
                if node.get("openingHours") is not None and node.get("openingHours") != hours
            ]
            if contradictory:
                result(
                    "defect",
                    "Observed LocalBusiness hours contradict current owner hours.",
                    [pair[0] for pair in contradictory],
                )
                return
            result(
                "needs_data",
                (
                    "Structured hours do not contradict the owner value; visible hours"
                    " and exceptional dates still need verification."
                ),
            )
        else:
            if not nodes or not data.get("business_identity"):
                result(
                    "needs_data",
                    "Applicable LocalBusiness markup and verified location identity are required.",
                )
                return
            identity = data["business_identity"]
            if not isinstance(identity, dict):
                result(
                    "needs_data",
                    "Business identity must contain scoped name/address/contact facts.",
                )
                return
            mismatched = [
                (e, node)
                for e, node in nodes
                if any(
                    key in node and node[key] != identity[key]
                    for key in ("name", "address", "telephone")
                    if key in identity
                )
            ]
            if mismatched:
                result(
                    "defect",
                    "Local markup contradicts the supplied real business identity.",
                    [pair[0] for pair in mismatched],
                )
                return
            result(
                "needs_data",
                (
                    "No observed markup contradiction; visible facts and location "
                    "identifiers still require semantic review."
                ),
            )
    elif id == "commerce.facts":
        offers = [e for e in pages if e.data.get("visible_offer")]
        if not offers:
            result(
                "needs_data",
                "Product markup alone cannot establish actual prices, selected variants or stock.",
                dependencies=[
                    "Rendered visible offer plus authoritative current catalog/variant facts"
                ],
            )
            return
        result(
            "needs_data",
            (
                "A rendered offer was observed; compare it to authoritative "
                "market/variant catalog facts before concluding."
            ),
        )
    elif id == "intl.hreflang":
        annotated = {url: doc for url, doc in docs.items() if doc.alternates}
        if not annotated:
            result(
                "not_applicable",
                (
                    "No language-alternative annotations were found in the collected "
                    "page sample; reassess if locale variants are introduced."
                ),
            )
            return
        missing = []
        for url, doc in annotated.items():
            for lang, href in doc.alternates.items():
                target = urljoin(url, href)
                if not re.fullmatch(
                    r"(?:[a-zA-Z]{2,3}(?:-[a-zA-Z]{4})?(?:-[a-zA-Z]{2}|-\d{3})?|x-default)", lang
                ):
                    result(
                        "defect",
                        "An observed hreflang language/region value is invalid.",
                        [e for e in pages if str(e.url) == url],
                    )
                    return
                if target not in docs:
                    missing.append(target)
                    continue
                return_links = {
                    urljoin(target, value) for value in docs[target].alternates.values()
                }
                if url not in return_links:
                    result(
                        "defect",
                        "An observed language alternative lacks a reciprocal return reference.",
                        [e for e in pages if str(e.url) in {url, target}],
                    )
                    return
        if missing:
            result(
                "needs_data",
                "Some declared locale targets were not collected.",
                dependencies=["Collect: " + ", ".join(sorted(set(missing))[:10])],
            )
            return
        result(
            "needs_data",
            (
                "Reciprocal annotations exist; actual locale equivalence, "
                "canonical selection and language facts still need confirmation."
            ),
            pages,
        )
    elif id == "ops.metrics":
        if (not data["search"] and not data["citations"]) or not any(
            e.data.get("provider") == "owner_context" for e in evidence
        ):
            result(
                "needs_data",
                (
                    "No real search or citation observations are connected. Missing "
                    "metrics remain unknown."
                ),
                dependencies=[
                    "Dated Search Console observations and/or engine-specific citation reports"
                ],
            )
            return
        result(
            "healthy",
            (
                "Structured real observations retain source, window and units; "
                "citation observations remain separate from search traffic. No "
                "causal uplift is inferred."
            ),
            [e for e in evidence if e.data.get("provider") == "owner_context"],
        )
    elif id == "ops.indexnow":
        receipts = [e for e in evidence if e.data.get("provider") == "indexnow"]
        if data.get("indexnow_enabled") is not True or not receipts:
            result(
                "needs_data",
                (
                    "No authorized, deployment-linked IndexNow receipt is available. "
                    "No submission or indexing success is claimed."
                ),
                dependencies=[
                    (
                        "Submission policy, ownership key, deployed public URLs and actual"
                        " engine receipt"
                    )
                ],
            )
            return
        good = [
            e
            for e in receipts
            if e.data.get("accepted") is True and e.data.get("deployment_verified") is True
        ]
        result(
            "healthy" if good else "needs_data",
            "Receipt acceptance is distinct from eventual indexing.",
            good,
        )
    elif id == "geo.experiment":
        observations = data["citations"]
        arms = {entry.arm for entry in observations}
        if not {"baseline", "treatment", "holdout"}.issubset(arms) or not data.get(
            "experiment_protocol"
        ):
            result(
                "needs_data",
                "A single answer is not a controlled GEO experiment.",
                dependencies=[
                    "Protocol and stopping rule",
                    "Repeated matched baseline, treatment and held-out observations",
                ],
            )
            return
        groups = {(c.engine, c.engine_version, c.market, c.query) for c in observations}
        if len(groups) < 2 or any(c.citation_accuracy == "unreviewed" for c in observations):
            result(
                "needs_data",
                "More comparable query runs and source-attribution review are required.",
            )
            return
        result(
            "needs_data",
            (
                "An experiment dataset is available; methodology and statistical "
                "limitations must be reviewed before reporting an effect."
            ),
            dependencies=["Review comparable arms, sample sizes, attribution and confounders"],
        )


def apply_reviews(
    report: dict[str, Any],
    reviews: list[CheckReview],
    evidence: list[Evidence],
    findings: list[Finding],
    requested: list[dict[str, Any]],
) -> None:
    allowed = {check["id"] for check in requested}
    seen: set[str] = set()
    ids = {e.id for e in evidence}
    rows = {row["check_id"]: row for row in report["coverage"]}
    for review in reviews:
        if review.check_id not in allowed or review.check_id in seen:
            raise ValueError("Model check review is unknown, duplicate or lacks required context")
        seen.add(review.check_id)
        if not set(review.evidence_ids).issubset(ids):
            raise ValueError("Model check review references unknown evidence")
        supporting = [e for e in evidence if e.id in review.evidence_ids]
        required = {**MODEL_INPUTS, **SEMANTIC_FOLLOWUPS}[review.check_id]
        if review.state != "needs_data" and (
            not any(e.kind != "screenshot" for e in supporting)
            or ("pages" in required and not any(e.kind == "http" for e in supporting))
            or ("dom" in required and not any(e.kind == "dom" for e in supporting))
        ):
            raise ValueError("Model review lacks its required non-visual evidence")
        if review.state == "healthy" and any(
            f.check_id == review.check_id and f.status in {"defect", "unresolved"} for f in findings
        ):
            raise ValueError("A healthy review conflicts with an unresolved or confirmed finding")
        if review.state == "defect" and not any(
            f.check_id == review.check_id
            and f.status == "defect"
            and set(f.evidence_ids).intersection(review.evidence_ids)
            for f in findings
        ):
            raise ValueError("Model defect review requires its corresponding grounded finding")
        row = rows[review.check_id]
        row.update(
            state=review.state,
            reason=review.reason,
            dependencies=review.dependencies,
            evidence_ids=review.evidence_ids,
            model_reviewed=True,
            evidence_urls=sorted(
                {str(e.url) for e in evidence if e.id in review.evidence_ids and e.url}
            ),
        )
    for id in allowed - seen:
        rows[id].update(
            state="needs_data",
            reason="The model did not return a locally valid assessment for this requested check.",
            dependencies=["Complete the requested structured model review"],
            model_reviewed=False,
        )
    summarize(report)


def reuse_reviews(
    report: dict[str, Any], previous: dict[str, Any], evidence: list[Evidence]
) -> None:
    """Carry forward validated semantic reviews only after the input fingerprint matches."""
    prior = {row["check_id"]: row for row in previous.get("coverage", [])}
    for row in report["coverage"]:
        old = prior.get(row["check_id"], {})
        if row["state"] != "needs_model" or not old.get("model_reviewed"):
            continue
        urls = set(old.get("evidence_urls", []))
        refs = [e for e in evidence if str(e.url) in urls and e.kind != "screenshot"]
        if old.get("state") not in {"healthy", "needs_data"} or not refs:
            continue
        row.update(
            state=old["state"],
            reason="Reused unchanged-input review: " + old["reason"],
            dependencies=old.get("dependencies", []),
            model_reviewed=True,
            evidence_ids=[e.id for e in refs],
            evidence_urls=sorted(urls),
        )
    for row in report["coverage"]:
        if row["state"] == "needs_model":
            row.update(
                state="needs_data",
                reason="A valid cached review is unavailable.",
                dependencies=["Complete a fresh structured semantic assessment"],
            )
    summarize(report)


def summarize(report: dict[str, Any]) -> None:
    rows = report["coverage"]
    assessed = [row for row in rows if row["state"] in {"healthy", "defect"}]
    applicable = [row for row in rows if row["state"] != "not_applicable"]
    report.update(
        evaluated_checks=len(assessed),
        total_checks=len(rows),
        applicable_checks=len(applicable),
        checks_with_dependencies=sum(row["state"] in {"needs_data", "needs_model"} for row in rows),
        catalog_checks_attempted=len(rows),
        score=round(100 * sum(row["state"] == "healthy" for row in assessed) / len(assessed))
        if assessed
        else None,
        coverage_percent=round(100 * len(assessed) / len(applicable)) if applicable else None,
        score_label="Partial observed check health"
        if len(assessed) != len(applicable)
        else "Observed check health",
    )
