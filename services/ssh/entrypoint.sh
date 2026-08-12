#!/bin/sh
# Bridges env-provided secrets to the files server.py expects:
#   mcp_key         -> private key file, used for BOTH hosts (VIE_SSH_KEY_FILE / FIN_SSH_KEY_FILE)
#   SSH_KNOWN_HOSTS -> known_hosts file (SSH_KNOWN_HOSTS_FILE)
# Existing *_SSH_KEY_FILE / SSH_KNOWN_HOSTS_FILE (e.g. mounted files) take precedence.
set -eu

# Cloud agent VMs run as non-root (e.g. ubuntu); /root/.ssh is not writable there.
# Prefer explicit SSH_DIR, then ~/.ssh, then a tmp fallback.
if [ -z "${SSH_DIR:-}" ]; then
    if [ -n "${HOME:-}" ] && mkdir -p "${HOME}/.ssh" 2>/dev/null; then
        SSH_DIR="${HOME}/.ssh"
    else
        SSH_DIR="${TMPDIR:-/tmp}/mcp-ssh"
        mkdir -p "$SSH_DIR"
    fi
else
    mkdir -p "$SSH_DIR"
fi
chmod 700 "$SSH_DIR"

# --- Private key (one key for both hosts) ---
KEY_MATERIAL="${mcp_key:-${MCP_KEY:-}}"
if [ -n "$KEY_MATERIAL" ]; then
    KEY_PATH="$SSH_DIR/mcp_key"
    case "$KEY_MATERIAL" in
        *'
'*) printf '%s' "$KEY_MATERIAL" > "$KEY_PATH" ;;   # already multiline
        *)  printf '%b' "$KEY_MATERIAL" > "$KEY_PATH" ;;  # restore literal \n
    esac
    # OpenSSH requires a trailing newline on key files
    if [ -n "$(tail -c1 "$KEY_PATH" 2>/dev/null)" ]; then
        printf '\n' >> "$KEY_PATH"
    fi
    chmod 600 "$KEY_PATH"
    export VIE_SSH_KEY_FILE="${VIE_SSH_KEY_FILE:-$KEY_PATH}"
    export FIN_SSH_KEY_FILE="${FIN_SSH_KEY_FILE:-$KEY_PATH}"
fi

# --- known_hosts (text -> file) ---
if [ -z "${SSH_KNOWN_HOSTS_FILE:-}" ] && [ -n "${SSH_KNOWN_HOSTS:-}" ]; then
    KH_PATH="$SSH_DIR/known_hosts"
    printf '%s\n' "$SSH_KNOWN_HOSTS" > "$KH_PATH"
    chmod 644 "$KH_PATH"
    export SSH_KNOWN_HOSTS_FILE="$KH_PATH"
fi

exec "$@"
