"""Existing PR updates append one-file commits and refuse races or foreign branches."""

import pytest

from seo_optimizer.application_models import ProjectSecrets
from seo_optimizer.github import GitHubClient


def test_existing_pr_followup_uses_one_file_commits_and_fast_forward(monkeypatch):
    client = GitHubClient(ProjectSecrets(github_token="test-token"))
    calls = []
    commits = 0

    def request(method, path, **kwargs):
        nonlocal commits
        calls.append((method, path, kwargs.get("json")))
        if path.endswith("/pulls/7"):
            return {
                "state": "open",
                "html_url": "https://github.com/example/site/pull/7",
                "head": {
                    "sha": "old",
                    "ref": "optimizer/job",
                    "repo": {"full_name": "example/site"},
                },
            }
        if "/git/ref/heads/" in path:
            return {"object": {"sha": "old"}}
        if method == "GET":
            return {"tree": {"sha": "tree"}}
        if path.endswith("/blobs"):
            return {"sha": "blob"}
        if path.endswith("/trees"):
            return {"sha": "tree-new"}
        if path.endswith("/commits"):
            commits += 1
            return {"sha": "commit-" + str(commits)}
        return {}

    monkeypatch.setattr(client, "request", request)
    result = client.update_pr(
        "example/site",
        7,
        "optimizer/job",
        "old",
        {"web/index.html": "first", "web/shop.html": "second"},
        "base",
    )
    assert result["head_sha"] == "commit-2"
    trees = [body for method, path, body in calls if path.endswith("/trees")]
    assert [len(body["tree"]) for body in trees] == [1, 1]
    commit_bodies = [body for method, path, body in calls if path.endswith("/commits")]
    assert [body["parents"] for body in commit_bodies] == [["old"], ["commit-1"]]
    assert calls[-1][2] == {"sha": "commit-2", "force": False}
    client.close()


def test_followup_refuses_changed_or_foreign_pr_without_writes(monkeypatch):
    client = GitHubClient(ProjectSecrets(github_token="test-token"))
    calls = []

    def request(method, path, **kwargs):
        calls.append(method)
        return {
            "state": "open",
            "head": {
                "sha": "collaborator-new-sha",
                "ref": "optimizer/job",
                "repo": {"full_name": "foreign/site"},
            },
        }

    monkeypatch.setattr(client, "request", request)
    with pytest.raises(ValueError, match="changed"):
        client.update_pr(
            "example/site", 7, "optimizer/job", "old", {"web/index.html": "patch"}, "base"
        )
    assert calls == ["GET"]
    client.close()
