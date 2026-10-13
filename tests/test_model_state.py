"""Compute reuse must follow stable evidence, current policy and actual tool verification."""

import json
from datetime import timedelta

import httpx
import pytest

from seo_optimizer.application_models import ProjectSpec, ProviderConfig
from seo_optimizer.contracts import Evidence, ProviderCapabilities, utc_now
from seo_optimizer.growth import Workspace
from seo_optimizer.knowledge import load_knowledge
from seo_optimizer.llm import ModelClient
from seo_optimizer.state import input_fingerprint


def test_model_input_fingerprint_excludes_collection_ids_but_keeps_policy_revision_and_content():
    spec = ProjectSpec(name="Guide", website_url="https://example.test/")
    evidence = [
        Evidence(
            id="one",
            tenant_id="tenant",
            project_id="project",
            environment="production",
            kind="http",
            url="https://example.test/",
            collected_at=utc_now(),
            observation="Collected page",
            data={"html": "<title>Guide</title>", "status_code": 200},
        )
    ]
    knowledge = load_knowledge()

    def fingerprint(revision="a"):
        return input_fingerprint(spec, evidence, revision, Workspace(), knowledge, True)

    original = fingerprint()
    evidence[0].id = "fresh-id"
    evidence[0].collected_at = utc_now() + timedelta(seconds=1)
    assert fingerprint() == original
    assert fingerprint("b") != original
    spec.goals = ["New business goal"]
    assert fingerprint() != original
    changed = fingerprint()
    evidence[0].data["html"] = "<title>Changed guide</title>"
    assert fingerprint() != changed


@pytest.mark.parametrize("verified", [True, False])
def test_tool_finalization_requires_actual_staged_verification(verified):
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return httpx.Response(
                200,
                json={
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{"function": {"name": "run_checks", "arguments": {}}}],
                    },
                    "prompt_eval_count": 10,
                    "eval_count": 2,
                },
            )
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {"findings": [], "changes": [], "summary": "Nothing verified"}
                    ),
                },
                "prompt_eval_count": 10,
                "eval_count": 2,
            },
        )

    config = ProviderConfig(
        kind="ollama",
        model="fixture",
        capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
    )
    client = ModelClient(config, client=httpx.Client(transport=httpx.MockTransport(respond)))
    tool = {
        "name": "run_checks",
        "description": "Independent verification",
        "parameters": {"type": "object", "properties": {}},
    }
    result = client.complete(
        "Task",
        {},
        [tool],
        lambda *_: {
            "success": verified,
            "scope": "staged_proposals" if verified else "original_snapshot",
            "ready_for_publication": verified,
        },
        stop_after_verified_tools=True,
    )
    assert result.finalized_from_tools is verified
    assert len(calls) == (1 if verified else 2)
    assert result.usage.input_tokens == (10 if verified else 20)
    client.close()
