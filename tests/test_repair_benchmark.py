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
