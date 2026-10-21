"""Opt-in real portfolio/Chromium/Docker/Ollama test; never pushes to GitHub.

Usage: uv run python scripts/test_portfolio.py --model gemma4:12b
Dependencies: browser extra, installed Chromium, Docker, running Ollama.
"""

import argparse
import hashlib
import json
import re
import secrets
import shutil
import subprocess
import threading
import time
from pathlib import Path
from uuid import uuid4

from portfolio_fixture import serve

from seo_optimizer.application_models import ProjectCreate, ProjectSpec, ProviderConfig
from seo_optimizer.contracts import ProviderCapabilities, TrustedFact, utc_now
from seo_optimizer.execution import run_git
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import hash_password
from seo_optimizer.worker import Worker

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "optimizer-portfolio-verify:local"


def command(argv, **kwargs):
    return subprocess.run(argv, check=True, **kwargs)


def fingerprint(repository):
    return hashlib.sha256(
        b"".join(
            path.read_bytes() for path in sorted((repository / "src").rglob("*")) if path.is_file()
        )
    ).hexdigest()


def prepare_build(repository, build):
    context = ROOT / ".data/portfolio-image"
    context.mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(repository / name, context / name)
    shutil.copyfile(ROOT / "tests/integration/portfolio.Dockerfile", context / "Dockerfile")
    shutil.copyfile(ROOT / "tests/integration/verify-portfolio.sh", context / "verify.sh")
    command(["docker", "build", "-t", IMAGE, str(context)])
    build.mkdir(parents=True, exist_ok=True)
    command(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "128",
            "--memory",
            "1g",
            "--cpus",
            "1",
            "--tmpfs",
            "/tmp:rw,size=256m",
            "--user",
            "65534:65534",
            "--mount",
            f"type=bind,source={repository},target=/workspace,readonly",
            "--mount",
            f"type=bind,source={build},target=/output",
            IMAGE,
            "/opt/verify-portfolio.sh",
        ]
    )


