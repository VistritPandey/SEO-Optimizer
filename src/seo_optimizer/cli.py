"""Offline CLI. All filesystem/network side effects are explicit in commands."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Literal, cast

from pydantic import ValidationError

from seo_optimizer.audit import audit
from seo_optimizer.contracts import ProviderCapabilities, ResponseRecord
from seo_optimizer.evaluation import evaluate, load_cases, load_responses, save_report, save_schemas
from seo_optimizer.knowledge import DEFAULT_KNOWLEDGE, load_knowledge


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seo-optimizer")
    parser.add_argument("--knowledge", type=Path, default=DEFAULT_KNOWLEDGE)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="Validate skill, sources, checks and local links offline")
    schemas = commands.add_parser("schemas", help="Export Pydantic JSON Schemas")
    schemas.add_argument("--output", type=Path, required=True)
    evaluation = commands.add_parser(
        "evaluate", help="Evaluate saved normalized provider responses"
    )
    evaluation.add_argument("--cases", type=Path, required=True)
    evaluation.add_argument("--responses", type=Path, required=True)
    evaluation.add_argument(
        "--split", choices=["development", "held_out", "all"], default="development"
    )
    evaluation.add_argument("--output", type=Path, required=True)
    baseline = commands.add_parser("rules", help="Run the limited offline deterministic baseline")
    baseline.add_argument("--cases", type=Path, required=True)
    baseline.add_argument("--output", type=Path, required=True)
    serve = commands.add_parser("serve", help="Run the dashboard and management API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    worker = commands.add_parser("worker", help="Run the durable autonomous worker")
    worker.add_argument("--once", action="store_true")
    worker.add_argument("--remote", action="store_true")
    worker.add_argument("--interval", type=float, default=3)
    commands.add_parser("demo", help="Create a local demo repository and account")
    live = commands.add_parser("benchmark-live", help="Evaluate real model decisions without repository writes")
    live.add_argument("--cases", type=Path, required=True)
    live.add_argument("--output", type=Path, required=True)
    live.add_argument("--provider", choices=["ollama", "openai", "anthropic", "google"], default="ollama")
    live.add_argument("--model", required=True)
    live.add_argument("--limit", type=int, default=5)
    live.add_argument("--split", choices=["development", "held_out"], default="development")
    args = parser.parse_args(argv)
    try:
        package = load_knowledge(args.knowledge)
        if args.command == "serve":
            import uvicorn

            from seo_optimizer.web import create_app

            uvicorn.run(create_app(), host=args.host, port=args.port, access_log=False)
        elif args.command == "worker":
            from seo_optimizer.settings import Settings
            from seo_optimizer.store import Store
            from seo_optimizer.worker import Worker

            settings = Settings.from_env()
            control: Store
            if args.remote:
                from seo_optimizer.remote import RemoteStore

                control = RemoteStore(
                    settings,
                    os.environ.get("OPT_CONTROL_URL", ""),
                    os.environ.get("OPT_WORKER_TOKEN", ""),
                )
            else:
                control = Store(settings)
            service = Worker(control, settings)
            while True:
                worked = service.tick()
                if args.once:
                    break
                if not worked:
                    time.sleep(max(1, args.interval))
        elif args.command == "demo":
            from seo_optimizer.demo import create_demo

            create_demo()
        elif args.command == "benchmark-live":
            from seo_optimizer.live_benchmark import benchmark
            benchmark(args.cases, args.output, args.provider, args.model, max(1, min(100, args.limit)), args.split)
        elif args.command == "validate":
            print(
                json.dumps(
                    {
                        "status": "passed",
                        "version": package.catalog.version,
                        "checks": len(package.checks),
                        "sources": len(package.sources),
                    }
                )
            )
        elif args.command == "schemas":
            save_schemas(args.output)
            print(f"Exported schemas to {args.output}")
        elif args.command == "rules":
            cases = load_cases(args.cases, package)
            records: list[ResponseRecord] = []
            coverage: dict[str, list[str]] = {}
            for case in cases:
                result = audit(case, package)
                coverage[case.id] = result.unsupported_checks
                if result.unsupported_checks:
                    continue  # Do not claim a complete audit for unimplemented checks.
                records.append(
                    ResponseRecord(
                        case_id=case.id,
                        provider="rules",
                        model="offline-http-v1",
                        capabilities=ProviderCapabilities(),
                        raw_response=result.assessment.model_dump_json(),
                    )
                )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps([record.model_dump(mode="json") for record in records], indent=2) + "\n"
            )
            print(json.dumps({"records": len(records), "unsupported_checks": coverage}))
        elif args.command == "evaluate":
            report = evaluate(
                load_cases(args.cases, package),
                load_responses(args.responses),
                package,
                cast(Literal["development", "held_out", "all"], args.split),
            )
            save_report(report, args.output)
            print(json.dumps(report.counts))
            return 1 if report.counts["failed"] else (2 if report.counts["skipped"] else 0)
    except (OSError, ValueError, ValidationError) as error:
        # Do not print validation input values, which can include private facts.
        print(f"{type(error).__name__}: input/package validation failed", file=sys.stderr)
        if isinstance(error, ValidationError):
            for item in error.errors(include_input=False):
                print(f"  {item['loc']}: {item['type']}", file=sys.stderr)
        elif isinstance(error, ValueError):
            print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
