"""Outbound-only local worker connection, scoped to one account's token."""

from typing import Any
from urllib.parse import urlparse

import httpx

from seo_optimizer.application_models import ProjectSecrets
from seo_optimizer.growth import Workspace
from seo_optimizer.settings import Settings
from seo_optimizer.store import Job, Project, Store


class RemoteStore(Store):
    def __init__(self, settings: Settings, control_url: str, token: str):
        parts = urlparse(control_url)
        if parts.scheme != "https" and parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Remote control plane requires HTTPS")
        if not token:
            raise ValueError("OPT_WORKER_TOKEN is required")
        self.settings = settings
        self.client = httpx.Client(
            base_url=control_url.rstrip("/"),
            timeout=30,
            headers={"Authorization": "Bearer " + token},
            follow_redirects=False,
        )
        self._projects: dict[tuple[str, str], Project] = {}
        self._credentials: dict[str, ProjectSecrets] = {}

    def reconcile(self, tenant: str | None = None) -> int:
        response = self.client.post("/api/v1/reconcile")
        response.raise_for_status()
        return int(response.json()["scheduled"])

    def claim(self, worker: str, tenant: str | None = None) -> Job | None:
        response = self.client.post("/api/v1/worker/claim", json={"worker_id": worker})
        response.raise_for_status()
        value = response.json()
        if value is None:
            return None
        job = Job(**value["job"])
        project = Project(**value["project"], tenant_id=job.tenant_id, credentials="", next_audit=0)
        self._projects[(job.tenant_id, project.id)] = project
        self._credentials[project.id] = ProjectSecrets.model_validate(value["credentials"])
        return job

    def project(self, tenant: str, id: str) -> Project | None:
        return self._projects.get((tenant, id))

    def secrets(self, project: Project) -> ProjectSecrets:
        return self._credentials[project.id]

    def workspace(self, tenant: str, project_id: str) -> Workspace:
        if self.project(tenant, project_id) is None:
            raise ValueError("Project not found")
        response = self.client.get(f"/api/v1/projects/{project_id}/workspace")
        response.raise_for_status()
        return Workspace.model_validate(response.json())

    def finish(
        self,
        tenant: str,
        id: str,
        worker: str,
        status: str,
        result: dict[str, Any],
        delay: float = 0,
    ) -> None:
        response = self.client.post(
            f"/api/v1/worker/jobs/{id}/finish",
            json={"worker_id": worker, "status": status, "result": result, "delay": delay},
        )
        response.raise_for_status()

    def remember_findings(
        self, tenant: str, project_id: str, findings: list[dict[str, Any]], audited_urls: list[str]
    ) -> int:
        response = self.client.post(
            "/api/v1/worker/findings",
            json={"project_id": project_id, "findings": findings, "audited_urls": audited_urls},
        )
        response.raise_for_status()
        return int(response.json()["fresh"])

    def enqueue(
        self, tenant: str, project_id: str, kind: str, key: str, payload: dict[str, Any]
    ) -> Job:
        response = self.client.post(
            "/api/v1/worker/enqueue",
            json={"project_id": project_id, "kind": kind, "key": key, "payload": payload},
        )
        response.raise_for_status()
        return Job(**response.json())
