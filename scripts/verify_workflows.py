"""Run repository tests and export explicit workflow coverage, failures and unknowns."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

from seo_optimizer.knowledge import load_knowledge

ROOT = Path(__file__).resolve().parents[1]


def outcome(case):
    if case.find("failure") is not None or case.find("error") is not None:
        return "failed"
    return "skipped" if case.find("skipped") is not None else "passed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sandbox", action="store_true", help="Run real Docker repair checks")
    parser.add_argument("--output", type=Path, default=ROOT / ".data/workflow-validation.json")
    args = parser.parse_args()
    environment = dict(os.environ)
    if args.sandbox:
        environment["OPT_TEST_SANDBOX"] = "1"
    with tempfile.TemporaryDirectory(prefix="optimiser-workflow-") as directory:
        junit = Path(directory) / "tests.xml"
        run = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", f"--junitxml={junit}"],
            cwd=ROOT,
            env=environment,
            timeout=600,
            check=False,
        )
        if not junit.exists():
            raise SystemExit("Test runner did not produce a report; no success is recorded")
        cases = list(ElementTree.parse(junit).iter("testcase"))
    catalog = []
    for check_id in sorted(load_knowledge().checks):
        matches = [
            case
            for case in cases
            if case.get("name")
            == f"test_every_check_reaches_a_grounded_conclusion_or_semantic_handoff[{check_id}]"
        ]
        catalog.append(
            {
                "check_id": check_id,
                "workflow_status": outcome(matches[0]) if len(matches) == 1 else "unverified",
            }
        )
    repairs = [
        {"case": case.get("name"), "status": outcome(case)}
        for case in cases
        if case.get("classname", "").endswith("test_repair_workflows")
    ]
    semantic = [
        case
        for case in cases
        if case.get("classname", "").endswith("test_catalog_workflows")
        and "every_check_reaches" not in case.get("name", "")
    ]
    source_hash = hashlib.sha256()
    for base in (ROOT / "src", ROOT / "tests", ROOT / "scripts"):
        for path in sorted(base.rglob("*.py")):
            source_hash.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes())
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    counts = {
        state: sum(outcome(case) == state for case in cases)
        for state in ("passed", "failed", "skipped")
    }
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "repository_revision": revision,
        "python_sources_sha256": source_hash.hexdigest(),
        "scope": "Software workflow validation; scripted provider replies are not model judgments",
        "counts": counts,
        "catalog": catalog,
        "semantic_and_missing_input_contracts": {
            state: sum(outcome(case) == state for case in semantic)
            for state in ("passed", "failed", "skipped")
        },
        "git_http_docker_provider_replay": repairs,
        "failures": [case.get("name") for case in cases if outcome(case) == "failed"],
        "skips": [case.get("name") for case in cases if outcome(case) == "skipped"],
        "unverified": [
            "Actual model judgment quality for all 39 catalog checks",
            "Live GitHub/webhook/cloud deployment of these scripted fixture scenarios",
            "Search indexing, ranking, traffic, conversions and consumer-engine citations",
            "General superiority to another product and blinded open versus paid model quality",
            "Production billing and cost per independently verified fix",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "counts": counts,
                "catalog_workflows_passed": sum(
                    row["workflow_status"] == "passed" for row in catalog
                ),
                "report": str(args.output),
            }
        )
    )
    complete = all(row["workflow_status"] == "passed" for row in catalog)
    sandbox_passed = len(repairs) == 6 and all(row["status"] == "passed" for row in repairs)
    return 0 if run.returncode == 0 and complete and (not args.sandbox or sandbox_passed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
