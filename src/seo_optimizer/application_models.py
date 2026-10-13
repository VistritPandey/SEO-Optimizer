"""Management API contracts, independent of templates and transport adapters."""

import re
from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import Field, HttpUrl, model_validator

from seo_optimizer.contracts import (
    Contract,
    Finding,
    ProviderCapabilities,
    TrustedFact,
    WebsiteType,
)


class ProviderConfig(Contract):
    kind: Literal["rules", "ollama", "openai", "anthropic", "google"] = "rules"
    model: str = ""
    base_url: str | None = None
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)
    max_output_tokens: int = Field(default=4096, ge=256, le=16384)
    max_total_tokens: int = Field(default=100_000, ge=1024, le=1_000_000)
    max_calls_per_step: int = Field(default=8, ge=1, le=16)
    request_timeout_seconds: int = Field(default=180, ge=5, le=300)
    ollama_think: bool | str | None = False
    ollama_num_ctx: int = Field(default=8192, ge=2048, le=32768)
    input_usd_per_million: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    output_usd_per_million: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class ProjectSpec(Contract):
    name: str = Field(min_length=1, max_length=100)
    website_url: HttpUrl
    repository: str = ""
    local_path: str | None = None
    branch: str = "main"
    environment: str = "production"
    website_types: list[WebsiteType] = Field(default_factory=lambda: [WebsiteType.GENERIC])
    allowed_paths: list[str] = Field(
        default_factory=lambda: [
            "public",
            "web",
            "src",
            "content",
            "app",
            "pages",
            "templates",
            "index.html",
        ]
    )
    monitored_paths: list[str] = Field(default_factory=list)
    audit_dependencies: list[str] = Field(
        default_factory=lambda: [
            "package.json",
            "next.config.js",
            "next.config.ts",
            "next.config.mjs",
            "astro.config.mjs",
            "svelte.config.js",
            "nuxt.config.ts",
            "vite.config.ts",
            "robots.txt",
            "sitemap.xml",
            "sitemap_index.xml",
        ]
    )
    page_intents: dict[str, bool] = Field(default_factory=dict)
    route_map: dict[str, str] = Field(default_factory=dict)
    facts: list[TrustedFact] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    crawler_preferences: dict[str, Literal["allow", "block", "unchanged"]] = Field(
        default_factory=dict
    )
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    enabled: bool = True
    auto_merge: bool = True
    auto_fix: bool = True
    allow_content_publication: bool = False
    auto_content_refresh: bool = False
    max_pages: int = Field(default=25, ge=1, le=100)
    max_files_changed: int = Field(default=5, ge=1, le=20)
    max_tool_steps: int = Field(default=6, ge=1, le=12)
    max_job_seconds: int = Field(default=480, ge=30, le=600)
    max_cost_usd: float = Field(default=2.0, gt=0, le=100, allow_inf_nan=False)
    reconcile_seconds: int = Field(default=3600, ge=300, le=604800)
    required_checks: list[str] = Field(default_factory=list)
    check_commands: list[list[str]] = Field(default_factory=list)
    sandbox_image: str = "python:3.12-slim"
    browser_enabled: bool = False
    measure_performance: bool = False
    rollback_on_regression: bool = True

    @model_validator(mode="after")
    def valid_repository(self) -> Self:
        if self.repository and not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository
        ):
            raise ValueError("repository must be owner/name")
        if self.repository and self.local_path:
            raise ValueError("choose a GitHub repository or a local repository")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]*", self.branch) or ".." in self.branch:
            raise ValueError("invalid branch")
        for path in (
            self.allowed_paths
            + self.monitored_paths
            + self.audit_dependencies
            + list(self.route_map.values())
        ):
            value = PurePosixPath(path)
            if value.is_absolute() or ".." in value.parts or str(value) == "." or "\\" in path:
                raise ValueError("repository paths must be confined relative paths")
        if self.provider.kind not in {"rules", "ollama"} and not self.provider.model:
            raise ValueError("cloud provider requires an explicit model identifier")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:@-]*", self.sandbox_image):
            raise ValueError("invalid sandbox image identifier")
        return self


class ProjectSecrets(Contract):
    provider_key: str = ""
    pagespeed_key: str = ""
    search_console_access_token: str = ""
    github_token: str = ""
    webhook_secret: str = ""
    github_app_id: str = ""
    github_installation_id: str = ""
    github_private_key: str = ""


class ProjectCreate(Contract):
    spec: ProjectSpec
    credentials: ProjectSecrets = Field(default_factory=ProjectSecrets)


class FileChange(Contract):
    path: str
    before: str = Field(max_length=100000)
    after: str = Field(max_length=100000)
    reason: str = Field(min_length=1)
    check_id: str
    evidence_ids: list[str] = Field(min_length=1)
    fact_ids: list[str] = Field(default_factory=list)


class AgentDecision(Contract):
    findings: list[Finding] = Field(default_factory=list)
    changes: list[FileChange] = Field(default_factory=list)
    summary: str = ""


class Registration(Contract):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=256)

    @model_validator(mode="after")
    def normalize_email(self) -> Self:
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.email):
            raise ValueError("invalid email")
        object.__setattr__(self, "email", self.email.strip().lower())
        return self
