"""A shareable film must not turn failed checks into a successful demonstration."""

import copy
import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
prepare = runpy.run_path(str(ROOT / "videos/scripts/prepare-session.py"))["prepare"]


def test_recorded_fixture_exports_only_public_evidence(tmp_path):
    source = ROOT / "videos/public/agent-run.json"
    exported = prepare(source, tmp_path)
    assert exported["after_defects"] == 0
    assert exported["protected_files_unchanged"]
    assert "provider" not in exported and "model" not in exported
    assert all(c["passed"] for c in exported["checks"])
    assert (tmp_path / "after-navigation.png").is_file()
    assert "No GitHub write" in exported["scope"]


@pytest.mark.parametrize("failure", ["regression", "check", "repeat", "irrelevant"])
def test_export_rejects_unverified_claims(tmp_path, failure):
    recording = copy.deepcopy(json.loads((ROOT / "videos/public/agent-run.json").read_text()))
    if failure == "regression":
        recording["repair"]["result"]["regressions"] = 1
    elif failure == "check":
        for tool in recording["repair"]["result"]["report"]["tool_trace"]:
            if tool["name"] == "run_checks":
                tool["result"]["checks"][0]["passed"] = False
    elif failure == "repeat":
        recording["repeat"]["created_commit"] = True
    else:
        recording["merged_docs_event"]["inference_requests"] = 1
    source = tmp_path / "bad.json"
    source.write_text(json.dumps(recording))
    with pytest.raises(AssertionError):
        prepare(source, tmp_path / "public")
    assert not (tmp_path / "public/session.json").exists()
