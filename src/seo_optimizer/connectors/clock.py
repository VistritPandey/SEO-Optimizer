"""Non-secret due times can be indexed without decrypting every tenant's connection."""

from typing import Any

EXPLICIT = {"ai_visibility", "dataforseo", "server_logs", "deployment"}


def record(key: str, value: dict[str, Any]) -> dict[str, Any] | None:
    parts = key.split(":")
    if len(parts) != 4 or parts[0] != "connector":
        return None
    config = value.get("config", {})
    return {
        "key": key,
        "tenant_id": parts[1],
        "project_id": parts[2],
        "platform": parts[3],
        "next_due": float(value.get("next_sync", 0)),
        "enabled": (
            bool(config.get("enabled"))
            and parts[3] not in EXPLICIT
            and value.get("status")
            not in {"credentials_required", "reconnect_required", "dependency", "configuration"}
        ),
    }
