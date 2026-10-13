"""Read-only Search Console connector. API keys are not Search Console authorization."""

import hashlib
from datetime import date
from urllib.parse import quote, urlparse

import httpx
from pydantic import HttpUrl

from seo_optimizer.contracts import utc_now
from seo_optimizer.growth import SearchObservation


def collect_search(
    site_url: str,
    start: date,
    end: date,
    access_token: str,
    client: httpx.Client | None = None,
) -> tuple[list[SearchObservation], dict[str, str | int | bool]]:
    parts = urlparse(site_url)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username:
        raise ValueError("Connector requires the project URL-prefix property")
    if not access_token:
        raise ValueError(
            "A Search Console OAuth access token is required; a model API key is insufficient"
        )
    if end < start or end > utc_now().date() or (end - start).days > 90:
        raise ValueError("Use a valid finalized measurement window of at most 91 days")
    owned = client is None
    transport = client or httpx.Client(timeout=30, follow_redirects=False)
    endpoint = (
        "https://www.googleapis.com/webmasters/v3/sites/"
        + quote(site_url, safe="")
        + "/searchAnalytics/query"
    )
    try:
        response = transport.post(
            endpoint,
            headers={"Authorization": "Bearer " + access_token},
            json={
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "dimensions": ["query", "page", "country", "device"],
                "type": "web",
                "dataState": "final",
                "rowLimit": 1000,
            },
        )
        if response.status_code != 200:
            raise ValueError(f"Search Console returned HTTP {response.status_code}")
        body = response.json()
        rows = body.get("rows", [])
        if not isinstance(rows, list) or len(rows) > 1000:
            raise ValueError("Search Console response exceeds the workspace budget")
        records = []
        for row in rows:
            keys = row.get("keys", [])
            if len(keys) != 4 or urlparse(keys[1]).netloc != parts.netloc:
                raise ValueError("Search Console returned unexpected dimensions or pages")
            records.append(
                SearchObservation(
                    id="gsc-"
                    + hashlib.sha256((str(keys) + str(start) + str(end)).encode()).hexdigest()[:24],
                    query=keys[0],
                    page=HttpUrl(keys[1]),
                    start=start,
                    end=end,
                    impressions=row["impressions"],
                    clicks=row["clicks"],
                    position=row.get("position"),
                    market=keys[2],
                    device=keys[3],
                    source="Search Console finalized web query/page API",
                )
            )
        return records, {
            "rows": len(records),
            "possibly_truncated": len(rows) == 1000,
            "coverage": "Top rows only; Search Console does not guarantee every query is returned",
            "authorization": "Owner-supplied OAuth access token; token refresh is external",
        }
    except httpx.HTTPError:
        raise ValueError("Search Console transport failed") from None
    finally:
        if owned:
            transport.close()
