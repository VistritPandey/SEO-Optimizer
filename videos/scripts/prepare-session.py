"""Export an allowlisted, evidence-linked film from a real private repair recording.

Run the existing scripts/demo_agent.py with --output under .data first. No model
output is trusted as a success assertion: the worker, staged checks, repeat audit,
and repository diff must agree before this exporter accepts the recording.
"""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def prepare(source: Path, destination: Path) -> dict:
    raw = source.read_bytes()
    run = json.loads(raw)
    result = run["repair"]["result"]
    assert run["status"] == "passed" and result["stage"] == "verified"
    assert run["before_defects"] == 4 and run["after_defects"] == 0
    assert result["regressions"] == 0 and run["protected_files_unchanged"]
    assert run["repeat"]["created_commit"] is False
    assert run["merged_docs_event"]["inference_requests"] == 0
    trace = result["report"]["tool_trace"]
    checks = [t for t in trace if t["name"] == "run_checks" and t["success"]]
    staged = next(t["result"] for t in checks if t["result"].get("scope") == "staged_proposals")
    assert all(c["passed"] for c in staged["checks"])
    stdout = next(c["stdout"].strip() for c in staged["checks"] if c.get("stdout"))
    patches = [t for t in trace if t["name"] == "apply_patch" and t["success"]]
    home = next(
        t["arguments"] for t in reversed(patches) if t["arguments"]["path"] == "web/index.html"
    )
    product = next(
        t["arguments"]
        for t in reversed(patches)
        if t["arguments"]["path"].endswith("cedar-lamp/index.html")
    )
    description = re.search(r'<meta\b[^>]*name="description"[^>]*>', home["after"])[0]
    snippets = [
        {"kind": "file", "text": "web/index.html"},
        {"kind": "add", "text": description},
        {"kind": "remove", "text": 'href="/collections/lighting/"'},
        {"kind": "add", "text": 'href="/shop/"'},
        {"kind": "file", "text": "web/products/cedar-lamp/index.html"},
        {"kind": "remove", "text": '"price":"129.00"'},
        {"kind": "add", "text": '"price":"89.00"'},
    ]
    for row in snippets:
        if row["kind"] == "file":
            continue
        patch = home if row in snippets[:4] else product
        assert row["text"] in patch["before" if row["kind"] == "remove" else "after"]
    # Only explicit tool names, relative paths and booleans enter the public cast.
    inspected = [
        {"tool": t["name"], "path": t["arguments"].get("path", ""), "success": t["success"]}
        for t in trace
        if t["name"] == "read_file" and t["arguments"].get("path") in run["changed_paths"]
    ]
    assert inspected and all(t["success"] for t in inspected)
    assert all(t["path"] in run["changed_paths"] for t in inspected)
    selected_events = [
        {"recorded_seconds": round(e["time"], 2), "text": e["text"]}
        for e in run["events"]
        if e["text"].startswith(
            (
                "START:",
                "TOOL read_file",
                "TOOL apply_patch",
                "TOOL run_checks",
                "REPEAT:",
                "MERGED DOCS BRANCH:",
                "DEFECTS:",
            )
        )
    ]
    proof = {
        "version": 1,
        "recorded_at": run["generated_at"],
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "site": "Cedar Workshop",
        "scope": "Real local agent run on a fictional shop. No GitHub write or ranking experiment.",
        "editing": (
            "Actual recorded output and exact patch excerpts; waits shortened. "
            "Excerpts omit surrounding HTML."
        ),
        "runtime_seconds": round(run["runtime_seconds"], 2),
        "before_defects": 4,
        "after_defects": 0,
        "regressions": 0,
        "changed_paths": run["changed_paths"],
        "inspected": inspected,
        "patch_excerpts": snippets,
        "check_stdout": stdout,
        "checks": [{"name": c["name"], "passed": c["passed"]} for c in staged["checks"]],
        "repeat_created_commit": False,
        "irrelevant_change_inference_requests": 0,
        "protected_files_unchanged": True,
        "events": selected_events,
    }
    encoded = json.dumps(proof, indent=2, ensure_ascii=False) + "\n"
    assert not re.search(r"/Users/|AIza|-----BEGIN|@", encoded, re.I)
    destination.mkdir(parents=True, exist_ok=True)
    for name in [
        "before-home.png",
        "before-navigation.png",
        "after-navigation.png",
        "after-product.png",
    ]:
        shutil.copy2(source.parent / name, destination / name)
    (destination / "session.json").write_text(encoded)
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--destination", type=Path, default=ROOT / "videos/public/session")
    args = parser.parse_args()
    proof = prepare(args.source, args.destination)
    print(
        f"Exported verified local session: "
        f"{proof['before_defects']} → {proof['after_defects']} defects."
    )
