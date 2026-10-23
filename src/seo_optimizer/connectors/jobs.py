"Durable connector jobs and periodic reconciliation using the existing project queue."

import time
from datetime import timedelta
from typing import Any
from uuid import uuid4

from seo_optimizer.connectors.models import CollectionRequest, Platform
from seo_optimizer.connectors.service import ConnectorService
from seo_optimizer.contracts import utc_now
from seo_optimizer.store import Job, Project, Store


def schedule(store: Store, project: Project, platforms: set[Platform] | None = None) -> int:
    if not project.spec.get("enabled", True):
        return 0
    service = ConnectorService(store, project)
    count = 0
    # Paid SERP and inference experiments require an explicit request and budget reservation.
    explicit = {
        Platform.AI_VISIBILITY,
        Platform.DATAFORSEO,
        Platform.SERVER_LOGS,
        Platform.DEPLOYMENT,
    }
    for p in platforms if platforms is not None else Platform:
        if p in explicit:
            continue
        state, version = service.state(p)
        if (
            not state.get("config", {}).get("enabled", False)
            or state.get("next_sync", 0) > time.time()
            or state.get("lease_until", 0) > time.time()
        ):
            continue
        due = int(state.get("next_sync", 0))
        try:
            store.enqueue(
                project.tenant_id,
                project.id,
                "connector",
                f"connector:{p.value}:{due}",
                {
                    "platform": p.value,
                    "operation": "collect",
                    "request": {
                        "start": str(utc_now().date() - timedelta(days=7)),
                        "end": str(utc_now().date() - timedelta(days=1)),
                    },
                },
            )
            state["next_sync"] = time.time() + state["config"].get("interval_seconds", 86400)
            service.save(p, state, version)
            count += 1
        except ValueError:
            continue  # Quota or a concurrent connection update must not stop other projects.

    return count


def process(
    store: Store, project: Project, job: Job, worker_id: str
) -> tuple[str, dict[str, Any], float]:
    service = ConnectorService(store, project)
    p = Platform(job.payload["platform"])
    operation = job.payload.get("operation", "collect")
    store.progress(
        project.tenant_id,
        job.id,
        worker_id,
        "Inspecting the configured platform within project policy",
    )
    if operation == "collect":
        result = service.collect(
            p, CollectionRequest.model_validate(job.payload.get("request", {}))
        )
        proposals = service.auto_propose(p, result["evidence_id"])
        if p in {Platform.GITLAB, Platform.BITBUCKET} and not job.payload.get("request", {}).get(
            "resource_id"
        ):
            inspected = 0
            for row in result["collection"]["records"][:100]:
                if not row["id"].endswith(".html"):
                    continue
                try:
                    service.check_path(row["id"])
                except ValueError:
                    continue
                if inspected >= service.spec.max_files_changed:
                    break
                inspected += 1
                source = service.collect(p, CollectionRequest(resource_id=row["id"], limit=1))
                proposals.extend(service.auto_propose(p, source["evidence_id"]))
                if len(proposals) >= service.spec.max_files_changed:
                    break
        return (
            "complete",
            {
                "summary": (
                    f"Collected {len(result['collection']['records'])} observations; "
                    f"{len(proposals)} supported proposals"
                ),
                **result,
                "proposals": proposals,
            },
            0,
        )
    if operation == "verify":
        from seo_optimizer.connectors.verification import verify_live

        result = verify_live(service, p, job.payload["proposal_id"])
    else:
        result = service.publish(p, job.payload["proposal_id"], rollback=operation == "rollback")
    return "complete", {"summary": "Connector operation recorded", "proposal": result}, 0


def enqueue(
    store: Store,
    project: Project,
    p: Platform,
    operation: str,
    request: dict[str, Any] | None = None,
    proposal_id: str = "",
) -> Job:
    if (
        operation == "collect"
        and p
        not in {
            Platform.SEARCH_CONSOLE,
            Platform.GA4,
            Platform.CLOUDFLARE,
            Platform.DATAFORSEO,
            Platform.AI_VISIBILITY,
        }
        and not (request or {}).get("resource_id")
    ):
        pending = next(
            (
                job
                for job in store.jobs(project.tenant_id, project.id)
                if job.kind == "connector"
                and job.status in {"queued", "running"}
                and job.payload.get("platform") == p.value
                and job.payload.get("operation") == "collect"
                and not job.payload.get("request", {}).get("resource_id")
            ),
            None,
        )
        if pending is not None:
            return pending
    return store.enqueue(
        project.tenant_id,
        project.id,
        "connector",
        "connector-request:" + str(uuid4()),
        {
            "platform": p.value,
            "operation": operation,
            "request": request or {},
            "proposal_id": proposal_id,
        },
    )


def reconcile(store: Store, tenant: str | None = None) -> int:
    grouped: dict[tuple[str, str], set[Platform]] = {}
    for owner, project_id, platform in store.connector_due(tenant):
        grouped.setdefault((owner, project_id), set()).add(Platform(platform))
    scheduled = 0
    for (owner, project_id), platforms in grouped.items():
        project = store.project(owner, project_id)
        if project is not None:
            scheduled += schedule(store, project, platforms)
    return scheduled
