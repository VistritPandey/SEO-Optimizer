"""Portable autonomous worker: observe, reason, verify, publish and reconcile."""

import base64
import re
import shutil
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from pydantic import ValidationError

from seo_optimizer.application_models import FileChange, ProjectSpec
from seo_optimizer.contracts import (
    Assessment,
    AuditRequest,
    Evidence,
    Finding,
    FindingStatus,
    utc_now,
)
from seo_optimizer.crawler import Crawler, capture_browser, page_excerpt
from seo_optimizer.execution import (
    apply_changes,
    commit_local,
    confined,
    run_git,
    snapshot_local,
    verify_workspace,
)
from seo_optimizer.github import GitHubClient
from seo_optimizer.knowledge import load_knowledge
from seo_optimizer.llm import ModelClient
from seo_optimizer.policy import validate_assessment
from seo_optimizer.scanner import affected_urls, context, scan
from seo_optimizer.settings import Settings
from seo_optimizer.store import Job, Project, Store


def infer_route_map(root: Path, spec: ProjectSpec) -> dict[str, str]:
    mapping = dict(spec.route_map)
    for base in spec.allowed_paths:
        directory = root / base
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if (
                not path.is_file()
                or path.is_symlink()
                or any(part in {"node_modules", ".git", ".venv"} for part in path.parts)
            ):
                continue
            relative = path.relative_to(directory)
            route: str | None = None
            if path.suffix == ".html":
                route = "/" + str(relative).replace("index.html", "")
            elif path.name in {"page.tsx", "page.jsx", "page.js", "page.py"}:
                route = "/" + str(relative.parent).replace(".", "")
            elif base == "pages" and path.suffix in {".tsx", ".jsx", ".js", ".astro"}:
                route = "/" + str(relative.with_suffix("")).replace("index", "")
            if route is not None:
                mapping.setdefault(route, str(path.relative_to(root)))
    return mapping


def builtin_changes(
    root: Path, spec: ProjectSpec, findings: list[Finding], evidence: list[Evidence]
) -> list[FileChange]:
    """A deterministic title repair uses observed H1 text, never invented business claims."""
    changes = []
    for finding in findings:
        if finding.check_id != "tech.title" or finding.status != FindingStatus.DEFECT:
            continue
        page = next((item for item in evidence if item.id in finding.evidence_ids), None)
        if page is None or page.url is None:
            continue
        from urllib.parse import urlparse

        route = urlparse(str(page.url)).path or "/"
        path = spec.route_map.get(route)
        if not path or not path.endswith(".html"):
            continue
        source = confined(root, path, spec.allowed_paths)
        text = source.read_text()
        heading = re.search(r"<h1\b[^>]*>(.*?)</h1>", text, flags=re.I | re.S)
        head = re.search(r"<head\b[^>]*>", text, flags=re.I)
        if not heading or not head or re.search(r"<title\b", text, re.I):
            continue
        from html import escape, unescape

        title = unescape(re.sub(r"<[^>]+>", "", heading.group(1))).strip()
        if not title or len(title) > 160:
            continue
        changes.append(
            FileChange(
                path=path,
                before=head.group(0),
                after=head.group(0) + "\n<title>" + escape(title) + "</title>",
                reason="Use the page's observed main heading as its descriptive title.",
                check_id=finding.check_id,
                evidence_ids=finding.evidence_ids,
            )
        )
    return changes


