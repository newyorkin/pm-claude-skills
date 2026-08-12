"""MCP tools for administering Debian hosts over SSH."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass

from fastmcp import FastMCP

mcp = FastMCP("SSH hosts")

HOST_ALIASES = {
    # Vienna
    "vie": "vie",
    "vienna": "vie",
    "вена": "vie",
    "вену": "vie",
    "вене": "vie",
    "веной": "vie",
    "вены": "vie",
    # Finland
    "fin": "fin",
    "finland": "fin",
    "финка": "fin",
    "финку": "fin",
    "финке": "fin",
    "финкой": "fin",
    "финки": "fin",
    "финляндия": "fin",
    "финляндию": "fin",
    "финляндии": "fin",
}
CONTAINER_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")
BLOCKED_COMMANDS = (
    re.compile(r"\brm\s+(-[^\s]*[rRfF][^\s]*)?\s*/(?:\s|$)"),
    re.compile(r"\bmkfs(?:\.\w+)?\b"),
    re.compile(r"\bdd\s+.*\bof=/dev/"),
    re.compile(r"\b(?:reboot|shutdown|poweroff|halt)\b"),
    re.compile(r"\b(?:useradd|usermod|userdel|passwd|visudo)\b"),
)


@dataclass(frozen=True)
class SshConfig:
    alias: str
    host: str
    user: str
    port: str
    key_path: str
    known_hosts_path: str


def _normalize_host(host: str) -> str:
    alias = HOST_ALIASES.get(host.strip().lower())
    if not alias:
        allowed = ", ".join(sorted(HOST_ALIASES))
        raise ValueError(f"Unknown host {host!r}. Use one of: {allowed}")
    return alias


def _env_flag(name: str, default: str = "false") -> bool:
    """Truthy env flag; strips whitespace/quotes (Cloud Secrets / .env paste quirks)."""
    raw = os.getenv(name, default)
    if raw is None:
        return False
    normalized = raw.strip().strip("\"'").lower()
    return normalized in {"1", "true", "yes", "on"}


def _config(host: str) -> SshConfig:
    alias = _normalize_host(host)
    prefix = alias.upper()
    known_hosts = os.getenv("SSH_KNOWN_HOSTS_FILE")
    required = {
        f"{prefix}_SSH_HOST": os.getenv(f"{prefix}_SSH_HOST"),
        f"{prefix}_SSH_USER": os.getenv(f"{prefix}_SSH_USER"),
        f"{prefix}_SSH_KEY_FILE": os.getenv(f"{prefix}_SSH_KEY_FILE"),
        "SSH_KNOWN_HOSTS_FILE": known_hosts,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")

    return SshConfig(
        alias=alias,
        host=required[f"{prefix}_SSH_HOST"],
        user=required[f"{prefix}_SSH_USER"],
        port=os.getenv(f"{prefix}_SSH_PORT", "2288"),
        key_path=required[f"{prefix}_SSH_KEY_FILE"],
        known_hosts_path=known_hosts,
    )


def _ssh(host: str, command: str, timeout_seconds: int = 60) -> str:
    config = _config(host)
    completed = subprocess.run(
        [
            "ssh",
            "-i",
            config.key_path,
            "-p",
            config.port,
            "-o",
            "BatchMode=yes",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"UserKnownHostsFile={config.known_hosts_path}",
            "-o",
            "ConnectTimeout=10",
            f"{config.user}@{config.host}",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode:
        raise RuntimeError(f"SSH command failed (exit {completed.returncode}): {output}")
    return output or "(no output)"


def _validate_timeout(timeout_seconds: int) -> int:
    if not 1 <= timeout_seconds <= 300:
        raise ValueError("timeout_seconds must be between 1 and 300")
    return timeout_seconds


@mcp.tool()
def list_hosts() -> str:
    """List configured SSH hosts. Aliases: vie/vienna/вена, fin/finland/финка."""
    lines = []
    labels = {"vie": "vie|vienna|вена", "fin": "fin|finland|финка"}
    for alias in ("vie", "fin"):
        prefix = alias.upper()
        host = os.getenv(f"{prefix}_SSH_HOST")
        user = os.getenv(f"{prefix}_SSH_USER")
        port = os.getenv(f"{prefix}_SSH_PORT", "2288")
        if host and user:
            lines.append(f"{labels[alias]}\t{user}@{host}:{port}")
        else:
            lines.append(f"{labels[alias]}\t(not configured)")
    # Surface gate flags so Automations can see why run_command is blocked.
    lines.append(
        "run_command\t"
        + ("enabled" if _env_flag("SSH_ENABLE_ARBITRARY_COMMANDS") else "disabled")
    )
    lines.append(
        "sudo\t" + ("enabled" if _env_flag("SSH_ALLOW_SUDO") else "disabled")
    )
    return "\n".join(lines)


@mcp.tool()
def host_status(host: str) -> str:
    """Return OS, uptime, memory, disk, and load. host: vie/вена or fin/финка."""
    return _ssh(host, "uname -a; echo; uptime; echo; free -h; echo; df -h /")


@mcp.tool()
def docker_containers(host: str, all_containers: bool = False) -> str:
    """List Docker containers. host: vie/вена or fin/финка."""
    flag = "-a " if all_containers else ""
    return _ssh(host, f"docker ps {flag}--format '{{{{.Names}}}}\t{{{{.Status}}}}\t{{{{.Image}}}}'")


@mcp.tool()
def docker_logs(host: str, container: str, tail: int = 200) -> str:
    """Read latest Docker logs. host: vie/вена or fin/финка."""
    if not CONTAINER_NAME.fullmatch(container):
        raise ValueError("container contains unsupported characters")
    if not 1 <= tail <= 1_000:
        raise ValueError("tail must be between 1 and 1000")
    return _ssh(host, f"docker logs --tail {tail} {container} 2>&1")


@mcp.tool()
def run_command(host: str, command: str, timeout_seconds: int = 60) -> str:
    """Run a remote shell command when enabled in .env. host: vie/вена or fin/финка."""
    if not _env_flag("SSH_ENABLE_ARBITRARY_COMMANDS"):
        raise PermissionError(
            "Arbitrary commands are disabled. Set SSH_ENABLE_ARBITRARY_COMMANDS=true "
            "in MCP env / Cloud Secrets only after reviewing the security implications."
        )
    if not command.strip() or len(command) > 4_000:
        raise ValueError("command must be between 1 and 4000 characters")
    if any(pattern.search(command) for pattern in BLOCKED_COMMANDS):
        raise PermissionError("Command matches a blocked destructive-operation policy")
    if not _env_flag("SSH_ALLOW_SUDO") and re.search(
        r"(^|[;&|]\s*)sudo\b", command
    ):
        raise PermissionError("sudo commands are disabled; set SSH_ALLOW_SUDO=true to permit them")
    return _ssh(host, command, _validate_timeout(timeout_seconds))


if __name__ == "__main__":
    mcp.run()