def commit_fixture(repository, message, path="public/index.html"):
    run_git(repository, "add", path)
    run_git(
        repository,
        "-c",
        "user.name=Portfolio Fixture",
        "-c",
        "user.email=fixture@localhost",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        message,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gemma4:12b")
    parser.add_argument("--repository-url", help="Private opt-in test repository; never hardcoded")
    parser.add_argument("--skip-model", action="store_true")
    parser.add_argument("--reuse-build", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--output", type=Path, default=ROOT / ".data/portfolio-runs/latest.json")
    args = parser.parse_args()
    repository, build = ROOT / ".data/portfolio-test", ROOT / ".data/portfolio-built"
    if not repository.exists():
        if not args.repository_url:
            parser.error("--repository-url is required when the local test checkout is absent")
        command(
            ["git", "-c", "core.hooksPath=/dev/null", "clone", args.repository_url, str(repository)]
        )
    if run_git(repository, "status", "--porcelain"):
        raise ValueError(
            "The local test checkout has uncommitted work; preserve it before rerunning"
        )
    original_sha = run_git(repository, "rev-parse", "refs/remotes/origin/HEAD")
    branch = "optimizer/portfolio-test-" + uuid4().hex[:8]
    run_git(repository, "checkout", "-b", branch, original_sha)
    source = repository / "public/index.html"
    original = source.read_text()
    # Repeated tests start from the upstream title rather than a previous experiment's copy.
    if not args.reuse_build:
        prepare_build(repository, build)
    if not (build / "index.html").is_file():
        raise ValueError("A real compiled portfolio build is required")
    settings_root = ROOT / ".data/portfolio-runs" / uuid4().hex
    settings_root.mkdir(parents=True)
    settings = Settings(
        data_dir=settings_root,
        database_url=f"sqlite:///{settings_root}/control.db",
        secret_key=secrets.token_urlsafe(48),
        allowed_repo_roots=(ROOT / ".data",),
    )
    store = Store(settings)
    account, _ = store.create_user(
        "portfolio-test@localhost.test", hash_password(secrets.token_urlsafe(24))
    )
    data = json.loads((repository / "public/resumeData.json").read_text())
    name = data["main"]["name"]
    server = serve(repository, build, args.port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/"
    spec = ProjectSpec.model_validate(
        {
            "name": "Historical portfolio integration test",
            "website_url": url,
            "local_path": str(repository),
            "branch": branch,
            "allowed_paths": ["public/index.html", "public/resumeData.json"],
            "route_map": {"/": "public/index.html"},
            "max_pages": 1,
            "auto_fix": False,
            "auto_merge": False,
            "browser_enabled": True,
            "check_commands": [["/opt/verify-portfolio.sh"]],
            "sandbox_image": IMAGE,
            "goals": [
                "Historical test copy. Preserve all existing biography and behavior. "
                "Improve metadata using the existing name and visible section labels only. "
                "Do not assert current role, age, address, affiliations or new credentials."
            ],
            "facts": [
                TrustedFact(
                    id="portfolio-name",
                    name="name",
                    value=name,
                    source="Historical repository public/resumeData.json main.name",
                    verified_at=utc_now(),
                ).model_dump(mode="json")
            ],
        }
    )
    project = store.create_project(account.id, ProjectCreate(spec=spec))
    worker = Worker(store, settings)
    report = {
        "generated_at": utc_now().isoformat(),
        "repository": run_git(repository, "remote", "get-url", "origin"),
        "upstream_sha": original_sha,
        "test_branch": branch,
        "model": args.model,
        "fixture_url": url,
        "cases": [],
        "github_writes": False,
        "fixture_method": "Real compiled React assets, with public/index.html head refreshed "
        "from the test checkout. Metadata-only deployment simulation.",
        "limits": [
            "Historical biography is not verified as current.",
            "External browser resources are blocked during collection.",
            "No live GitHub PR, cloud deployment or search uplift is measured.",
        ],
    }
    baseline_fingerprint = fingerprint(repository)

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    def run(label, enqueue=True, kind="audit"):
        if enqueue:
            store.enqueue(account.id, project.id, kind, label + ":" + uuid4().hex, {})
        started = time.monotonic()
        worker.tick(account.id)
        job = store.jobs(account.id, project.id)[0]
        record = {
            "case": label,
            "status": job.status,
            "runtime_ms": (time.monotonic() - started) * 1000,
            "result": job.result,
        }
        report["cases"].append(record)
        save()
        print(f"{label}: {job.status} - {job.result.get('summary', '')}", flush=True)
        return job

    baseline = run("baseline", False)
    assert baseline.status == "complete"
    assert "tech.title" not in {item["check_id"] for item in baseline.result["findings"]}
    assert any(item["check_id"] == "tech.metadata" for item in baseline.result["findings"])
    report["baseline_source_title"] = re.search(r"<title>(.*?)</title>", original, re.S).group(1)
    modified = re.sub(r"\s*<title\b[^>]*>.*?</title>", "", original, flags=re.I | re.S)
    assert modified != original
    source.write_text(modified)
    commit_fixture(repository, "Test missing title")
    defect_sha = run_git(repository, "rev-parse", "HEAD")
    spec.auto_fix, spec.auto_merge = True, True
    store.update_project(account.id, project.id, spec)
    fixed = run("rendered-title-repair")
    assert fixed.status == "complete" and fixed.result["verified_fixes"] == 1
    assert fixed.result["stage"] == "verified"
    assert name in re.search(r"<title>(.*?)</title>", source.read_text(), re.S).group(1)
    fixed_sha = run_git(repository, "rev-parse", "HEAD")
    assert fixed_sha != defect_sha
    assert run_git(repository, "diff", "--name-only", defect_sha, fixed_sha) == "public/index.html"
    repeated = run("repeat-audit")
    assert repeated.status == "complete" and run_git(repository, "rev-parse", "HEAD") == fixed_sha
    data_path = repository / "public/resumeData.json"
    original_data = data_path.read_text()
    changed_data = json.loads(original_data)
    changed_data["_optimizer_fixture_marker"] = "incremental-scope-test"
    data_path.write_text(json.dumps(changed_data, indent=2) + "\n")
    commit_fixture(repository, "Test content data event", "public/resumeData.json")
    event = run("json-data-push", kind="push")
    assert event.status == "complete" and event.result["report"]["pages"] == 1
    readme_path = repository / "README.md"
    original_readme = readme_path.read_text()
    readme_path.write_text(original_readme + "\nLocal test marker\n")
    commit_fixture(repository, "Test irrelevant event", "README.md")
    irrelevant = run("irrelevant-readme-push", kind="push")
    assert "No affected website routes" in irrelevant.result["summary"]
    assert store.project(account.id, project.id).last_revision == run_git(
        repository, "rev-parse", "HEAD"
    )
    data_path.write_text(original_data)
    commit_fixture(repository, "Restore fixture data", "public/resumeData.json")
    readme_path.write_text(original_readme)
    commit_fixture(repository, "Restore fixture readme", "README.md")
    report["json_data_audited"] = True
    report["irrelevant_event_skipped"] = True
    report["rules_cycle"] = "passed"
    report["repeat_created_commit"] = False
    report["rendered_title"] = re.search(r"<title>(.*?)</title>", source.read_text(), re.S).group(1)
    save()
    if not args.skip_model:
        spec.provider = ProviderConfig(
            kind="ollama",
            model=args.model,
            max_output_tokens=2048,
            capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
            ollama_num_ctx=8192,
        )
        spec.max_tool_steps = 6
        store.update_project(account.id, project.id, spec)
        model_job = run("ollama-metadata-audit")
        report["model_outcome"] = model_job.status
        report["model_published"] = model_job.result.get("stage") == "verified"
    else:
        report["model_outcome"] = "skipped"
    assert fingerprint(repository) == baseline_fingerprint
    report["react_source_preserved"] = True
    report["final_sha"] = run_git(repository, "rev-parse", "HEAD")
    report["changed_upstream_paths"] = run_git(
        repository, "diff", "--name-only", original_sha, "HEAD"
    ).splitlines()
    report["image_id"] = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", IMAGE], text=True
    ).strip()
    save()
    server.shutdown()
    server.server_close()
    store.engine.dispose()
    return 0 if report["model_outcome"] in {"complete", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
