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

The `claude_code` backend requires the Claude Code CLI inside the container. The provided Dockerfile installs it via npm:

```dockerfile
RUN npm install -g @anthropic-ai/claude-code
```

However, Claude Code CLI must be **authenticated**. In Docker, this means either:

1. **Mount the auth config** from the host:
   ```yaml
   volumes:
     - ~/.claude:/root/.claude:ro
   ```

2. **Set `ANTHROPIC_API_KEY`** in the environment:
   ```yaml
   environment:
     - ANTHROPIC_API_KEY=your-key
   ```

3. **Run the `claude_code` backend on the host** instead of in Docker (recommended if Claude Code is already authenticated on the host).

Option 3 is simplest: run Elsegate directly on the host where `claude` is authenticated, and use Docker only for deployments that don't need the `claude_code` backend.

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
