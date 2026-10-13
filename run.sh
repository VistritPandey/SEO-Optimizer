#!/usr/bin/env bash
# Your Optimiser: bootstrap the pinned Python environment and start the setup wizard.
set -euo pipefail
INSTALL_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$INSTALL_ROOT"
if ! command -v uv >/dev/null 2>&1; then
  printf 'Installing uv, the Python environment manager…\n'
  INSTALL_SCRIPT="$(mktemp)"
  trap 'rm -f "$INSTALL_SCRIPT"' EXIT
  if command -v curl >/dev/null 2>&1; then
    curl --proto '=https' --tlsv1.2 -fsSL https://astral.sh/uv/install.sh -o "$INSTALL_SCRIPT"
  elif command -v wget >/dev/null 2>&1; then
    wget -q https://astral.sh/uv/install.sh -O "$INSTALL_SCRIPT"
  else
    printf 'Install curl or wget, then run ./run.sh again.\n' >&2; exit 1
  fi
  sh "$INSTALL_SCRIPT"
  export PATH="${XDG_BIN_HOME:-${HOME}/.local/bin}:$PATH"
fi
uv sync --locked --no-dev --python 3.12
exec uv run --no-sync python -m seo_optimizer.local "$@"
