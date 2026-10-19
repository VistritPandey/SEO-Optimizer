"""Provision one Cloud Run service plus managed storage, task delivery and isolated checks."""

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml
from dotenv import dotenv_values

from seo_optimizer.settings import validate_firestore_database

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CONFIG = (
    "NEXT_PUBLIC_FIREBASE_API_KEY",
    "NEXT_PUBLIC_FIREBASE_PROJECT_ID",
    "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN",
    "NEXT_PUBLIC_FIREBASE_APP_ID",
)


class DeployError(Exception):
    pass


def configuration(config: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for source in (ROOT / ".env", ROOT / "frontend/.env.local", config):
        if source.exists():
            result.update({k: v for k, v in dotenv_values(source, interpolate=False).items() if v})
    result.update(os.environ)
    defaults = {
        "REGION": "us-central1",
        "SERVICE_NAME": "your-optimiser",
        "MEMORY": "2Gi",
        "CPU": "1",
        "MAX_INSTANCES": "1",
        "MANAGED_PROVIDER": "google",
        "MANAGED_MODEL": "gemini-3.8-flash",
        "RECONCILE_SCHEDULE": "0 * * * *",
    }
    for key, value in defaults.items():
        result.setdefault(key, value)
    if not result.get("PROJECT_ID"):
        result["PROJECT_ID"] = result.get("GOOGLE_CLOUD_PROJECT", "")
    missing = [
        k
        for k in (
            "PROJECT_ID",
            "OPT_FIRESTORE_DATABASE",
            "GITHUB_APP_ID",
            "GITHUB_APP_SLUG",
            "GITHUB_CLIENT_ID",
            *PUBLIC_CONFIG,
        )
        if not result.get(k)
    ]
    if missing:
        raise DeployError("Missing configuration: " + ", ".join(missing))
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", result["PROJECT_ID"]):
        raise DeployError("PROJECT_ID must explicitly identify the intended Google Cloud project")
    if result["NEXT_PUBLIC_FIREBASE_PROJECT_ID"] != result["PROJECT_ID"]:
        raise DeployError("Firebase and Cloud deployment must use the same project")
    try:
        validate_firestore_database(result["OPT_FIRESTORE_DATABASE"])
    except ValueError as error:
        raise DeployError(str(error)) from error
    for key in ("SERVICE_NAME", "REGION"):
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", result[key]):
            raise DeployError(f"Invalid {key}")
    if not result["CPU"].isdigit() or not 1 <= int(result["CPU"]) <= 2:
        raise DeployError("CPU must be 1 or 2 for this beta configuration")
    if not result["MAX_INSTANCES"].isdigit() or not 1 <= int(result["MAX_INSTANCES"]) <= 3:
        raise DeployError("MAX_INSTANCES must be between 1 and 3")
    if len(result["PROJECT_ID"] + "-" + result["SERVICE_NAME"] + "-checks") > 63:
        raise DeployError("SERVICE_NAME is too long for the source-check bucket name")
    if result["MEMORY"] not in {"2Gi", "4Gi"}:
        raise DeployError("MEMORY must be 2Gi or 4Gi for combined browser/agent work")
    if result["MANAGED_PROVIDER"] not in {"google", "openai", "anthropic"}:
        raise DeployError("Unsupported MANAGED_PROVIDER")
    if len(result["RECONCILE_SCHEDULE"].split()) != 5:
        raise DeployError("RECONCILE_SCHEDULE must be a five-field cron expression")
    if result.get("SITE_URL"):
        url = urlparse(result["SITE_URL"])
        if url.scheme != "https" or not url.hostname or url.path not in {"", "/"} or url.query:
            raise DeployError("SITE_URL must be an HTTPS origin")
        result["SITE_URL"] = result["SITE_URL"].rstrip("/")
    return result


def secret_specs(c: dict[str, str]) -> list[tuple[str, str, str]]:
    prefix = c["SERVICE_NAME"]
    provider_key = c.get("OPT_MANAGED_API_KEY") or c.get(
        {
            "google": "GOOGLE_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }[c["MANAGED_PROVIDER"]],
        "",
    )
    pem = c.get("GITHUB_PRIVATE_KEY", "").replace("\\n", "\n")
    if c.get("GITHUB_PRIVATE_KEY_FILE"):
        pem = Path(c["GITHUB_PRIVATE_KEY_FILE"]).expanduser().read_text()
    specs = [
        (
            "OPT_SECRET_KEY",
            c.get("APP_SECRET_RESOURCE", prefix + "-app-key"),
            c.get("OPT_SECRET_KEY", ""),
        ),
        (
            "OPT_MANAGED_API_KEY",
            c.get("MODEL_SECRET_RESOURCE", prefix + "-model-key"),
            provider_key,
        ),
        ("GITHUB_PRIVATE_KEY", c.get("GITHUB_KEY_RESOURCE", prefix + "-github-pem"), pem),
        (
            "GITHUB_CLIENT_SECRET",
            c.get("GITHUB_OAUTH_RESOURCE", prefix + "-github-oauth"),
            c.get("GITHUB_CLIENT_SECRET", ""),
        ),
        (
            "GITHUB_WEBHOOK_SECRET",
            c.get("GITHUB_WEBHOOK_RESOURCE", prefix + "-webhook"),
            c.get("GITHUB_WEBHOOK_SECRET", ""),
        ),
    ]
    for _, resource, _ in specs:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,254}", resource):
            raise DeployError("Invalid Secret Manager resource name")
    if len({resource for _, resource, _ in specs}) != len(specs):
        raise DeployError("Each credential needs a distinct Secret Manager resource")
    return specs


class Cloud:
    def __init__(self, project: str):
        self.project = project

    def run(self, *args: str, stdin: str | None = None) -> str:
        command = ["gcloud", *args, "--project=" + self.project, "--quiet"]
        result = subprocess.run(command, input=stdin, text=True, capture_output=True)
        if result.returncode:
            # Command arguments contain only public configuration/resource names, never keys.
            raise DeployError("gcloud " + " ".join(args[:3]) + " failed: " + result.stderr[-2500:])
        return result.stdout.strip()

    def exists(self, *args: str) -> bool:
        result = subprocess.run(
            ["gcloud", *args, "--project=" + self.project, "--quiet"],
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            return True
        message = result.stderr.lower()
        denied = any(
            code in message
            for code in ("permission_denied", "permission denied", "unauthenticated")
        )
        if not denied and any(
            code in message
            for code in (
                "not_found",
                "not found",
                "does not exist",
                "cannot find",
                "could not find",
            )
        ):
            return False
        raise DeployError("Could not inspect resource: " + result.stderr[-1000:])

    def grant(self, account: str, role: str) -> None:
        self.run(
            "projects",
            "add-iam-policy-binding",
            self.project,
            "--member=serviceAccount:" + account,
            "--role=" + role,
        )


def build_config(c: dict[str, str], image: str, site: str, builder: str) -> dict[str, Any]:
    args = ["build", "--file", "deploy/combined.Dockerfile", "--tag", image]
    for key in PUBLIC_CONFIG:
        args += ["--build-arg", key + "=" + c[key]]
    args += ["--build-arg", "NEXT_PUBLIC_SITE_URL=" + site, "."]
    return {
        "steps": [{"name": "gcr.io/cloud-builders/docker", "args": args}],
        "images": [image],
        "timeout": "1800s",
        "serviceAccount": "projects/" + c["PROJECT_ID"] + "/serviceAccounts/" + builder,
        "options": {"logging": "CLOUD_LOGGING_ONLY"},
    }


def deploy(c: dict[str, str], cloud: Cloud) -> str:
    project, region, name = c["PROJECT_ID"], c["REGION"], c["SERVICE_NAME"]
    app, checks, builder, delivery = (
        f"{label}@{project}.iam.gserviceaccount.com"
        for label in ("optimiser-app", "optimiser-checks", "optimiser-image", "optimiser-tasks")
    )
    queue_name, bucket = name + "-work", project + "-" + name + "-checks"
    specs = secret_specs(c)
    print(f"Deploying {name} to {project} / {region}", flush=True)
    cloud.run(
        "services",
        "enable",
        "run.googleapis.com",
        "iam.googleapis.com",
        "iamcredentials.googleapis.com",
        "cloudresourcemanager.googleapis.com",
        "cloudtasks.googleapis.com",
        "artifactregistry.googleapis.com",
        "cloudbuild.googleapis.com",
        "firestore.googleapis.com",
        "secretmanager.googleapis.com",
        "cloudscheduler.googleapis.com",
        "identitytoolkit.googleapis.com",
    )
    # Validate every initial credential before creating resources or a partial deployment.
    new_secrets = []
    for key, resource, value in specs:
        if cloud.exists("secrets", "describe", resource):
            if not cloud.exists(
                "secrets", "versions", "describe", "latest", "--secret=" + resource
            ):
                raise DeployError(f"Secret {resource} has no usable version")
            continue
        if not value and key in {"OPT_SECRET_KEY", "GITHUB_WEBHOOK_SECRET"}:
            value = secrets.token_urlsafe(48)
        if not value:
            raise DeployError(f"Supply {key} or create Secret Manager secret {resource} first")
        if key == "OPT_SECRET_KEY" and len(value) < 32:
            raise DeployError("OPT_SECRET_KEY must have at least 32 characters")
        if key == "GITHUB_PRIVATE_KEY" and "PRIVATE KEY-----" not in value:
            raise DeployError("GITHUB_PRIVATE_KEY must be a PEM private key")
        new_secrets.append((resource, value))
    for resource, value in new_secrets:
        cloud.run(
            "secrets",
            "create",
            resource,
            "--replication-policy=automatic",
            "--data-file=-",
            stdin=value,
        )
    for account in (app, checks, builder, delivery):
        if not cloud.exists("iam", "service-accounts", "describe", account):
            cloud.run("iam", "service-accounts", "create", account.split("@")[0])
    for role in (
        "roles/datastore.user",
        "roles/firebaseauth.viewer",
        "roles/cloudbuild.builds.editor",
    ):
        cloud.grant(app, role)
    for role in (
        "roles/logging.logWriter",
        "roles/artifactregistry.writer",
        "roles/storage.objectViewer",
    ):
        cloud.grant(builder, role)
    cloud.grant(checks, "roles/logging.logWriter")
    for account in (checks, delivery):
        cloud.run(
            "iam",
            "service-accounts",
            "add-iam-policy-binding",
            account,
            "--member=serviceAccount:" + app,
            "--role=roles/iam.serviceAccountUser",
        )
    for _, resource, _ in specs:
        cloud.run(
            "secrets",
            "add-iam-policy-binding",
            resource,
            "--member=serviceAccount:" + app,
            "--role=roles/secretmanager.secretAccessor",
        )
    if not cloud.exists("artifacts", "repositories", "describe", name, "--location=" + region):
        cloud.run(
            "artifacts",
            "repositories",
            "create",
            name,
            "--location=" + region,
            "--repository-format=docker",
        )
    database = c["OPT_FIRESTORE_DATABASE"]
    if not cloud.exists("firestore", "databases", "describe", "--database=" + database):
        cloud.run(
            "firestore",
            "databases",
            "create",
            "--database=" + database,
            "--location=" + region,
            "--type=firestore-native",
        )
    if not cloud.exists("storage", "buckets", "describe", "gs://" + bucket):
        cloud.run(
            "storage",
            "buckets",
            "create",
            "gs://" + bucket,
            "--location=" + region,
            "--uniform-bucket-level-access",
            "--public-access-prevention",
        )
    cloud.run(
        "storage",
        "buckets",
        "update",
        "gs://" + bucket,
        "--lifecycle-file=" + str(ROOT / "deploy/source-lifecycle.json"),
    )
    for account, role in (
        (app, "roles/storage.objectAdmin"),
        (checks, "roles/storage.objectViewer"),
    ):
        cloud.run(
            "storage",
            "buckets",
            "add-iam-policy-binding",
            "gs://" + bucket,
            "--member=serviceAccount:" + account,
            "--role=" + role,
        )
    operation = (
        "update"
        if cloud.exists("tasks", "queues", "describe", queue_name, "--location=" + region)
        else "create"
    )
    cloud.run(
        "tasks",
        "queues",
        operation,
        queue_name,
        "--location=" + region,
        "--max-concurrent-dispatches=1",
        "--max-dispatches-per-second=1",
        "--max-attempts=5",
        "--min-backoff=30s",
        "--max-backoff=900s",
        "--max-retry-duration=3600s",
    )
    cloud.run(
        "tasks",
        "queues",
        "add-iam-policy-binding",
        queue_name,
        "--location=" + region,
        "--member=serviceAccount:" + app,
        "--role=roles/cloudtasks.enqueuer",
    )
    # Bootstrap the stable run.app URL without exposing a placeholder application.
    if cloud.exists("run", "services", "describe", name, "--region=" + region):
        service_url = cloud.run(
            "run", "services", "describe", name, "--region=" + region, "--format=value(status.url)"
        )
    else:
        number = cloud.run("projects", "describe", project, "--format=value(projectNumber)")
        service_url = f"https://{name}-{number}.{region}.run.app"
    site = c.get("SITE_URL", service_url)
    env = {
        "OPT_ENV": "production",
        "OPT_HOSTED": "1",
        "OPT_STORAGE": "firestore",
        "OPT_FIRESTORE_DATABASE": database,
        "GOOGLE_CLOUD_PROJECT": project,
        "OPT_REGISTRATION": "0",
        "OPT_DATA_DIR": "/tmp/optimiser",
        "OPT_PUBLIC_URL": site,
        "OPT_FRONTEND_URL": site,
        "OPT_TASKS_AUDIENCE": service_url,
        "OPT_TASKS_ACCOUNT": delivery,
        "OPT_TASKS_QUEUE": f"projects/{project}/locations/{region}/queues/{queue_name}",
        "OPT_MANAGED_PROVIDER": c["MANAGED_PROVIDER"],
        "OPT_MANAGED_MODEL": c["MANAGED_MODEL"],
        "GITHUB_APP_ID": c["GITHUB_APP_ID"],
        "GITHUB_APP_SLUG": c["GITHUB_APP_SLUG"],
        "GITHUB_CLIENT_ID": c["GITHUB_CLIENT_ID"],
        "OPT_BUILD_BACKEND": "cloud-build",
        "OPT_BUILD_BUCKET": bucket,
        "OPT_BUILD_ACCOUNT": checks,
        "OPT_BUILD_REGION": region,
        "OPT_BUILD_MAX_PER_JOB": "3",
    }
    image = f"{region}-docker.pkg.dev/{project}/{name}/app:{secrets.token_hex(6)}"
    with tempfile.TemporaryDirectory(prefix="optimiser-deploy-") as folder:
        build = Path(folder) / "build.json"
        build.write_text(json.dumps(build_config(c, image, site, builder)))
        environment = Path(folder) / "runtime.yaml"
        environment.write_text(yaml.safe_dump(env))
        firebase_config = Path(folder) / "firebase.json"
        for filename in ("firestore.rules", "firestore.indexes.json"):
            shutil.copyfile(ROOT / "deploy" / filename, Path(folder) / filename)
        firebase_config.write_text(
            json.dumps(
                {
                    "firestore": [
                        {
                            "database": database,
                            "rules": "firestore.rules",
                            "indexes": "firestore.indexes.json",
                        }
                    ]
                }
            )
        )
        print("Building the combined container (first build includes Chromium).", flush=True)
        cloud.run(
            "builds",
            "submit",
            str(ROOT),
            "--region=" + region,
            "--config=" + str(build),
            "--default-buckets-behavior=regional-user-owned-bucket",
        )
        subprocess.run(
            [
                "firebase",
                "deploy",
                "--only",
                "firestore",
                "--project",
                project,
                "--config",
                str(firebase_config),
                "--non-interactive",
            ],
            cwd=ROOT,
            check=True,
        )
        print("Deploying one web service and the authenticated task handler.", flush=True)
        cloud.run(
            "run",
            "deploy",
            name,
            "--region=" + region,
            "--image=" + image,
            "--service-account=" + app,
            "--allow-unauthenticated",
            "--port=8080",
            "--memory=" + c["MEMORY"],
            "--cpu=" + c["CPU"],
            "--min-instances=0",
            "--max-instances=" + c["MAX_INSTANCES"],
            "--concurrency=8",
            "--timeout=1250s",
            "--cpu-throttling",
            "--env-vars-file=" + str(environment),
            "--set-secrets=" + ",".join(f"{key}={resource}:latest" for key, resource, _ in specs),
        )
    cloud.run(
        "run",
        "services",
        "add-iam-policy-binding",
        name,
        "--region=" + region,
        "--member=serviceAccount:" + delivery,
        "--role=roles/run.invoker",
    )
    scheduler = name + "-reconcile"
    operation = (
        "update"
        if cloud.exists("scheduler", "jobs", "describe", scheduler, "--location=" + region)
        else "create"
    )
    cloud.run(
        "scheduler",
        "jobs",
        operation,
        "http",
        scheduler,
        "--location=" + region,
        "--schedule=" + c["RECONCILE_SCHEDULE"],
        "--time-zone=Etc/UTC",
        "--uri=" + service_url + "/api/v1/internal/wake",
        "--http-method=POST",
        "--oidc-service-account-email=" + delivery,
        "--oidc-token-audience=" + service_url,
    )
    with httpx.Client(timeout=60) as client:
        response = client.get(service_url + "/healthz")
        if response.status_code != 200 or response.json().get("status") != "ready":
            raise DeployError("Deployment finished but the API health check failed")
        response = client.get(service_url + "/")
        if response.status_code != 200 or "Your Optimiser" not in response.text:
            raise DeployError("Deployment finished but the frontend smoke check failed")
    print(
        f"\nDeployed: {site}\nGitHub callback: {site}/api/v1/github/callback\n"
        f"GitHub webhook: {site}/webhooks/github\n"
        "Finish Firebase Auth providers/authorized domains and GitHub App URLs in their consoles.\n"
        "The webhook secret is in Secret Manager; existing encryption keys were preserved.\n"
        "Live sign-in and GitHub PR verification are still required before inviting users."
    )
    return site


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / ".env.deploy")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate config and show plan; no cloud calls"
    )
    args = parser.parse_args()
    try:
        config = configuration(args.config.expanduser().resolve())
        secret_specs(config)
        if args.dry_run:
            print(
                json.dumps(
                    {
                        "project": config["PROJECT_ID"],
                        "region": config["REGION"],
                        "service": config["SERVICE_NAME"],
                        "firestore_database": config["OPT_FIRESTORE_DATABASE"],
                        "min_instances": 0,
                        "max_instances": int(config["MAX_INSTANCES"]),
                        "resources": [
                            "one Cloud Run service",
                            "Cloud Tasks queue",
                            "hourly Scheduler wake-up (configurable)",
                            "Firestore",
                            "Secret Manager",
                            "Artifact Registry",
                            "Cloud Build",
                        ],
                        "mutations": False,
                        "secret_values": "never printed or embedded in images",
                    },
                    indent=2,
                )
            )
            return 0
        for binary in ("gcloud", "firebase"):
            if not shutil.which(binary):
                raise DeployError(f"Install and sign in to {binary} before deploying")
        deploy(config, Cloud(config["PROJECT_ID"]))
        return 0
    except (DeployError, OSError, subprocess.SubprocessError, httpx.HTTPError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
