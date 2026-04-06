# Elsegate

> **Early alpha. Use at your own risk.** Tested with Mistral API and Claude Code CLI only. Other OpenAI-compatible providers (OpenAI, Groq, Together, etc.) should work via `openai_compat` but are untested.

Ollama-compatible LLM gateway. Route requests to multiple backends through a single API endpoint.

```
Client (any Ollama-compatible app)
    │
    ▼  Ollama protocol (:11434)
┌──────────────────────────────────┐
│  Elsegate                        │
│  model name → backend            │
│                                  │
│  mistral-embed → Mistral API  ✓ │
│  claude-opus   → Claude Code  ✓ │
│  gpt-4o        → OpenAI API  ? │
│  llama3:8b     → local Ollama ? │
└──────────────────────────────────┘
  ✓ = tested    ? = should work, untested
```

## Why

- You have applications that only speak Ollama protocol, but you want to use other providers.
- You want a single endpoint for multiple LLM backends (cloud APIs, Claude Code, local models).
- You want to add new providers via config, not code.

## Quick Start

```bash
git clone https://github.com/wizz-cmd/elsegate.git
cd elsegate
pip install -e .
```

Create `elsegate.yaml`:

```yaml
server:
  port: 11434

routes:
  mistral-embed:
    backend: openai_compat
    provider_url: https://api.mistral.ai/v1
    provider_model: mistral-embed
    api_key_env: MISTRAL_API_KEY

  claude-opus:
    backend: claude_code
    stateless: true

  "*":
    backend: ollama_passthru
    ollama_url: http://localhost:11434
```

```bash
export MISTRAL_API_KEY=your-key
uvicorn elsegate.server:app --port 11434
```

Now any Ollama client can use `mistral-embed` for embeddings and `claude-opus` for chat, transparently.

## Backends

### `openai_compat`

Routes to any OpenAI-compatible API. Tested with Mistral. Should work with OpenAI, Groq, Together, Fireworks, and others (untested).

```yaml
my-model:
  backend: openai_compat
  provider_url: https://api.mistral.ai/v1
  provider_model: mistral-small-latest
  api_key_env: MISTRAL_API_KEY
```

Supports: `/api/embed`, `/api/embeddings`, `/api/generate`, `/api/chat`.

### `claude_code`

Wraps [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) as an Ollama-compatible endpoint. Claude Code executes tools natively (web search, shell, file I/O) and returns the final result.

```yaml
claude-opus:
  backend: claude_code
  cli_path: claude          # must be installed and authenticated
  max_turns: 50
  timeout: 300
  stateless: true           # fresh session per request (default)
```

Supports: `/api/generate`, `/api/chat`. Does **not** support `/api/embed`.

**Tool handling:** If the caller sends Ollama `tools` definitions, they are converted to prompt context. Claude Code fulfills the intent using its native tools. No `tool_calls` are returned -- the response is always a final text answer.

**Modes:**

| Mode | Behavior | Use case |
|------|----------|----------|
| `stateless: true` (default) | Fresh session per request | Callers that send full context per request |
| `stateless: false` | Persistent session, uses `--resume` | Interactive sessions where context accumulates |

### `ollama_passthru`

Forwards requests unchanged to a real Ollama instance. Use as the wildcard fallback for local models. Untested -- included for completeness.

```yaml
"*":
  backend: ollama_passthru
  ollama_url: http://localhost:11434
```

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/embed` | POST | Generate embeddings (newer Ollama format) |
| `/api/embeddings` | POST | Generate embeddings (older Ollama format) |
| `/api/generate` | POST | Text completion |
| `/api/chat` | POST | Chat completion (with optional `tools`) |
| `/api/tags` | GET | List available models |
| `/health` | GET | Health check |

## Docker

```bash
docker build -t elsegate .
docker run -p 11434:11434 -v ./elsegate.yaml:/app/elsegate.yaml \
  -e MISTRAL_API_KEY=your-key elsegate
```

## Documentation

- **[Configuration Reference](docs/configuration.md)** -- all settings, all backends, all parameters
- **[Docker Deployment](docs/docker.md)** -- Docker Compose, `.env` files, health checks
- **[examples/elsegate.yaml](examples/elsegate.yaml)** -- annotated example config

## Design

- **Strategy Pattern** for backends -- new providers require only a new class, no changes to routing or server.
- **Router Pattern** for dispatch -- model name in the request determines the backend, configured via YAML.
- ~400 lines of Python. No framework beyond FastAPI.

## Requirements

- Python 3.11+
- For `claude_code` backend: [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated

## Status

**Early alpha (v0.1.0).** This project scratches a specific itch and is shared as-is.

Tested:
- `openai_compat` backend with Mistral API (embeddings + chat)
- `claude_code` backend with Claude Code CLI v2.1.92 (chat + native tool execution)

Not tested:
- `openai_compat` with OpenAI, Groq, Together, or other providers
- `ollama_passthru` backend
- Streaming (`"stream": true` is silently ignored)
- High concurrency
- Production hardening

Contributions and bug reports welcome.

## License

AGPL-3.0. See [LICENSE](LICENSE).
