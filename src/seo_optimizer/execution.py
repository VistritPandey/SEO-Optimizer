"""Repository snapshots, confined edits and verification outside model authority."""

import os
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from seo_optimizer.application_models import FileChange, ProjectSpec

SECRET_NAMES = re.compile(
    r"(^\.env($|\.)|\.pem$|\.key$|credentials|secret|id_rsa|id_ed25519)", re.I
)


def without_metadata(text: str) -> str:
    """Remove a data-only JS metadata declaration for a conservative body-equality gate."""
    match = re.search(r"export\s+const\s+metadata(?:\s*:\s*Metadata)?\s*=\s*\{", text)
    if not match:
        return text.strip()
    depth, quote, escaped, end = 1, "", False, match.end()
    for end in range(match.end(), len(text)):
        char = text[end]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        elif char in {"'", '"'}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end += 1
                if text[end : end + 1] == ";":
                    end += 1
                break
        elif char in "()`=":
            raise ValueError("Metadata must contain data, not executable expressions")
    if depth or quote:
        raise ValueError("Metadata declaration is not balanced")
    return (text[: match.start()] + text[end:]).strip()


def run_git(root: Path, *arguments: str) -> str:
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(root),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        timeout=60,
        env=environment,
    )
    if result.returncode:
        raise ValueError("Git operation failed: " + arguments[0])
    return result.stdout.strip()


def confined(root: Path, path: str, allowed: list[str]) -> Path:
    target = (root / path).resolve()
    if (
        not target.is_relative_to(root.resolve())
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or "\\" in path
        or SECRET_NAMES.search(Path(path).name)
        or ".git" in Path(path).parts
    ):
        raise ValueError("File is outside the permitted repository scope")
    if not any(
        target == (root / item).resolve() or target.is_relative_to((root / item).resolve())
        for item in allowed
    ):
        raise ValueError("File path is not allowed by project policy")
    return target


def snapshot_local(
    source: Path, destination: Path, branch: str, allowed_roots: tuple[Path, ...]
) -> str:
    source = source.resolve()
    if not any(source.is_relative_to(root) for root in allowed_roots):
        raise ValueError("Local repository is outside administrator-configured roots")
    sha = run_git(source, "rev-parse", branch)
    destination.parent.mkdir(parents=True, exist_ok=True)
    run_git(
        destination.parent,
        "clone",
        "--no-hardlinks",
        "--no-checkout",
        str(source),
        str(destination),
    )
    run_git(destination, "checkout", "--detach", sha)
    return sha


def apply_changes(
    root: Path,
    spec: ProjectSpec,
    changes: list[FileChange],
    evidence_ids: set[str],
    check_ids: set[str],
) -> dict[str, str]:
    if len(changes) > spec.max_files_changed:
        raise ValueError("Patch exceeds the configured file limit")
    seen: set[str] = set()
    result: dict[str, str] = {}
    for change in changes:
        if change.path in seen:
            raise ValueError("Duplicate file edits must be combined into one change")
        seen.add(change.path)
        if not set(change.evidence_ids).issubset(evidence_ids) or change.check_id not in check_ids:
            raise ValueError("Patch is not supported by collected findings")
        target = confined(root, change.path, spec.allowed_paths)
        intents = {
            urlparse(route).path or "/": intent for route, intent in spec.page_intents.items()
        }
        private_paths = {
            path
            for route, path in spec.route_map.items()
            if not intents.get(route, spec.environment == "production")
        }
        if change.path in private_paths:
            raise ValueError("Intentional private pages must not be changed")
        creating = not target.exists()
        if creating and (
            change.before
            or not spec.allow_content_publication
            or not spec.check_commands
            or not spec.facts
        ):
            raise ValueError("New content requires publication policy, facts and sandbox checks")
        if not creating and (not target.is_file() or target.stat().st_size > 200_000):
            raise ValueError("Patch target is missing or too large")
        original = "" if creating else target.read_text()
        if not creating and (not change.before or original.count(change.before) != 1):
            raise ValueError("Patch context is stale or ambiguous")
        updated = change.after if creating else original.replace(change.before, change.after, 1)
        if updated == original:
            raise ValueError("Patch does not change the file")
        if not spec.allow_content_publication:
            # Default automatic scope is document-head metadata, not arbitrary app code.
            if target.suffix.lower() in {".tsx", ".jsx", ".js", ".ts"}:
                if (
                    change.check_id
                    not in {"tech.title", "tech.metadata", "tech.canonical", "tech.indexability"}
                    or not spec.check_commands
                ):
                    raise ValueError(
                        "Framework metadata edits require configured build verification"
                    )
                if without_metadata(original) != without_metadata(updated):
                    raise ValueError("Framework edit changes application behavior beyond metadata")
            elif target.suffix.lower() == ".html":
                head = re.search(r"<head\b[^>]*>(.*?)</head>", original, flags=re.S | re.I)
                start = original.find(change.before)
                if not head or not (
                    head.start() <= start and start + len(change.before) <= head.end()
                ):
                    raise ValueError("Automatic edit extends beyond permitted page metadata")
                updated_head = re.search(r"<head\b[^>]*>(.*?)</head>", updated, flags=re.S | re.I)
                if updated_head is None:
                    raise ValueError("Edit removes the document head")

                def fixed_head(value: str) -> str:
                    value = re.sub(r"\s*<title\b[^>]*>.*?</title>\s*", "", value, flags=re.S | re.I)
                    value = re.sub(r"\s*<meta\b[^>]*>\s*", "", value, flags=re.I)
                    value = re.sub(
                        r"\s*<link\b(?=[^>]*\brel\s*=\s*['\"](?:canonical|alternate)['\"])[^>]*>\s*",
                        "",
                        value,
                        flags=re.I,
                    )
                    return value.strip()

                if fixed_head(head.group(0)) != fixed_head(updated_head.group(0)):
                    raise ValueError("Edit changes executable or unrelated head content")
                if re.search(
                    r"<meta\b[^>]*http-equiv\s*=\s*['\"]?refresh\b", updated_head.group(0), re.I
                ):
                    raise ValueError("Automatic metadata cannot introduce a redirect")
                directives = re.compile(
                    r"<meta\b(?=[^>]*\bname\s*=\s*['\"](?:robots|googlebot|bingbot)['\"])[^>]*>",
                    re.I,
                )
                if directives.findall(original) != directives.findall(updated):
                    routes = [
                        route for route, path in spec.route_map.items() if path == change.path
                    ]
                    if (
                        change.check_id != "tech.indexability"
                        or not routes
                        or not all(intents.get(route) is True for route in routes)
                    ):
                        raise ValueError(
                            "Indexing directives require explicit matching public intent"
                        )
            else:
                raise ValueError("Application/content edits require explicit publication policy")
        elif not spec.facts:
            raise ValueError("Content publication requires verified business facts")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(updated)
        result[change.path] = updated
    return result


