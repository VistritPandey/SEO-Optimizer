"""First-run setup and foreground supervision; no Node or cloud account required."""

import argparse
import getpass
import hashlib
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any, Literal, cast

import httpx
from pydantic import HttpUrl, ValidationError

from seo_optimizer.application_models import (
    ProjectCreate,
    ProjectSecrets,
    ProjectSpec,
    ProviderConfig,
    Registration,
)
from seo_optimizer.contracts import ProviderCapabilities
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import hash_password

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".your-optimiser.json"


def private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")
    temporary.replace(path)
    path.chmod(0o600)


def ask(label: str, default: str = "") -> str:
    value = input(f"{label}{' [' + default + ']' if default else ''}: ").strip()
    return value or default


def environment(value: dict[str, Any]) -> dict[str, str]:
    return {
        **os.environ,
        "OPT_ENV": "development",
        "OPT_STORAGE": "sql",
        "OPT_HOSTED": "0",
        "OPT_ALLOW_PRIVATE_NETWORK": "1",
        "OPT_BUILD_BACKEND": "docker",
        "OPT_DATA_DIR": str(value["data_dir"]),
        "OPT_DATABASE_URL": f"sqlite:///{Path(value['data_dir']) / 'control.db'}",
        "OPT_REPO_ROOTS": str(value["repo_root"]),
        "OPT_PUBLIC_URL": f"http://127.0.0.1:{value['port']}",
        "OPT_REGISTRATION": "0",
    }


def configure(args: argparse.Namespace) -> dict[str, Any]:
    if args.config.exists():
        return cast(dict[str, Any], json.loads(args.config.read_text()))
    interactive = not args.no_start and sys.stdin.isatty()
    if not interactive and not (args.repo and args.url and args.password_env):
        raise ValueError("Non-interactive setup needs --repo, --url and --password-env")
    print("\nYour Optimiser · first-time setup\n")
    default_data = (
        Path.home()
        / ".local"
        / "share"
        / "your-optimiser"
        / hashlib.sha256(str(ROOT).encode()).hexdigest()[:10]
    )
    data_dir = (
        Path(
            args.data_dir
            or (ask("Store data here", str(default_data)) if interactive else default_data)
        )
        .expanduser()
        .resolve()
    )
    repo = Path(args.repo or ask("Website's local Git repository", str(Path.cwd()))).expanduser()
    repo = repo.resolve()
    if not shutil.which("git"):
        raise ValueError("Install Git, then run the launcher again")
    branch = subprocess.run(
        ["git", "-C", str(repo), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "HEAD"], check=True, capture_output=True
    )
    if not branch:
        raise ValueError("Check out a branch in the website repository first")
    url = args.url or ask("Website URL (deployed or localhost)")
    provider = args.provider or (
        ask("Model: rules, ollama, google, openai, anthropic", "ollama") if interactive else "rules"
    )
    model = args.model or ""
    base_url: str | None = None
    key = ""
    if provider == "ollama":
        base_url = args.endpoint or "http://127.0.0.1:11434"
        with httpx.Client(timeout=10) as client:
            response = client.get(base_url.rstrip("/") + "/api/tags")
            response.raise_for_status()
            models = [str(item["name"]) for item in response.json().get("models", [])]
        print("Installed local models: " + ", ".join(models))
        if not model:
            model = ask("Local model", models[0] if models else "") if interactive else ""
        if model not in models:
            raise ValueError("Choose an installed Ollama model; use ollama pull to install one")
    elif provider != "rules":
        model = model or ask("Model identifier from your provider")
        key = os.getenv(args.key_env, "") if args.key_env else getpass.getpass("API key: ").strip()
        if not key:
            raise ValueError("A provider API key is required")
    email = args.email or (
        ask("Dashboard email", "owner@localhost.test") if interactive else "owner@localhost.test"
    )
    password = (
        os.getenv(args.password_env, "")
        if args.password_env
        else getpass.getpass("Dashboard password (12+ characters): ")
    )
    registration = Registration(email=email, password=password)
    paths = args.paths or (
        ask(
            "Directories to monitor (comma separated)",
            "public,web,src/app,src/pages,src/components,app,pages,content",
        )
        if interactive
        else "public,web,src/app,src/pages,src/components,app,pages,content"
    )
    auto_fix = args.auto_fix or (
        interactive and ask("Allow verified metadata edits? yes/no", "no") == "yes"
    )
    spec = ProjectSpec(
        name=args.name or repo.name,
        local_path=str(repo),
        branch=branch,
        website_url=HttpUrl(url),
        allowed_paths=[item.strip() for item in paths.split(",") if item.strip()],
        provider=ProviderConfig(
            kind=cast(Literal["rules", "ollama", "openai", "anthropic", "google"], provider),
            model=model,
            base_url=base_url,
            capabilities=ProviderCapabilities(
                tool_calling=provider != "rules", json_schema=provider != "rules"
            ),
        ),
        auto_fix=auto_fix,
        auto_merge=False,
        reconcile_seconds=args.interval,
    )
    value: dict[str, Any] = {
        "version": 1,
        "data_dir": str(data_dir),
        "repo_root": str(repo),
        "port": args.port,
    }
    env = environment(value)
    previous = {key: os.environ.get(key) for key in env if key.startswith("OPT_")}
    try:
        os.environ.update(env)
        settings = Settings.from_env()
        store = Store(settings)
        account = store.user(email=registration.email)
        if account is None:
            account, _ = store.create_user(registration.email, hash_password(password))
        elif not args.password_env:
            raise ValueError("Data folder already has this account; resume its original config")
        project = store.create_project(
            account.id,
            ProjectCreate(
                spec=spec,
                credentials=ProjectSecrets(provider_key=key),
            ),
        )
        value.update(tenant_id=account.id, project_id=project.id)
        store.engine.dispose()
    finally:
        for key, old in previous.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
    private_json(args.config, value)
    print("Setup saved. Keys are encrypted in the local database; keep secret.key backed up.")
    print("The first audit is queued. Automatic edits: " + ("enabled" if auto_fix else "off"))
    print("Docker is needed for project build/test commands, not basic metadata audits.")
    return value


