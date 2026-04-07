# Running Elsegate with systemd

This guide covers running Elsegate as a user-level systemd service. This is the recommended approach for production use without Docker -- it provides automatic restarts, log management, and clean integration with the OS.

## Prerequisites

- Elsegate installed in a virtual environment (see [INSTALLATION.md](../INSTALLATION.md))
- A working `elsegate.yaml` configuration
- Linux with systemd (any modern distro)

## Quick Setup

### 1. Create the secrets file

Store API keys in a separate file that systemd reads at startup. This keeps secrets out of the service unit, config files, and shell history.

```bash
mkdir -p ~/.config/elsegate
cat > ~/.config/elsegate/env <<'EOF'
MISTRAL_API_KEY=your-mistral-key
# Add more keys as needed:
# OPENAI_API_KEY=your-openai-key
EOF
chmod 600 ~/.config/elsegate/env
```

### 2. Create the service unit

```bash
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/elsegate.service <<'EOF'
[Unit]
Description=Elsegate LLM Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/path/to/elsegate
ExecStart=/path/to/elsegate/.venv/bin/python3 -m uvicorn elsegate.server:app --host 0.0.0.0 --port 11434
Restart=always
RestartSec=10
EnvironmentFile=%h/.config/elsegate/env
Environment=ELSEGATE_CONFIG=/path/to/elsegate/elsegate.yaml
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
EOF
```

Replace `/path/to/elsegate` with your actual installation directory.

### 3. Enable and start

```bash
systemctl --user daemon-reload
systemctl --user enable elsegate
systemctl --user start elsegate
```

### 4. Enable lingering (optional but recommended)

By default, user services only run while the user is logged in. Enable lingering to keep Elsegate running after logout:

```bash
sudo loginctl enable-linger $USER
```

### 5. Verify

```bash
systemctl --user status elsegate
curl http://localhost:11434/health
```

## Commands

| Action | Command |
|--------|---------|
| Start | `systemctl --user start elsegate` |
| Stop | `systemctl --user stop elsegate` |
| Restart | `systemctl --user restart elsegate` |
| Status | `systemctl --user status elsegate` |
| Logs (recent) | `journalctl --user -u elsegate -n 50` |
| Logs (follow) | `journalctl --user -u elsegate -f` |
| Logs (since time) | `journalctl --user -u elsegate --since "10 min ago"` |
| Enable on boot | `systemctl --user enable elsegate` |
| Disable on boot | `systemctl --user disable elsegate` |

## Secrets Management

The `EnvironmentFile` directive loads environment variables from a file at service startup. This is the recommended way to handle API keys:

```
~/.config/elsegate/env      ← secrets file (chmod 600)
     │
     ▼
systemd reads at startup
     │
     ▼
elsegate.yaml references via api_key_env
     │
     ▼
Elsegate reads os.environ["MISTRAL_API_KEY"]
```

**Security notes:**

- The env file should be owned by your user and mode `600` (readable only by you)
- Secrets never appear in the service unit file, config files, or process arguments
- `systemctl show elsegate --property=Environment` will show the resolved variables -- this is expected for user services
- For stricter isolation, consider a system-level service (see below)

## Adjusting for Your Setup

### Custom Python path

If your venv is in a non-standard location:

```ini
ExecStart=/home/user/apps/elsegate/.venv/bin/python3 -m uvicorn elsegate.server:app --host 0.0.0.0 --port 11434
```

### Custom port

Change the port in both `elsegate.yaml` and the `ExecStart` line:

```ini
ExecStart=... --port 8080
```

### Claude Code backend

If you use the `claude_code` backend with a local `claude` binary, make sure the `PATH` includes the directory where `claude` is installed:

```ini
Environment=PATH=/home/user/.local/bin:/usr/local/bin:/usr/bin:/bin
```

If Claude Code is on a remote machine (via `cli_command: ["ssh", ...]`), ensure the user running the service has passwordless SSH access to the target.

### Memory limits

To limit Elsegate's memory usage:

```ini
[Service]
MemoryMax=512M
```

Note: this does NOT limit Claude Code subprocesses spawned by the `claude_code` backend. Those run as separate processes.

## System-Level Service (Alternative)

For environments where you want Elsegate to run as a system service (not tied to a user), create the unit file in `/etc/systemd/system/` instead:

```bash
sudo cat > /etc/systemd/system/elsegate.service <<'EOF'
[Unit]
Description=Elsegate LLM Gateway
After=network-online.target

[Service]
Type=simple
User=elsegate
Group=elsegate
WorkingDirectory=/opt/elsegate
ExecStart=/opt/elsegate/.venv/bin/python3 -m uvicorn elsegate.server:app --host 0.0.0.0 --port 11434
Restart=always
RestartSec=10
EnvironmentFile=/etc/elsegate/env
Environment=ELSEGATE_CONFIG=/opt/elsegate/elsegate.yaml

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable elsegate
sudo systemctl start elsegate
```

This runs as a dedicated `elsegate` system user. Create it with:

```bash
sudo useradd --system --no-create-home elsegate
```

## Troubleshooting

### Service fails to start

Check the logs:

```bash
journalctl --user -u elsegate --since "5 min ago" --no-pager
```

Common issues:

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: elsegate` | Wrong Python path | Check `ExecStart` points to the venv's python |
| `env var 'X' is not set` | Missing secret | Check `~/.config/elsegate/env` has the key |
| `FileNotFoundError: elsegate.yaml` | Wrong config path | Check `ELSEGATE_CONFIG` in the unit file |
| `Address already in use` | Port conflict | Another process uses 11434. Check with `ss -tlnp \| grep 11434` |
| `claude: not found` | Missing PATH | Add Claude Code's directory to `Environment=PATH=...` |

### Service stops after logout

Enable lingering:

```bash
sudo loginctl enable-linger $USER
```

### Logs are too verbose / too quiet

Set `ELSEGATE_LOG_LEVEL` in the env file:

```bash
# ~/.config/elsegate/env
ELSEGATE_LOG_LEVEL=WARNING    # or DEBUG, INFO, ERROR
```

(Note: Elsegate does not read this variable yet. This is a planned feature.)
