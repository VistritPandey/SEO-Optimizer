"""Naming preferences cannot authorize branch takeover or forge author identity."""

import pytest
from pydantic import ValidationError

from seo_optimizer.application_models import GitConventions, ProjectSecrets, ProjectSpec
from seo_optimizer.github import GitHubClient


@pytest.mark.parametrize(
    "field,value",
    [
        ("branch_prefix", "../main"),
        ("branch_prefix", "refs//heads"),
        ("branch_prefix", "team.lock"),
        ("branch_prefix", "team\nmain"),
        ("branch_suffix", "../main"),
        ("branch_suffix", "seo: main"),
        ("commit_scope", "seo)\nCo-authored-by: someone"),
        ("commit_type", "anything\nelse"),
        ("commit_style", "shell"),
    ],
)
def test_invalid_git_preferences_are_rejected(field, value):
    with pytest.raises(ValidationError):
        GitConventions.model_validate({field: value})


def test_instructions_are_bounded_and_old_projects_keep_default_names():
    spec = ProjectSpec(name="Example", website_url="https://example.test/")
    assert not spec.agent_instructions
    assert spec.git_conventions.branch_name("job") == "optimizer/job"
    assert spec.git_conventions.commit_message("web/page.tsx") == "Fix page.tsx"
    with pytest.raises(ValidationError):
        spec.agent_instructions = "x" * 8001
    with pytest.raises(ValueError):
        spec.git_conventions.branch_name("../main")


def test_custom_branches_and_commits_preserve_one_file_commits_and_api_authorship(monkeypatch):
    client = GitHubClient(ProjectSecrets(github_token="fixture"))
    calls = []
    commits = []
    conventions = GitConventions(
        branch_prefix="team/repairs",
        branch_suffix="seo",
        commit_style="conventional",
        commit_scope="search",
    )

    def request(method, path, **kwargs):
        body = kwargs.get("json")
        calls.append((method, path, body))
        if path.endswith("/pulls") and method == "GET":
            assert kwargs["params"]["head"] == "example:team/repairs/job-seo"
            return []
        if "/git/ref/heads/" in path:
            return {"object": {"sha": "base"}}
        if method == "GET":
            return {"tree": {"sha": "tree"}}
        if path.endswith("/commits"):
            commits.append(body)
            return {"sha": "commit-" + str(len(commits))}
        if path.endswith("/pulls"):
            return {"number": 9, "html_url": "https://github.com/example/site/pull/9"}
        return {"sha": "object"}

    monkeypatch.setattr(client, "request", request)
    try:
        result = client.create_pr(
            "example/site",
            "main",
            "base",
            "job",
            {"web/page.tsx": "first", "web/about.tsx": "second"},
            "Confirmed repairs",
            conventions,
            title="Repair broken links",
        )
        assert result["branch"] == "team/repairs/job-seo"
        assert [c["message"] for c in commits] == [
            "fix(search): fix page.tsx",
            "fix(search): fix about.tsx",
        ]
        assert [c["parents"] for c in commits] == [["base"], ["commit-1"]]
        assert all(set(c) == {"message", "tree", "parents"} for c in commits)
        assert all(len(body["tree"]) == 1 for _, path, body in calls if path.endswith("/trees"))
        assert calls[-1][2]["title"] == "Repair broken links"
        assert calls[-2][2]["ref"] == "refs/heads/team/repairs/job-seo"
    finally:
        client.close()


def test_followup_keeps_original_custom_branch_when_preferences_change(monkeypatch):
    client = GitHubClient(ProjectSecrets(github_token="fixture"))
    calls = []

    def request(method, path, **kwargs):
        body = kwargs.get("json")
        calls.append((method, path, body))
        if path.endswith("/pulls/9"):
            return {
                "state": "open",
                "html_url": "https://github.com/example/site/pull/9",
                "base": {"ref": "main"},
                "head": {
                    "sha": "old",
                    "ref": "team/repairs/job-seo",
                    "repo": {"full_name": "example/site"},
                },
            }
        if "/git/ref/heads/" in path:
            return {"object": {"sha": "old"}}
        if method == "GET":
            return {"tree": {"sha": "tree"}}
        return {"sha": "object"}

    monkeypatch.setattr(client, "request", request)
    try:
        result = client.update_pr(
            "example/site",
            9,
            "team/repairs/job-seo",
            "old",
            {"web/page.tsx": "corrected"},
            "base",
            GitConventions(branch_prefix="different", commit_style="conventional"),
        )
        assert result["branch"] == "team/repairs/job-seo"
        assert calls[-1][2] == {"sha": "object", "force": False}
        assert (
            next(body for _, path, body in calls if path.endswith("/commits"))["message"]
            == "fix: refine page.tsx"
        )
        with pytest.raises(ValueError, match="changed"):
            client.update_pr("example/site", 9, "different/job", "old", {}, "base")
    finally:
        client.close()
