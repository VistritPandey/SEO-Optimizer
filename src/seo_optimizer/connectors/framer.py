"Optional official Framer SDK bridge. Credentials travel through stdin, never process args."

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from seo_optimizer.connectors.models import ConnectionInput
from seo_optimizer.connectors.transport import ConnectorError, identifier


def bridge(connection: ConnectionInput, request: dict[str, Any]) -> list[dict[str, Any]]:
    if not connection.options.get("collection_id"):
        raise ConnectorError("configuration", "Configure a Framer CMS collection ID")
    identifier(connection.resource)
    root = Path(__file__).resolve().parents[3]
    script = Path(os.getenv("OPT_FRAMER_BRIDGE", str(root / "integrations/framer/bridge.mjs")))
    if not script.is_file():
        raise ConnectorError(
            "dependency", "Install the bundled Framer bridge before using this connector"
        )
    try:
        result = subprocess.run(
            ["node", str(script)],
            input=json.dumps({"connection": connection.model_dump(), "request": request}),
            text=True,
            capture_output=True,
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ConnectorError(
            "write_uncertain" if request["action"] == "write" else "transport_failed",
            "Framer bridge failed; inspect the project before retrying a write",
        ) from None
    if result.returncode or len(result.stdout) > 2_000_000:
        raise ConnectorError(
            "provider_error", "Framer operation failed; check credentials, mappings and revision"
        )
    try:
        value = json.loads(result.stdout)
        if not isinstance(value, list):
            raise ValueError
        return value
    except ValueError:
        raise ConnectorError("invalid_response", "Framer returned an invalid document") from None
