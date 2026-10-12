"""GitHub credential, revision, pull request and webhook primitives."""

import base64
import hashlib
import hmac
import io
import tarfile
import time
from pathlib import Path, PurePosixPath
from typing import Any

import httpx
import jwt

from seo_optimizer.application_models import ProjectSecrets


def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return bool(secret) and hmac.compare_digest(expected, signature)


class GitHubClient:
    def __init__(
        self,
        credentials: ProjectSecrets,
        client: httpx.Client | None = None,
        base_url: str = "https://api.github.com",
    ):
        self.credentials = credentials
        self.client = client or httpx.Client(timeout=30, follow_redirects=False)
        self.owns_client = client is None
        self.base_url, self._token, self._expires = (
            base_url.rstrip("/"),
            credentials.github_token,
            0.0,
        )

    def close(self) -> None:
        if self.owns_client:
            self.client.close()

    def token(self) -> str:
        if self.credentials.github_token:
            return self.credentials.github_token
        if self._token and self._expires > time.time():
            return self._token
        if not all(
            (
                self.credentials.github_app_id,
                self.credentials.github_installation_id,
                self.credentials.github_private_key,
            )
        ):
            raise ValueError("GitHub credentials are not configured")
        now = int(time.time())
        signed = jwt.encode(
            {"iat": now - 60, "exp": now + 540, "iss": self.credentials.github_app_id},
            self.credentials.github_private_key,
            algorithm="RS256",
        )
        response = self.client.post(
            self.base_url
            + f"/app/installations/{self.credentials.github_installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {signed}", "Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        self._token = response.json()["token"]
        self._expires = time.time() + 3000
        return self._token

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.client.request(
            method,
            self.base_url + path,
            headers={
                "Authorization": "Bearer " + self.token(),
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            **kwargs,
        )
        response.raise_for_status()
        return response.json() if response.content else {}

    def head(self, repo: str, branch: str) -> str:
        return str(self.request("GET", f"/repos/{repo}/git/ref/heads/{branch}")["object"]["sha"])

    def changed_files(self, repo: str, before: str, after: str) -> list[str] | None:
        if not before or set(before) == {"0"}:
            return None
        data = self.request("GET", f"/repos/{repo}/compare/{before}...{after}")
        # Compare file lists are bounded by GitHub. Fall back to a broader audit.
        if len(data.get("files", [])) >= 300:
            return None
        return [item["filename"] for item in data.get("files", [])]

    def checkout(self, repo: str, sha: str, root: Path) -> None:
        response = self.client.get(
            self.base_url + f"/repos/{repo}/tarball/{sha}",
            headers={"Authorization": "Bearer " + self.token()},
        )
        if response.is_redirect:
            location = response.headers["location"]
            if not location.startswith("https://codeload.github.com/"):
                raise ValueError("Unexpected archive redirect")
            response = self.client.get(location)  # No credential forwarded to the archive host.
        response.raise_for_status()
        if len(response.content) > 50_000_000:
            raise ValueError("Repository archive is too large")
        root.mkdir(parents=True, exist_ok=True)
        total = 0
        with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as archive:
            for member in archive:
                parts = PurePosixPath(member.name).parts
                relative = PurePosixPath(*parts[1:])
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or member.issym()
                    or member.islnk()
                ):
                    raise ValueError("Unsafe repository archive member")
                if not relative.parts:
                    continue
                target = root / str(relative)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    total += member.size
                    if total > 200_000_000:
                        raise ValueError("Expanded repository exceeds the size limit")
                    handle = archive.extractfile(member)
                    if handle:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(handle.read())

    def create_pr(
        self,
        repo: str,
        branch: str,
        base_sha: str,
        job_id: str,
        changes: dict[str, str],
        summary: str,
    ) -> dict[str, Any]:
        name = f"optimizer/{job_id}"
        existing = self.request(
            "GET",
            f"/repos/{repo}/pulls",
            params={"head": repo.split("/")[0] + ":" + name, "state": "all"},
        )
        if existing:
            prior = existing[0]
            if prior["state"] != "open":
                raise ValueError("The job's existing pull request is closed")
            return {
                "number": prior["number"],
                "url": prior["html_url"],
                "head_sha": prior["head"]["sha"],
                "base_sha": base_sha,
            }
        if self.head(repo, branch) != base_sha:
            raise ValueError("Target revision changed before publication")
        base = self.request("GET", f"/repos/{repo}/git/commits/{base_sha}")
        parent_sha, tree_sha = base_sha, base["tree"]["sha"]
        for path, content in changes.items():
            blob = self.request(
                "POST",
                f"/repos/{repo}/git/blobs",
                json={"content": base64.b64encode(content.encode()).decode(), "encoding": "base64"},
            )
            tree = self.request(
                "POST",
                f"/repos/{repo}/git/trees",
                json={
                    "base_tree": tree_sha,
                    "tree": [{"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]}],
                },
            )
            commit = self.request(
                "POST",
                f"/repos/{repo}/git/commits",
                json={
                    "message": "Fix " + Path(path).name,
                    "tree": tree["sha"],
                    "parents": [parent_sha],
                },
            )
            parent_sha, tree_sha = commit["sha"], tree["sha"]
        name = f"optimizer/{job_id}"
        self.request(
            "POST",
            f"/repos/{repo}/git/refs",
            json={"ref": "refs/heads/" + name, "sha": parent_sha},
        )
        value = self.request(
            "POST",
            f"/repos/{repo}/pulls",
            json={
                "title": "Improve website search metadata",
                "head": name,
                "base": branch,
                "body": summary
                + "\n\nValidated against the configured website and project checks. "
                "Automated by the repository's configured optimization policy.",
            },
        )
        return {
            "number": value["number"],
            "url": value["html_url"],
            "head_sha": parent_sha,
            "base_sha": base_sha,
        }

    def checks_ready(self, repo: str, sha: str, required: list[str]) -> str:
        statuses = self.request(
            "GET", f"/repos/{repo}/commits/{sha}/status", params={"per_page": 100}
        )
        checks = self.request(
            "GET",
            f"/repos/{repo}/commits/{sha}/check-runs",
            params={"per_page": 100, "filter": "latest"},
        )
        by_name: dict[str, str] = {}
        for item in statuses.get("statuses", []):
            by_name.setdefault(item["context"], item["state"])
        if checks.get("total_count", 0) > len(checks.get("check_runs", [])):
            return "pending"
        for item in checks.get("check_runs", []):
            by_name[item["name"]] = (
                "pending"
                if item.get("status") != "completed"
                else ("success" if item.get("conclusion") == "success" else "failure")
            )
        if any(value in {"failure", "error"} for value in by_name.values()):
            return "failed"
        if any(value == "pending" for value in by_name.values()) or any(
            by_name.get(name) != "success" for name in required
        ):
            return "pending"
        return "ready"

    def merge(self, repo: str, number: int, sha: str) -> dict[str, Any]:
        return dict(
            self.request(
                "PUT",
                f"/repos/{repo}/pulls/{number}/merge",
                json={
                    "sha": sha,
                    "merge_method": "rebase",
                    "commit_title": "Improve website search metadata",
                },
            )
        )

    def revert(self, repo: str, branch: str, merged_sha: str, previous_sha: str) -> str:
        if self.head(repo, branch) != merged_sha:
            raise ValueError("A newer change prevents automatic rollback")
        original = self.request("GET", f"/repos/{repo}/git/commits/{previous_sha}")
        reverted = self.request(
            "POST",
            f"/repos/{repo}/git/commits",
            json={
                "message": "Revert failed website optimization",
                "tree": original["tree"]["sha"],
                "parents": [merged_sha],
            },
        )
        self.request(
            "PATCH",
            f"/repos/{repo}/git/refs/heads/{branch}",
            json={"sha": reverted["sha"], "force": False},
        )
        return str(reverted["sha"])
