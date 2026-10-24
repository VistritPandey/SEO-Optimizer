"""Opt-in Vercel/Netlify QA with approved private .env.qa tokens.

Deploys only a tiny fictional, non-indexable static page. Never imports a repository,
changes DNS or upgrades a plan. Native webhook delivery remains a separate test.
"""

import io
import json
import secrets
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

from seo_optimizer.application_models import ProjectCreate, ProjectSpec
from seo_optimizer.connectors.models import CollectionRequest, ConnectionInput, Platform
from seo_optimizer.connectors.service import ConnectorService
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".data/live-connectors/hosting"
HTML = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="robots" content="noindex,nofollow"><title>Connector QA</title>'
    "</head><body><h1>Connector QA</h1><p>Fictional deployment fixture.</p></body></html>"
)


def main() -> int:
    values = dotenv_values(ROOT / ".env.qa")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    RUNTIME.chmod(0o700)
    report = {
        "verified_at": datetime.now(UTC).isoformat(),
        "scope": "Real provider deployment APIs and local connector service",
        "passed": [],
        "failed": [],
        "dependencies": [],
        "unverified": ["Native webhook delivery, hosted tenant UI and search outcomes"],
    }
    fixtures = {}

    def private(name, data):
        target = RUNTIME / name
        target.write_text(json.dumps(data, indent=2) + "\n")
        target.chmod(0o600)

    with httpx.Client(timeout=30, follow_redirects=False) as client:
        for provider in ["vercel", "netlify"]:
            token = values.get("QA_" + provider.upper() + "_TOKEN") or ""
            if not token:
                report["dependencies"].append(provider + ": approved token missing")
                continue

            def api(method, url, _token=token, _provider=provider, **kwargs):
                response = client.request(
                    method, url, headers={"Authorization": "Bearer " + _token}, **kwargs
                )
                if not response.is_success:
                    raise RuntimeError(f"{_provider} API HTTP {response.status_code}")
                return response.json()

            try:
                if provider == "vercel":
                    slug = values.get("QA_VERCEL_PROJECT_SLUG") or ""
                    team = values.get("QA_VERCEL_TEAM_SLUG") or ""
                    if team != "your-optimiser-qa" or not slug:
                        raise ValueError("Use only the dedicated QA team/project")
                    project = api(
                        "GET",
                        "https://api.vercel.com/v9/projects/" + slug,
                        params={"slug": team},
                    )
                    params = {"teamId": project["accountId"]}
                    deployment = api(
                        "POST",
                        "https://api.vercel.com/v13/deployments",
                        params=params,
                        json={
                            "name": project["name"],
                            "project": project["id"],
                            "target": "production",
                            "files": [{"file": "index.html", "data": HTML}],
                            "projectSettings": {"framework": None},
                        },
                    )
                    identity = deployment["id"]
                    status_url = "https://api.vercel.com/v13/deployments/" + identity
                    resource = project["id"]
                    options = {"team_id": project["accountId"]}
                else:
                    accounts = api("GET", "https://api.netlify.com/api/v1/accounts")
                    matches = [a for a in accounts if a["name"] == "Your Optimiser QA"]
                    if len(matches) != 1:
                        raise ValueError("Use only the dedicated new QA team")
                    account = matches[0]
                    saved = RUNTIME / "netlify-site.json"
                    if saved.exists():
                        site = api(
                            "GET",
                            "https://api.netlify.com/api/v1/sites/"
                            + json.loads(saved.read_text())["id"],
                        )
                        if not site["name"].startswith("your-optimiser-qa-"):
                            raise ValueError("The saved site is not the QA fixture")
                    else:
                        site = api(
                            "POST",
                            f"https://api.netlify.com/api/v1/{account['slug']}/sites",
                            json={"name": "your-optimiser-qa-" + secrets.token_hex(5)},
                        )
                        private("netlify-site.json", {"id": site["id"], "name": site["name"]})
                    content = io.BytesIO()
                    with zipfile.ZipFile(content, "w", zipfile.ZIP_DEFLATED) as bundle:
                        bundle.writestr("index.html", HTML)
                    response = client.post(
                        f"https://api.netlify.com/api/v1/sites/{site['id']}/deploys",
                        headers={
                            "Authorization": "Bearer " + token,
                            "Content-Type": "application/zip",
                        },
                        content=content.getvalue(),
                    )
                    if not response.is_success:
                        raise RuntimeError(f"Netlify upload HTTP {response.status_code}")
                    deployment = response.json()
                    identity = deployment["id"]
                    status_url = "https://api.netlify.com/api/v1/deploys/" + identity
                    resource, options, params = site["id"], {}, {}
                for _ in range(20):
                    deployment = api("GET", status_url, params=params)
                    state = deployment.get("readyState", deployment.get("state", "")).lower()
                    if state in {"ready", "error", "failed", "canceled"}:
                        break
                    time.sleep(2)
                assert state == "ready", "Deployment did not become ready within QA time budget"
                url = (
                    "https://" + (deployment.get("alias") or [deployment["url"]])[0]
                    if provider == "vercel"
                    else deployment["ssl_url"]
                )
                # The live website gets no API authorization header.
                live = client.get(url)
                if live.status_code == 200 and "Fictional deployment fixture." in live.text:
                    report["passed"].append(provider + ": deployed HTML verified over HTTPS")
                else:
                    report["dependencies"].append(
                        provider
                        + f": live page verification needs inspection (HTTP {live.status_code})"
                    )
                with tempfile.TemporaryDirectory(prefix="optimiser-hosting-qa-") as folder:
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
                            ProjectCreate(spec=ProjectSpec(name="Hosting QA", website_url=url)),
                        )
                        service = ConnectorService(store, project)
                        platform = Platform(provider)
                        service.configure(
                            ConnectionInput(
                                platform=platform,
                                resource=resource,
                                options=options,
                                credentials={"access_token": token},
                            )
                        )
                        result = service.collect(platform, CollectionRequest(limit=10))
                        assert any(r["id"] == identity for r in result["collection"]["records"])
                        report["passed"].append(
                            provider + ": encrypted connection and real deployment collection"
                        )
                    finally:
                        store.close()
                fixtures[provider] = {"resource": resource, "deployment": identity, "url": url}
                print(provider + ": deployment and collection complete", flush=True)
            except Exception as error:
                report["failed"].append({"provider": provider, "error_type": type(error).__name__})
                diagnostic = RUNTIME / (provider + "-error.txt")
                diagnostic.write_text(str(error))
                diagnostic.chmod(0o600)
                print(provider + ": inspect private QA report", flush=True)
    private("fixtures.json", fixtures)
    private("report.json", report)
    print(json.dumps(report, indent=2))
    return int(bool(report["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())
