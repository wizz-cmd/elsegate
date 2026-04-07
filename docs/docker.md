# Docker Deployment

## Quick Start

```bash
docker build -t elsegate .
docker run -p 11434:11434 \
  -v ./elsegate.yaml:/app/elsegate.yaml:ro \
  -e MISTRAL_API_KEY=your-key \
  elsegate
```

## Docker Compose

Create a `docker-compose.yml`:

```yaml
services:
  elsegate:
    build: .
    container_name: elsegate
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ./elsegate.yaml:/app/elsegate.yaml:ro
    env_file: .env
    environment:
      - ELSEGATE_CONFIG=/app/elsegate.yaml
```

Create a `.env` file for secrets (**never commit this file**):

```bash
# .env
MISTRAL_API_KEY=your-mistral-api-key
OPENAI_API_KEY=your-openai-api-key
```

Start:

```bash
docker compose up -d
docker compose logs -f elsegate
```

## Using `.env` for API Keys

Docker Compose reads `.env` automatically. The `env_file: .env` directive passes all variables to the container. Elsegate's config references them via `api_key_env`:

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ .env         │────▶│ Docker Compose    │────▶│ Container env       │
│              │     │ (env_file: .env)  │     │                     │
│ MISTRAL_API_ │     │                   │     │ MISTRAL_API_KEY=... │
│ KEY=sk-...   │     │                   │     │                     │
└─────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                         │
                                              ┌──────────▼──────────┐
                                              │ elsegate.yaml        │
                                              │                      │
                                              │ api_key_env:         │
                                              │   MISTRAL_API_KEY    │
                                              │                      │
                                              │ → Elsegate reads     │
                                              │   os.environ[...]    │
                                              └──────────────────────┘
```

This keeps secrets out of config files and version control.

## Claude Code Backend in Docker

The `claude_code` backend needs access to an **authenticated** Claude Code CLI. Claude Code authenticates via OAuth or API key -- the credentials are stored in `~/.claude/` on the machine where `claude login` was run.

In a Docker deployment, there are several ways to handle this:

### Option A: Don't use Claude Code in Docker (simplest)

If you only need `openai_compat` routes (embeddings, chat via Mistral/OpenAI), the Docker image works out of the box. Skip the `claude_code` route in your config.

If you also need Claude Code, run Elsegate directly on the host where `claude` is authenticated (as a systemd service or in a shell), not in Docker.

### Option B: Reach a remote Claude Code via SSH

If Claude Code is authenticated on a different machine, use `cli_command` in your config to call it via SSH. Elsegate runs in Docker, Claude Code runs elsewhere:

```yaml
# elsegate.yaml
claude-opus:
  backend: claude_code
  cli_command: ["ssh", "ai-server.local", "claude"]
  stateless: true
```

The Docker container only needs SSH client access to the target host. No Claude Code installation needed in the container.

### Option C: Mount host credentials into the container

Mount `~/.claude/` from the host into the container:

```yaml
# docker-compose.yml
volumes:
  - ~/.claude:/root/.claude:ro
```

This shares the host's authentication with the container. Claude Code CLI must also be installed in the container (the Dockerfile handles this).

### Option D: API key in environment

Set `ANTHROPIC_API_KEY` in the container's environment:

```yaml
# docker-compose.yml
environment:
  - ANTHROPIC_API_KEY=your-key
```

This bypasses OAuth and authenticates directly. Claude Code CLI must be installed in the container.

## Health Check

Add a health check to your compose file:

```yaml
services:
  elsegate:
    # ...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

## Example: Embeddings-Only Deployment

A minimal deployment that just proxies embedding requests to Mistral:

```yaml
# docker-compose.yml
services:
  elsegate:
    build: .
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ./elsegate.yaml:/app/elsegate.yaml:ro
    env_file: .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

```yaml
# elsegate.yaml
server:
  port: 11434

routes:
  mistral-embed:
    backend: openai_compat
    provider_url: https://api.mistral.ai/v1
    provider_model: mistral-embed
    api_key_env: MISTRAL_API_KEY
```

```bash
# .env
MISTRAL_API_KEY=your-key
```

```bash
docker compose up -d
curl http://localhost:11434/health
```
