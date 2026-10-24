"""Real Framer SDK/connector QA in a dedicated, unpublished project.

Uses only the approved project key from ignored .env.qa. A trusted fictional fact
grounds the manual proposal: the connector deliberately does not infer a title
from the CMS slug. This test does not claim model inference or publication.
"""

import json
import re
import secrets
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values

from seo_optimizer.application_models import ProjectCreate, ProjectSpec
from seo_optimizer.connectors.models import (
    CollectionRequest,
    ConnectionInput,
    Platform,
    ProposalInput,
)
from seo_optimizer.connectors.service import ConnectorService
from seo_optimizer.contracts import TrustedFact, utc_now
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".data/live-connectors/framer"
SDK = """
import { connect } from 'framer-api';
let text = ''; for await (const chunk of process.stdin) text += chunk;
const input = JSON.parse(text);
const framer = await connect(input.url, input.token);
try {
  let collection = (await framer.getCollections()).find(c => c.name === 'Connector QA');
  if (!collection) collection = await framer.createCollection('Connector QA');
  if (input.action === 'seed') {
    let fields = await collection.getFields();
    for (const name of ['SEO title', 'SEO description', 'QA marker']) {
      if (!fields.some(f => f.name === name)) {
        await collection.addFields([{type:'string', name}]);
      }
    }
    fields = await collection.getFields();
    const mapped = Object.fromEntries(fields.map(f => [f.name, f.id]));
    const data = {
      [mapped['SEO title']]: {type:'string',value:''},
      [mapped['SEO description']]: {type:'string',value:'Workshop lighting guide.'},
      [mapped['QA marker']]: {type:'string',value:'preserve-me'},
    };
    if (mapped.Name) data[mapped.Name] = {type:'string',value:'Cedar workshop'};
    await collection.addItems([{slug:input.slug,fieldData:data}]);
    const item = (await collection.getItems()).find(i => i.slug === input.slug);
    process.stdout.write(JSON.stringify({collection_id:collection.id,item_id:item.id,
      title_field:mapped['SEO title'],description_field:mapped['SEO description'],
      marker_field:mapped['QA marker']}));
  } else {
    const item = (await collection.getItems()).find(i => i.id === input.item_id);
    process.stdout.write(JSON.stringify(item.fieldData));
  }
} finally { await framer.disconnect(); }
"""


def main() -> int:
    values = dotenv_values(ROOT / ".env.qa")
    url = values.get("QA_FRAMER_PROJECT_URL") or ""
    token = values.get("QA_FRAMER_TOKEN") or ""
    match = re.search(r"/Connector-QA--([A-Za-z0-9]{20})", url)
    if not match or not token:
        raise ValueError("Use only the dedicated Connector QA project and its approved key")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    RUNTIME.chmod(0o700)
    report = {
        "verified_at": datetime.now(UTC).isoformat(),
        "scope": "Real Framer SDK and local service; grounded manual proposal, no publishing",
        "passed": [],
        "failed": [],
        "unverified": ["Hosted tenant flow, model inference, publication, indexing and rankings"],
    }

    def sdk(**body):
        result = subprocess.run(
            ["node", "--input-type=module", "-e", SDK],
            cwd=ROOT / "integrations/framer",
            input=json.dumps({"url": url, "token": token, **body}),
            text=True,
            capture_output=True,
            timeout=60,
        )
        if result.returncode:
            diagnostic = RUNTIME / "sdk-error.txt"
            diagnostic.write_text(result.stderr.replace(token, "[REDACTED]"))
            diagnostic.chmod(0o600)
            raise RuntimeError("SDK operation failed; inspect private QA diagnostics")
        return json.loads(result.stdout)

    try:
        fixture = sdk(action="seed", slug="qa-" + secrets.token_hex(5))
        report["passed"].append("Official SDK authentication and fictional CMS fixture creation")
        target = RUNTIME / "fixture.json"
        target.write_text(json.dumps(fixture))
        target.chmod(0o600)
        with tempfile.TemporaryDirectory(prefix="optimiser-framer-qa-") as folder:
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
                            name="Framer QA",
                            website_url="https://example.test/",
                            publishing_platform="framer",
                            auto_fix=True,
                            facts=[
                                TrustedFact(
                                    id="fixture-title",
                                    name="Page title",
                                    value="Cedar workshop",
                                    source="Explicit fictional QA fixture",
                                    verified_at=utc_now(),
                                )
                            ],
                        )
                    ),
                )
                service = ConnectorService(store, project)
                saved = service.configure(
                    ConnectionInput(
                        platform=Platform.FRAMER,
                        resource=match.group(1),
                        options={
                            "collection_id": fixture["collection_id"],
                            "seo_title_field": fixture["title_field"],
                            "seo_description_field": fixture["description_field"],
                        },
                        credentials={"access_token": token},
                        allow_writes=True,
                    )
                )
                assert token not in json.dumps(saved)
                result = service.collect(
                    Platform.FRAMER, CollectionRequest(resource_id=fixture["item_id"])
                )
                assert not service.auto_propose(Platform.FRAMER, result["evidence_id"])
                proposal = service.propose(
                    Platform.FRAMER,
                    ProposalInput(
                        resource_id=fixture["item_id"],
                        changes={"seo_title": "Cedar workshop"},
                        reason="Apply the supported fictional QA title.",
                        fact_ids=["fixture-title"],
                        evidence_ids=[result["evidence_id"]],
                    ),
                )
                applied = service.publish(Platform.FRAMER, proposal["id"])
                native = sdk(action="read", item_id=fixture["item_id"])
                assert applied["status"] == "waiting_publication"
                assert applied["verification"]["provider_readback"]
                assert native[fixture["title_field"]]["value"] == "Cedar workshop"
                assert native[fixture["marker_field"]]["value"] == "preserve-me"
                report["passed"].append(
                    "Real SDK bridge collection, fact-grounded proposal, revision check, "
                    "field update and readback preserve the unrelated marker"
                )
                restored = service.publish(Platform.FRAMER, proposal["id"], rollback=True)
                native = sdk(action="read", item_id=fixture["item_id"])
                assert restored["status"] == "rolled_back"
                assert native[fixture["title_field"]]["value"] == ""
                assert native[fixture["marker_field"]]["value"] == "preserve-me"
                report["passed"].append("Restoration preserves the original mapped fields")
            finally:
                store.close()
    except Exception as error:
        report["failed"].append({"id": "framer-qa-workflow", "error_type": type(error).__name__})
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
