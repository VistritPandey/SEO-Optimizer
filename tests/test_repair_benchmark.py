"""Benchmark machinery must not mutate an active run or accept a broken healthy control."""

import json
import shutil
from pathlib import Path

import pytest

from seo_optimizer.repair_benchmark import benchmark_repairs, grade, healthy_sources


def test_healthy_control_and_independent_grader(tmp_path):
    shutil.copytree(Path(__file__).parent / "fixtures/agent_site", tmp_path / "repository")
    root = tmp_path / "repository"
    assert grade(root)["verified_fixes"] == 0
    healthy_sources(root, "__ORIGIN__")
    assert grade(root)["verified_fixes"] == 4
    assert grade(root)["protected_files_unchanged"]
    (root / "web/robots.txt").write_text("User-agent: *\nAllow: /")
    assert not grade(root)["protected_files_unchanged"]


def test_active_resume_reserves_server_before_any_git_mutation(tmp_path, monkeypatch):
    output = tmp_path / "run.json"
    output.write_text(
        json.dumps(
            {"workspace_id": "repair-work-fixture", "fixture_port": 8810, "base_sha": "a" * 40}
        )
    )
    mutations = []
    monkeypatch.setattr(
        "seo_optimizer.repair_benchmark.run_git", lambda *args: mutations.append(args)
    )

    def occupied(*args, **kwargs):
        raise OSError("Fixture is active")

    monkeypatch.setattr("seo_optimizer.repair_benchmark.ThreadingHTTPServer", occupied)
    with pytest.raises(OSError, match="active"):
        benchmark_repairs(tmp_path, output, "local", "paid", resume=True)
    assert mutations == []


def test_failed_inference_keeps_completed_calls_and_tool_results(monkeypatch):
    import httpx

    from seo_optimizer.application_models import ProviderConfig
    from seo_optimizer.contracts import ProviderCapabilities
    from seo_optimizer.llm import ModelClient
    from seo_optimizer.repair_benchmark import run_observed

    responses = [
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "read_file", "arguments": {"path": "web/index.html"}}}
                ],
            },
            "prompt_eval_count": 10,
            "eval_count": 2,
        },
    ]

    def post(self, path, payload, headers):
        if responses:
            return responses.pop()
        raise httpx.ReadTimeout("fixture timeout")

    monkeypatch.setattr(ModelClient, "_post", post)

    class ControlledWorker:
        def tick(self, tenant):
            from seo_optimizer.worker import ModelClient as CurrentClient

            config = ProviderConfig(
                kind="ollama",
                model="fixture",
                capabilities=ProviderCapabilities(tool_calling=True, json_schema=True),
            )
            client = CurrentClient(config)
            try:
                client.complete(
                    "Task",
                    {},
                    [
                        {
                            "name": "read_file",
                            "description": "Read",
                            "parameters": {"type": "object", "properties": {}},
                        }
                    ],
                    lambda *_: {"success": True},
                    max_steps=3,
                )
            except httpx.ReadTimeout:
                pass  # The production worker records the failed job independently.
            finally:
                client.close()

    telemetry = run_observed(ControlledWorker(), "tenant")
    assert len(telemetry["requests"]) == 2 and not telemetry["usage_complete"]
    assert telemetry["requests"][0]["usage"]["prompt_eval_count"] == 10
    assert telemetry["requests"][1]["error_type"] == "ReadTimeout"
    assert telemetry["tools"][0]["success"]
