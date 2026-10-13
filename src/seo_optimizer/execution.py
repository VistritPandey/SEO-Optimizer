"""Repository snapshots, confined edits and verification outside model authority."""

import os
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from seo_optimizer.application_models import FileChange, ProjectSpec
from seo_optimizer.contracts import utc_now

SECRET_NAMES = re.compile(
    r"(^\.env($|\.)|\.pem$|\.key$|credentials|secret|id_rsa|id_ed25519)", re.I
)


class VerificationFailure(ValueError):
    def __init__(self, checks: list[dict[str, Any]]) -> None:
        super().__init__("Configured sandbox verification failed")
        self.checks = checks


class BehaviorParser(HTMLParser):
    """Fingerprint active content; copy publication is not execution authority."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.records: list[tuple[str, str]] = []
        self.in_script = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        active = tag in {
            "form",
            "input",
            "button",
            "select",
            "textarea",
            "iframe",
            "object",
            "embed",
            "base",
        }
        if tag == "style" or (tag == "script" and values.get("type") != "application/ld+json"):
            self.in_script = True
            active = True
        if (tag == "link" and values.get("rel") not in {"canonical", "alternate"}) or (
            tag == "meta" and (values.get("http-equiv") or values.get("name") == "viewport")
        ):
            active = True
        if active:
            self.records.append((tag, repr(sorted(attrs))))
        for key, value in attrs:
            if key.startswith("on") or (
                value and value.strip().lower().startswith(("javascript:", "vbscript:", "data:"))
            ):
                self.records.append((tag + ":" + key, value or ""))

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self.records.append(("script-data", data))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.in_script = False


def validate_robots_policy(original: str, updated: str, spec: ProjectSpec) -> None:
    def groups(value: str) -> dict[str, list[tuple[str, str]]]:
        result: dict[str, list[tuple[str, str]]] = {}
        agents: list[str] = []
        started = False
        for line in value.splitlines():
            line = line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            field, content = (item.strip() for item in line.split(":", 1))
            field = field.lower()
            if field == "user-agent":
                if started:
                    agents, started = [], False
                agents.append(content.lower())
                result.setdefault(content.lower(), [])
            else:
                started = True
                for agent in agents or ["__global__"]:
                    result.setdefault(agent, []).append((field, content))
        return result

    before, after = groups(original), groups(updated)
    preferences = {name.lower(): intent for name, intent in spec.crawler_preferences.items()}
    for bot in before.keys() | after.keys():
        if before.get(bot) == after.get(bot):
            continue
        preference = preferences.get(bot, "unchanged")
        allowed = [("disallow", "/")] if preference == "block" else [("disallow", "")]
        if preference == "unchanged" or after.get(bot) not in (allowed, []):
            raise ValueError("Crawler change lacks explicit matching owner intent")
        if preference == "block" and after.get(bot) != allowed:
            raise ValueError("Training/discovery block must cover every path")
    old, new = RobotFileParser(), RobotFileParser()
    old.parse(original.splitlines())
    new.parse(updated.splitlines())
    bots = {
        "GPTBot",
        "OAI-SearchBot",
        "ChatGPT-User",
        "ClaudeBot",
        "Claude-SearchBot",
        "Claude-User",
        "Google-Extended",
        "Googlebot",
        "Bingbot",
    }
    for bot in bots:
        if preferences.get(bot.lower(), "unchanged") == "unchanged" and any(
            old.can_fetch(bot, path) != new.can_fetch(bot, path)
            for path in (str(spec.website_url), str(spec.website_url) + "policy-probe")
        ):
            raise ValueError("Crawler change alters an unconfigured discovery/training preference")


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
    if (
        sum(len(change.before.encode()) + len(change.after.encode()) for change in changes)
        > 750_000
    ):
        raise ValueError("Patch exceeds the total content budget")
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
        if (
            creating
            and target.name != "robots.txt"
            and (
                change.before
                or not spec.allow_content_publication
                or not spec.check_commands
                or not spec.facts
            )
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
        if target.suffix.lower() in {".html", ".md"}:
            old_behavior, new_behavior = BehaviorParser(), BehaviorParser()
            old_behavior.feed(original)
            new_behavior.feed(updated)
            if old_behavior.records != new_behavior.records:
                raise ValueError(
                    "Content edits cannot change scripts, controls or embedded behavior"
                )
            directives = re.compile(
                r"<meta\b(?=[^>]*\bname\s*=\s*['\"](?:robots|googlebot|bingbot)['\"])[^>]*>",
                re.I,
            )
            if directives.findall(original) != directives.findall(updated):
                routes = [route for route, path in spec.route_map.items() if path == change.path]
                if (
                    change.check_id != "tech.indexability"
                    or not routes
                    or not all(intents.get(route) is True for route in routes)
                ):
                    raise ValueError("Indexing directives require explicit matching public intent")
        if target.name == "robots.txt":
            if change.check_id != "geo.crawlers" or not spec.crawler_preferences:
                raise ValueError("Crawler changes require explicit crawler policy")
            validate_robots_policy(original, updated, spec)
        elif not spec.allow_content_publication:
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
            else:
                raise ValueError("Application/content edits require explicit publication policy")
        else:
            if target.suffix.lower() in {".tsx", ".jsx", ".js", ".ts"}:
                if not spec.check_commands or without_metadata(original) != without_metadata(
                    updated
                ):
                    raise ValueError(
                        "Content permission does not authorize application-code changes"
                    )
            elif target.suffix.lower() not in {".html", ".md"}:
                raise ValueError("Content publication supports static HTML and Markdown only")
            else:
                facts = {fact.id: fact for fact in spec.facts}
                if not change.fact_ids or not set(change.fact_ids).issubset(facts):
                    raise ValueError("Content publication requires referenced owner-verified facts")
                if any(
                    fact.valid_until is not None and fact.valid_until < utc_now()
                    for fact in (facts[id] for id in change.fact_ids)
                ):
                    raise ValueError("Content publication references expired facts")
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
        if Path(path).name == "robots.txt":
            checks.append({"name": "Explicit crawler policy", "path": path, "passed": True})
        if path.endswith(".html"):
            page = PageParser()
            page.feed(text)
            if not "".join(page.title).strip():
                raise ValueError("Patched page still lacks a title")
            if len(set(page.canonicals)) > 1:
                raise ValueError("Patched page has conflicting canonical declarations")
            checks.append({"name": "HTML metadata", "path": path, "passed": True})
    if not spec.check_commands:
        if any(not path.endswith(".html") and Path(path).name != "robots.txt" for path in changes):
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
        check = {
            "name": command[0],
            "passed": value.returncode == 0,
            "exit_code": value.returncode,
            "stdout": value.stdout.decode(errors="replace")[-2000:],
            "stderr": value.stderr.decode(errors="replace")[-2000:],
        }
        checks.append(check)
        if value.returncode:
            raise VerificationFailure(checks)
    return checks


def verify_proposals(
    root: Path,
    spec: ProjectSpec,
    changes: list[FileChange],
    evidence_ids: set[str],
    check_ids: set[str],
) -> list[dict[str, Any]]:
    """Check staged edits in an ephemeral copy; publication still checks independently."""
    with tempfile.TemporaryDirectory(prefix="proposal-", dir=root.parent) as directory:
        preview = Path(directory) / "repository"
        shutil.copytree(root, preview, symlinks=True)
        files = apply_changes(preview, spec, changes, evidence_ids, check_ids)
        return verify_workspace(preview, spec, files)


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
