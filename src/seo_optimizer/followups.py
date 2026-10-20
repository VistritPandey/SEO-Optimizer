"""Signed GitHub events: coalesced branch audits and bounded, authorized PR follow-ups."""

import json
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.github import GitHubClient, verify_signature
from seo_optimizer.settings import Settings
from seo_optimizer.store import Project, Store


def merge_key(project: Project, sha: str) -> str:
    return f"repair-merge:{project.tenant_id}:{project.id}:{sha}"


def register_project(store: Store, project: Project) -> None:
    credentials = store.secrets(project)
    if not credentials.github_installation_id:
        return
    key = "installation:" + credentials.github_installation_id
    for _ in range(20):
        value, version = store.state(key)
        projects = value.get("projects", [])
        entry = {"tenant": project.tenant_id, "project": project.id}
        if entry in projects or store.save_state(key, {"projects": [*projects, entry]}, version):
            return
    raise ValueError("Connection registry contention")


def handle_event(
    store: Store, project: Project, event: str, payload: dict[str, Any], delivery: str
) -> dict[str, Any]:
    spec = ProjectSpec.model_validate(project.spec)
    if not spec.enabled:
        return {"status": "paused"}
    if payload.get("repository", {}).get("full_name") != spec.repository:
        raise HTTPException(403, "Repository does not match this connection")
    if event == "deployment_status":
        deployment = payload.get("deployment", {})
        status = payload.get("deployment_status", {})
        if (
            status.get("state") != "success"
            or str(deployment.get("environment", "")).casefold() != spec.environment.casefold()
        ):
            return {"status": "ignored"}
        from seo_optimizer.web import re_sha

        sha = str(deployment.get("sha", ""))
        if not re_sha(sha):
            raise HTTPException(400, "Invalid deployment revision")
        if store.state(merge_key(project, sha))[0]:
            return {"status": "own_change_suppressed"}
        # A push audit can precede deployment. Recollect the served site even if
        # its source revision was already audited; worker head checks reject stale events.
        job = store.enqueue(
            project.tenant_id,
            project.id,
            "audit",
            "deployed:" + sha + ":" + spec.environment.casefold(),
            {
                "after": sha,
                "trigger": "successful_deployment",
                "deployment_id": deployment.get("id"),
            },
        )
        return {"status": "queued", "job_id": job.id}
    if (
        event == "push"
        and payload.get("ref") == "refs/heads/" + spec.branch
        and not payload.get("deleted")
    ):
        from seo_optimizer.web import re_sha

        sha = str(payload.get("after", ""))
        if not re_sha(sha):
            raise HTTPException(400, "Invalid revision")
        if store.state(merge_key(project, sha))[0] or any(
            job.result.get("merged_sha") == sha for job in store.jobs(project.tenant_id, project.id)
        ):
            return {"status": "own_change_suppressed"}
        job = store.enqueue(
            project.tenant_id,
            project.id,
            "push",
            "push:" + sha,
            {"before": payload.get("before"), "after": sha},
        )
        return {"status": "queued", "job_id": job.id}
    feedback = ""
    number = 0
    if (
        event == "issue_comment"
        and payload.get("action") == "created"
        and payload.get("issue", {}).get("pull_request")
    ):
        number = int(payload["issue"]["number"])
        feedback = str(payload.get("comment", {}).get("body", ""))
    elif event == "pull_request_review_comment" and payload.get("action") == "created":
        number = int(payload.get("pull_request", {}).get("number", 0))
        feedback = str(payload.get("comment", {}).get("body", ""))
    elif (
        event == "pull_request_review"
        and payload.get("action") == "submitted"
        and payload.get("review", {}).get("state") == "changes_requested"
    ):
        number = int(payload.get("pull_request", {}).get("number", 0))
        feedback = str(payload.get("review", {}).get("body", ""))
    elif (
        event == "pull_request"
        and payload.get("action") == "closed"
        and payload.get("pull_request", {}).get("merged")
    ):
        number = int(payload["pull_request"]["number"])
    else:
        return {"status": "ignored"}
    tracked = store.pr_job(project.tenant_id, project.id, number)
    if tracked is None:
        return {"status": "untracked_pull_request"}
    if event == "pull_request":
        pull = payload["pull_request"]
        sha = str(pull.get("merge_commit_sha", ""))
        from seo_optimizer.web import re_sha

        if (
            re_sha(sha)
            and pull.get("head", {}).get("sha") == tracked.result.get("pr", {}).get("head_sha")
            and pull.get("base", {}).get("ref") == spec.branch
        ):
            key = merge_key(project, sha)
            for _ in range(3):
                value, version = store.state(key)
                if value or store.save_state(key, {"origin": tracked.id, "pr": number}, version):
                    break
        job = store.enqueue(
            project.tenant_id,
            project.id,
            "pull_request",
            "merged:" + str(number),
            {"origin": tracked.id, "pr_number": number},
        )
        return {"status": "queued", "job_id": job.id}
    sender = payload.get("sender", {})
    if sender.get("type") != "User" or not feedback.strip():
        return {"status": "ignored"}
    client = GitHubClient(store.secrets(project))
    try:
        permission = client.request(
            "GET", f"/repos/{spec.repository}/collaborators/{sender['login']}/permission"
        )
        if permission.get("permission") not in {"write", "maintain", "admin"}:
            return {"status": "unauthorized_reviewer"}
        pull = client.request("GET", f"/repos/{spec.repository}/pulls/{number}")
        if (
            pull.get("state") != "open"
            or pull["head"]["repo"]["full_name"] != spec.repository
            or not pull["head"]["ref"].startswith("optimizer/")
        ):
            return {"status": "closed_or_foreign_pull_request"}
    finally:
        client.close()
    if not delivery:
        delivery = str(payload.get("comment", payload.get("review", {})).get("id", ""))
    if not delivery or not store.reserve_review(project.tenant_id, project.id, number, delivery):
        return {"status": "followup_limit"}
    job = store.enqueue(
        project.tenant_id,
        project.id,
        "followup",
        "review:" + delivery,
        {
            "origin": tracked.id,
            "pr_number": number,
            "feedback": feedback[:8000],
            "head_sha": pull["head"]["sha"],
            "branch": pull["head"]["ref"],
        },
    )
    return {"status": "queued", "job_id": job.id}


