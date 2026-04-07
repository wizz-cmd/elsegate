# Claude Code via Tailscale SSH

This guide covers running the `claude_code` backend via Tailscale SSH, where Elsegate runs on one machine (or in Docker) and Claude Code CLI runs on a remote machine authenticated via Tailscale.

## Overview

```
Elsegate (Docker on host A)
    │
    │ tailscale ssh anna@remote-host /path/to/claude --print ...
    │
    ▼
Remote host (Tailscale network)
    │
    │ claude --print --output-format json -p -
    │
    ▼
Claude Code CLI (authenticated, local to remote host)
```

## Prerequisites

1. **Both machines in the same Tailnet** (Tailscale network)
2. **Tailscale SSH enabled on the remote host:**
   ```bash
   sudo tailscale set --ssh
   ```
3. **Tailscale ACL** allows SSH from Elsegate to the remote host (see below)
4. **Claude Code CLI** installed and authenticated on the remote host

## Tailscale ACL Configuration

Tailscale SSH requires explicit ACL rules. This is configured in the Tailscale Admin Console: https://login.tailscale.com/admin/acls

### Step 1: Define tags

Both machines need tags. Add to `tagOwners`:

```json
"tagOwners": {
    "tag:container": ["autogroup:admin"],
    "tag:agent":     ["autogroup:admin"]
}
```

- `tag:container`: for Elsegate (set via `TS_EXTRA_ARGS=--advertise-tags=tag:container` in docker-compose)
- `tag:agent`: for the remote host running Claude Code

### Step 2: Tag the remote host

On the remote host:

```bash
sudo tailscale set --advertise-tags=tag:agent
```

Or via the Tailscale Admin Console: find the machine, edit, add `tag:agent`.

### Step 3: Add SSH ACL rule

In the `ssh` section of your ACL:

```json
"ssh": [
    {
        "action": "accept",
        "src":    ["tag:container"],
        "dst":    ["tag:agent"],
        "users":  ["anna"]
    }
]
```

This allows Elsegate (`tag:container`) to SSH to the remote host (`tag:agent`) as the `anna` OS user.

**Important notes on SSH ACL syntax:**
- `dst` must be a **tag** or **autogroup** -- not a hostname or IP
- `src` with tags cannot target `autogroup:self` (tagged devices are in a separate identity space)
- Tags on both sides is the correct pattern for machine-to-machine SSH

### Step 4: Verify

Changes take effect immediately. Test from the Elsegate container:

```bash
docker exec elsegate-server tailscale --socket /var/run/tailscale/tailscaled.sock \
    ssh anna@remote-host.ts.net 'whoami'
```

## Elsegate Configuration

### Docker Compose

The Elsegate container needs access to the Tailscale daemon socket to use `tailscale ssh`. Share the socket via a Docker volume between the Tailscale sidecar and the Elsegate container:

```yaml
services:
  elsegate:
    # ...
    volumes:
      - tailscale-sock:/var/run/tailscale
    network_mode: "service:tailscale"

  tailscale:
    image: tailscale/tailscale:latest
    # ...
    volumes:
      - tailscale-sock:/var/run/tailscale
    environment:
      - TS_SOCKET=/var/run/tailscale/tailscaled.sock

volumes:
  tailscale-sock:
```

The Elsegate Docker image must include the `tailscale` CLI (for `tailscale ssh`). The provided Dockerfile installs it.

### Route Configuration

Note the argument order: `--socket` is a flag to `tailscale` (before `ssh`), not to the remote command.

```yaml
routes:
  claude-opus:
    backend: claude_code
    cli_command:
      - "tailscale"
      - "--socket"
      - "/var/run/tailscale/tailscaled.sock"
      - "ssh"
      - "anna@remote-host.dusky-anaconda.ts.net"
      - "/path/to/claude"
    stateless: true
    timeout: 600    # longer timeout for network latency
```

Elsegate appends `--print --output-format json --session-id <uuid> -p -` to this command. The full command becomes:

```
tailscale --socket /var/run/tailscale/tailscaled.sock ssh anna@remote-host /path/to/claude --print --output-format json --session-id <uuid> -p -
```

The prompt is piped via stdin (avoiding ARG_MAX limits).

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `tailnet policy does not permit you to SSH` | ACL rule missing or wrong tags | Check ACL `ssh` rules, verify both machines are tagged |
| `tailscale ssh: not found` | `tailscale` CLI not in container | Rebuild Docker image with Tailscale installed |
| `flag provided but not defined: -socket` | `--socket` in wrong position | Must be before `ssh` subcommand: `tailscale --socket ... ssh ...` |
| `connection refused` | Tailscale SSH not enabled on remote | Run `sudo tailscale set --ssh` on the remote host |
| `user not found` | Wrong OS user in ACL or config | Check `users` in ACL matches the OS user on the remote host |
| Version mismatch warnings | Different tailscale versions | Non-fatal, can be ignored. Update both sides when convenient. |
