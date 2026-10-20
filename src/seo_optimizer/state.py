"""Cache only identical model inputs, policy, source revision and loaded knowledge."""

import hashlib
import json
from pathlib import Path

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.contracts import Evidence, utc_now
from seo_optimizer.growth import Workspace
from seo_optimizer.knowledge import KnowledgePackage


def input_fingerprint(
    spec: ProjectSpec,
    evidence: list[Evidence],
    revision: str,
    workspace: Workspace,
    knowledge: KnowledgePackage,
    use_knowledge: bool,
) -> str:
    records = []
    for item in evidence:
        if item.kind == "tool":
            records.append(
                {
                    "kind": item.kind,
                    "url": str(item.url),
                    "data": {
                        key: value
                        for key, value in item.data.items()
                        if key not in {"measured_at", "collected_at"}
                    },
                }
            )
            continue
        if item.kind not in {"http", "dom"}:
            continue
        data = {
            key: value
            for key, value in item.data.items()
            if key
            in {
                "html",
                "status_code",
                "headers",
                "link_status",
                "robots_txt",
                "sitemap_xml",
                "visible_offer",
                "render_settled",
                "media_observations",
                "navigation_observations",
                "final_url",
            }
        }
        records.append({"kind": item.kind, "url": str(item.url), "data": data})
    records.sort(key=lambda item: (str(item["url"]), str(item["kind"])))
    # Collection IDs/timestamps and artifact paths are not meaningful page changes.
    payload = {
        "policy": spec.model_dump(mode="json"),
        "revision": revision,
        "workspace": workspace.model_dump(mode="json"),
        "observations": records,
        "fact_validity": {f.id: not f.valid_until or f.valid_until > utc_now() for f in spec.facts},
        "material_validity": {
            m.id: not m.valid_until or m.valid_until > utc_now() for m in workspace.materials
        },
        "knowledge": hashlib.sha256(
            b"".join(
                path.read_bytes() for path in sorted(knowledge.root.rglob("*")) if path.is_file()
            )
        ).hexdigest()
        if use_knowledge
        else "minimal",
        "visual": [
            hashlib.sha256(Path(e.screenshot).read_bytes()).hexdigest()
            for e in evidence
            if spec.provider.capabilities.vision and e.screenshot
        ],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