def cron_line(config: Path, root: Path = ROOT) -> str:
    command = [
        str(root / ".venv" / "bin" / "python"),
        "-m",
        "seo_optimizer.local",
        "--config",
        str(config.resolve()),
        "--once",
    ]
    # Cron treats percent specially even inside shell quotes.
    invocation = shlex.join(command).replace("%", "\\%")
    marker = hashlib.sha256(str(config.resolve()).encode()).hexdigest()[:12]
    directory = shlex.quote(str(root)).replace("%", "\\%")
    return f"*/5 * * * * cd {directory} && {invocation} # your-optimiser:{marker}"


def install_cron(config: Path) -> None:
    if not shutil.which("crontab"):
        raise ValueError(
            "crontab is unavailable; use the foreground scheduler or OS task scheduler"
        )
    line = cron_line(config)
    marker = line.rsplit(" # ", 1)[1]
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if current.returncode not in {0, 1}:
        raise ValueError("Cannot read crontab; existing schedules were preserved")
    entries = [item for item in current.stdout.splitlines() if marker not in item]
    subprocess.run(
        ["crontab", "-"], input="\n".join([*entries, line]) + "\n", text=True, check=True
    )
    print("Scheduled every five minutes. Existing cron entries were preserved.")


def run(value: dict[str, Any], *, once: bool, browser: bool) -> int:
    env = environment(value)
    if once:
        return subprocess.run(
            [sys.executable, "-m", "seo_optimizer.cli", "worker", "--once"], cwd=ROOT, env=env
        ).returncode
    port = int(value["port"])
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise ValueError(
                f"Port {port} is in use; stop the other launcher or use --port"
            ) from error
    processes: list[subprocess.Popen[bytes]] = []
    try:
        for command in (["serve", "--port", str(port)], ["worker"]):
            processes.append(
                subprocess.Popen(
                    [sys.executable, "-m", "seo_optimizer.cli", *command], cwd=ROOT, env=env
                )
            )
        url = f"http://127.0.0.1:{port}"
        print(
            f"\nYour Optimiser: {url}\nBackground audits run while this launcher is open. "
            "Ctrl+C stops both processes."
        )
        if browser:
            with httpx.Client(timeout=2) as client:
                for _ in range(30):
                    try:
                        if client.get(url + "/healthz").is_success:
                            webbrowser.open(url)
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.3)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="Your Optimiser")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--data-dir")
    parser.add_argument("--repo")
    parser.add_argument("--url")
    parser.add_argument("--name")
    parser.add_argument("--email")
    parser.add_argument("--password-env")
    parser.add_argument("--provider", choices=["rules", "ollama", "google", "openai", "anthropic"])
    parser.add_argument("--model")
    parser.add_argument("--endpoint")
    parser.add_argument("--key-env")
    parser.add_argument("--paths")
    parser.add_argument("--auto-fix", action="store_true")
    parser.add_argument("--interval", type=int, default=3600)
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-start", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--schedule", choices=["foreground", "cron"], default="foreground")
    args = parser.parse_args(argv)
    try:
        value = configure(args)
        if "--port" in (argv if argv is not None else sys.argv[1:]):
            value["port"] = args.port
        if (
            not args.no_start
            and not args.once
            and sys.stdin.isatty()
            and "--schedule" not in (argv if argv is not None else sys.argv[1:])
        ):
            args.schedule = ask(
                "Schedule: foreground (while open) or cron (every 5 minutes)", "foreground"
            )
        if args.schedule == "cron":
            install_cron(args.config)
        if args.no_start:
            return 0
        return run(value, once=args.once, browser=not args.no_browser)
    except (ValueError, OSError, subprocess.SubprocessError, httpx.HTTPError, ValidationError):
        print(
            "Setup could not complete. Check the repository, URL, model availability "
            "and password (12+ characters).",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
