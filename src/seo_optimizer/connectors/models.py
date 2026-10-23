"""Bounded connector contracts. Credentials never appear in public connection records."""

from datetime import date
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import AwareDatetime, Field, field_validator, model_validator

from seo_optimizer.contracts import Contract, utc_now


class Platform(StrEnum):
    SEARCH_CONSOLE = "search_console"
    WORDPRESS = "wordpress"
    WOOCOMMERCE = "woocommerce"
    SHOPIFY = "shopify"
    WEBFLOW = "webflow"
    GA4 = "ga4"
    VERCEL = "vercel"
    NETLIFY = "netlify"
    DEPLOYMENT = "deployment"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    BING = "bing"
    BUSINESS_PROFILE = "business_profile"
    CLOUDFLARE = "cloudflare"
    SERVER_LOGS = "server_logs"
    WIX = "wix"
    SQUARESPACE = "squarespace"
    FRAMER = "framer"
    SANITY = "sanity"
    CONTENTFUL = "contentful"
    DATAFORSEO = "dataforseo"
    AI_VISIBILITY = "ai_visibility"


class ConnectionInput(Contract):
    platform: Platform
    label: str = Field(default="", max_length=100)
    resource: str = Field(default="", max_length=500)
    options: dict[str, str] = Field(default_factory=dict, max_length=20)
    credentials: dict[str, str] = Field(
        default_factory=dict, max_length=12, repr=False, json_schema_extra={"writeOnly": True}
    )
    allow_writes: bool = False
    auto_apply: bool = False
    interval_seconds: int = Field(default=86400, ge=3600, le=604800)
    enabled: bool = True

    @field_validator("options", "credentials")
    @classmethod
    def bounded_values(cls, value: dict[str, str]) -> dict[str, str]:
        if any(len(k) > 100 or len(v) > 16000 for k, v in value.items()):
            raise ValueError("Connector configuration exceeds its limit")
        return value

    @model_validator(mode="after")
    def write_policy(self) -> Self:
        if self.auto_apply and not self.allow_writes:
            raise ValueError("Automatic publication requires write permission")
        return self


class CollectionRequest(Contract):
    start: date = Field(default_factory=lambda: utc_now().date())
    end: date = Field(default_factory=lambda: utc_now().date())
    limit: int = Field(default=50, ge=1, le=100)
    resource_id: str = Field(default="", max_length=300)
    query: str = Field(default="", max_length=500)
    market: str = Field(default="United States", min_length=1, max_length=100)
    model: str = Field(default="", max_length=100)
    engine: Literal["openai", "anthropic", "google", "perplexity"] = "google"
    experiment: str = Field(default="visibility", max_length=100)

    @model_validator(mode="after")
    def window(self) -> Self:
        if (
            self.end < self.start
            or self.end > utc_now().date()
            or (self.end - self.start).days > 90
        ):
            raise ValueError("Use a past measurement window of at most 91 days")
        return self


class Resource(Contract):
    id: str = Field(min_length=1, max_length=1000)
    kind: str
    fields: dict[str, Any]
    revision: str = ""
    url: str = ""


class Collection(Contract):
    platform: Platform
    collected_at: AwareDatetime = Field(default_factory=utc_now)
    records: list[Resource] = Field(default_factory=list, max_length=100)
    complete: bool = False
    warnings: list[str] = Field(default_factory=list)
    cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    measurement: Literal[
        "content",
        "search",
        "analytics",
        "deployment",
        "crawler",
        "api_experiment",
        "consumer_observation",
    ] = "content"


class ProposalInput(Contract):
    resource_id: str = Field(min_length=1, max_length=300)
    verification_url: str = Field(default="", max_length=2000)
    changes: dict[str, str] = Field(min_length=1, max_length=8)
    reason: str = Field(min_length=10, max_length=2000)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)
    fact_ids: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("changes")
    @classmethod
    def bounded_changes(cls, value: dict[str, str]) -> dict[str, str]:
        if any(len(v) > 20000 or len(k) > 200 for k, v in value.items()):
            raise ValueError("Change exceeds the publication budget")
        return value


class DeploymentEvent(Contract):
    event_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:-]+$")
    resource: str = Field(min_length=1, max_length=500)
    environment: str = Field(default="production", max_length=100)
    revision: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2000)
    occurred_at: AwareDatetime
    status: Literal["succeeded", "failed"]
    changed_paths: list[str] = Field(default_factory=list, max_length=100)


class ImportRequest(Contract):
    kind: Literal["crawler", "consumer_observation"]
    records: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    source: str = Field(min_length=5, max_length=500)
