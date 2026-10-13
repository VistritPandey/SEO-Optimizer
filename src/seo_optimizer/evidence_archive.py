"""Bounded, inspectable job evidence without cookies or private skill instructions."""

import hashlib
import json
from typing import Any

from seo_optimizer.audit import PageParser
from seo_optimizer.contracts import Evidence


def archive_evidence(evidence: list[Evidence], budget: int = 550_000) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    remaining = budget
    for item in evidence:
        record = item.model_dump(mode="json")
        data: dict[str, Any] = {"persisted_subset": True}
        if item.kind in {"http", "dom"}:
            html = str(item.data.get("html", ""))
            page = PageParser()
            page.feed(html)
            headers = item.data.get("headers", {})
            if not isinstance(headers, dict):
                headers = {}
            data.update(
                status_code=item.data.get("status_code"),
                canonical_urls=page.canonicals,
                title="".join(page.title),
                html_sha256=hashlib.sha256(html.encode()).hexdigest(),
                html_excerpt=html[:2000],
                html_excerpt_truncated=len(html) > 2000,
                headers={
                    key: value
                    for key, value in headers.items()
                    if key.lower() in {"content-type", "x-robots-tag", "link", "location"}
                },
                visible_offer=item.data.get("visible_offer"),
                render_settled=item.data.get("render_settled"),
            )
        elif item.kind == "source":
            text = str(item.data.get("text", ""))
            data.update(
                source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                source_excerpt=text[:2000],
                source_excerpt_truncated=len(text) > 2000,
                revision=item.data.get("revision"),
                branch=item.data.get("branch"),
            )
        elif item.kind == "screenshot":
            # Worker filesystem artifacts are ephemeral; never pretend the stored path is a URL.
            data["artifact_persisted"] = False
            data["dependency"] = "Screenshot pixels are not retained in the job JSON"
            record["screenshot"] = None
        else:
            data["dependency"] = (
                "Detailed tool measurements are recorded in the report when available"
            )
        record["data"] = data
        encoded = len(json.dumps(record).encode())
        if encoded > remaining:
            record["data"] = {
                "persisted_subset": True,
                "dependency": "Evidence archive budget reached",
            }
        else:
            remaining -= encoded
        records.append(record)
    return records
