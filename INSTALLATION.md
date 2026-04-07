# Installation

## Requirements

- Python 3.11 or later
- For the `claude_code` backend: [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated (on this machine or a remote one)
- For the `openai_compat` backend: An API key for your provider (Mistral, OpenAI, etc.)

## From Source

```bash
git clone https://github.com/wizz-cmd/elsegate.git
cd elsegate
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Verify:

```bash
python -c "import elsegate; print(elsegate.__version__)"
```

## Configuration

Copy the example config and edit it:

```bash
cp examples/elsegate.yaml elsegate.yaml
```

Set your API keys as environment variables:

```bash
export MISTRAL_API_KEY=your-key-here
```

See [docs/configuration.md](docs/configuration.md) for the full reference.

## Running

### Foreground (for testing)

```bash
uvicorn elsegate.server:app --host 0.0.0.0 --port 11434
```

Or with a custom config path:

```bash
ELSEGATE_CONFIG=/path/to/elsegate.yaml uvicorn elsegate.server:app --host 0.0.0.0 --port 11434
```

Verify it works:

```bash
curl http://localhost:11434/health
```

### systemd (for production)

See [docs/systemd.md](docs/systemd.md) for a complete guide to running Elsegate as a system service with automatic restarts, log management, and secure secret handling.

### Docker

See [docs/docker.md](docs/docker.md) for container deployment with Docker Compose.

## Upgrading

```bash
cd elsegate
git pull
pip install -e .
```

If running via systemd:

```bash
git pull && pip install -e .
systemctl --user restart elsegate
```

## Uninstalling

```bash
pip uninstall elsegate
```

If installed as a systemd service:

```bash
systemctl --user stop elsegate
systemctl --user disable elsegate
rm ~/.config/systemd/user/elsegate.service
systemctl --user daemon-reload
```
