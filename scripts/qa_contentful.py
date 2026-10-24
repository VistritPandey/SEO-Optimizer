"""Real Contentful QA using a dedicated blank space and ignored .env.qa credentials.

Creates a fictional unpublished entry, exercises the local application service and
restores its original SEO field. No entry publication or customer data is required.
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
from seo_optimizer.connectors.transport import identifier
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".data/live-connectors/contentful"


def finish(report, status):
    target = RUNTIME / "report.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    target.chmod(0o600)
    print(json.dumps(report, indent=2))
    return status


def main() -> int:
    values = dotenv_values(ROOT / ".env.qa")
    space = identifier(values.get("QA_CONTENTFUL_SPACE_ID") or "")
    environment = identifier(values.get("QA_CONTENTFUL_ENVIRONMENT") or "")
    locale = values.get("QA_CONTENTFUL_LOCALE") or "en-US"
    token = values.get("QA_CONTENTFUL_TOKEN") or ""
    if not token:
        raise ValueError("Configure the approved dedicated QA management token")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    RUNTIME.chmod(0o700)
    report = {
        "verified_at": datetime.now(UTC).isoformat(),
        "scope": "Real Contentful API and local application service, fictional unpublished entry",
        "passed": [],
        "failed": [],
        "dependencies": [],
        "unverified": ["Hosted authorization, public rendering, indexing and rankings"],
    }
    base = f"https://api.contentful.com/spaces/{space}/environments/{environment}"
    with httpx.Client(
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/vnd.contentful.management.v1+json",
        },
        timeout=25,
    ) as client:

        def request(method, url, **kwargs):
            response = client.request(method, url, **kwargs)
            if not response.is_success:
                raise RuntimeError(f"Contentful QA request failed (HTTP {response.status_code})")
            return response.json()

        # Never rename or seed an existing customer workspace.
        space_url = f"https://api.contentful.com/spaces/{space}"
        access = client.get(space_url)
        if access.status_code in {401, 403}:
            identity = client.get("https://api.contentful.com/users/me")
            if identity.status_code == 200:
                report["passed"].append("Real token authentication")
            report["dependencies"].append(
                "The management token needs organization authorization for the QA space; "
                "no entry or schema was created"
            )
            return finish(report, 2)
        if access.status_code != 200:
            raise RuntimeError(f"QA space read failed (HTTP {access.status_code})")
        current_space = access.json()
        if current_space["name"] == "Blank":
            current_space = request(
                "PUT",
                space_url,
                headers={"X-Contentful-Version": str(current_space["sys"]["version"])},
                json={"name": "Your Optimiser QA"},
            )
        if current_space["name"] != "Your Optimiser QA":
            raise ValueError("Use only the dedicated Your Optimiser QA space")
        model_url = base + "/content_types/connectorQaPage"
        model_response = client.get(model_url)
        if model_response.status_code == 404:
            model = request(
                "PUT",
                model_url,
                json={
                    "name": "Connector QA page",
                    "displayField": "title",
                    "fields": [
                        {"id": key, "name": key, "type": "Symbol", "localized": True}
                        for key in ["title", "seoTitle", "seoDescription", "qaMarker"]
                    ],
                },
            )
            request(
                "PUT",
                model_url + "/published",
                headers={"X-Contentful-Version": str(model["sys"]["version"])},
            )
        else:
            if model_response.status_code != 200:
                raise RuntimeError("QA schema is unavailable")
            model = model_response.json()
            if model.get("name") != "Connector QA page":
                raise ValueError("Existing schema is not the QA fixture")
        rid = "qa-page-" + secrets.token_hex(6)
        entry_url = base + "/entries/" + rid
        baseline = {
            "title": {locale: "Cedar workshop"},
            "seoTitle": {locale: ""},
            "seoDescription": {locale: "Workshop lighting guide."},
            "qaMarker": {locale: "preserve-me"},
        }
        request(
            "PUT",
            entry_url,
            headers={"X-Contentful-Content-Type": "connectorQaPage"},
            json={"fields": baseline},
        )
        report["passed"].append("Real management authentication, QA schema and unpublished entry")
        try:
            with tempfile.TemporaryDirectory(prefix="optimiser-contentful-qa-") as folder:
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
                                name="Contentful QA",
                                website_url="https://example.test/",
                                publishing_platform="contentful",
                                auto_fix=True,
                            )
                        ),
                    )
                    service = ConnectorService(store, project)
                    saved = service.configure(
                        ConnectionInput(
                            platform=Platform.CONTENTFUL,
                            resource=space,
                            options={
                                "environment": environment,
                                "locale": locale,
                                "seo_title_field": "seoTitle",
                                "seo_description_field": "seoDescription",
                            },
                            credentials={"access_token": token},
                            allow_writes=True,
                        )
                    )
                    assert token not in json.dumps(saved)
                    collected = service.collect(
                        Platform.CONTENTFUL, CollectionRequest(resource_id=rid)
                    )
                    proposals = service.auto_propose(Platform.CONTENTFUL, collected["evidence_id"])
                    assert len(proposals) == 1
                    proposal = service.publish(Platform.CONTENTFUL, proposals[0]["id"])
                    native = request("GET", entry_url)
                    assert proposal["status"] == "waiting_publication"
                    assert proposal["verification"]["provider_readback"]
                    assert native["fields"]["seoTitle"][locale] == "Cedar workshop"
                    assert "publishedVersion" not in native["sys"]
                    assert native["fields"]["qaMarker"] == baseline["qaMarker"]
                    report["passed"].append(
                        "Encrypted connection, real entry collection, grounded proposal, "
                        "version-guarded write and provider readback; entry stays unpublished"
                    )
                    restored = service.publish(
                        Platform.CONTENTFUL, proposals[0]["id"], rollback=True
                    )
                    native = request("GET", entry_url)
                    assert restored["status"] == "rolled_back"
                    assert native["fields"] == baseline and "publishedVersion" not in native["sys"]
                    report["passed"].append("Restoration preserves all original fixture fields")
                finally:
                    store.close()
        except Exception as error:
            report["failed"].append(
                {"id": "contentful-draft-workflow", "error_type": type(error).__name__}
            )
        fixture = RUNTIME / "fixture.json"
        fixture.write_text(json.dumps({"entry_id": rid}))
        fixture.chmod(0o600)
    return finish(report, int(bool(report["failed"])))


if __name__ == "__main__":
    raise SystemExit(main())
