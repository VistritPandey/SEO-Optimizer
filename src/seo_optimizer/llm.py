"""Native provider adapters with a bounded, normalized tool loop and usage ledger."""

import copy
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from seo_optimizer.application_models import AgentDecision, ProviderConfig
from seo_optimizer.contracts import Usage

DEFAULT_URLS = {
    "ollama": "http://127.0.0.1:11434",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
}


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Compile bounded objects to the strict provider subset; retain local validation."""
    value = copy.deepcopy(schema)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for item in list(node.values()):
                visit(item)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(value)
    return value


@dataclass
class Inference:
    decision: AgentDecision
    usage: Usage
    model: str
    runtime_ms: float
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    finalized_from_tools: bool = False


class ProviderError(RuntimeError):
    pass


class ModelClient:
    def __init__(
        self,
        config: ProviderConfig,
        key: str = "",
        client: httpx.Client | None = None,
        allow_custom_endpoint: bool = True,
    ):
        self.config, self.key = config, key
        self.client = client or httpx.Client(
            timeout=config.request_timeout_seconds, follow_redirects=False
        )
        self.owns_client = client is None
        self.url = (config.base_url or DEFAULT_URLS.get(config.kind, "")).rstrip("/")
        parts = urlparse(self.url)
        if parts.scheme not in {"http", "https"} or parts.username or parts.password:
            self.close()
            raise ProviderError("Invalid provider endpoint")
        if not allow_custom_endpoint and self.url != DEFAULT_URLS.get(config.kind):
            self.close()
            raise ProviderError("Custom model endpoints are disabled on this shared worker")
        if not allow_custom_endpoint and config.kind == "ollama":
            self.close()
            raise ProviderError("Local models require an account-scoped local worker")

    def close(self) -> None:
        if self.owns_client:
            self.client.close()

    def _post(self, path: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        if self.config.kind == "google":
            return self._google_sdk(payload)
        response = self.client.post(self.url + path, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ProviderError(f"Provider returned HTTP {response.status_code}")
        result: dict[str, Any] = response.json()
        return result

    def _google_sdk(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Use the current official SDK, while keeping tool execution in our bounded loop."""
        from google import genai
        from google.genai import errors, types

        timeout = self.client.timeout.read or self.config.request_timeout_seconds
        sdk = genai.Client(
            api_key=self.key,
            http_options=types.HttpOptions(
                base_url=self.url.removesuffix("/v1beta"),
                api_version="v1beta",
                httpx_client=self.client,
                timeout=int(timeout * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        config = {
            **payload["generationConfig"],
            "system_instruction": payload["systemInstruction"],
            "automatic_function_calling": {"disable": True},
        }
        if payload.get("tools"):
            config["tools"] = payload["tools"]
        try:
            response = sdk.models.generate_content(
                model=self.config.model,
                contents=payload["contents"],
                config=types.GenerateContentConfig.model_validate(config),
            )
            result: dict[str, Any] = response.model_dump(
                mode="json", by_alias=True, exclude_none=True, exclude={"text", "parsed"}
            )
            return result
        except errors.APIError as error:
            # Provider messages can contain request data; expose only the status code.
            raise ProviderError(f"Provider returned HTTP {error.code}") from None
        finally:
            sdk.close()

    def models(self) -> list[str]:
        if self.config.kind != "ollama":
            return [self.config.model] if self.config.model else []
        response = self.client.get(self.url + "/api/tags")
        response.raise_for_status()
        return [item["name"] for item in response.json().get("models", [])]

    def complete(
        self,
        instructions: str,
        request: dict[str, Any],
        tools: list[dict[str, Any]],
        execute: Callable[[str, dict[str, Any]], dict[str, Any]],
        max_steps: int = 6,
        max_seconds: float = 480,
        max_cost: float = 2,
        images: list[str] | None = None,
        stop_after_verified_tools: bool = False,
    ) -> Inference:
        kind, model = self.config.kind, self.config.model
        if kind == "rules":
            raise ProviderError("Rules mode does not invoke an LLM")
        if kind != "ollama" and not self.key:
            raise ProviderError("Provider credential is not configured")
        if not model:
            available = self.models()
            if not available:
                raise ProviderError("No local model is installed")
            model = available[0]
        if images and not self.config.capabilities.vision:
            raise ProviderError("Vision capability is not enabled for this model")
        schema = strict_schema(AgentDecision.model_json_schema())
        content = json.dumps(request)
        history: list[dict[str, Any]] = [{"role": "user", "content": content}]
        if images:
            history[0]["images"] = images
        native_input: list[dict[str, Any]] = [{"role": "user", "content": content}]
        if images:
            native_input[0]["content"] = [
                {"type": "input_text", "text": content},
                *[
                    {"type": "input_image", "image_url": "data:image/png;base64," + item}
                    for item in images
                ],
            ]
        google_history: list[dict[str, Any]] = [{"role": "user", "parts": [{"text": content}]}]
        if images:
            google_history[0]["parts"].extend(
                [{"inlineData": {"mimeType": "image/png", "data": image}} for image in images]
            )
        input_tokens, output_tokens = 0, 0
        input_available, output_available = True, True
        trace: list[dict[str, Any]] = []
        started = time.monotonic()
        for step in range(max_steps):
            if time.monotonic() - started > max_seconds:
                raise ProviderError("Model time budget exhausted")
            self.client.timeout = httpx.Timeout(
                max(
                    0.1,
                    min(
                        self.config.request_timeout_seconds,
                        max_seconds - (time.monotonic() - started),
                    ),
                )
            )
            definitions = (
                tools if self.config.capabilities.tool_calling and step < max_steps - 1 else []
            )
            calls: list[dict[str, Any]] = []
            text = ""
            if kind == "ollama":
                payload: dict[str, Any] = {
                    "model": model,
                    "stream": False,
                    "think": self.config.ollama_think,
                    "messages": [{"role": "system", "content": instructions}, *history],
                    "options": {
                        "temperature": 0,
                        "num_predict": self.config.max_output_tokens,
                        "num_ctx": self.config.ollama_num_ctx,
                    },
                }
                if self.config.capabilities.json_schema and (
                    not definitions or step == max_steps - 1
                ):
                    payload["format"] = schema
                if definitions:
                    payload["tools"] = [
                        {"type": "function", "function": item} for item in definitions
                    ]
                result = self._post("/api/chat", payload, {})
                message = result["message"]
                input_available &= "prompt_eval_count" in result
                output_available &= "eval_count" in result
                text = message.get("content", "")
                input_tokens += result.get("prompt_eval_count", 0)
                output_tokens += result.get("eval_count", 0)
                history.append(message)
                calls = [
                    {
                        "id": f"{step}-{index}",
                        "name": item["function"]["name"],
                        "arguments": item["function"]["arguments"],
                    }
                    for index, item in enumerate(message.get("tool_calls", []))
                ]
            elif kind == "openai":
                payload = {
                    "model": model,
                    "instructions": instructions,
                    "input": native_input,
                    "max_output_tokens": self.config.max_output_tokens,
                    "store": False,
                }
                if definitions:
                    payload["tools"] = [
                        {
                            "type": "function",
                            **item,
                            "strict": True,
                            "parameters": strict_schema(item["parameters"]),
                        }
                        for item in definitions
                    ]
                payload["text"] = (
                    {
                        "format": {
                            "type": "json_schema",
                            "name": "optimization",
                            "strict": True,
                            "schema": schema,
                        }
                    }
                    if self.config.capabilities.json_schema
                    else {"format": {"type": "json_object"}}
                )
                result = self._post("/responses", payload, {"Authorization": f"Bearer {self.key}"})
                native_input.extend(result.get("output", []))
                input_available &= "input_tokens" in result.get("usage", {})
                output_available &= "output_tokens" in result.get("usage", {})
                input_tokens += result.get("usage", {}).get("input_tokens", 0)
                output_tokens += result.get("usage", {}).get("output_tokens", 0)
                for item in result.get("output", []):
                    if item["type"] == "function_call":
                        calls.append(
                            {
                                "id": item["call_id"],
                                "name": item["name"],
                                "arguments": json.loads(item["arguments"]),
                            }
                        )
                    elif item["type"] == "message":
                        text += "".join(part.get("text", "") for part in item.get("content", []))
            elif kind == "anthropic":
                messages = copy.deepcopy(history)
                if images and step == 0:
                    messages[0]["content"] = [
                        {"type": "text", "text": content},
                        *[
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image,
                                },
                            }
                            for image in images
                        ],
                    ]
                payload = {
                    "model": model,
                    "system": instructions,
                    "messages": messages,
                    "max_tokens": self.config.max_output_tokens,
                }
                if definitions:
                    payload["tools"] = [
                        {
                            "name": item["name"],
                            "description": item["description"],
                            "input_schema": item["parameters"],
                        }
                        for item in definitions
                    ]
                if self.config.capabilities.json_schema:
                    payload["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
                result = self._post(
                    "/messages", payload, {"x-api-key": self.key, "anthropic-version": "2023-06-01"}
                )
                history.append({"role": "assistant", "content": result["content"]})
                input_available &= "input_tokens" in result.get("usage", {})
                output_available &= "output_tokens" in result.get("usage", {})
                input_tokens += result.get("usage", {}).get("input_tokens", 0)
                output_tokens += result.get("usage", {}).get("output_tokens", 0)
                for item in result["content"]:
                    if item["type"] == "tool_use":
                        calls.append(
                            {"id": item["id"], "name": item["name"], "arguments": item["input"]}
                        )
                    elif item["type"] == "text":
                        text += item["text"]
            else:
                payload = {
                    "systemInstruction": {"parts": [{"text": instructions}]},
                    "contents": google_history,
                    "generationConfig": {
                        "maxOutputTokens": self.config.max_output_tokens,
                        "temperature": 0,
                    },
                }
                if definitions:
                    payload["tools"] = [
                        {
                            "functionDeclarations": [
                                {
                                    "name": item["name"],
                                    "description": item["description"],
                                    "parametersJsonSchema": item["parameters"],
                                }
                                for item in definitions
                            ]
                        }
                    ]
                if self.config.capabilities.json_schema and not definitions:
                    payload["generationConfig"].update(
                        responseMimeType="application/json", responseJsonSchema=schema
                    )
                result = self._post(
                    f"/models/{model}:generateContent", payload, {"x-goog-api-key": self.key}
                )
                input_available &= "promptTokenCount" in result.get("usageMetadata", {})
                output_available &= "candidatesTokenCount" in result.get("usageMetadata", {})
                message = result.get("candidates", [{}])[0].get("content", {})
                google_history.append(message)
                input_tokens += result.get("usageMetadata", {}).get("promptTokenCount", 0)
                output_tokens += result.get("usageMetadata", {}).get("candidatesTokenCount", 0)
                output_tokens += result.get("usageMetadata", {}).get("thoughtsTokenCount", 0)
                for index, item in enumerate(message.get("parts", [])):
                    if "functionCall" in item:
                        function = item["functionCall"]
                        calls.append(
                            {
                                "id": function.get("id", f"{step}-{index}"),
                                "name": function["name"],
                                "arguments": function.get("args", {}),
                            }
                        )
                    else:
                        text += item.get("text", "")
            cost = None
            if (
                input_available
                and output_available
                and self.config.input_usd_per_million is not None
                and self.config.output_usd_per_million is not None
            ):
                cost = (
                    input_tokens * self.config.input_usd_per_million
                    + output_tokens * self.config.output_usd_per_million
                ) / 1_000_000
                if cost > max_cost:
                    raise ProviderError("Model spending budget exhausted")
            if input_tokens + output_tokens > self.config.max_total_tokens:
                raise ProviderError("Model token budget exhausted")
            if not calls:
                try:
                    decision = AgentDecision.model_validate_json(text, strict=True)
                except ValidationError:
                    if not self.config.capabilities.json_schema or step + 1 >= max_steps:
                        raise
                    # Explicit, bounded re-generation; never strip/repair raw JSON locally.
                    tools = []
                    correction = (
                        "Return the final decision again as schema-compliant JSON only. "
                        "No Markdown fences. Keep all conclusions grounded in "
                        "the observations already collected."
                    )
                    history.append({"role": "user", "content": correction})
                    native_input.append({"role": "user", "content": correction})
                    google_history.append({"role": "user", "parts": [{"text": correction}]})
                    continue
                return Inference(
                    decision=decision,
                    usage=Usage(
                        input_tokens=input_tokens if input_available else None,
                        output_tokens=output_tokens if output_available else None,
                        api_cost_usd=0 if kind == "ollama" else cost,
                    ),
                    model=model,
                    runtime_ms=(time.monotonic() - started) * 1000,
                    tool_trace=trace,
                )
            if not definitions or len(calls) > self.config.max_calls_per_step:
                raise ProviderError("Unexpected or excessive tool calls")
            results = []
            verified_staged = False
            for call in calls:
                arguments = call["arguments"]
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                if time.monotonic() - started > max_seconds:
                    raise ProviderError("Model time budget exhausted before tool execution")
                tool_started = time.monotonic()
                outcome = execute(call["name"], arguments)
                if call["name"] == "apply_patch" and outcome.get("success"):
                    verified_staged = False
                if call["name"] == "run_checks":
                    verified_staged = bool(
                        outcome.get("success")
                        and outcome.get("ready_for_publication")
                        and outcome.get("scope") == "staged_proposals"
                    )
                trace.append(
                    {
                        "name": call["name"],
                        "success": outcome.get("success", False),
                        "arguments": arguments,
                        "result": (
                            {
                                "success": outcome.get("success", False),
                                "check_id": arguments.get("check_id"),
                            }
                            if call["name"] == "get_check"
                            else outcome
                        ),
                        "runtime_ms": (time.monotonic() - tool_started) * 1000,
                    }
                )
                encoded = json.dumps(outcome)
                if kind == "ollama":
                    history.append({"role": "tool", "tool_name": call["name"], "content": encoded})
                elif kind == "openai":
                    native_input.append(
                        {"type": "function_call_output", "call_id": call["id"], "output": encoded}
                    )
                elif kind == "anthropic":
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call["id"],
                            "content": encoded,
                            "is_error": not outcome.get("success", False),
                        }
                    )
                else:
                    results.append(
                        {"functionResponse": {"name": call["name"], "response": outcome}}
                    )
            if stop_after_verified_tools and verified_staged:
                return Inference(
                    decision=AgentDecision(
                        summary="Staged proposals passed tool verification; independent "
                        "publication and served checks remain the application's responsibility."
                    ),
                    usage=Usage(
                        input_tokens=input_tokens if input_available else None,
                        output_tokens=output_tokens if output_available else None,
                        api_cost_usd=0 if kind == "ollama" else cost,
                    ),
                    model=model,
                    runtime_ms=(time.monotonic() - started) * 1000,
                    tool_trace=trace,
                    finalized_from_tools=True,
                )
            if kind == "anthropic":
                history.append({"role": "user", "content": results})
            elif kind == "google":
                google_history.append({"role": "user", "parts": results})
        raise ProviderError("Model tool-step budget exhausted")
