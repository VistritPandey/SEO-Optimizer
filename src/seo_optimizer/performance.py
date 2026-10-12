"""Optional official PageSpeed measurements; lab and field evidence stay separate."""

from typing import Any
from uuid import uuid4

import httpx

from seo_optimizer.contracts import Evidence, utc_now
from seo_optimizer.crawler import Crawler

ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def collect_performance(
    url: str,
    tenant: str,
    project: str,
    environment: str,
    key: str = "",
    client: httpx.Client | None = None,
) -> Evidence:
    observation: dict[str, Any]
    owned = client is None
    connection = client or httpx.Client(timeout=45, follow_redirects=False)
    try:
        # A third-party diagnostic may inspect only an explicitly public target.
        validator = Crawler(url, allow_private=False, client=connection)
        validator.check_url(url)
        params = {"url": url, "strategy": "mobile", "category": "performance"}
        if key:
            params["key"] = key
        response = connection.get(ENDPOINT, params=params)
        if response.status_code >= 400:
            raise ValueError("Measurement API returned an error")
        if len(response.content) > 8_000_000:
            raise ValueError("Measurement response exceeds the limit")
        payload = response.json()
        lighthouse = payload.get("lighthouseResult", {})
        audits = lighthouse.get("audits", {})
        observation = {
            "provider": "pagespeed",
            "device": "mobile",
            "measured_at": payload.get("analysisUTCTimestamp"),
            "lighthouse_version": lighthouse.get("lighthouseVersion"),
            "final_url": lighthouse.get("finalUrl"),
            "lab_score": lighthouse.get("categories", {}).get("performance", {}).get("score"),
            "lab": {
                name: audits.get(name, {}).get("numericValue")
                for name in (
                    "largest-contentful-paint",
                    "cumulative-layout-shift",
                    "total-blocking-time",
                )
            },
            "field_url": payload.get("loadingExperience") or None,
            "field_origin": payload.get("originLoadingExperience") or None,
            "warnings": lighthouse.get("runWarnings", []),
            "runtime_error": lighthouse.get("runtimeError"),
            "limits": "Lab snapshots do not establish field INP, ranking or causal search uplift.",
        }
    except (httpx.HTTPError, ValueError, KeyError, AttributeError, TypeError) as error:
        observation = {"provider": "pagespeed", "collection_error": type(error).__name__}
    finally:
        if owned:
            connection.close()
    return Evidence.model_validate(
        {
            "id": str(uuid4()),
            "tenant_id": tenant,
            "project_id": project,
            "environment": environment,
            "kind": "tool",
            "url": url,
            "observation": (
                "Official performance diagnostic, with scope and missing field data retained"
            ),
            "collected_at": utc_now(),
            "data": observation,
        }
    )