class Worker:
    def __init__(self, store: Store, settings: Settings, worker_id: str | None = None):
        self.store, self.settings = store, settings
        self.id = worker_id or "worker-" + str(uuid4())
        self.knowledge = load_knowledge()

    def tick(self, tenant: str | None = None) -> bool:
        self.store.reconcile()
        job = self.store.claim(self.id, tenant)
        if job is None:
            return False
        project = self.store.project(job.tenant_id, job.project_id)
        if project is None:
            self.store.finish(
                job.tenant_id, job.id, self.id, "blocked", {"summary": "Project no longer exists"}
            )
            return True
        if job.attempts > 3:
            self.store.finish(
                job.tenant_id, job.id, self.id, "failed", {"summary": "Job retry budget exhausted"}
            )
            return True
        try:
            status, result, delay = self.process(project, job)
        except (httpx.HTTPError, OSError) as error:
            status = "queued" if job.attempts < 3 else "failed"
            result, delay = (
                {**job.result, "summary": f"Transient integration failure: {type(error).__name__}"},
                30 * max(1, job.attempts),
            )
        except Exception as error:
            status, delay = "blocked", 0
            message = (
                "Structured model output failed local validation"
                if isinstance(error, ValidationError)
                else str(error)
            )
            credentials = self.store.secrets(project)
            for secret in credentials.model_dump().values():
                if secret:
                    message = message.replace(secret, "[redacted]")
            result = {"summary": message[:500], "error_type": type(error).__name__}
        if result.get("stage") == "verified":
            self.store.remember_findings(
                job.tenant_id,
                job.project_id,
                result.get("findings", []),
                result.get("audited_urls", []),
            )
        self.store.finish(job.tenant_id, job.id, self.id, status, result, delay)
        snapshot = self.settings.data_dir / "workspaces" / job.id / "repository"
        if snapshot.is_dir():
            shutil.rmtree(snapshot)
        return True

    def process(self, project: Project, job: Job) -> tuple[str, dict[str, Any], float]:
        spec = ProjectSpec.model_validate(project.spec)
        if not spec.enabled:
            return "canceled", {"summary": "Project is paused"}, 0
        credentials = self.store.secrets(project)
        github = GitHubClient(credentials) if spec.repository else None
        crawler = Crawler(str(spec.website_url), self.settings.allow_private_network)
        try:
            if job.result.get("stage") == "checks" and github:
                return self.finish_pr(project, job, spec, github)
            if job.result.get("stage") == "deployment" and github:
                deployments = github.request(
                    "GET",
                    f"/repos/{spec.repository}/deployments",
                    params={"sha": job.result["merged_sha"]},
                )
                deployed = False
                for deployment in deployments:
                    statuses = github.request(
                        "GET", f"/repos/{spec.repository}/deployments/{deployment['id']}/statuses"
                    )
                    if (
                        statuses
                        and statuses[0].get("state") == "success"
                        and deployment.get("environment") == spec.environment
                    ):
                        deployed = True
                        break
                if not deployed:
                    if time.time() - job.created_at > 3600:
                        return (
                            "blocked",
                            {
                                **job.result,
                                "summary": (
                                    "Deployment of the merged revision has not been confirmed"
                                ),
                            },
                            0,
                        )
                    return "waiting_deployment", job.result, 30
                after = crawler.collect(
                    project.tenant_id, project.id, spec, job.result["audited_urls"]
                )
                return self.verify_deployment(spec, job.result, after, github)
            return self.audit_job(project, job, spec, crawler, github)
        finally:
            crawler.close()
            if github:
                github.close()

    def audit_job(
        self,
        project: Project,
        job: Job,
        spec: ProjectSpec,
        crawler: Crawler,
        github: GitHubClient | None,
    ) -> tuple[str, dict[str, Any], float]:
        started = time.monotonic()
        credentials = self.store.secrets(project)
        root = self.settings.data_dir / "workspaces" / job.id
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        revision = ""
        changed: list[str] | None = None
        if spec.local_path:
            if not self.settings.allow_local_repositories:
                raise ValueError("Local repositories are disabled on this host")
            repository = root / "repository"
            revision = snapshot_local(
                Path(spec.local_path), repository, spec.branch, self.settings.allowed_repo_roots
            )
            if project.last_revision:
                try:
                    changed = run_git(
                        repository, "diff", "--name-only", project.last_revision, revision
                    ).splitlines()
                except ValueError:
                    changed = None
        elif github:
            revision = github.head(spec.repository, spec.branch)
            if job.payload.get("after") and job.payload["after"] != revision:
                return (
                    "superseded",
                    {
                        "summary": "A newer repository revision superseded this job",
                        "revision": revision,
                    },
                    0,
                )
            changed = (
                github.changed_files(spec.repository, project.last_revision, revision)
                if project.last_revision
                else None
            )
            repository = root / "repository"
            github.checkout(spec.repository, revision, repository)
        else:
            repository = root / "repository"
            repository.mkdir()
        spec.route_map = infer_route_map(repository, spec)
        urls = affected_urls(spec, changed) if job.kind == "push" else None
        if urls == []:
            return (
                "complete",
                {"summary": "No affected website routes; model work skipped", "revision": revision},
                0,
            )
        evidence = crawler.collect(project.tenant_id, project.id, spec, urls)
        if not any(item.data.get("status_code") == 200 for item in evidence):
            raise ValueError("No successful public page could be collected")
        if (
            spec.measure_performance
            and spec.environment == "production"
            and (
                context(project.tenant_id, project.id, spec).page_intents.get(
                    str(spec.website_url), True
                )
            )
        ):
            from seo_optimizer.performance import collect_performance

            evidence.append(
                collect_performance(
                    str(spec.website_url),
                    project.tenant_id,
                    project.id,
                    spec.environment,
                    credentials.pagespeed_key,
                )
            )
        if spec.browser_enabled:
            evidence.extend(
                capture_browser(
                    str(spec.website_url),
                    crawler,
                    project.tenant_id,
                    project.id,
                    spec.environment,
                    root / "artifacts",
                )
            )
        project_context = context(project.tenant_id, project.id, spec)
        findings, report = scan(project_context, spec, evidence, self.knowledge)
        changes = builtin_changes(repository, spec, findings, evidence) if spec.auto_fix else []
        usage: dict[str, Any] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "api_cost_usd": 0,
            "electricity_cost_usd": None,
            "hardware_cost_usd": None,
        }
        model_name = "rules"
        if spec.provider.kind != "rules":
            tool_changes: list[FileChange] = []
            trace_failed = False

            def execute(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
                nonlocal trace_failed
                try:
                    if name == "read_file":
                        path = str(arguments["path"])
                        target = confined(repository, path, spec.allowed_paths)
                        if target.stat().st_size > 100000:
                            raise ValueError("File exceeds the read budget")
                        text = target.read_text()
                        item = Evidence(
                            id=str(uuid4()),
                            tenant_id=project.tenant_id,
                            project_id=project.id,
                            environment=spec.environment,
                            kind="source",
                            source_file=path,
                            collected_at=utc_now(),
                            observation="Read current repository file",
                            data={"text": text},
                        )
                        evidence.append(item)
                        return {"success": True, "evidence_id": item.id, "text": text[:20000]}
                    if name in {"inspect_route", "crawl_page"}:
                        url = str(arguments["url"])
                        observed = next((item for item in evidence if str(item.url) == url), None)
                        if observed is None:
                            raise ValueError("Route is outside the collected job scope")
                        return {
                            "success": True,
                            "evidence_id": observed.id,
                            "data": {
                                key: value for key, value in observed.data.items() if key != "html"
                            },
                            "html": str(observed.data.get("html", ""))[:12000],
                        }
                    if name == "get_diff":
                        return {
                            "success": True,
                            "changed_files": changed,
                            "route_map": spec.route_map,
                        }
                    if name == "apply_patch":
                        change = FileChange.model_validate(arguments)
                        confined(repository, change.path, spec.allowed_paths)
                        tool_changes.append(change)
                        return {"success": True, "staged_for_independent_verification": True}
                    if name == "run_checks":
                        return {"success": True, "checks": verify_workspace(repository, spec, {})}
                    raise ValueError("Unknown tool")
                except (ValueError, OSError, KeyError):
                    trace_failed = True
                    return {
                        "success": False,
                        "error": "Tool arguments or project policy prevented the operation",
                    }

            def definition(
                name: str, description: str, properties: dict[str, Any]
            ) -> dict[str, Any]:
                return {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": list(properties),
                        "additionalProperties": False,
                    },
                }

            tools = [
                definition(
                    "read_file",
                    "Read an allowed repository file and obtain its evidence ID",
                    {"path": {"type": "string"}},
                ),
                definition(
                    "inspect_route",
                    "Inspect an already collected route",
                    {"url": {"type": "string"}},
                ),
                definition("get_diff", "Inspect the changed files and route mapping", {}),
                definition("run_checks", "Run explicitly configured isolated verification", {}),
            ]
            if spec.auto_fix:
                tools.append(
                    {
                        "name": "apply_patch",
                        "description": (
                            "Stage a grounded exact replacement for independent validation"
                        ),
                        "parameters": FileChange.model_json_schema(),
                    }
                )
            modules = {self.knowledge.checks[item.check_id].module.value for item in findings}
            if not modules:
                modules = {"content"}
            instructions = (self.knowledge.root / "SKILL.md").read_text()
            for module in sorted(modules)[:2]:
                instructions += (
                    "\n" + (self.knowledge.root / "references" / f"{module}.md").read_text()
                )
            instructions += (
                "\nReturn only an AgentDecision JSON object with findings, changes and summary. "
                "Changes must fix evidenced problems, preserve privacy "
                "and stay within project policy. "
                "Use tools to read exact source before proposing replacements. "
                "No change is better than unsupported work. "
                "Never claim tools have merged or deployed a change."
            )
            observations = [
                {
                    "id": item.id,
                    "url": str(item.url),
                    "kind": item.kind,
                    "excerpt": page_excerpt(str(item.data.get("html", ""))),
                    "status_code": item.data.get("status_code"),
                    "data": item.data if item.kind == "tool" else None,
                }
                for item in (
                    [e for e in evidence if e.kind == "http"][:6]
                    + [e for e in evidence if e.kind != "http"][:6]
                )
            ]
            request = {
                "project": project_context.model_dump(mode="json"),
                "observations": observations,
                "deterministic_findings": [item.model_dump(mode="json") for item in findings[:10]],
                "route_map": spec.route_map,
                "checks": [
                    {"id": item.id, "title": item.title, "sources": item.source_ids}
                    for item in self.knowledge.catalog.checks
                ],
            }
            images = (
                [
                    base64.b64encode(Path(item.screenshot).read_bytes()).decode()
                    for item in evidence
                    if item.kind == "screenshot" and item.screenshot
                ]
                if spec.provider.capabilities.vision
                else []
            )
            client = ModelClient(
                spec.provider,
                credentials.provider_key,
                allow_custom_endpoint=self.settings.allow_private_network,
            )
            try:
                inference = client.complete(
                    instructions,
                    request,
                    tools,
                    execute,
                    spec.max_tool_steps,
                    max(5, spec.max_job_seconds - (time.monotonic() - started)),
                    spec.max_cost_usd,
                    images,
                )
            finally:
                client.close()
            assessment = Assessment(
                tenant_id=project.tenant_id,
                project_id=project.id,
                environment=spec.environment,
                findings=inference.decision.findings,
            )
            errors = validate_assessment(
                assessment,
                AuditRequest(
                    project=project_context,
                    environment=spec.environment,
                    evidence=evidence,
                    allowed_check_ids=list(self.knowledge.checks),
                ),
                self.knowledge,
                spec.provider.capabilities,
            )
            if errors:
                raise ValueError(
                    "Model assessment failed grounding/policy validation: " + errors[0]
                )
            if trace_failed and (inference.decision.changes or tool_changes):
                raise ValueError("Failed model tools prevent automatic publication")
            findings.extend(
                item
                for item in inference.decision.findings
                if item.model_dump() not in [existing.model_dump() for existing in findings]
            )
            candidates = inference.decision.changes + tool_changes
            existing_paths = {change.path for change in changes}
            changes.extend(change for change in candidates if change.path not in existing_paths)
            usage, model_name = inference.usage.model_dump(mode="json"), inference.model
        evidence_by_id = {item.id: item for item in evidence}
        enriched = [
            {
                **finding.model_dump(mode="json"),
                "url": next(
                    (
                        str(evidence_by_id[id].url)
                        for id in finding.evidence_ids
                        if id in evidence_by_id and evidence_by_id[id].url
                    ),
                    None,
                ),
            }
            for finding in findings
        ]
        report.update(findings=len(findings), usage=usage, model=model_name)
        fresh = self.store.remember_findings(
            project.tenant_id,
            project.id,
            enriched,
            [str(item.url) for item in evidence if item.kind == "http"],
        )
        result: dict[str, Any] = {
            "summary": f"Audited {report['pages']} pages; {fresh} new findings",
            "report": report,
            "findings": enriched,
            "revision": revision,
            "audited_urls": [str(item.url) for item in evidence if item.kind == "http"],
            "before_defects": [
                {"check_id": item["check_id"], "url": item["url"]}
                for item in enriched
                if item["status"] == "defect"
            ],
        }
        if not changes or not spec.auto_fix:
            return "complete", result, 0
        result["proposals"] = [change.model_dump(mode="json") for change in changes]
        files = apply_changes(
            repository,
            spec,
            changes,
            set(evidence_by_id),
            {item.check_id for item in findings if item.status == FindingStatus.DEFECT},
        )
        result["verification"] = verify_workspace(repository, spec, files)
        result["fixed_checks"] = sorted({change.check_id for change in changes})
        result["fixed_targets"] = [
            {"check_id": change.check_id, "url": str(evidence_by_id[id].url)}
            for change in changes
            for id in change.evidence_ids
            if evidence_by_id[id].url is not None
        ]
        if time.monotonic() - started > spec.max_job_seconds:
            raise ValueError("Job budget exhausted before publication")
        if spec.local_path and spec.auto_merge:
            result["merged_sha"] = commit_local(
                Path(spec.local_path), repository, spec.branch, revision, list(files)
            )
            after = crawler.collect(project.tenant_id, project.id, spec, result["audited_urls"])
            return self.verify_deployment(spec, result, after, None)
        if github:
            result["pr"] = github.create_pr(
                spec.repository,
                spec.branch,
                revision,
                job.id,
                files,
                "Fixes: " + ", ".join(result["fixed_checks"]),
            )
            result["stage"] = "checks"
            result["summary"] = "Verified changes published to a pull request"
            return "waiting_checks", result, 15
        result["summary"] = "Verified changes prepared; automatic merge is disabled"
        return "complete", result, 0

    def finish_pr(
        self, project: Project, job: Job, spec: ProjectSpec, github: GitHubClient
    ) -> tuple[str, dict[str, Any], float]:
        result = dict(job.result)
        pr = result["pr"]
        current = github.request("GET", f"/repos/{spec.repository}/pulls/{pr['number']}")
        if current.get("head", {}).get("sha") != pr["head_sha"]:
            return "blocked", {**result, "summary": "Pull request revision changed"}, 0
        if current.get("merged"):
            result.update(
                merged_sha=current["merge_commit_sha"],
                stage="deployment",
                summary="Merged revision recovered; waiting for deployment",
            )
            return "waiting_deployment", result, 15
        if current.get("state") == "closed":
            return "blocked", {**result, "summary": "Pull request was closed without merging"}, 0
        ready = github.checks_ready(spec.repository, pr["head_sha"], spec.required_checks)
        if ready == "failed":
            return (
                "blocked",
                {**result, "summary": "Repository checks rejected the proposed change"},
                0,
            )
        if ready == "pending":
            if time.time() - job.created_at > 86400:
                return (
                    "blocked",
                    {**result, "summary": "Required repository checks did not complete"},
                    0,
                )
            return "waiting_checks", result, 30
        if not spec.auto_merge:
            return "complete", {**result, "summary": "Pull request is verified and ready"}, 0
        if github.head(spec.repository, spec.branch) != pr["base_sha"]:
            self.store.enqueue(project.tenant_id, project.id, "audit", "supersede:" + job.id, {})
            return "superseded", {**result, "summary": "Base changed; a fresh audit was queued"}, 0
        merged = github.merge(spec.repository, pr["number"], pr["head_sha"])
        if not merged.get("merged"):
            return (
                "blocked",
                {**result, "summary": "Repository policy prevented automatic merge"},
                0,
            )
        result.update(
            merged_sha=merged["sha"],
            stage="deployment",
            summary="Merged; waiting for deployment confirmation",
        )
        return "waiting_deployment", result, 15

    def verify_deployment(
        self,
        spec: ProjectSpec,
        result: dict[str, Any],
        after: list[Evidence],
        github: GitHubClient | None,
    ) -> tuple[str, dict[str, Any], float]:
        if not after or any(item.data.get("status_code") != 200 for item in after):
            return (
                "blocked",
                {
                    **result,
                    "summary": "Deployment verification is inconclusive; no rollback performed",
                },
                0,
            )
        project_context = context(after[0].tenant_id, after[0].project_id, spec)
        findings, report = scan(project_context, spec, after, self.knowledge)
        fixed = set(result.get("fixed_checks", []))
        after_ids = {item.id: item for item in after}
        targets = {(item["check_id"], item["url"]) for item in result.get("fixed_targets", [])}
        still_broken = [
            item
            for item in findings
            if item.check_id in fixed
            and item.status == FindingStatus.DEFECT
            and (
                not targets
                or any(
                    id in after_ids and (item.check_id, str(after_ids[id].url)) in targets
                    for id in item.evidence_ids
                )
            )
        ]
        before = {(item["check_id"], item["url"]) for item in result.get("before_defects", [])}
        audited_urls = set(result.get("audited_urls", []))
        regressions = [
            item
            for item in findings
            if item.status == FindingStatus.DEFECT
            and any(
                id in after_ids
                and str(after_ids[id].url) in audited_urls
                and (item.check_id, str(after_ids[id].url)) not in before
                for id in item.evidence_ids
            )
        ]
        if still_broken or regressions:
            if github and spec.rollback_on_regression:
                result["rollback_sha"] = github.revert(
                    spec.repository, spec.branch, result["merged_sha"], result["revision"]
                )
            return (
                "blocked",
                {
                    **result,
                    "summary": "Confirmed deployed fix failed verification or introduced a defect",
                    "regressions": len(regressions),
                    "after_report": report,
                },
                0,
            )
        enriched = [
            {
                **item.model_dump(mode="json"),
                "url": next(
                    (
                        str(after_ids[id].url)
                        for id in item.evidence_ids
                        if id in after_ids and after_ids[id].url
                    ),
                    None,
                ),
            }
            for item in findings
        ]
        report.update(
            usage=result.get("report", {}).get("usage"),
            model=result.get("report", {}).get("model", "rules"),
        )
        result.update(
            summary="Changes verified on the deployed website",
            stage="verified",
            report=report,
            verified_fixes=len(targets) if targets else len(fixed),
            after_report=report,
            findings=enriched,
            prior_revision=result.get("revision"),
            revision=result.get("merged_sha", result.get("revision")),
            regressions=0,
        )
        return "complete", result, 0
