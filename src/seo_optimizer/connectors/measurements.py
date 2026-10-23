"Read adapters for search, analytics, local facts, deployments and paid SERP samples."

from typing import Any
from urllib.parse import quote, urlparse

from seo_optimizer.connectors.models import Collection, CollectionRequest, Platform, Resource
from seo_optimizer.connectors.transport import ConnectorError, Transport, identifier, segment


def collect(t: Transport, q: CollectionRequest) -> Collection:
    c = t.connection
    p, r = c.platform, c.resource
    h = t.bearer() if p not in {Platform.BING, Platform.DATAFORSEO} else {}
    records: list[Resource] = []
    warnings: list[str] = []
    complete = False
    measurement: Any = "search"
    cost = None
    if p == Platform.SEARCH_CONSOLE:
        base = "https://www.googleapis.com/webmasters/v3/sites/" + quote(r, safe="")
        if q.resource_id:
            data = t.request(
                "POST",
                "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                headers=h,
                body={"inspectionUrl": q.resource_id, "siteUrl": r},
            )
            records = [Resource(id=q.resource_id, kind="index_inspection", fields=data)]
        else:
            data = t.request(
                "POST",
                base + "/searchAnalytics/query",
                headers=h,
                body={
                    "startDate": str(q.start),
                    "endDate": str(q.end),
                    "dimensions": ["query", "page", "country", "device", "date"],
                    "type": "web",
                    "dataState": "final",
                    "rowLimit": q.limit,
                },
            )
            for i, row in enumerate(data.get("rows", [])):
                if len(row.get("keys", [])) not in {4, 5}:
                    raise ConnectorError("invalid_response", "Search response dimensions differ")
                records.append(
                    Resource(
                        id=str(i),
                        kind="search_query",
                        fields={
                            **row,
                            "keys": row["keys"][:4],
                            "start": row["keys"][4] if len(row["keys"]) == 5 else str(q.start),
                            "end": row["keys"][4] if len(row["keys"]) == 5 else str(q.end),
                        },
                        url=row["keys"][1],
                    )
                )
            maps = t.request("GET", base + "/sitemaps", headers=h)
            records = records[: max(0, q.limit - 1)] + [
                Resource(id="sitemaps", kind="sitemaps", fields=maps)
            ]
        warnings.append(
            "Top rows only; query omissions and average-position aggregation apply. "
            "Inspection describes the indexed version, not a live test."
        )
    elif p == Platform.GA4:
        data = t.request(
            "POST",
            f"https://analyticsdata.googleapis.com/v1beta/properties/{identifier(r)}:runReport",
            headers=h,
            body={
                "dateRanges": [{"startDate": str(q.start), "endDate": str(q.end)}],
                "dimensions": [
                    {"name": "landingPagePlusQueryString"},
                    {"name": "sessionDefaultChannelGroup"},
                ],
                "metrics": [
                    {"name": m}
                    for m in ["sessions", "engagedSessions", "keyEvents", "totalRevenue"]
                ],
                "dimensionFilter": {
                    "filter": {
                        "fieldName": "sessionDefaultChannelGroup",
                        "stringFilter": {"matchType": "EXACT", "value": "Organic Search"},
                    }
                },
                "limit": q.limit,
                "returnPropertyQuota": True,
            },
        )
        for i, row in enumerate(data.get("rows", [])):
            records.append(
                Resource(
                    id=str(i),
                    kind="organic_landing_page",
                    fields={
                        **row,
                        "dimensions": data.get("dimensionHeaders", []),
                        "metrics": data.get("metricHeaders", []),
                    },
                )
            )
        measurement = "analytics"
        warnings.append(
            "Configured key events and attribution determine meaning. Traffic changes "
            "alone do not prove a fix caused growth."
        )
        complete = int(data.get("rowCount", 0)) <= q.limit
    elif p == Platform.BING:
        method = "GetCrawlStats" if q.resource_id == "crawl" else "GetQueryStats"
        data = t.request(
            "GET",
            "https://ssl.bing.com/webmaster/api.svc/json/" + method,
            params={"apikey": t.secret("api_key"), "siteUrl": r},
        )
        rows = data.get("d", [])
        records = [
            Resource(id=str(i), kind="bing_observation", fields=row)
            for i, row in enumerate(rows[: q.limit])
        ]
        complete = len(rows) <= q.limit
        warnings.append(
            "Provider aggregation windows apply; Bing AI citation report API ingestion "
            "is not included."
        )
    elif p == Platform.BUSINESS_PROFILE:
        if not r.startswith("locations/"):
            raise ConnectorError("configuration", "Use locations/ID for the business profile")
        data = t.request(
            "GET",
            "https://mybusinessbusinessinformation.googleapis.com/v1/locations/"
            + segment(r.split("/", 1)[1]),
            headers=h,
            params={
                "readMask": (
                    "name,title,storefrontAddress,phoneNumbers,websiteUri,regularHours,categories"
                )
            },
        )
        records = [Resource(id=r, kind="business_location", fields=data)]
        measurement = "content"
        complete = True
        warnings.append(
            "Business Profile API approval and location permission are required; "
            "distance cannot be optimized by changing facts."
        )
    elif p == Platform.VERCEL:
        params: dict[str, Any] = {"projectId": r, "limit": q.limit}
        if c.options.get("team_id"):
            params["teamId"] = c.options["team_id"]
        data = t.request("GET", "https://api.vercel.com/v6/deployments", headers=h, params=params)
        records = [
            Resource(
                id=row["uid"],
                kind="deployment",
                fields={key: row.get(key) for key in ["state", "target", "created", "meta", "url"]},
                url="https://" + row["url"],
            )
            for row in data.get("deployments", [])[: q.limit]
        ]
        complete = not data.get("pagination", {}).get("next")
        measurement = "deployment"
    elif p == Platform.NETLIFY:
        data = t.request(
            "GET",
            f"https://api.netlify.com/api/v1/sites/{segment(r)}/deploys",
            headers=h,
            params={"per_page": q.limit},
        )
        records = [
            Resource(
                id=row["id"],
                kind="deployment",
                fields={
                    key: row.get(key) for key in ["state", "context", "commit_ref", "published_at"]
                },
                url=row.get("ssl_url", ""),
            )
            for row in data[: q.limit]
        ]
        measurement = "deployment"
    elif p == Platform.CLOUDFLARE:
        query = (
            "query($zone: String!, $start: Time!, $end: Time!, $limit: Int!) { viewer { "
            "zones(filter: {zoneTag: $zone}) { httpRequestsAdaptiveGroups(limit: $limit,"
            " filter: {datetime_geq: $start, datetime_leq: $end}) { count dimensions { "
            "clientRequestHTTPHost clientRequestPath edgeResponseStatus } } } } }"
        )
        data = t.request(
            "POST",
            "https://api.cloudflare.com/client/v4/graphql",
            headers=h,
            body={
                "query": query,
                "variables": {
                    "zone": r,
                    "start": str(q.start) + "T00:00:00Z",
                    "end": str(q.end) + "T23:59:59Z",
                    "limit": q.limit,
                },
            },
        )
        zones = data.get("data", {}).get("viewer", {}).get("zones", [])
        records = [
            Resource(id=str(i), kind="request_group", fields=row)
            for i, row in enumerate(zones[0].get("httpRequestsAdaptiveGroups", []) if zones else [])
        ]
        measurement = "crawler"
        warnings.append(
            "Adaptive data may be sampled and plan restricted. No crawler identity or AI"
            " citation is inferred from these groups."
        )
    elif p == Platform.DATAFORSEO:
        if not q.query:
            raise ConnectorError("configuration", "A tracked keyword is required")
        data = t.request(
            "POST",
            "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
            headers=t.basic("username", "password"),
            body=[
                {
                    "keyword": q.query,
                    "location_code": int(c.options.get("location_code", "2840")),
                    "language_code": c.options.get("language_code", "en"),
                    "depth": min(q.limit, 100),
                }
            ],
            read_only=False,
        )
        tasks = data.get("tasks", [])
        if data.get("status_code") != 20000 or not tasks or tasks[0].get("status_code") != 20000:
            raise ConnectorError("provider_error", "SERP provider did not complete the task")
        task = tasks[0]
        result = (task.get("result") or [{}])[0]
        host = r.removeprefix("www.").lower()
        for i, row in enumerate(result.get("items", [])[: q.limit]):
            url = row.get("url", "")
            records.append(
                Resource(
                    id=str(i),
                    kind="serp_result",
                    url=url,
                    fields={
                        "query": q.query,
                        "market": q.market,
                        "location_code": c.options.get("location_code", "2840"),
                        "language": c.options.get("language_code", "en"),
                        "type": row.get("type"),
                        "position": row.get("rank_group"),
                        "title": row.get("title"),
                        "target_match": urlparse(url).hostname in {host, "www." + host},
                    },
                )
            )
        cost = float(data["cost"]) if data.get("cost") is not None else None
        warnings.append(
            "Single paid SERP sample; results vary by location, device and time. "
            "Competitor data is observed, not inferred from the model."
        )
    else:
        raise ConnectorError(
            "unsupported", "This connector uses a dedicated content or import workflow"
        )
    if len(records) > q.limit:
        raise ConnectorError("response_limit", "Provider ignored the requested row limit")
    return Collection(
        platform=p,
        records=records,
        complete=complete,
        warnings=warnings,
        cost_usd=cost,
        measurement=measurement,
    )
