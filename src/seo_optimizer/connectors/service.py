"Tenant-scoped encrypted state, evidence, optimistic publication and reversible changes."

import hashlib
import json
import re
import time
from datetime import timedelta
from html import unescape
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.connectors import measurements, publishing, repositories, visibility
from seo_optimizer.connectors.catalog import DEFINITIONS, catalog
from seo_optimizer.connectors.models import (
    Collection,
    CollectionRequest,
    ConnectionInput,
    ImportRequest,
    Platform,
    ProposalInput,
    Resource,
)
from seo_optimizer.connectors.transport import ConnectorError, Transport
from seo_optimizer.contracts import utc_now
from seo_optimizer.store import Project, Store

REPOSITORIES = {Platform.GITLAB, Platform.BITBUCKET}
IMPORTS = {Platform.SERVER_LOGS, Platform.DEPLOYMENT}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def public_collection(value: dict[str, Any]) -> dict[str, Any]:
    return {
        **value,
        "records": [
            {**row, "fields": {k: v for k, v in row["fields"].items() if k != "_native"}}
            for row in value.get("records", [])
        ],
    }


def plain(value: Any) -> str:
    return unescape(re.sub(r"<[^>]*>", " ", str(value))).strip()


class ConnectorService:
    def __init__(self, store: Store, project: Project, client: httpx.Client | None = None):
        if store.project(project.tenant_id, project.id) is None:
            raise ConnectorError("not_found", "Project not found")
        self.store, self.project, self.client = store, project, client
        self.spec = ProjectSpec.model_validate(project.spec)

    def key(self, platform: Platform) -> str:
        return f"connector:{self.project.tenant_id}:{self.project.id}:{platform.value}"

    def state(self, platform: Platform) -> tuple[dict[str, Any], int]:
        return self.store.state(self.key(platform))

    def save(self, platform: Platform, value: dict[str, Any], version: int) -> None:
        if not self.store.save_state(self.key(platform), value, version):
            raise ConnectorError("conflict", "Connection changed; reload and retry")

    def public(self, platform: Platform) -> dict[str, Any]:
        state, _ = self.state(platform)
        config = state.get("config", {})
        public = {k: v for k, v in config.items() if k != "credentials"}
        return {
            "platform": platform.value,
            "definition": DEFINITIONS[platform.value],
            "connected": bool(config),
            "config": public,
            "credential_fields": list(config.get("credentials", {})),
            "webhook_url": (
                self.store.settings.public_url.rstrip("/")
                + (
                    f"/webhooks/connectors/{self.project.tenant_id}/"
                    f"{self.project.id}/{platform.value}"
                )
                if "webhook_secret" in DEFINITIONS[platform.value]["secrets"] and config
                else None
            ),
            "status": state.get("status", "not_connected"),
            "last_sync": state.get("last_sync"),
            "last_error": state.get("last_error"),
            "evidence": [
                {**entry, "collection": public_collection(entry["collection"])}
                for entry in state.get("evidence", [])
            ],
            "proposals": [
                {k: v for k, v in item.items() if k not in {"before", "after"}}
                for item in state.get("proposals", [])
            ],
            "history": state.get("history", [])[-20:],
            "next_sync": state.get("next_sync"),
        }

    def overview(self) -> dict[str, Any]:
        return {"catalog": catalog(), "connections": [self.public(p) for p in Platform]}

    def configure(self, value: ConnectionInput) -> dict[str, Any]:
        definition = DEFINITIONS[value.platform.value]
        if set(value.options) - set(definition["options"]):
            raise ConnectorError("configuration", "Unknown connector option")
        if set(value.credentials) - set(definition["secrets"]):
            raise ConnectorError("configuration", "Unknown connector credential")
        if value.allow_writes and not definition["write"]:
            raise ConnectorError("policy", "This connector is read-only")
        if value.platform in {Platform.WORDPRESS, Platform.WOOCOMMERCE}:
            cms_resource = urlparse(value.resource)
            website = urlparse(str(self.spec.website_url))
            if cms_resource.scheme != "https" and not self.store.settings.allow_private_network:
                raise ConnectorError("configuration", "CMS credentials require HTTPS")
            if (
                cms_resource.username
                or cms_resource.password
                or cms_resource.query
                or cms_resource.fragment
                or (cms_resource.scheme, cms_resource.netloc) != (website.scheme, website.netloc)
            ):
                raise ConnectorError(
                    "configuration", "Self-hosted CMS must use the configured project origin"
                )
        if value.platform == Platform.SEARCH_CONSOLE:
            website = urlparse(str(self.spec.website_url))
            resource = value.resource
            if resource.startswith("sc-domain:"):
                domain = resource[10:]
                if not domain or not (
                    website.hostname == domain or (website.hostname or "").endswith("." + domain)
                ):
                    raise ConnectorError(
                        "configuration", "Search Console property does not cover the project"
                    )
            elif (
                not str(self.spec.website_url).startswith(resource)
                or urlparse(resource).netloc != website.netloc
            ):
                raise ConnectorError(
                    "configuration", "Search Console property does not cover the project"
                )
        state, version = self.state(value.platform)
        if state.get("lease_until", 0) > time.time():
            raise ConnectorError("busy", "Connection has an operation in progress")
        existing = state.get("config", {}).get("credentials", {})
        # Omitted fields preserve secrets. Explicit empty values remove individual secrets.
        creds = {**existing, **value.credentials}
        creds = {k: v for k, v in creds.items() if v}
        value = value.model_copy(update={"credentials": creds})
        previous = state.get("config", {})
        same_resource = (
            previous.get("resource") == value.resource
            and previous.get("options", {}) == value.options
        )
        self.save(
            value.platform,
            {
                **(state if same_resource else {}),
                "config": value.model_dump(),
                "generation": state.get("generation", str(uuid4()))
                if same_resource
                else str(uuid4()),
                "status": "configured",
                "proposals": state.get("proposals", []) if same_resource else [],
                "evidence": state.get("evidence", []) if same_resource else [],
                "history": state.get("history", []) if same_resource else [],
                "next_sync": time.time(),
            },
            version,
        )
        return self.public(value.platform)

    def disconnect(self, p: Platform) -> None:
        state, version = self.state(p)
        if state.get("lease_until", 0) > time.time():
            raise ConnectorError(
                "busy", "Wait for the current operation to finish before disconnecting"
            )
        self.save(p, {}, version)

    def lock(self, p: Platform) -> tuple[dict[str, Any], int]:
        state, version = self.state(p)
        if not state.get("config") or not state["config"].get("enabled", True):
            raise ConnectorError("not_connected", "Connect and enable the platform first")
        if state.get("lease_until", 0) > time.time():
            raise ConnectorError("busy", "Connection operation is already running")
        state["lease_until"] = time.time() + 600
        self.save(p, state, version)
        return state, version + 1

    def transport(self, config: ConnectionInput) -> Transport:
        return Transport(config, self.client, self.store.settings.allow_private_network)

    def refresh_google(self, config: ConnectionInput) -> None:
        from seo_optimizer.connectors.oauth import refresh_access

        refresh_access(config, self.client)

    def observe(self, t: Transport, q: CollectionRequest) -> Collection:
        p = t.connection.platform
        if p == Platform.SEARCH_CONSOLE and q.resource_id:
            if urlparse(q.resource_id).netloc != urlparse(str(self.spec.website_url)).netloc:
                raise ConnectorError("policy", "Inspect only project URLs")
        if p in REPOSITORIES and q.resource_id:
            self.check_path(q.resource_id)
        try:
            if p in publishing.CMS:
                return publishing.collect(t, q)
            if p in REPOSITORIES:
                return repositories.collect(t, q)
            if p == Platform.AI_VISIBILITY:
                return visibility.collect(t, q)
            return measurements.collect(t, q)
        except ConnectorError as error:
            if (
                error.code == "reconnect_required"
                and p
                in {
                    Platform.SEARCH_CONSOLE,
                    Platform.GA4,
                    Platform.BUSINESS_PROFILE,
                    Platform.GITLAB,
                    Platform.BITBUCKET,
                    Platform.SHOPIFY,
                }
                and t.connection.credentials.get("refresh_token")
            ):
                self.refresh_google(t.connection)
                # Only collection requests are replayed after refreshing access, never writes.
                if p in publishing.CMS:
                    return publishing.collect(t, q)
                if p in REPOSITORIES:
                    return repositories.collect(t, q)
                return measurements.collect(t, q)
            raise

    def collect(self, p: Platform, q: CollectionRequest) -> dict[str, Any]:
        if p in IMPORTS:
            raise ConnectorError(
                "unsupported", "Use the signed event or structured import workflow"
            )
        state, version = self.lock(p)
        config = ConnectionInput.model_validate(state["config"])
        t = self.transport(config)
        try:
            result = self.observe(t, q)
            evidence_id = "connector-" + str(uuid4())
            evidence = {
                "id": evidence_id,
                "tenant_id": self.project.tenant_id,
                "project_id": self.project.id,
                "environment": self.spec.environment,
                "collection": result.model_dump(mode="json"),
            }
            state.update(
                config=config.model_dump(),
                status="connected",
                last_error=None,
                last_sync=time.time(),
                next_sync=time.time() + config.interval_seconds,
                evidence=[*state.get("evidence", [])[-4:], evidence],
            )
            try:
                self.ingest_search(result)
            except ValueError:
                result.warnings.append(
                    "Search data was collected, but its research workspace import is unresolved "
                    "because existing windows overlap or its observation budget is exhausted."
                )
                state["evidence"][-1]["collection"] = result.model_dump(mode="json")
            state["lease_until"] = 0
            self.save(p, state, version)
            return {
                "evidence_id": evidence_id,
                "collection": public_collection(result.model_dump(mode="json")),
                "requests": t.calls,
            }
        except ConnectorError as error:
            state.update(
                config=config.model_dump(),
                status=error.code,
                last_error=str(error),
                lease_until=0,
                next_sync=time.time() + max(error.retry_after, 3600),
            )
            self.save(p, state, version)
            raise
        except Exception:
            state.update(
                status="invalid_response",
                last_error="Provider response could not be validated",
                lease_until=0,
                next_sync=time.time() + 3600,
            )
            self.save(p, state, version)
            raise ConnectorError(
                "invalid_response", "Provider response could not be validated"
            ) from None
        finally:
            t.close()

    def ingest_search(self, result: Collection) -> None:
        if result.platform != Platform.SEARCH_CONSOLE:
            return
        from pydantic import HttpUrl

        from seo_optimizer.growth import SearchObservation, Workspace

        rows = []
        for record in result.records:
            if record.kind != "search_query":
                continue
            d = record.fields
            k = d["keys"]
            if urlparse(k[1]).netloc != urlparse(str(self.spec.website_url)).netloc:
                continue
            rows.append(
                SearchObservation(
                    id="gsc-" + digest([k, d["start"], d["end"]])[:24],
                    query=k[0],
                    page=HttpUrl(k[1]),
                    start=d["start"],
                    end=d["end"],
                    impressions=d["impressions"],
                    clicks=d["clicks"],
                    position=d.get("position"),
                    market=k[2],
                    device=k[3],
                    source="Search Console finalized web query/page API",
                )
            )
        if rows:
            ws = self.store.workspace(self.project.tenant_id, self.project.id)
            ids = {r.id for r in rows}
            value = {**ws.model_dump(), "search": [r for r in ws.search if r.id not in ids] + rows}
            self.store.save_workspace(
                self.project.tenant_id, self.project.id, Workspace.model_validate(value)
            )

    def check_path(self, path: str) -> None:
        value = PurePosixPath(path)
        if (
            value.is_absolute()
            or ".." in value.parts
            or "\\" in path
            or any(part.startswith(".") for part in value.parts)
            or any(part in {"node_modules", "vendor"} for part in value.parts)
        ):
            raise ConnectorError("policy", "Repository path is outside the permitted source scope")
        if not any(
            path == prefix or path.startswith(prefix.rstrip("/") + "/")
            for prefix in self.spec.allowed_paths
        ):
            raise ConnectorError("policy", "Repository path is outside configured allowed paths")
        if value.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            raise ConnectorError("policy", "Credential files cannot be inspected")

    def grounded(self, proposal: ProposalInput, current: Resource) -> None:
        facts = {
            f.id: f
            for f in self.spec.facts
            if f.verified_at <= utc_now() and (f.valid_until is None or f.valid_until > utc_now())
        }
        if not set(proposal.fact_ids) <= set(facts):
            raise ConnectorError("policy", "Proposal references unknown or expired facts")
        if current.kind == "source_file":
            self.check_path(current.id)
            from seo_optimizer.connectors.source_checks import validate_source_change

            validate_source_change(
                current.id,
                str(current.fields.get("content", "")),
                proposal.changes.get("content", ""),
            )
            from seo_optimizer.connectors.source_checks import validate_metadata_claims

            validate_metadata_claims(
                str(current.fields.get("content", "")),
                proposal.changes.get("content", ""),
                {str(facts[id].value) for id in proposal.fact_ids},
                current.id,
            )
            return
        for key, value in proposal.changes.items():
            if key == "regularHours":
                try:
                    hours = json.loads(value)
                except ValueError:
                    raise ConnectorError(
                        "policy", "Business hours must be valid structured facts"
                    ) from None
                if not any(facts[id].value == hours for id in proposal.fact_ids):
                    raise ConnectorError("policy", "Business hours require matching trusted facts")
            elif (
                value
                and plain(value)
                not in plain(current.fields.get("title", ""))
                + " "
                + plain(current.fields.get("content", ""))
                and not any(str(facts[id].value) == value for id in proposal.fact_ids)
            ):
                raise ConnectorError("policy", "New claims require matching trusted project facts")

    def propose(self, p: Platform, value: ProposalInput) -> dict[str, Any]:
        state, version = self.state(p)
        if not state.get("config"):
            raise ConnectorError("not_connected", "Connect the platform first")
        if state.get("lease_until", 0) > time.time():
            raise ConnectorError("busy", "Connection operation is running")
        records = []
        for evidence in state.get("evidence", []):
            if evidence["id"] in value.evidence_ids:
                collected = Collection.model_validate(evidence["collection"])
                if utc_now() - collected.collected_at > timedelta(hours=24):
                    raise ConnectorError("stale", "Collect fresh evidence before proposing changes")
                records.extend(collected.records)
        if not set(value.evidence_ids) <= {e["id"] for e in state.get("evidence", [])}:
            raise ConnectorError("policy", "Unknown evidence reference")
        current = next((r for r in reversed(records) if r.id == value.resource_id), None)
        if current is None:
            raise ConnectorError("policy", "Resource is missing from the referenced evidence")
        config = ConnectionInput.model_validate(state["config"])
        t = self.transport(config)
        try:
            allowed = {"content"} if p in REPOSITORIES else publishing.allowed_fields(t)
        finally:
            t.close()
        if not set(value.changes) <= allowed:
            raise ConnectorError("policy", "Change targets unsupported fields")
        self.grounded(value, current)
        if all(
            current.fields.get(k, "") == (json.loads(v) if k == "regularHours" else v)
            for k, v in value.changes.items()
        ):
            raise ConnectorError("no_change", "No change is needed")
        identity = digest(
            [value.model_dump(exclude={"evidence_ids", "reason"}), current.model_dump()]
        )[:32]
        existing = next((x for x in state.get("proposals", []) if x["id"] == identity), None)
        if existing:
            if existing["status"] == "proposed":
                # Collection IDs identify observations, not different actions.
                # Keep an unchanged pending action attached to fresh evidence,
                # including after older observations leave the bounded history.
                existing["evidence_ids"] = value.evidence_ids
                existing["created_at"] = time.time()
                self.save(p, state, version)
            return {k: v for k, v in existing.items() if k not in {"before", "after"}}
        proposal = {
            "id": identity,
            **value.model_dump(),
            "before": current.model_dump(),
            "status": "proposed",
            "created_at": time.time(),
            "diff": {
                k: {
                    "before": (
                        json.dumps(current.fields.get(k, {}))
                        if k == "regularHours"
                        else current.fields.get(k, "")
                    ),
                    "after": v,
                }
                for k, v in value.changes.items()
            },
        }
        state["proposals"] = [*state.get("proposals", [])[-19:], proposal]
        self.save(p, state, version)
        return {k: v for k, v in proposal.items() if k != "before"}

    def publish(self, p: Platform, proposal_id: str, rollback: bool = False) -> dict[str, Any]:
        state, version = self.lock(p)
        config = ConnectionInput.model_validate(state["config"])
        proposal = next((x for x in state.get("proposals", []) if x["id"] == proposal_id), None)
        t = self.transport(config)
        try:
            if proposal is None:
                raise ConnectorError("not_found", "Proposal not found")
            if not config.allow_writes or not self.spec.auto_fix or not self.spec.enabled:
                raise ConnectorError(
                    "policy", "Project and connector write permissions are required"
                )
            if (
                proposal["status"]
                in {
                    "verified",
                    "deployed_verified",
                    "waiting_publication",
                    "pr_opened",
                    "rolled_back",
                }
                and not rollback
            ):
                state["lease_until"] = 0
                self.save(p, state, version)
                return {k: v for k, v in proposal.items() if k not in {"before", "after"}}
            expected_status = (
                {"verified", "deployed_verified", "waiting_publication"}
                if rollback
                else {"proposed"}
            )
            if proposal["status"] not in expected_status:
                raise ConnectorError(
                    "policy", "Proposal cannot be safely repeated; inspect its recorded outcome"
                )
            if rollback and p in REPOSITORIES:
                raise ConnectorError(
                    "unsupported", "Revert repository changes through a reviewed PR"
                )
            if not rollback and time.time() - proposal["created_at"] > 86400:
                raise ConnectorError("stale", "Create a fresh proposal")
            before = Resource.model_validate(proposal["after"] if rollback else proposal["before"])
            current = self.observe(t, CollectionRequest(resource_id=before.id, limit=1)).records[0]
            if (
                digest(current.fields) != digest(before.fields)
                or current.revision != before.revision
            ):
                raise ConnectorError(
                    "conflict", "Source changed after the proposal; no write was made"
                )
            changes = (
                {
                    k: (
                        json.dumps(proposal["before"]["fields"].get(k, {}))
                        if k == "regularHours"
                        else str(proposal["before"]["fields"].get(k, ""))
                    )
                    for k in proposal["changes"]
                }
                if rollback
                else proposal["changes"]
            )
            if not rollback:
                self.grounded(
                    ProposalInput.model_validate(
                        {key: proposal[key] for key in ProposalInput.model_fields}
                    ),
                    current,
                )
            proposal["status"] = "publishing"
            self.save(p, state, version)
            version += 1
            if p in REPOSITORIES:
                branch = self.spec.git_conventions.branch_name("connector-" + proposal_id[:12])
                proposal["pr"] = repositories.write(
                    t,
                    current,
                    changes,
                    branch,
                    self.spec.git_conventions.commit_message(current.id),
                    proposal["reason"],
                )
                proposal["status"] = "pr_opened"
                proposal["verification"] = {
                    "source_checked": True,
                    "build_ci": "unverified",
                    "deployed_site": "unverified",
                }
            else:
                publishing.write(t, current, changes)
                after = self.observe(t, CollectionRequest(resource_id=current.id, limit=1)).records[
                    0
                ]
                matched = all(
                    after.fields.get(k, "") == (json.loads(v) if k == "regularHours" else v)
                    for k, v in changes.items()
                )
                proposal["after"] = after.model_dump()
                proposal["status"] = (
                    (
                        "rolled_back"
                        if rollback
                        else "waiting_publication"
                        if p
                        in {Platform.WEBFLOW, Platform.SANITY, Platform.CONTENTFUL, Platform.FRAMER}
                        else "verified"
                    )
                    if matched
                    else "verification_failed"
                )
                proposal["verification"] = {
                    "provider_readback": matched,
                    "deployed_site": "unverified",
                    "note": (
                        "Provider content readback does not establish deployed "
                        "rendering, indexing or ranking."
                    ),
                }
            state["status"] = "connected"
            state["lease_until"] = 0
            state["history"] = [
                *state.get("history", [])[-19:],
                {"time": time.time(), "proposal": proposal_id, "status": proposal["status"]},
            ]
            self.save(p, state, version)
            return {k: v for k, v in proposal.items() if k not in {"before", "after"}}
        except ConnectorError as error:
            if proposal and proposal.get("status") == "publishing":
                proposal["status"] = (
                    "write_uncertain"
                    if error.code in {"write_uncertain", "transport_failed"}
                    else "publication_failed"
                )
            state.update(lease_until=0, status=error.code, last_error=str(error))
            self.save(p, state, version)
            raise
        except Exception:
            if proposal and proposal.get("status") == "publishing":
                proposal["status"] = "write_uncertain"
            state.update(
                lease_until=0,
                status="unresolved",
                last_error="Publication outcome requires inspection",
            )
            self.save(p, state, version)
            raise ConnectorError("unresolved", "Publication outcome requires inspection") from None
        finally:
            t.close()

    def auto_propose(self, p: Platform, evidence_id: str) -> list[dict[str, Any]]:
        state, _ = self.state(p)
        created = []
        evidence = next(e for e in state["evidence"] if e["id"] == evidence_id)
        for row in evidence["collection"]["records"][: self.spec.max_files_changed]:
            fields = row["fields"]
            if self.spec.environment != "production" or fields.get("status") in {
                "private",
                "draft",
                "pending",
                "future",
                "trash",
            }:
                continue
            if (
                row.get("url")
                and self.spec.page_intents.get(urlparse(row["url"]).path, True) is False
            ):
                continue
            if p == Platform.SANITY and not row["id"].startswith("drafts."):
                continue
            if row["kind"] == "source_file" and row["id"].endswith(".html"):
                from html import escape

                source = fields.get("content", "")
                from seo_optimizer.audit import PageParser

                parser = PageParser()
                parser.feed(source)
                if any("noindex" in directive.lower() for directive in parser.robots):
                    continue
                heading = re.search(r"<h1\b[^>]*>(.*?)</h1>", source, re.I | re.S)
                head = re.search(r"<head\b[^>]*>", source, re.I)
                empty = re.search(r"<title\b[^>]*>\s*</title\s*>", source, re.I)
                if heading and head and (empty or not re.search(r"<title\b", source, re.I)):
                    title_text = plain(heading.group(1))
                    if title_text and len(title_text) <= 160:
                        tag = "<title>" + escape(title_text) + "</title>"
                        after = (
                            source.replace(empty.group(0), tag, 1)
                            if empty
                            else source[: head.end()] + tag + source[head.end() :]
                        )
                        created.append(
                            self.propose(
                                p,
                                ProposalInput(
                                    resource_id=row["id"],
                                    changes={"content": after},
                                    reason=(
                                        "Use the observed main heading for the missing page title."
                                    ),
                                    evidence_ids=[evidence_id],
                                ),
                            )
                        )
                continue
            title = plain(fields.get("title", ""))
            if "seo_title" in fields and not fields["seo_title"] and title and len(title) <= 160:
                if p == Platform.WORDPRESS and not self.wordpress_title_missing(
                    p, evidence_id, row
                ):
                    continue
                created.append(
                    self.propose(
                        p,
                        ProposalInput(
                            resource_id=row["id"],
                            changes={"seo_title": title},
                            reason="Use the resource's observed title for its missing SEO title.",
                            evidence_ids=[evidence_id],
                        ),
                    )
                )
        for proposal in created:
            if state["config"].get("auto_apply") and self.spec.auto_fix:
                self.publish(p, proposal["id"])
        return created

    def wordpress_title_missing(self, p: Platform, evidence_id: str, row: dict[str, Any]) -> bool:
        """An empty plugin override alone is not a missing rendered title."""
        from seo_optimizer.audit import PageParser
        from seo_optimizer.crawler import Crawler, CrawlError

        observation: dict[str, Any] = {
            "url": row.get("url", ""),
            "collected_at": utc_now().isoformat(),
            "missing_title_confirmed": False,
        }
        crawler = Crawler(
            str(self.spec.website_url), self.store.settings.allow_private_network, self.client
        )
        try:
            if not observation["url"]:
                raise CrawlError("A canonical page URL is required")
            response = crawler.fetch(observation["url"])
            parser = PageParser()
            parser.feed(response.text)
            directives = [*parser.robots, *response.headers.get_list("x-robots-tag")]
            title = "".join(parser.title).strip()
            html = "text/html" in response.headers.get("content-type", "").lower()
            missing = (
                response.status_code == 200
                and html
                and not title
                and not any(
                    re.search(r"\b(?:noindex|none)\b", directive, re.I) for directive in directives
                )
            )
            observation.update(
                status_code=response.status_code,
                title=title[:1000],
                robots=directives[:20],
                missing_title_confirmed=missing,
                content_sha256=hashlib.sha256(response.content).hexdigest(),
            )
        except (CrawlError, httpx.HTTPError):
            observation["dependency"] = "Live title evidence could not be collected safely"
        finally:
            crawler.close()
        state, version = self.state(p)
        evidence = next(e for e in state["evidence"] if e["id"] == evidence_id)
        observations = evidence.setdefault("live_observations", [])
        observations.append(observation)
        del observations[: -self.spec.max_files_changed]
        self.save(p, state, version)
        return bool(observation["missing_title_confirmed"])

    def import_records(self, p: Platform, value: ImportRequest) -> dict[str, Any]:
        from seo_optimizer.connectors.imports import normalize_import

        state, version = self.lock(p)
        try:
            collection = normalize_import(p, value, str(self.spec.website_url))
            evidence = {
                "id": "connector-" + str(uuid4()),
                "tenant_id": self.project.tenant_id,
                "project_id": self.project.id,
                "environment": self.spec.environment,
                "collection": collection.model_dump(mode="json"),
            }
            state.update(
                lease_until=0,
                status="connected",
                last_sync=time.time(),
                evidence=[*state.get("evidence", [])[-4:], evidence],
            )
            self.save(p, state, version)
            return evidence
        except Exception:
            state["lease_until"] = 0
            self.save(p, state, version)
            raise
