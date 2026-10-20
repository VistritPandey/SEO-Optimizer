"""Managed build checks in a separate, credential-free Docker child container.

The control service submits only a server-generated build configuration. Repository
commands execute without networking, write access, host mounts or cloud credentials.
Cloud Build's orchestration identity can read the temporary source bucket and write
logs; it has no application database or Secret Manager permissions.
"""

import io
import os
import tarfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from seo_optimizer.application_models import ProjectSpec


@dataclass
class Scope:
    tenant: str
    job: str
    count: int = 0


SCOPE: ContextVar[Scope | None] = ContextVar("build_verification_scope", default=None)


@contextmanager
def verification_scope(tenant: str, job: str) -> Iterator[None]:
    token = SCOPE.set(Scope(tenant, job))
    try:
        yield
    finally:
        SCOPE.reset(token)


def archive_source(root: Path) -> bytes:
    output = io.BytesIO()
    total = 0
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if any(
                part in {".git", ".venv", "node_modules", ".data", "__pycache__"}
                or part.startswith(".env")
                for part in relative.parts
            ):
                continue
            if path.is_symlink():
                raise ValueError("Build source cannot contain symlinks")
            if not path.is_file():
                continue
            total += path.stat().st_size
            if total > 50_000_000:
                raise ValueError("Build source exceeds fifty megabytes")
            info = archive.gettarinfo(str(path), arcname=str(relative))
            info.uid, info.gid, info.uname, info.gname = 65534, 65534, "", ""
            info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
            with path.open("rb") as handle:
                archive.addfile(info, handle)
    return output.getvalue()


def build_config(
    spec: ProjectSpec,
    project: str,
    bucket: str,
    object_name: str,
    service_account: str,
    tenant: str,
    job: str,
) -> dict[str, Any]:
    if not spec.check_commands or any(not command for command in spec.check_commands):
        raise ValueError("Cloud verification needs explicit check commands")
    steps = []
    for index, command in enumerate(spec.check_commands):
        steps.append(
            {
                "id": f"verify-{index}",
                "name": "gcr.io/cloud-builders/docker",
                "args": [
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
                    "type=bind,source=/workspace,target=/source,readonly",
                    "--workdir",
                    "/source",
                    spec.sandbox_image,
                    *command,
                ],
            }
        )
    return {
        "source": {"storage_source": {"bucket": bucket, "object_": object_name}},
        "steps": steps,
        "timeout": {"seconds": 180},
        "queue_ttl": {"seconds": 60},
        "service_account": f"projects/{project}/serviceAccounts/{service_account}",
        "options": {"logging": "CLOUD_LOGGING_ONLY"},
        "tags": ["your-optimiser", "tenant-" + tenant, "job-" + job],
    }


def verify_cloud(root: Path, spec: ProjectSpec) -> list[dict[str, Any]]:
    from google.api_core.exceptions import GoogleAPICallError
    from google.cloud import storage  # type: ignore[attr-defined]
    from google.cloud.devtools import cloudbuild_v1

    scope = SCOPE.get()
    if scope is None:
        raise ValueError("Cloud verification requires a tenant/job scope")
    scope.count += 1
    if scope.count > min(5, max(1, int(os.getenv("OPT_BUILD_MAX_PER_JOB", "3")))):
        raise ValueError("Cloud build verification budget exhausted")
    project, bucket, account = (
        os.getenv(name, "")
        for name in ("GOOGLE_CLOUD_PROJECT", "OPT_BUILD_BUCKET", "OPT_BUILD_ACCOUNT")
    )
    if not all((project, bucket, account)):
        raise ValueError("Cloud build verification is not configured")
    region = os.getenv("OPT_BUILD_REGION", "us-central1")
    object_name = f"checks/{scope.tenant}/{scope.job}/{uuid4()}.tar.gz"
    storage_client = storage.Client(project=project)
    build_client = cloudbuild_v1.CloudBuildClient(
        client_options={"api_endpoint": f"{region}-cloudbuild.googleapis.com"}
    )
    blob = storage_client.bucket(bucket).blob(object_name)
    started = time.monotonic()
    operation: Any = None
    submitted, terminal = False, False
    try:
        blob.upload_from_string(archive_source(root), content_type="application/gzip", timeout=30)
        submitted = True
        operation = build_client.create_build(
            request={
                "parent": f"projects/{project}/locations/{region}",
                "project_id": project,
                "build": build_config(
                    spec, project, bucket, object_name, account, scope.tenant, scope.job
                ),
            },
            timeout=30,
        )
        build = operation.result(timeout=260)
        terminal = build.status not in {
            cloudbuild_v1.Build.Status.STATUS_UNKNOWN,
            cloudbuild_v1.Build.Status.PENDING,
            cloudbuild_v1.Build.Status.QUEUED,
            cloudbuild_v1.Build.Status.WORKING,
        }
        if not terminal:
            raise ValueError("Cloud verification has not reached a terminal result")
        passed = build.status == cloudbuild_v1.Build.Status.SUCCESS
        checks = [
            {
                "name": "Isolated Cloud Build verification",
                "passed": passed,
                "build_id": build.id,
                "log_url": build.log_url,
                "status": cloudbuild_v1.Build.Status(build.status).name,
                "runtime_ms": round((time.monotonic() - started) * 1000),
                "cloud_cost_usd": None,
                "scope": {"tenant_id": scope.tenant, "job_id": scope.job},
            }
        ]
        if not passed:
            from seo_optimizer.execution import VerificationFailure

            raise VerificationFailure(checks)
        return checks
    except TimeoutError as error:
        if operation is not None and getattr(operation.metadata, "build", None):
            build_client.cancel_build(request={"name": operation.metadata.build.name})
        raise ValueError("Cloud verification exceeded its time budget") from error
    except GoogleAPICallError as error:
        raise ValueError("Cloud verification service is unavailable") from error
    finally:
        try:
            if terminal or not submitted:
                blob.delete(timeout=15)
        except GoogleAPICallError:
            pass  # The required bucket lifecycle removes orphaned source objects.
        finally:
            storage_client.close()
            build_client.transport.close()  # type: ignore[no-untyped-call]
