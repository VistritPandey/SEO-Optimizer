"""Confirmed defects require a proposal or a scoped, explicit blocker."""

import json

import httpx
import pytest

from seo_optimizer.application_models import AgentDecision, ProviderConfig
from seo_optimizer.contracts import ProviderCapabilities
from seo_optimizer.llm import ModelClient, ModelOutputError, pending_repairs

TARGET = {
    "check_id": "tech.links",
    "url": "https://example.test/",
    "evidence_ids": ["broken-link-page"],
}
PROGRESS = {"summary": "Inspecting the destination"}
BLOCKED = {
    "summary": "The destination requires owner confirmation",
    "findings": [
        {
            "check_id": "tech.links",
            "summary": "The intended destination is not established",
            "status": "unresolved",
            "severity": "medium",
            "evidence_strength": "hypothesis",
            "evidence_ids": ["broken-link-page"],
            "source_ids": ["google-starter"],
            "action": {"kind": "collect_evidence", "rationale": "Confirm destination"},
            "verification_criteria": ["Observe intended destination and source anchor"],
            "dependencies": ["Owner-confirmed intended public destination"],
        }
    ],
}


@pytest.mark.parametrize("always_progress", [False, True])
def test_progress_only_completion_retries_with_tools_then_blocks_at_budget(always_progress):
    seen = []

    def transport(request):
        payload = json.loads(request.content)
        seen.append(payload)
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        PROGRESS if len(seen) == 1 or always_progress else BLOCKED
                    )
                },
                "prompt_eval_count": 10,
                "eval_count": 5,
            },
        )

    with httpx.Client(transport=httpx.MockTransport(transport)) as connection:
        client = ModelClient(
            ProviderConfig(
                kind="ollama",
                model="fixture",
                capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
            ),
            client=connection,
        )
        kwargs = {
            "instructions": "Repair confirmed defects or record missing evidence",
            "request": {"repair_targets": [TARGET]},
            "tools": [{"name": "read_file", "parameters": {"type": "object"}}],
            "execute": lambda *a: {"success": True},
            "max_steps": 3,
        }
        if always_progress:
            with pytest.raises(ModelOutputError) as caught:
                client.complete(**kwargs)
            assert len(seen) == 5
            assert caught.value.usage.input_tokens == 50
            assert "unfinished" in str(caught.value.validation_errors)
        else:
            result = client.complete(**kwargs)
            assert len(seen) == 2
            assert result.decision.findings[0].status == "unresolved"
        assert seen[1]["tools"], "A semantic retry must retain remaining tools"
        assert "Unhandled confirmed targets" in seen[1]["messages"][-1]["content"]


def test_repair_completion_requires_matching_check_and_page_evidence():
    request = {"repair_targets": [TARGET]}
    assert pending_repairs(request, AgentDecision.model_validate(BLOCKED), []) == []
    unrelated = json.loads(json.dumps(BLOCKED))
    unrelated["findings"][0]["evidence_ids"] = ["another-page"]
    assert pending_repairs(request, AgentDecision.model_validate(unrelated), []) == [TARGET]
    patch = {
        "path": "web/index.html",
        "check_id": "tech.links",
        "evidence_ids": ["broken-link-page", "source-read"],
    }
    trace = [{"name": "apply_patch", "success": True, "arguments": patch}]
    assert pending_repairs(request, AgentDecision(), trace) == []
    trace.append(
        {"name": "apply_patch", "success": False, "arguments": {**patch, "check_id": "other"}}
    )
    assert pending_repairs(request, AgentDecision(), trace) == []
    trace.append(
        {"name": "apply_patch", "success": True, "arguments": {**patch, "check_id": "other"}}
    )
    assert pending_repairs(request, AgentDecision(), trace) == [TARGET]


def test_every_configured_tool_round_is_available_before_final_schema_output():
    seen = []
    executed = []

    def transport(request):
        payload = json.loads(request.content)
        seen.append(payload)
        message = (
            {
                "tool_calls": [
                    {"function": {"name": "read_file", "arguments": {"path": "web/index.html"}}}
                ]
            }
            if len(seen) <= 2
            else {"content": json.dumps({"summary": "Observed"})}
        )
        return httpx.Response(200, json={"message": message})

    with httpx.Client(transport=httpx.MockTransport(transport)) as connection:
        client = ModelClient(
            ProviderConfig(
                kind="ollama",
                model="fixture",
                capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
            ),
            client=connection,
        )
        client.complete(
            "Inspect",
            {},
            [{"name": "read_file", "parameters": {"type": "object"}}],
            lambda name, args: executed.append(name) or {"success": True},
            max_steps=2,
        )
    assert executed == ["read_file", "read_file"]
    assert all(payload.get("tools") and "format" not in payload for payload in seen[:2])
    assert "tools" not in seen[2] and seen[2]["format"]
