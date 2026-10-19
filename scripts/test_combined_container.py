"""Smoke-test the built single-service image with local disposable state and no paid calls."""

import argparse
import json
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import httpx
from test_public_site import check_public_site

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="your-optimiser:deploy-test")
    args = parser.parse_args()
    name = "optimiser-smoke-" + uuid4().hex[:8]
    passed = []

    def docker(*command):
        return subprocess.check_output(["docker", *command], text=True).strip()

    try:
        docker("run", "-d", "--name", name, "-p", "127.0.0.1::8080", args.image)
        info = json.loads(docker("inspect", name))[0]
        port = info["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"]
        base = "http://127.0.0.1:" + port
        with httpx.Client(base_url=base, timeout=20) as client:
            for _attempt in range(40):
                try:
                    first = client.get("/")
                    assert first.status_code == 200, "Ingress opened before the frontend was ready"
                    if client.get("/api/v1/health").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.5)
            else:
                raise AssertionError("Combined container never became healthy")
            assert "Your Optimiser" in client.get("/").text
            assert client.get("/api/v1/health").json()["status"] == "ready"
            assert client.get("/demo.mp4").status_code == 200
            assert client.get("/demo-poster.png").status_code == 200
            assert client.get("/demo-captions.vtt").text.startswith("WEBVTT")
            passed.append("One ingress serves Next pages, public video assets and Python health")
            public_site_checks = check_public_site(base)
            passed.append(
                "Public content, metadata, crawl files, policies and branding "
                "pass served-page checks"
            )
            assert client.get("/api/backend/projects").status_code == 401
            assert client.post("/api/v1/internal/work").status_code == 503
            assert client.post("/webhooks/github", json={}).status_code == 403
            passed.append("Customer proxy and task/webhook handlers reject unconfigured access")
            token = docker(
                "exec",
                name,
                "python",
                "-c",
                (
                    "from seo_optimizer.settings import Settings; "
                    "from seo_optimizer.store import Store; "
                    "s=Store(Settings.from_env()); "
                    "u,t=s.create_user('fixture@example.test','unused'); print(t); s.close()"
                ),
            )
            response = client.get(
                "/api/backend/projects", headers={"Authorization": "Bearer " + token}
            )
            assert response.status_code == 200 and response.json() == []
            passed.append("Production Next proxy reaches only the configured loopback API")
        browser = docker(
            "exec",
            name,
            "python",
            "-c",
            (
                "from playwright.sync_api import sync_playwright; "
                "p=sync_playwright().start(); b=p.chromium.launch(channel='chromium'); "
                "page=b.new_page(); page.set_content('<h1>Container browser works</h1>'); "
                "assert page.locator('h1').inner_text()=='Container browser works'; "
                "b.close(); p.stop(); print('passed')"
            ),
        )
        assert browser == "passed"
        passed.append("Bundled Chromium launches under the unprivileged application user")
        assert docker("exec", name, "id", "-u") == "10001"
        assert docker("exec", name, "sh", "-c", "test ! -e /app/.env && echo passed") == "passed"
        passed.append("Runtime is non-root and contains no root .env")
        # A failed web child must stop the instance instead of leaving a half-working deployment.
        docker(
            "exec",
            name,
            "python",
            "-c",
            (
                "from pathlib import Path; import os,signal; "
                "pids=[int(p.name) for p in Path('/proc').iterdir() "
                "if p.name.isdigit() and (p/'cmdline').exists() "
                "and (p/'cmdline').read_bytes().startswith("
                "(b'node\\x00server.js\\x00',b'next-server'))]; "
                "assert len(pids)==1; os.kill(pids[0],signal.SIGTERM)"
            ),
        )
        for _ in range(30):
            state = json.loads(docker("inspect", name))[0]["State"]
            if not state["Running"]:
                assert state["ExitCode"] == 1
                break
            time.sleep(0.5)
        else:
            raise AssertionError("Supervisor left a half-working container running")
        passed.append("Failed frontend process stops the entire container for platform recovery")
        report = {
            "status": "passed",
            "passed": passed,
            "failed": [],
            "model_calls": 0,
            "environment": "local Docker container with disposable SQLite state",
            "public_site_checks": public_site_checks,
            "unverified": [
                "Live GCP IAM and provisioning",
                "Firebase sign-in",
                "Real Cloud Tasks OIDC delivery",
                "Customer GitHub PR/deployment",
            ],
        }
        (ROOT / "reports/combined-container.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


if __name__ == "__main__":
    main()
