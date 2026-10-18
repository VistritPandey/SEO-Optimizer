#!/usr/bin/env bash
# One public Cloud Run service for Your Optimiser. Configuration is parsed, never sourced.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v uv >/dev/null 2>&1; then
  printf 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/\n' >&2
  exit 1
fi
cd "$ROOT"
exec uv run --locked --all-extras python scripts/deploy_gcp.py "$@"
