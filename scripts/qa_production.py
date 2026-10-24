"""Opt-in hosted QA using existing disposable identities and fictional CMS fixtures.

Run only after approval to upload the four QA credentials to the hosted service.
All API operations use normal Firebase bearer authentication and Cloud Tasks.
This does not certify provider OAuth, publication, indexing or ranking outcomes.
"""

import argparse
import json
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".data/production-qa"
ORIGIN = "https://youroptimiser.com"


def load(path):
    return json.loads(path.read_text())


def save(name, value):
    path = PRIVATE / name
    path.write_text(json.dumps(value, indent=2) + "\n")
    path.chmod(0o600)


class HostedQA:
    def __init__(self):
        self.values = dotenv_values(ROOT / ".env.qa")
        self.identities = load(PRIVATE / "identities.json")
        self.project_id = load(PRIVATE / "api-state.json")["project_id"]
        self.client = httpx.Client(base_url=ORIGIN, timeout=60, follow_redirects=False)
        self.client.headers["Authorization"] = "Bearer " + self.identities[0]["id_token"]
        self.report = {
            "verified_at": datetime.now(UTC).isoformat(),
            "origin": ORIGIN,
            "transport": "Normal authenticated HTTPS API and actual hosted worker jobs",
            "passed": [],
            "failed": [],
            "unverified": [
                "Provider OAuth onboarding and credential renewal",
                "Production publication, deployed rendering, indexing and rankings",
                "Model generation quality; these repairs use observed facts",
            ],
        }

    def call(self, method, path, body=None, expected=200):
        response = self.client.request(method, path, json=body)
        if response.status_code != expected:
            raise RuntimeError(f"Hosted {method} returned HTTP {response.status_code}")
        return response.json()

    @property
    def project_path(self):
        return "/api/v1/projects/" + self.project_id

    def connection(self, platform):
        overview = self.call("GET", self.project_path + "/connectors")
        return next(row for row in overview["connections"] if row["platform"] == platform)

    def job(self, path, body=None):
        job = self.call("POST", path, body or {}, expected=202)
        save("last-job.json", {"id": job["id"], "path": path})
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            job = self.call("GET", "/api/v1/jobs/" + job["id"])
            if job["status"] not in {"queued", "running"}:
                save("last-job-result.json", job)
                if job["status"] != "complete":
                    raise RuntimeError("Hosted worker ended with status " + job["status"])
                return job["result"]
            time.sleep(3)
        raise TimeoutError("Hosted worker did not complete within four minutes")

    def config(self, platform):
        fixture = load(ROOT / ".data/live-connectors" / platform / "fixture.json")
        options = {}
        if platform == "shopify":
            resource = self.values["QA_SHOPIFY_SHOP"]
            if resource != "your-optimiser-qa.myshopify.com":
                raise ValueError("Only the dedicated QA development store is permitted")
            rid, title = fixture["product_id"], "Cedar workshop lamp"
        elif platform == "sanity":
            resource = self.values["QA_SANITY_PROJECT_ID"]
            dataset = self.values["QA_SANITY_DATASET"]
            if not dataset.startswith("qa"):
                raise ValueError("Only the QA dataset is permitted")
            options = {"dataset": dataset, "document_type": "qaPage"}
            rid, title = fixture["document_id"], "Cedar workshop"
            if not rid.startswith("drafts.connector-qa-"):
                raise ValueError("Only an existing fictional QA draft is permitted")
        elif platform == "contentful":
            resource = self.values["QA_CONTENTFUL_SPACE_ID"]
            options = {
                "environment": self.values["QA_CONTENTFUL_ENVIRONMENT"],
                "locale": self.values["QA_CONTENTFUL_LOCALE"],
            }
            rid, title = fixture["entry_id"], "Cedar workshop"
        else:
            match = re.search(
                r"/Connector-QA--([A-Za-z0-9]{20})", self.values["QA_FRAMER_PROJECT_URL"]
            )
            if not match:
                raise ValueError("Only the authorized Framer QA project is permitted")
            resource = match.group(1)
            options = {
                "collection_id": fixture["collection_id"],
                "seo_title_field": fixture["title_field"],
                "seo_description_field": fixture["description_field"],
            }
            rid, title = fixture["item_id"], "Cedar workshop"
        if platform in {"sanity", "contentful"}:
            options.update(seo_title_field="seoTitle", seo_description_field="seoDescription")
        return (
            {
                "platform": platform,
                "label": "Disposable production QA",
                "resource": resource,
                "options": options,
                "credentials": {"access_token": self.values["QA_" + platform.upper() + "_TOKEN"]},
                "allow_writes": True,
                "auto_apply": False,
                "enabled": True,
            },
            rid,
            title,
            fixture,
        )

    def native(self, platform, config, rid, fixture):
        token = config["credentials"]["access_token"]
        resource, options = config["resource"], config["options"]
        with httpx.Client(timeout=40) as client:
            if platform == "shopify":
                response = client.post(
                    f"https://{resource}/admin/api/2026-10/graphql.json",
                    headers={"X-Shopify-Access-Token": token},
                    json={
                        "query": "query($id:ID!){product(id:$id){title status descriptionHtml "
                        "seo{title description} variants(first:10){nodes{id price "
                        "inventoryQuantity}}}}",
                        "variables": {"id": rid},
                    },
                )
                response.raise_for_status()
                data = response.json()["data"]["product"]
                assert data["status"] == "DRAFT", "Fixture must remain a draft"
                return {**data, "seo_title": data["seo"]["title"] or data["title"]}
            if platform == "sanity":
                response = client.get(
                    f"https://{resource}.api.sanity.io/v2025-02-19/data/query/"
                    + options["dataset"],
                    headers={"Authorization": "Bearer " + token},
                    params={
                        "query": "*[_id == $id][0]",
                        "$id": json.dumps(rid),
                        "perspective": "raw",
                    },
                )
                response.raise_for_status()
                data = response.json()["result"]
                assert data["_type"] == "qaPage"
                return {
                    **{k: v for k, v in data.items() if k not in {"_rev", "_updatedAt"}},
                    "seo_title": data.get("seoTitle", ""),
                }
            if platform == "contentful":
                response = client.get(
                    f"https://api.contentful.com/spaces/{resource}/environments/"
                    + options["environment"]
                    + "/entries/"
                    + rid,
                    headers={"Authorization": "Bearer " + token},
                )
                response.raise_for_status()
                data = response.json()
                assert "publishedVersion" not in data["sys"], "Fixture must be unpublished"
                return {
                    "fields": data["fields"],
                    "seo_title": data["fields"].get("seoTitle", {}).get(options["locale"], ""),
                }
        script = """
import {connect} from 'framer-api';
let s='';for await(const chunk of process.stdin)s+=chunk;
const q=JSON.parse(s);const f=await connect(q.url,q.token);
try{const c=(await f.getCollections()).find(x=>x.id===q.collection);
const i=(await c.getItems()).find(x=>x.id===q.id);
process.stdout.write(JSON.stringify(i.fieldData));}finally{await f.disconnect();}
"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=ROOT / "integrations/framer",
            input=json.dumps(
                {
                    "url": self.values["QA_FRAMER_PROJECT_URL"],
                    "token": token,
                    "collection": fixture["collection_id"],
                    "id": rid,
                }
            ),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode:
            raise RuntimeError("Independent Framer SDK read failed")
        data = json.loads(result.stdout)
        return {"fields": data, "seo_title": data[fixture["title_field"]]["value"]}

    def run_platform(self, platform):
        config, rid, title, fixture = self.config(platform)
        path = self.project_path + "/connectors/" + platform
        before = self.native(platform, config, rid, fixture)
        assert before["seo_title"] != title, "Fixture already has the proposed title"
        saved = self.call("PUT", path, config)
        assert config["credentials"]["access_token"] not in json.dumps(saved)
        assert "credentials" not in saved["config"]
        proposal = None
        try:
            result = self.job(path + "/collect", {"resource_id": rid, "limit": 1})
            assert len(result["collection"]["records"]) == 1
            proposals = [
                p
                for p in self.connection(platform)["proposals"]
                if p["resource_id"] == rid and p["status"] == "proposed"
            ]
            if platform in {"sanity", "contentful"}:
                assert len(proposals) == 1, "Expected an automatically grounded proposal"
                proposal = proposals[0]
            else:
                proposal = self.call(
                    "POST",
                    path + "/proposals",
                    {
                        "resource_id": rid,
                        "changes": {"seo_title": title},
                        "reason": "Reuse the verified fictional QA title without new claims.",
                        "evidence_ids": [result["evidence_id"]],
                        "fact_ids": ["qa-title"],
                    },
                    expected=201,
                )
            invalid = self.client.post(
                path + "/proposals",
                json={
                    "resource_id": rid,
                    "changes": {"seo_title": title},
                    "reason": "Invalid evidence must not permit a write.",
                    "evidence_ids": ["unknown-qa-evidence"],
                },
            )
            assert invalid.status_code == 403, "Unknown evidence was not rejected"
            applied = self.job(path + "/proposals/" + proposal["id"] + "/apply")
            assert applied["proposal"]["verification"]["provider_readback"]
            after = self.native(platform, config, rid, fixture)
            assert after["seo_title"] == title, "Independent provider readback mismatch"
            if platform == "shopify":
                assert after["variants"] == before["variants"]
                assert after["descriptionHtml"] == before["descriptionHtml"]
                assert after["seo"]["description"] == before["seo"]["description"]
            elif platform == "sanity":
                assert after["qaMarker"] == before["qaMarker"]
                assert after["seoDescription"] == before["seoDescription"]
            else:
                key = fixture["title_field"] if platform == "framer" else "seoTitle"
                assert {k: v for k, v in after["fields"].items() if k != key} == {
                    k: v for k, v in before["fields"].items() if k != key
                }
            self.report["passed"].append(
                {
                    "platform": platform,
                    "check": "Encrypted save, real queued collection, grounded proposal, "
                    "evidence rejection, hosted write and independent provider readback",
                }
            )
        finally:
            if proposal:
                current = next(
                    p for p in self.connection(platform)["proposals"] if p["id"] == proposal["id"]
                )
                if current["status"] in {"verified", "deployed_verified", "waiting_publication"}:
                    restored = self.job(path + "/proposals/" + proposal["id"] + "/rollback")
                    assert restored["proposal"]["status"] == "rolled_back"
                    assert self.native(platform, config, rid, fixture) == before
                    self.report["passed"].append(
                        {"platform": platform, "check": "Hosted rollback restores original fields"}
                    )
                elif current["status"] not in {"proposed", "rolled_back", "publication_failed"}:
                    raise RuntimeError("Inspect uncertain provider state before disconnecting")
            self.call("DELETE", path)
            assert not self.connection(platform)["connected"]
            self.report["passed"].append(
                {"platform": platform, "check": "Disconnect removes stored QA credentials"}
            )

    def run(self, platforms):
        project = self.call("GET", self.project_path)
        if project["spec"]["name"] != "Production API QA":
            raise ValueError("Only the dedicated API QA project is permitted")
        spec = project["spec"]
        spec.update(
            enabled=True,
            auto_fix=True,
            auto_merge=False,
            facts=[
                {
                    "id": "qa-title",
                    "name": "Page title",
                    "value": "Cedar workshop",
                    "source": "Explicit fictional QA fixture",
                    "verified_at": datetime.now(UTC).isoformat(),
                }
            ],
        )
        self.call("PATCH", self.project_path, spec)
        try:
            for platform in platforms:
                print("Production QA:", platform, "started", flush=True)
                try:
                    self.run_platform(platform)
                    print("Production QA:", platform, "passed", flush=True)
                except Exception as error:
                    self.report["failed"].append(
                        {
                            "platform": platform,
                            "error_type": type(error).__name__,
                            "detail": str(error)[:300],
                        }
                    )
                    print("Production QA:", platform, "failed:", type(error).__name__, flush=True)
                save("connector-report.json", self.report)
        finally:
            spec["enabled"] = False
            self.call("PATCH", self.project_path, spec)
            self.client.close()
            save("connector-report.json", self.report)
        return int(bool(self.report["failed"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-credential-upload", action="store_true", required=True)
    parser.add_argument(
        "--platform", choices=["shopify", "sanity", "contentful", "framer"], action="append"
    )
    args = parser.parse_args()
    return HostedQA().run(args.platform or ["sanity", "contentful", "framer", "shopify"])


if __name__ == "__main__":
    raise SystemExit(main())
