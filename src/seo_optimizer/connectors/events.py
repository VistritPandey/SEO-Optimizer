"Authenticated, replay-safe deployment and repository events. Public payloads are untrusted."

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlparse

from seo_optimizer.connectors.models import DeploymentEvent, Platform
from seo_optimizer.connectors.service import REPOSITORIES, ConnectorService
from seo_optimizer.connectors.transport import ConnectorError
from seo_optimizer.contracts import utc_now
from seo_optimizer.scanner import affected_urls


def signature(secret: str, timestamp: str, body: bytes) -> str:
    return (
        "sha256="
        + hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    )


def handle(
    service: ConnectorService, p: Platform, headers: dict[str, str], raw: bytes
) -> dict[str, Any]:
    state, version = service.state(p)
    config = state.get("config", {})
    secret = config.get("credentials", {}).get("webhook_secret", "")
    if not config.get("enabled") or not secret:
        raise ConnectorError("signature", "Event access is not configured")
    stamp = headers.get("x-optimiser-timestamp", "")
    if (
        not stamp.isdigit()
        or abs(time.time() - int(stamp)) > 300
        or not hmac.compare_digest(
            signature(secret, stamp, raw), headers.get("x-optimiser-signature", "")
        )
    ):
        raise ConnectorError("signature", "Event signature is invalid or expired")
    event = DeploymentEvent.model_validate_json(raw)
    if event.resource != config.get("resource") or event.environment != service.spec.environment:
        return {"ignored": "Event belongs to another resource or environment"}
    if abs((utc_now() - event.occurred_at).total_seconds()) > 3600:
        return {"ignored": "Event observation is stale"}
    parsed = urlparse(event.url)
    website = urlparse(str(service.spec.website_url))
    if (parsed.scheme, parsed.netloc) != (website.scheme, website.netloc):
        raise ConnectorError("policy", "Deployment URL is outside the project origin")
    if event.status != "succeeded":
        return {"ignored": "Failed deployments do not trigger verification"}
    if state.get("lease_until", 0) > time.time():
        raise ConnectorError("busy", "Connection operation is running; redeliver later")
    seen = state.get("event_ids", [])
    if event.event_id in seen:
        return {"duplicate": True}
    epoch = event.occurred_at.timestamp()
    if epoch < state.get("last_deployment_at", 0):
        return {"ignored": "Out-of-order deployment"}
    if event.changed_paths and affected_urls(service.spec, event.changed_paths) == []:
        result: dict[str, Any] = {"ignored": "No monitored website files changed"}
    else:
        store = service.store
        project = service.project
        job = store.enqueue(
            project.tenant_id,
            project.id,
            "audit",
            "deployment:" + p.value + ":" + event.event_id,
            {"deployment_revision": event.revision, "deployment_origin": event.url},
        )
        result = {"queued": job.id}
        # Hosting and publishing connections share a project but keep separate credentials.
        for publisher in Platform:
            publisher_state, _ = service.state(publisher)
            for proposal in publisher_state.get("proposals", []):
                if proposal["status"] in {"waiting_publication", "verified", "pr_opened"} and (
                    proposal.get("verification_url") or proposal["before"].get("url")
                ):
                    store.enqueue(
                        project.tenant_id,
                        project.id,
                        "connector",
                        f"verify:{proposal['id']}:{event.event_id}",
                        {
                            "platform": publisher.value,
                            "operation": "verify",
                            "proposal_id": proposal["id"],
                        },
                    )
    state.update(
        event_ids=[*seen[-99:], event.event_id],
        last_deployment_at=epoch,
        last_deployment={
            "revision": event.revision,
            "url": event.url,
            "observed_at": str(event.occurred_at),
        },
    )
    service.save(p, state, version)
    return result


