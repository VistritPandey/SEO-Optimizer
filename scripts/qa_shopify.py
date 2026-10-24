"""Opt-in real Shopify QA on the explicitly named development store only.

Uses ignored .env.qa credentials. Creates a fictional draft product, applies one
grounded metadata proposal and restores it. No publication, price or stock writes.
"""

import json
import secrets
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

from seo_optimizer.application_models import ProjectCreate, ProjectSpec
from seo_optimizer.connectors.models import (
    CollectionRequest,
    ConnectionInput,
    Platform,
    ProposalInput,
)
from seo_optimizer.connectors.service import ConnectorService
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".data/live-connectors/shopify"


def main() -> int:
    values = dotenv_values(ROOT / ".env.qa")
    shop, token = values.get("QA_SHOPIFY_SHOP"), values.get("QA_SHOPIFY_TOKEN")
    if shop != "your-optimiser-qa.myshopify.com" or not token:
        raise ValueError("Use only the explicitly authorized development store and token")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    RUNTIME.chmod(0o700)
    report = {
        "verified_at": datetime.now(UTC).isoformat(),
        "scope": "Real Shopify GraphQL 2026-10 and local service, fictional draft product",
        "passed": [],
        "failed": [],
        "unverified": ["Merchant OAuth, deployed rendering, indexing and rankings"],
    }
    with httpx.Client(
        headers={"X-Shopify-Access-Token": token}, timeout=25, follow_redirects=False
    ) as client:

        def graphql(query, variables):
            response = client.post(
                f"https://{shop}/admin/api/2026-10/graphql.json",
                json={"query": query, "variables": variables},
            )
            if response.status_code != 200 or response.json().get("errors"):
                raise RuntimeError(f"Shopify QA query failed (HTTP {response.status_code})")
            return response.json()["data"]

        created = graphql(
            "mutation($product:ProductCreateInput!){productCreate(product:$product){"
            "product{id} userErrors{field message}}}",
            {
                "product": {
                    "title": "Cedar workshop lamp",
                    "descriptionHtml": "<p>Workshop lighting guide.</p>",
                    "status": "DRAFT",
                    "tags": ["your-optimiser-qa"],
                    "seo": {"title": "QA lamp", "description": "Workshop lighting guide."},
                }
            },
        )["productCreate"]
        if created["userErrors"]:
            raise RuntimeError("Shopify rejected the fictional draft fixture")
        rid = created["product"]["id"]
        fixture = RUNTIME / "fixture.json"
        fixture.write_text(json.dumps({"product_id": rid}))
        fixture.chmod(0o600)

        def native():
            return graphql(
                "query($id:ID!){product(id:$id){id title status seo{title description} "
                "variants(first:10){nodes{id price inventoryQuantity}}}}",
                {"id": rid},
            )["product"]

        before = native()
        for _ in range(10):
            if before["seo"]["title"] == "QA lamp":
                break
            time.sleep(0.5)
            before = native()
        assert before["status"] == "DRAFT"
        assert before["seo"]["title"] == "QA lamp", "Seed metadata was not readable"
        report["passed"].append("Scoped GraphQL authentication and fictional draft product setup")
        try:
            with tempfile.TemporaryDirectory(prefix="optimiser-shopify-qa-") as folder:
                settings = Settings(
                    data_dir=Path(folder),
                    database_url="sqlite:///" + folder + "/control.db",
                    secret_key=secrets.token_urlsafe(32),
                )
                store = Store(settings)
                try:
                    owner, _ = store.create_user("owner@example.test", "local-qa-hash")
                    project = store.create_project(
                        owner.id,
                        ProjectCreate(
                            spec=ProjectSpec(
                                name="Shopify QA",
                                website_url="https://" + shop,
                                publishing_platform="shopify",
                                auto_fix=True,
                            )
                        ),
                    )
                    service = ConnectorService(store, project)
                    saved = service.configure(
                        ConnectionInput(
                            platform=Platform.SHOPIFY,
                            resource=shop,
                            credentials={"access_token": token},
                            allow_writes=True,
                        )
                    )
                    assert token not in json.dumps(saved)
                    result = service.collect(Platform.SHOPIFY, CollectionRequest(resource_id=rid))
                    proposal = service.propose(
                        Platform.SHOPIFY,
                        ProposalInput(
                            resource_id=rid,
                            changes={"seo_title": "Cedar workshop lamp"},
                            reason="Reuse the observed fictional product title.",
                            evidence_ids=[result["evidence_id"]],
                        ),
                    )
                    applied = service.publish(Platform.SHOPIFY, proposal["id"])
                    after = native()
                    assert applied["verification"]["provider_readback"], (
                        "Immediate provider readback did not confirm the write"
                    )
                    effective_title = after["seo"]["title"] or after["title"]
                    assert effective_title == "Cedar workshop lamp", "SEO title mismatch"
                    assert after["seo"]["description"] == before["seo"]["description"]
                    assert after["variants"] == before["variants"], (
                        "Product business fields changed"
                    )
                    assert after["status"] == "DRAFT", "Product publication status changed"
                    report["passed"].append(
                        "Encrypted connection, product collection, grounded proposal, "
                        "SEO-only write and real readback preserve price, stock and draft status"
                    )
                    restored = service.publish(Platform.SHOPIFY, proposal["id"], rollback=True)
                    final = native()
                    assert restored["status"] == "rolled_back"
                    assert final["seo"] == before["seo"]
                    assert final["variants"] == before["variants"] and final["status"] == "DRAFT"
                    report["passed"].append("Restoration preserves product business fields")
                finally:
                    store.close()
        except Exception as error:
            report["failed"].append(
                {"id": "shopify-product-workflow", "error_type": type(error).__name__}
            )
            diagnostic = RUNTIME / "error.txt"
            diagnostic.write_text(str(error).replace(token, "[REDACTED]"))
            diagnostic.chmod(0o600)
    target = RUNTIME / "report.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    target.chmod(0o600)
    print(json.dumps(report, indent=2))
    return int(bool(report["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())
