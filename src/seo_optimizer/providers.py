"""Adapter contracts and a saved-response implementation; no model SDK dependency."""

from typing import Protocol

from pydantic import JsonValue

from seo_optimizer.contracts import (
    Assessment,
    Evidence,
    ProjectContext,
    ProviderCapabilities,
    ResponseRecord,
    ToolCall,
    ToolResult,
)


class Provider(Protocol):
    @property
    def capabilities(self) -> ProviderCapabilities: ...

    def assess(
        self, project: ProjectContext, evidence: list[Evidence],
        instructions: str, output_schema: dict[str, JsonValue],
    ) -> ResponseRecord: ...


class ToolExecutor(Protocol):
    def execute(self, project: ProjectContext, call: ToolCall) -> ToolResult: ...


class SavedResponseProvider:
    """Explicitly an offline replay, not evidence of a live provider's capability."""

    def __init__(self, response: ResponseRecord):
        self.response = response

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self.response.capabilities

    def assess(
        self, project: ProjectContext, evidence: list[Evidence],
        instructions: str, output_schema: dict[str, JsonValue],
    ) -> ResponseRecord:
        return self.response


def parse_assessment(raw: str) -> Assessment:
    # No markdown stripping or silent repairs: malformed outputs remain visible.
    return Assessment.model_validate_json(raw)