def native_repository(
    service: ConnectorService, p: Platform, headers: dict[str, str], raw: bytes
) -> dict[str, Any]:
    if p not in REPOSITORIES:
        raise ConnectorError("unsupported", "Native event is unsupported")
    state, _ = service.state(p)
    config = state.get("config", {})
    secret = config.get("credentials", {}).get("webhook_secret", "")
    if not secret or not config.get("enabled"):
        raise ConnectorError("signature", "Repository webhook is not configured")
    if p == Platform.GITLAB:
        if not hmac.compare_digest(secret, headers.get("x-gitlab-token", "")):
            raise ConnectorError("signature", "Invalid repository event token")
    else:
        expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, headers.get("x-hub-signature", "")):
            raise ConnectorError("signature", "Invalid repository event signature")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ConnectorError("invalid_response", "Invalid event document")
    if p == Platform.GITLAB:
        if (
            data.get("object_kind") != "push"
            or data.get("project", {}).get("path_with_namespace") != config["resource"]
            or data.get("ref") != "refs/heads/" + config.get("options", {}).get("branch", "main")
        ):
            return {"ignored": "Not a push to the configured branch"}
        paths = [
            path
            for commit in data.get("commits", [])
            for kind in ["added", "modified", "removed"]
            for path in commit.get(kind, [])
        ]
        revision = data.get("after", "")
    else:
        if (
            headers.get("x-event-key") != "repo:push"
            or data.get("repository", {}).get("full_name") != config["resource"]
        ):
            return {"ignored": "Not the configured repository"}
        changes = [
            x
            for x in data.get("push", {}).get("changes", [])
            if (x.get("new") or {}).get("name") == config.get("options", {}).get("branch", "main")
        ]
        if not changes:
            return {"ignored": "Not the configured branch"}
        paths = []
        revision = changes[-1].get("new", {}).get("target", {}).get("hash", "")
    if not revision or len(revision) > 100:
        raise ConnectorError("invalid_response", "Event lacks a bounded revision")
    if paths and affected_urls(service.spec, paths) == []:
        return {"ignored": "No monitored website files changed"}
    job = service.store.enqueue(
        service.project.tenant_id,
        service.project.id,
        "connector",
        f"repo-event:{p.value}:{hashlib.sha256(revision.encode()).hexdigest()}",
        {"platform": p.value, "operation": "collect"},
    )
    return {"queued": job.id}


def native_deployment(
    service: ConnectorService, p: Platform, headers: dict[str, str], raw: bytes
) -> dict[str, Any]:
    """Validate documented native signatures before normalizing into the common event."""
    from datetime import UTC, datetime

    import jwt

    state, _ = service.state(p)
    config = state.get("config", {})
    secret = config.get("credentials", {}).get("webhook_secret", "")
    if not secret or not config.get("enabled"):
        raise ConnectorError("signature", "Deployment webhook is not configured")
    if p == Platform.VERCEL:
        expected = hmac.new(secret.encode(), raw, hashlib.sha1).hexdigest()
        if not hmac.compare_digest(expected, headers.get("x-vercel-signature", "")):
            raise ConnectorError("signature", "Invalid Vercel signature")
    elif p == Platform.NETLIFY:
        try:
            token = jwt.decode(
                headers.get("x-webhook-signature", ""),
                secret,
                algorithms=["HS256"],
                issuer="netlify",
            )
            if not hmac.compare_digest(token.get("sha256", ""), hashlib.sha256(raw).hexdigest()):
                raise ValueError
        except (jwt.PyJWTError, ValueError, TypeError):
            raise ConnectorError("signature", "Invalid Netlify signature") from None
    else:
        raise ConnectorError("unsupported", "Native hosting event is unsupported")
    data = json.loads(raw)
    if p == Platform.VERCEL:
        if data.get("type") not in {"deployment.succeeded", "deployment.promoted"}:
            return {"ignored": "Not a successful deployment"}
        payload = data.get("payload", {})
        if payload.get("target") != "production":
            return {"ignored": "Not a production deployment"}
        deployment = payload.get("deployment", {})
        resource = payload.get("project", {}).get("id")
        meta = deployment.get("meta", {})
        revision = (
            meta.get("githubCommitSha") or meta.get("gitlabCommitSha") or deployment.get("id")
        )
        observed = datetime.fromtimestamp(float(data.get("createdAt", 0)) / 1000, UTC)
    else:
        if data.get("state") != "ready" or data.get("context") != "production":
            return {"ignored": "Not a successful production deployment"}
        resource = data.get("site_id")
        revision = data.get("commit_ref") or data.get("id")
        observed = datetime.fromisoformat(data.get("published_at", "").replace("Z", "+00:00"))
    normalized = (
        DeploymentEvent(
            event_id="native-" + hashlib.sha256(raw).hexdigest(),
            resource=resource,
            environment=service.spec.environment,
            revision=revision,
            url=str(service.spec.website_url),
            occurred_at=observed,
            status="succeeded",
        )
        .model_dump_json()
        .encode()
    )
    stamp = str(int(time.time()))
    return handle(
        service,
        p,
        {
            "x-optimiser-timestamp": stamp,
            "x-optimiser-signature": signature(secret, stamp, normalized),
        },
        normalized,
    )
