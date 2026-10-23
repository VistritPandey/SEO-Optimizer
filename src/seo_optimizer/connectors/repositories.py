"""GitLab and Bitbucket file/PR adapters. Never merge, deploy or bypass branch checks."""

import base64
from typing import Any
from urllib.parse import quote

from seo_optimizer.connectors.models import Collection, CollectionRequest, Platform, Resource
from seo_optimizer.connectors.transport import ConnectorError, Transport, segment


def endpoint(t: Transport) -> str:
    resource = t.connection.resource
    if resource.count("/") < 1:
        raise ConnectorError("configuration", "Use an owner/repository identifier")
    if t.connection.platform == Platform.GITLAB:
        return "https://gitlab.com/api/v4/projects/" + segment(resource)
    return "https://api.bitbucket.org/2.0/repositories/" + "/".join(
        segment(p) for p in resource.split("/")
    )


def collect(t: Transport, q: CollectionRequest) -> Collection:
    c = t.connection
    branch = c.options.get("branch", "main")
    base = endpoint(t)
    branch_id = segment(branch)
    if c.platform == Platform.GITLAB:
        h = {"PRIVATE-TOKEN": t.secret()}
        if not q.resource_id:
            rows = t.request(
                "GET",
                base + "/repository/tree",
                headers=h,
                params={"ref": branch, "per_page": q.limit, "recursive": "true"},
            )
            records = [
                Resource(
                    id=row["path"],
                    kind="repository_path",
                    fields={"path": row["path"], "type": row["type"]},
                    revision=row["id"],
                )
                for row in rows
            ]
        else:
            data = t.request(
                "GET",
                base + "/repository/files/" + segment(q.resource_id),
                headers=h,
                params={"ref": branch},
            )
            content = base64.b64decode(data["content"], validate=True).decode("utf-8")
            records = [
                Resource(
                    id=q.resource_id,
                    kind="source_file",
                    fields={"content": content, "path": q.resource_id, "branch": branch},
                    revision=data["last_commit_id"],
                )
            ]
    else:
        h = t.bearer()
        head = t.request("GET", base + "/refs/branches/" + branch_id, headers=h)["target"]["hash"]
        if not q.resource_id:
            data = t.request(
                "GET", base + "/src/" + segment(head) + "/", headers=h, params={"pagelen": q.limit}
            )
            records = [
                Resource(
                    id=row["path"],
                    kind="repository_path",
                    fields={"path": row["path"], "type": row["type"]},
                    revision=head,
                )
                for row in data.get("values", [])
            ]
        else:
            content = t.request(
                "GET",
                base + "/src/" + segment(head) + "/" + quote(q.resource_id, safe="/"),
                headers=h,
                raw=True,
            )
            records = [
                Resource(
                    id=q.resource_id,
                    kind="source_file",
                    fields={"content": content, "path": q.resource_id, "branch": branch},
                    revision=head,
                )
            ]
    return Collection(
        platform=c.platform,
        records=records,
        complete=bool(q.resource_id),
        warnings=[
            (
                "Repository listing is bounded. Source verification is separate from "
                "CI/build and deployed-site verification; PRs are never automatically merged"
                " by this adapter."
            )
        ],
    )


def write(
    t: Transport, current: Resource, changes: dict[str, str], branch: str, title: str, reason: str
) -> dict[str, Any]:
    if set(changes) != {"content"} or current.kind != "source_file":
        raise ConnectorError("policy", "Repository proposals must modify one observed source file")
    c = t.connection
    base = endpoint(t)
    target = c.options.get("branch", "main")
    if c.platform == Platform.GITLAB:
        h = {"PRIVATE-TOKEN": t.secret()}
        # last_commit_id prevents an overwrite when the source changed after inspection.
        t.request(
            "POST",
            base + "/repository/commits",
            headers=h,
            body={
                "branch": branch,
                "start_branch": target,
                "commit_message": title,
                "actions": [
                    {
                        "action": "update",
                        "file_path": current.id,
                        "content": changes["content"],
                        "last_commit_id": current.revision,
                    }
                ],
            },
            read_only=False,
        )
        pr = t.request(
            "POST",
            base + "/merge_requests",
            headers=h,
            body={
                "source_branch": branch,
                "target_branch": target,
                "title": title,
                "description": reason
                + (
                    "\n\nSource checked locally. "
                    "Build/CI and deployed-site verification remain required."
                ),
                "remove_source_branch": True,
            },
            read_only=False,
        )
        return {"url": pr["web_url"], "number": pr["iid"], "branch": branch, "merged": False}
    # Pin commit parent, and create a unique branch; no existing target branch is updated.
    t.request(
        "POST",
        base + "/refs/branches",
        headers=t.bearer(),
        body={"name": branch, "target": {"hash": current.revision}},
        read_only=False,
    )
    t.request(
        "POST",
        base + "/src",
        headers=t.bearer(),
        form={
            "branch": branch,
            "parents": current.revision,
            "message": title,
            current.id: changes["content"],
        },
        multipart=True,
        read_only=False,
    )
    pr = t.request(
        "POST",
        base + "/pullrequests",
        headers=t.bearer(),
        body={
            "title": title,
            "description": reason
            + (
                "\n\nSource checked locally. "
                "Build/CI and deployed-site verification remain required."
            ),
            "source": {"branch": {"name": branch}},
            "destination": {"branch": {"name": target}},
            "close_source_branch": True,
        },
        read_only=False,
    )
    return {
        "url": pr["links"]["html"]["href"],
        "number": pr["id"],
        "branch": branch,
        "merged": False,
    }