def verify_workspace(
    root: Path, spec: ProjectSpec, changes: dict[str, str]
) -> list[dict[str, Any]]:
    from seo_optimizer.audit import PageParser

    checks: list[dict[str, Any]] = []
    for path, text in changes.items():
        if path.endswith(".html"):
            page = PageParser()
            page.feed(text)
            if not "".join(page.title).strip():
                raise ValueError("Patched page still lacks a title")
            if len(set(page.canonicals)) > 1:
                raise ValueError("Patched page has conflicting canonical declarations")
            checks.append({"name": "HTML metadata", "path": path, "passed": True})
    if not spec.check_commands:
        if any(not path.endswith(".html") for path in changes):
            raise ValueError("Non-HTML changes require configured sandbox checks")
        return checks
    for command in spec.check_commands:
        if not command or not all(isinstance(argument, str) for argument in command):
            raise ValueError("Verification commands must be explicit argument lists")
        argv = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "128",
            "--memory",
            "1g",
            "--cpus",
            "1",
            "--tmpfs",
            "/tmp:rw,size=256m",
            "--user",
            "65534:65534",
            "--mount",
            f"type=bind,source={root.resolve()},target=/workspace,readonly",
            "--workdir",
            "/workspace",
            spec.sandbox_image,
            *command,
        ]
        try:
            value = subprocess.run(
                argv,
                capture_output=True,
                timeout=180,
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(root)},
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError("Verification sandbox is unavailable or timed out") from error
        if value.returncode:
            raise ValueError("Configured sandbox verification failed")
        checks.append({"name": command[0], "passed": True})
    return checks


def commit_local(
    source: Path, workspace: Path, branch: str, base_sha: str, files: list[str]
) -> str:
    if run_git(source, "rev-parse", branch) != base_sha or run_git(source, "status", "--porcelain"):
        raise ValueError("Target repository changed or contains uncommitted work")
    if run_git(source, "branch", "--show-current") != branch:
        raise ValueError("Target branch is not checked out in the local repository")
    for path in files:
        run_git(workspace, "add", "--", path)
        run_git(
            workspace,
            "-c",
            "user.name=Optimizer",
            "-c",
            "user.email=optimizer@localhost",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--only",
            "-m",
            "Fix " + Path(path).name,
            "--",
            path,
        )
    sha = run_git(workspace, "rev-parse", "HEAD")
    run_git(source, "fetch", str(workspace), sha)
    if run_git(source, "rev-parse", branch) != base_sha:
        raise ValueError("Target revision changed during verification")
    run_git(source, "merge", "--ff-only", "FETCH_HEAD")
    return sha
