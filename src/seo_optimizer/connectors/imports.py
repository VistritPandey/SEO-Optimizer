"Evidence imports exclude visitor identifiers and separate observed consumer answers."

from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import AwareDatetime, Field, TypeAdapter

from seo_optimizer.connectors.models import Collection, ImportRequest, Platform, Resource
from seo_optimizer.connectors.transport import ConnectorError
from seo_optimizer.connectors.visibility import safe_citations
from seo_optimizer.contracts import Contract, utc_now


class LogRow(Contract):
    path: str = Field(min_length=1, max_length=2000)
    status: int = Field(ge=100, le=599)
    user_agent: str = Field(default="", max_length=500)
    occurred_at: AwareDatetime
    count: int = Field(default=1, ge=1, le=1000000)


class AnswerRow(Contract):
    query: str = Field(min_length=1, max_length=500)
    engine: str = Field(min_length=1, max_length=100)
    engine_version: str = Field(default="unknown", max_length=100)
    market: str = Field(min_length=1, max_length=100)
    answer: str = Field(min_length=1, max_length=20000)
    cited_urls: list[str] = Field(default_factory=list, max_length=100)
    observed_at: AwareDatetime
    experiment: str = Field(default="consumer-observation", max_length=100)


def normalize_import(p: Platform, value: ImportRequest, website: str) -> Collection:
    records = []
    measurement: Any = value.kind
    if (
        (p == Platform.SERVER_LOGS and value.kind != "crawler")
        or (p == Platform.AI_VISIBILITY and value.kind != "consumer_observation")
        or p not in {Platform.SERVER_LOGS, Platform.AI_VISIBILITY}
    ):
        raise ConnectorError("policy", "Import type does not match this connector")
    for item in value.records:
        if value.kind == "crawler":
            row = LogRow.model_validate(item)
            if not row.path.startswith("/") or row.path.startswith("//") or "?" in row.path:
                raise ConnectorError(
                    "policy", "Log paths must omit query strings and visitor identifiers"
                )
            fields = row.model_dump(mode="json")
            fields.update(source=value.source, identity_verified=False)
            measurement = "crawler"
        else:
            answer = AnswerRow.model_validate(item)
            fields = answer.model_dump(mode="json")
            fields["cited_urls"] = safe_citations(answer.cited_urls)
            fields.update(
                source=value.source,
                citation_accuracy="unreviewed",
                target_cited=any(
                    urlparse(url).hostname == urlparse(website).hostname
                    for url in fields["cited_urls"]
                ),
            )
        observed = fields.get("occurred_at", fields.get("observed_at"))
        if TypeAdapter(AwareDatetime).validate_python(observed) > utc_now():
            raise ConnectorError("policy", "Observations cannot be from the future")
        records.append(Resource(id=str(uuid4()), kind=value.kind, fields=fields))
    return Collection(
        platform=p,
        records=records,
        measurement=measurement,
        warnings=[
            (
                "Imported evidence is owner supplied; collection provenance and authenticity"
                " are not independently verified."
            ),
            (
                "Crawler user agents do not establish identity. Consumer observations are "
                "separate from API experiments and universal rankings."
            ),
        ],
    )
