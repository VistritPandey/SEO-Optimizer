"""Opt-in real Sanity draft QA. Requires a dedicated QA dataset and scoped token.

Reads ignored .env.qa. Creates only uniquely named fictional drafts, never publishes.
Reports are private until reviewed for inclusion in the public QA report.
"""

import json
import secrets
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

from seo_optimizer.application_models import ProjectCreate, ProjectSpec
from seo_optimizer.connectors.models import CollectionRequest, ConnectionInput, Platform
from seo_optimizer.connectors.service import ConnectorService
from seo_optimizer.connectors.transport import ConnectorError, identifier
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".data/live-connectors/sanity"


def main() -> int:
    values = dotenv_values(ROOT / ".env.qa")
    project_id = identifier(values.get("QA_SANITY_PROJECT_ID") or "")
    dataset = identifier(values.get("QA_SANITY_DATASET") or "")
    token = values.get("QA_SANITY_TOKEN") or ""
    if not dataset.startswith("qa") or not token:
        raise ValueError("Use a dedicated qa-prefixed dataset and scoped QA token")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    RUNTIME.chmod(0o700)
    document_id = "drafts.connector-qa-" + secrets.token_hex(6)
    base = f"https://{project_id}.api.sanity.io/v2025-02-19/data"
    report = {
        "verified_at": datetime.now(UTC).isoformat(),
        "scope": "Real Sanity API and local application service, fictional unpublished draft",
        "passed": [],
        "failed": [],
        "unverified": ["Hosted OAuth, public rendering, indexing and ranking"],
    }
    with httpx.Client(headers={"Authorization": "Bearer " + token}, timeout=25) as client:
        seeded = client.post(
            base + "/mutate/" + dataset,
            json={
                "mutations": [
                    {
                        "create": {
                            "_id": document_id,
                            "_type": "qaPage",
                            "title": "Cedar workshop",
                            "seoTitle": "",
                            "seoDescription": "Workshop lighting guide.",
                            "qaMarker": "preserve-me",
                        }
                    }
                ]
            },
        )
        if seeded.status_code != 200:
            raise RuntimeError(f"QA draft creation failed (HTTP {seeded.status_code})")

        def native():
            response = client.get(
                base + "/query/" + dataset,
                params={
                    "query": "*[_id == $id][0]",
                    "$id": json.dumps(document_id),
                    "perspective": "raw",
                },
            )
            if response.status_code != 200:
                raise RuntimeError(f"QA draft read failed (HTTP {response.status_code})")
            return response.json()["result"]

        assert native()["qaMarker"] == "preserve-me"
        report["passed"].append("Authorized draft creation and explicit raw-perspective read")
        with tempfile.TemporaryDirectory(prefix="optimiser-sanity-qa-") as folder:
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
                            name="Sanity QA",
                            website_url="https://example.test/",
                            publishing_platform="sanity",
                            auto_fix=True,
                        )
                    ),
                )
                service = ConnectorService(store, project)
                saved = service.configure(
                    ConnectionInput(
                        platform=Platform.SANITY,
                        resource=project_id,
                        options={
                            "dataset": dataset,
                            "document_type": "qaPage",
                            "seo_title_field": "seoTitle",
                            "seo_description_field": "seoDescription",
                        },
                        credentials={"access_token": token},
                        allow_writes=True,
                    )
                )
                assert token not in json.dumps(saved)
                try:
                    collected = service.collect(
                        Platform.SANITY, CollectionRequest(resource_id=document_id)
                    )
                    proposals = service.auto_propose(Platform.SANITY, collected["evidence_id"])
                    assert len(proposals) == 1
                    proposal = service.publish(Platform.SANITY, proposals[0]["id"])
                    after = native()
                    assert proposal["status"] == "waiting_publication"
                    assert proposal["verification"]["provider_readback"]
                    assert after["seoTitle"] == "Cedar workshop"
                    assert after["qaMarker"] == "preserve-me"
                    report["passed"].append(
                        "Encrypted connection, draft collection, grounded title proposal, "
                        "revision-guarded write and actual provider readback"
                    )
                    restored = service.publish(Platform.SANITY, proposals[0]["id"], rollback=True)
                    assert restored["status"] == "rolled_back" and native()["seoTitle"] == ""
                    report["passed"].append("Draft restoration preserves unrelated content")
                except ConnectorError as error:
                    report["failed"].append(
                        {
                            "id": "sanity-existing-draft-collection",
                            "provider_error_code": error.code,
                            "expected": "The adapter reads the authorized existing draft",
                            "observed": "Adapter could not complete the real draft workflow",
                            "control": "Explicit raw-perspective query reads the same draft",
                        }
                    )
            finally:
                store.close()
        # Read-only assertion: no published counterpart was created.
        published = client.get(
            base + "/query/" + dataset,
            params={
                "query": "*[_id == $id][0]",
                "$id": json.dumps(document_id.removeprefix("drafts.")),
                "perspective": "raw",
            },
        )
        assert published.status_code == 200 and published.json()["result"] is None
        report["passed"].append("No published counterpart created")
    target = RUNTIME / "report.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    target.chmod(0o600)
    fixture = RUNTIME / "fixture.json"
    fixture.write_text(json.dumps({"document_id": document_id}))
    fixture.chmod(0o600)
    print(json.dumps(report, indent=2))
    return int(bool(report["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())