def install_webhook(app: FastAPI, store: Store, settings: Settings) -> None:
    @app.post("/webhooks/github")
    async def app_webhook(request: Request) -> dict[str, Any]:
        raw = await request.body()
        if not verify_signature(
            settings.github_webhook_secret, raw, request.headers.get("x-hub-signature-256", "")
        ):
            raise HTTPException(403, "Webhook signature is invalid")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid webhook body") from None
        if not isinstance(payload, dict):
            raise HTTPException(400, "Invalid webhook payload")
        installation = str(payload.get("installation", {}).get("id", ""))
        registry, _ = store.state("installation:" + installation)
        event = request.headers.get("x-github-event", "")
        result = []
        for entry in registry.get("projects", []):
            project = store.project(entry["tenant"], entry["project"])
            if project is None or store.secrets(project).github_installation_id != installation:
                continue
            if event in {"installation", "installation_repositories"}:
                revoked = payload.get("action") in {"deleted", "suspend"} or any(
                    repo.get("full_name") == project.spec.get("repository")
                    for repo in payload.get("repositories_removed", [])
                )
                if revoked:
                    spec = ProjectSpec.model_validate(project.spec)
                    spec.enabled = False
                    credentials = store.secrets(project)
                    credentials.github_installation_id = ""
                    store.update_project(project.tenant_id, project.id, spec, credentials)
                    key = "github-repo:" + project.tenant_id + ":" + spec.repository
                    _, version = store.state(key)
                    store.save_state(key, {}, version)
                continue
            if payload.get("repository", {}).get("full_name") == project.spec.get("repository"):
                result.append(
                    handle_event(
                        store, project, event, payload, request.headers.get("x-github-delivery", "")
                    )
                )
        return {"results": result}
