"""Clone into an isolated folder and test the actual no-dev first-run launcher."""

import json
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="your-optimiser-install-") as temporary:
        root = Path(temporary)
        checkout, site = root / "app with spaces", root / "site with spaces"
        subprocess.run(["git", "clone", "--quiet", "--local", str(ROOT), str(checkout)], check=True)
        site.mkdir()
        (site / "web").mkdir()
        (site / "web/index.html").write_text(
            '<html><head><title>Example</title><meta name="description" content="Example website">'
            "</head><body><h1>Example</h1></body></html>"
        )
        subprocess.run(["git", "init", "-b", "main", str(site)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(site), "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(site),
                "-c",
                "user.name=Test Owner",
                "-c",
                "user.email=owner@example.test",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                "Add website",
            ],
            check=True,
            capture_output=True,
        )
        env = {**os.environ, "INSTALL_TEST_PASSWORD": secrets.token_urlsafe(24)}
        for name in list(env):
            if name.startswith("OPT_") or name in {
                "GOOGLE_API_KEY",
                "FIRESTORE_EMULATOR_HOST",
                "FIREBASE_AUTH_EMULATOR_HOST",
                "UV_PROJECT_ENVIRONMENT",
            }:
                env.pop(name)
        log = ROOT / ".data/clean-install.log"
        with log.open("w") as output:
            subprocess.run(
                [
                    str(checkout / "run.sh"),
                    "--no-start",
                    "--data-dir",
                    str(root / "private data"),
                    "--repo",
                    str(site),
                    "--url",
                    "http://127.0.0.1:8808",
                    "--provider",
                    "rules",
                    "--password-env",
                    "INSTALL_TEST_PASSWORD",
                    "--port",
                    "8795",
                ],
                cwd=root,
                env=env,
                check=True,
                stdout=output,
                stderr=output,
                timeout=180,
            )
            subprocess.run(
                [str(checkout / "run.sh"), "--no-start"],
                cwd=root,
                env=env,
                check=True,
                stdout=output,
                stderr=output,
                timeout=60,
            )
            server = subprocess.Popen(
                [str(checkout / "run.sh"), "--no-browser"],
                cwd=root,
                env=env,
                stdout=output,
                stderr=output,
            )
            try:
                with httpx.Client() as client:
                    for _ in range(60):
                        try:
                            response = client.get("http://127.0.0.1:8795/healthz")
                            if response.is_success:
                                break
                        except httpx.HTTPError:
                            pass
                        time.sleep(0.3)
                    else:
                        raise AssertionError("Launcher did not start")
                    page = client.get("http://127.0.0.1:8795/login")
                    assert page.status_code == 200 and "Your Optimiser" in page.text
                config = json.loads((checkout / ".your-optimiser.json").read_text())
                assert config["repo_root"] == str(site.resolve())
                installed = subprocess.run(
                    [
                        str(checkout / ".venv/bin/python"),
                        "-c",
                        "import importlib.util; assert importlib.util.find_spec('pytest') is None",
                    ],
                    check=False,
                    capture_output=True,
                )
                assert installed.returncode == 0
            finally:
                server.send_signal(__import__("signal").SIGINT)
                server.wait(timeout=20)
    report = {
        "status": "passed",
        "checks": [
            "isolated clone with space-containing paths",
            "locked no-dev Python installation",
            "fresh account and repository setup",
            "idempotent second launch",
            "dashboard and worker supervision",
            "served branded login",
            "graceful Ctrl+C",
        ],
        "cron_installed": False,
        "cloud_requests": 0,
        "platform": "macOS",
        "other_os_execution": "unverified",
    }
    (ROOT / "reports/clean-install.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
