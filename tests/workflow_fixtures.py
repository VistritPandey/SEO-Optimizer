"""Fictional rich context for exercising every catalog route, never live SEO evidence."""

import json
from datetime import timedelta

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.contracts import Evidence, TrustedFact, utc_now
from seo_optimizer.growth import CitationObservation, Material, SearchObservation, Workspace

ROOT = "https://example.test/"
PASSAGE = "Our cedar desk lamp uses a replaceable linen shade and a measured 45 cm setup."


def rich_context():
    now = utc_now()
    facts = {
        "hours": "Mo 09:00-17:00",
        "business_identity": {"name": "Cedar Workshop", "telephone": "+1-202-555-0100"},
        "business_profile": {"verified": True, "name": "Cedar Workshop", "source": "Owner record"},
        "service_footprint": {"market": "Example City", "service": "Lamp repairs"},
        "offer_facts": {
            "sku": "cedar-natural",
            "price": "89.00",
            "priceCurrency": "USD",
            "availability": "InStock",
        },
        "variants": [{"sku": "cedar-natural", "color": "natural", "url": ROOT}],
        "category_policy": {"facets": "Do not index sort parameters", "category": "desk lamps"},
        "merchant_policy": {"returns": "30 days", "shipping_market": "US"},
        "merchant_observations": {"source": "Owner merchant export", "price": "89.00"},
        "locale_map": {"en": ROOT, "fr": ROOT + "fr/"},
        "localized_facts": {"en": {"currency": "USD"}, "fr": {"currency": "USD"}},
        "migration_map": [{"from": ROOT + "old-guide", "to": ROOT}],
        "migration_observations": [{"from": ROOT + "old-guide", "status": 301, "to": ROOT}],
        "change_history": [
            {"revision": "fixture-change", "path": "web/index.html", "date": now.date().isoformat()}
        ],
        "incremental_trace": {
            "changed": ["web/index.html"],
            "audited": [ROOT],
            "ignored": ["api/server.py"],
        },
        "verification_observations": {
            "revision": "fixture-change",
            "build": "passed",
            "served": "observed",
        },
        "google_ai_inclusion": True,
        "indexnow_enabled": True,
        "experiment_protocol": {
            "queries": ["cedar desk lamps", "replaceable shades"],
            "arms": ["baseline", "treatment", "holdout"],
            "limits": "Workflow fixture, no effect inference",
        },
        "original_passage": PASSAGE,
    }
    spec = ProjectSpec(
        name="Fictional workshop",
        website_url=ROOT,
        website_types=["generic", "local", "ecommerce", "publishing", "docs", "saas"],
        goals=["Help visitors choose and repair lamps"],
        allowed_paths=["web"],
        route_map={"/": "web/index.html", "/fr/": "web/fr/index.html"},
        page_intents={"/": True, "/fr/": True, "/private/": False},
        crawler_preferences={"Googlebot": "allow", "GPTBot": "block"},
        facts=[
            TrustedFact(
                id=name, name=name, value=value, source="Fictional owner fixture", verified_at=now
            )
            for name, value in facts.items()
        ],
    )
    workspace = Workspace(
        materials=[
            Material(
                id="original",
                title="Owner measurements",
                text=PASSAGE,
                origin="owner",
                source="Fictional notebook",
                collected_at=now,
                reviewed=True,
                original=True,
                fact_ids=["original_passage"],
                target_path="/",
            ),
            Material(
                id="competitor",
                title="Independent competitor material",
                text="Example competitor lamp specifications.",
                origin="competitor",
                source="https://competitor.example/spec",
                collected_at=now,
                reviewed=True,
            ),
        ],
        search=[
            SearchObservation(
                id="search",
                query="cedar desk lamps",
                page=ROOT,
                start=now.date() - timedelta(days=28),
                end=now.date(),
                impressions=120,
                clicks=4,
                source="Fictional authorized search export",
                business_relevance="confirmed",
            )
        ],
        citations=[
            CitationObservation(
                id=f"{query}-{arm}",
                experiment="fixture",
                query=query,
                engine="Fixture answer engine",
                engine_version="fixture-v1",
                arm=arm,
                observed_at=now,
                market="en-US",
                answer="A cedar lamp with a replaceable shade.",
                cited_urls=[ROOT],
                source="Fictional transcript fixture",
                retrieval_enabled=True,
                citation_accuracy="supported",
            )
            for query in ["cedar desk lamps", "replaceable shades"]
            for arm in ["baseline", "treatment", "holdout"]
        ],
    )
    nodes = [
        {"@type": "LocalBusiness", **facts["business_identity"], "openingHours": facts["hours"]},
        {
            "@type": "Product",
            "name": "Cedar desk lamp",
            "sku": "cedar-natural",
            "offers": {
                "price": "89.00",
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock",
            },
        },
    ]
    evidence = []
    for locale, url in [("en", ROOT), ("fr", ROOT + "fr/")]:
        html = (
            f'<html lang="{locale}"><head><title>Cedar desk lamp</title>'
            '<meta name="description" content="A cedar desk lamp with a replaceable shade">'
            f'<link rel="canonical" href="{url}"><link rel="alternate" hreflang="en" href="{ROOT}">'
            f'<link rel="alternate" hreflang="fr" href="{ROOT}fr/">'
            f'<script type="application/ld+json">{json.dumps(nodes)}</script></head>'
            f'<body><nav><a href="{ROOT}">Workshop</a></nav><main>'
            f"<h1>Cedar desk lamp</h1><p>{PASSAGE}</p>"
            "<p>Cedar Workshop. Monday 09:00-17:00. USD 89.00. In stock.</p></main></body></html>"
        )
        data = {
            "status_code": 200,
            "html": html,
            "link_status": {ROOT: 200},
            "robots_txt": "User-agent: Googlebot\nAllow: /\nUser-agent: GPTBot\nDisallow: /",
            "sitemap_xml": (
                f"<urlset><url><loc>{ROOT}</loc></url><url><loc>{ROOT}fr/</loc></url></urlset>"
            ),
            "visible_offer": {"price": "89.00", "priceCurrency": "USD", "availability": "InStock"},
        }
        evidence.append(
            Evidence(
                id="http-" + locale,
                tenant_id="fixture-tenant",
                project_id="fixture-site",
                environment="production",
                kind="http",
                url=url,
                observation="Fictional served response",
                collected_at=now,
                data=data,
            )
        )
        evidence.append(
            evidence[-1].model_copy(
                update={
                    "id": "dom-" + locale,
                    "kind": "dom",
                    "data": {
                        **data,
                        "render_settled": True,
                        "media_observations": [
                            {
                                "src": ROOT + "lamp.png",
                                "width": 200,
                                "height": 100,
                                "alt": "Cedar lamp",
                            }
                        ],
                        "navigation_observations": {
                            "links": [{"href": ROOT, "text": "Workshop"}],
                            "viewport": "desktop",
                        },
                    },
                }
            )
        )
    for id, data in [
        (
            "owner",
            {
                "provider": "owner_context",
                "project": spec.model_dump(mode="json"),
                "workspace": workspace.model_dump(mode="json"),
            },
        ),
        (
            "field",
            {
                "provider": "pagespeed",
                "field_url": {
                    "id": ROOT,
                    "metrics": {
                        "LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 1900},
                        "INTERACTION_TO_NEXT_PAINT": {"percentile": 130},
                        "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 5},
                    },
                },
            },
        ),
        ("inclusion", {"provider": "search_console_control", "included": True}),
        ("indexnow", {"provider": "indexnow", "accepted": True, "deployment_verified": True}),
    ]:
        evidence.append(
            Evidence(
                id=id,
                tenant_id="fixture-tenant",
                project_id="fixture-site",
                environment="production",
                kind="tool",
                url=ROOT,
                observation="Fictional authorized observation",
                collected_at=now,
                data=data,
            )
        )
    return spec, workspace, evidence
