#!/usr/bin/env bash
# Launch the SSH admin MCP over stdio (Cursor IDE / Cloud Agents / Automations).
# Secrets come from the process environment (Cloud Secrets) — do not hardcode them here.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export SSH_DIR="${SSH_DIR:-${HOME:-/tmp}/.ssh}"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

# Ensure FastMCP is importable in cloud VMs without a prior install step.
if ! python3 -c 'import fastmcp' 2>/dev/null; then
  python3 -m pip install --user -q fastmcp
fi
export PATH="${HOME:-/home/ubuntu}/.local/bin:${PATH}"

# Strip quotes/whitespace from flags (Secrets UI / .env paste often stores "true").
strip_env_quotes() {
  local name="$1"
  local val="${!name-}"
  if [ -n "${val}" ]; then
    val="${val#\"}"; val="${val%\"}"
    val="${val#\'}"; val="${val%\'}"
    export "$name=$val"
  fi
}
strip_env_quotes SSH_ENABLE_ARBITRARY_COMMANDS
strip_env_quotes SSH_ALLOW_SUDO

exec "$ROOT/services/ssh/entrypoint.sh" python3 "$ROOT/services/ssh/server.py"
