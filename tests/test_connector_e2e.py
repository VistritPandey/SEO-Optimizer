"""Real local HTTP CMS, authenticated API, encrypted SQL queue, worker and served-page proof."""

import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from seo_optimizer.connectors.events import signature
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import create_app
from seo_optimizer.worker import Worker


@pytest.mark.integration
@pytest.mark.enable_socket
@pytest.mark.allow_hosts(["127.0.0.1"])
def test_cms_connect_collect_propose_apply_live_verify_and_restore(tmp_path):
    state = {"title": "", "revision": 1, "writes": 0}

    class CMS(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, value, content_type="application/json"):
            body = (json.dumps(value) if content_type == "application/json" else value).encode()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def record(self):
            return {
                "id": 1,
                "title": {"raw": "Desk lamps"},
                "content": {"raw": "Handmade desk lamps."},
                "status": "publish",
                "meta": {"seo_title": state["title"]},
                "modified_gmt": str(state["revision"]),
                "link": base + "/",
            }

        def do_GET(self):
            if self.path.startswith("/wp-json/"):
                assert (
                    self.headers.get("Authorization")
                    == "Basic " + base64.b64encode(b"fixture-user:fixture-app-password").decode()
                )
                self.send(
                    self.record() if self.path.split("?")[0].endswith("/1") else [self.record()]
                )
            elif self.path == "/robots.txt":
                self.send("User-agent: *\nAllow: /\n", "text/plain")
            elif self.path == "/sitemap.xml":
                self.send(
                    f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{base}/</loc></url></urlset>',
                    "application/xml",
                )
            else:
                title = f"<title>{state['title']}</title>" if state["title"] else ""
                self.send(
                    (
                        f'<html lang="en"><head>{title}'
                        '<meta name="description" content="Handmade desk lamps.">'
                        f'<link rel="canonical" href="{base}/"></head>'
                        "<body><main><h1>Desk lamps</h1>"
                        "<p>Handmade desk lamps.</p></main></body></html>"
                    ),
                    "text/html",
                )

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert self.path == "/wp-json/wp/v2/pages/1"
            assert set(body) == {"meta"}
            state["title"] = body["meta"]["seo_title"]
            state["writes"] += 1
            state["revision"] += 1
            self.send(self.record())

    server = ThreadingHTTPServer(("127.0.0.1", 0), CMS)
    base = f"http://127.0.0.1:{server.server_port}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    settings = Settings(
        data_dir=tmp_path,
        database_url=f"sqlite:///{tmp_path / 'control.db'}",
        secret_key="fixture-e2e-key",
        allow_private_network=True,
    )
    store = Store(settings)
    owner, token = store.create_user("owner@example.test", "fixture-password-hash")
    headers = {"Authorization": "Bearer " + token}
    try:
        with TestClient(create_app(settings, store)) as api:
            response = api.post(
                "/api/v1/projects",
                headers=headers,
                json={
                    "spec": {
                        "name": "Fixture store",
                        "website_url": base,
                        "publishing_platform": "wordpress",
                        "auto_fix": True,
                        "auto_merge": False,
                    }
                },
            )
            assert response.status_code == 201, response.text
            pid = response.json()["id"]
            path = f"/api/v1/projects/{pid}/connectors/wordpress"
            assert (
                api.put(
                    path,
                    headers=headers,
                    json={
                        "platform": "wordpress",
                        "resource": base,
                        "options": {"seo_title_field": "seo_title"},
                        "credentials": {
                            "username": "fixture-user",
                            "application_password": "fixture-app-password",
                            "webhook_secret": "not-an-allowed-field",
                        },
                    },
                ).status_code
                == 422
            )
            saved = api.put(
                path,
                headers=headers,
                json={
                    "platform": "wordpress",
                    "resource": base,
                    "options": {"seo_title_field": "seo_title"},
                    "credentials": {
                        "username": "fixture-user",
                        "application_password": "fixture-app-password",
                    },
                    "allow_writes": True,
                },
            )
            assert saved.status_code == 200 and "fixture-app-password" not in saved.text
            worker = Worker(store, settings)
            assert worker.tick(owner.id)  # Real initial website audit, no source writes.
            queued = api.post(path + "/collect", headers=headers, json={})
            assert queued.status_code == 202
            assert worker.tick(owner.id)
            job = store.job(owner.id, queued.json()["id"])
            assert job.status == "complete", job.result
            connection = api.get(f"/api/v1/projects/{pid}/connectors", headers=headers).json()
            wp = next(c for c in connection["connections"] if c["platform"] == "wordpress")
            assert len(wp["proposals"]) == 1
            proposal = wp["proposals"][0]
            assert proposal["status"] == "proposed" and state["writes"] == 0
            applied = api.post(path + f"/proposals/{proposal['id']}/apply", headers=headers)
            assert applied.status_code == 202 and worker.tick(owner.id)
            job = store.job(owner.id, applied.json()["id"])
            assert job.status == "complete", job.result
            assert job.result["proposal"]["verification"]["provider_readback"]
            assert state["title"] == "Desk lamps" and state["writes"] == 1
            verified = api.post(path + f"/proposals/{proposal['id']}/verify", headers=headers)
            assert verified.status_code == 202 and worker.tick(owner.id)
            result = store.job(owner.id, verified.json()["id"]).result
            assert result["proposal"]["status"] == "deployed_verified", result
            assert result["proposal"]["verification"]["deployed_site"] == "passed"
            # Restore must remain available after successful live verification.
            rollback = api.post(path + f"/proposals/{proposal['id']}/rollback", headers=headers)
            assert rollback.status_code == 202 and worker.tick(owner.id)
            result = store.job(owner.id, rollback.json()["id"]).result
            assert result["proposal"]["status"] == "rolled_back", result
            assert state["title"] == "" and state["writes"] == 2
            # A deployment event from CI is authenticated independently from user sessions.
            deployment = f"/api/v1/projects/{pid}/connectors/deployment"
            assert (
                api.put(
                    deployment,
                    headers=headers,
                    json={
                        "platform": "deployment",
                        "resource": "fixture-ci",
                        "credentials": {"webhook_secret": "fixture-ci-signing-secret"},
                    },
                ).status_code
                == 200
            )
            raw = json.dumps(
                {
                    "event_id": "local-deploy-1",
                    "resource": "fixture-ci",
                    "revision": "fixture-revision",
                    "url": base + "/",
                    "occurred_at": __import__("datetime")
                    .datetime.now(__import__("datetime").UTC)
                    .isoformat(),
                    "status": "succeeded",
                }
            ).encode()
            stamp = str(int(time.time()))
            event_headers = {
                "x-optimiser-timestamp": stamp,
                "x-optimiser-signature": signature("fixture-ci-signing-secret", stamp, raw),
                "Content-Type": "application/json",
            }
            hook = f"/webhooks/connectors/{owner.id}/{pid}/deployment"
            delivered = api.post(hook, content=raw, headers=event_headers)
            assert delivered.status_code == 200 and delivered.json()["queued"]
            assert api.post(hook, content=raw, headers=event_headers).json() == {"duplicate": True}
            assert api.post(hook, content=raw, headers={}).status_code == 403
    finally:
        server.shutdown()
        server.server_close()
        store.close()
