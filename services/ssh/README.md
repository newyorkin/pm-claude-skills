# mcp-ssh — SSH admin MCP server (VIE / FIN)

A Dockerized [FastMCP](https://gofastmcp.com) server that lets an MCP client run
administrative SSH tasks on two hosts — **VIE** (Vienna) and **FIN** (Finland).
Transport is **stdio** (the container speaks MCP over stdin/stdout).

## Tools

| Tool | Description |
|---|---|
| `list_hosts` | List configured hosts and whether each is set up. |
| `host_status(host)` | `uname`, uptime, memory, disk, load. |
| `docker_containers(host, all_containers=False)` | `docker ps` (names/status/image). |
| `docker_logs(host, container, tail=200)` | Last N log lines of a container. |
| `run_command(host, command, timeout_seconds=60)` | Arbitrary command — **only** when `SSH_ENABLE_ARBITRARY_COMMANDS=true`; `sudo` needs `SSH_ALLOW_SUDO=true`; destructive patterns (`rm -rf /`, `mkfs`, `dd of=/dev/…`, reboot/shutdown, user/passwd changes) are blocked. |

`host` accepts aliases, including Russian cases: `vie`/`vienna`/`вена…`, `fin`/`finland`/`финка…`.

## Configuration (environment variables)

Secrets are provided as env vars. `entrypoint.sh` bridges the two "material"
secrets into the files `server.py` expects, so you pass **one** key for both hosts:

| Env var | Required | Notes |
|---|---|---|
| `mcp_key` | yes | Private key **material** (text). Written to a file (mode 600) and used for BOTH hosts. |
| `SSH_KNOWN_HOSTS` | yes | `known_hosts` **text** (`ssh-keyscan -p 2288 <vie_host> <fin_host>`). Required because `StrictHostKeyChecking=yes`. |
| `VIE_SSH_HOST`, `VIE_SSH_USER` | yes | Vienna host + user. |
| `FIN_SSH_HOST`, `FIN_SSH_USER` | yes | Finland host + user. |
| `VIE_SSH_PORT`, `FIN_SSH_PORT` | no | Default `2288`. |
| `SSH_ENABLE_ARBITRARY_COMMANDS` | no | `true` to enable `run_command`. Default off. |
| `SSH_ALLOW_SUDO` | no | `true` to permit `sudo` in `run_command`. Default off. |

The entrypoint sets `VIE_SSH_KEY_FILE` / `FIN_SSH_KEY_FILE` / `SSH_KNOWN_HOSTS_FILE`
automatically from `mcp_key` / `SSH_KNOWN_HOSTS`. If you instead mount real files
and set those `*_FILE` vars yourself, they take precedence.

## Build

```bash
docker build -t mcp-ssh services/ssh
```

## Run (as a stdio MCP server)

MCP client config (`mcpServers`) — the client launches the container per session:

```json
{
  "mcpServers": {
    "ssh": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "mcp_key",
        "-e", "SSH_KNOWN_HOSTS",
        "-e", "VIE_SSH_HOST", "-e", "VIE_SSH_PORT", "-e", "VIE_SSH_USER",
        "-e", "FIN_SSH_HOST", "-e", "FIN_SSH_PORT", "-e", "FIN_SSH_USER",
        "-e", "SSH_ENABLE_ARBITRARY_COMMANDS",
        "-e", "SSH_ALLOW_SUDO",
        "mcp-ssh"
      ]
    }
  }
}
```

The `-e VAR` (no value) forwards the variable from the client's environment, so
secret **values** stay out of this config.

## Cursor Cloud Agent notes

- Add the secrets in the **Secrets** panel; they are injected on a **fresh run**
  (a follow-up in an existing conversation keeps the same VM and won't see new secrets).
- Inside the micro-VM, Docker needs the `vfs` storage driver — start the daemon with
  `dockerd --storage-driver=vfs` (default `overlayfs` fails to mount there).
- The target hosts must be reachable from the cloud VM (public IP/domain).

## Quick smoke test (no MCP client needed)

Verify the image and the entrypoint bridge with a throwaway key:

```bash
docker build -t mcp-ssh services/ssh
export mcp_key="$(cat /path/to/test_key)"
export SSH_KNOWN_HOSTS="$(ssh-keyscan -p 2288 <vie_host> <fin_host>)"
docker run --rm -e mcp_key -e SSH_KNOWN_HOSTS mcp-ssh \
  sh -c 'ls -l /root/.ssh; echo "$VIE_SSH_KEY_FILE $SSH_KNOWN_HOSTS_FILE"'
```

Then drive the tools with any MCP client (e.g. `fastmcp`'s `Client` over a
`StdioTransport` launching `docker run -i --rm … mcp-ssh`) and call
`list_hosts`, `host_status("vie")`, `docker_containers("fin")`.

## Security

`run_command` + `SSH_ALLOW_SUDO` grant an AI agent root-capable arbitrary command
execution on both hosts. Enable deliberately, prefer a least-privilege SSH user,
keep `SSH_ALLOW_SUDO=false` unless required, and always populate `SSH_KNOWN_HOSTS`.
