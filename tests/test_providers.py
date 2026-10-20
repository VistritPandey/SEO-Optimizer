import json

import httpx
import pytest

from seo_optimizer.application_models import ProviderConfig
from seo_optimizer.contracts import ProviderCapabilities
from seo_optimizer.llm import ModelClient, ProviderError

FINAL = {"findings": [], "changes": [], "summary": "No unsupported work needed."}
TOOL = {
    "name": "read_file",
    "description": "Read a permitted file",
    "parameters": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "additionalProperties": False,
    },
}


@pytest.mark.parametrize("kind", ["ollama", "openai", "anthropic", "google"])
def test_native_tool_loop_and_usage(kind):
    seen = []

    def transport(request):
        payload = json.loads(request.content)
        seen.append(payload)
        first = len(seen) == 1
        if kind == "ollama":
            return httpx.Response(
                200,
                json={
                    "message": {
                        "role": "assistant",
                        "content": "" if first else json.dumps(FINAL),
                        **(
                            {
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "read_file",
                                            "arguments": {"path": "web/index.html"},
                                        }
                                    }
                                ]
                            }
                            if first
                            else {}
                        ),
                    },
                    "prompt_eval_count": 10,
                    "eval_count": 5,
                },
            )
        if kind == "openai":
            output = (
                [
                    {
                        "type": "function_call",
                        "call_id": "one",
                        "name": "read_file",
                        "arguments": '{"path":"web/index.html"}',
                    }
                ]
                if first
                else [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": json.dumps(FINAL)}],
                    }
                ]
            )
            return httpx.Response(
                200, json={"output": output, "usage": {"input_tokens": 10, "output_tokens": 5}}
            )
        if kind == "anthropic":
            content = (
                [
                    {
                        "type": "tool_use",
                        "id": "one",
                        "name": "read_file",
                        "input": {"path": "web/index.html"},
                    }
                ]
                if first
                else [{"type": "text", "text": json.dumps(FINAL)}]
            )
            return httpx.Response(
                200, json={"content": content, "usage": {"input_tokens": 10, "output_tokens": 5}}
            )
        parts = (
            [
                {
                    "functionCall": {"name": "read_file", "args": {"path": "web/index.html"}},
                    "thoughtSignature": "cmV0YWluLXRoaXM=",
                }
            ]
            if first
            else [{"text": json.dumps(FINAL)}]
        )
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": parts}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
            },
        )

    config = ProviderConfig(
        kind=kind,
        model="fixture-model",
        capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
    )
    called = []

    def execute(name, args):
        called.append((name, args))
        return {"success": True, "text": "observed source"}

    client = ModelClient(
        config, "fixture-key", httpx.Client(transport=httpx.MockTransport(transport))
    )
    result = client.complete("Return JSON", {}, [TOOL], execute, max_steps=3)
    assert result.decision.summary == FINAL["summary"]
    assert called == [("read_file", {"path": "web/index.html"})]
    assert result.usage.input_tokens == 20 and result.usage.output_tokens == 10
    assert len(result.tool_trace) == 1 and result.tool_trace[0]["success"]
    if kind == "google":
        assert seen[1]["contents"][1]["parts"][0]["thoughtSignature"] == "cmV0YWluLXRoaXM="


def test_missing_credentials_and_budget_stop():
    client = ModelClient(ProviderConfig(kind="openai", model="fixture"))
    with pytest.raises(ProviderError, match="credential"):
        client.complete("", {}, [], lambda n, a: {})
    client.close()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "message": {"content": json.dumps(FINAL)},
                "prompt_eval_count": 1000000,
                "eval_count": 1000000,
            },
        )
    )
    client = ModelClient(
        ProviderConfig(
            kind="ollama", model="fixture", input_usd_per_million=2, output_usd_per_million=2
        ),
        client=httpx.Client(transport=transport),
    )
    with pytest.raises(ProviderError, match="budget"):
        client.complete("", {}, [], lambda n, a: {}, max_cost=0.01)


def test_unsupported_vision_rejected():
    client = ModelClient(ProviderConfig(kind="ollama", model="fixture"))
    with pytest.raises(ProviderError, match="Vision"):
        client.complete("", {}, [], lambda n, a: {}, images=["image"])
    client.close()


def test_missing_usage_remains_unknown_with_configured_prices():
    client = ModelClient(
        ProviderConfig(
            kind="openai", model="fixture", input_usd_per_million=1, output_usd_per_million=1
        ),
        "fixture-key",
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "output": [
                            {
                                "type": "message",
                                "role": "assistant",
                                "content": [{"type": "output_text", "text": json.dumps(FINAL)}],
                            }
                        ],
                    },
                )
            )
        ),
    )
    result = client.complete("Return JSON", {}, [], lambda n, a: {})
    assert result.usage.input_tokens is None and result.usage.output_tokens is None
    assert result.usage.api_cost_usd is None


def test_final_schema_correction_has_a_reserved_round_and_no_additional_tools():
    seen = []

    def transport(request):
        payload = json.loads(request.content)
        seen.append(payload)
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": (
                        json.dumps(
                            {
                                **FINAL,
                                "check_reviews": [
                                    {
                                        "check_id": "tech.metadata",
                                        "state": "healthy",
                                        "reason": "Observed",
                                        "evidence_ids": [],
                                    }
                                ],
                            }
                        )
                        if len(seen) == 1
                        else json.dumps(FINAL)
                    ),
                },
                "prompt_eval_count": 10,
                "eval_count": 5,
            },
        )

    client = ModelClient(
        ProviderConfig(
            kind="ollama",
            model="fixture",
            capabilities=ProviderCapabilities(json_schema=True),
        ),
        client=httpx.Client(transport=httpx.MockTransport(transport)),
    )
    try:
        result = client.complete("Return grounded JSON", {}, [TOOL], lambda *a: {}, max_steps=1)
        assert len(seen) == 2 and result.usage.input_tokens == 20
        assert not seen[1].get("tools")
        correction = seen[1]["messages"][-1]["content"]
        assert "check_reviews.0" in correction and "value_error" in correction
        assert '"input"' not in correction
    finally:
        client.client.close()


def test_invalid_final_preserves_usage_and_safe_validation_locations():
    from seo_optimizer.llm import ModelOutputError

    client = ModelClient(
        ProviderConfig(kind="ollama", model="fixture"),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={
                        "message": {"content": '{"summary": 123, "unexpected": "private-input"}'},
                        "prompt_eval_count": 10,
                        "eval_count": 5,
                    },
                )
            )
        ),
    )
    try:
        with pytest.raises(ModelOutputError) as caught:
            client.complete("JSON", {}, [], lambda *a: {}, max_steps=1)
        error = caught.value
        assert error.usage.input_tokens == 10 and error.runtime_ms >= 0
        assert "private-input" not in json.dumps(error.validation_errors)
        assert any(e["path"] == "unexpected" for e in error.validation_errors)
    finally:
        client.client.close()
