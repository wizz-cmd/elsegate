# Configuration Reference

Elsegate is configured via a single YAML file. By default, it looks for `elsegate.yaml` in the current directory. Override with the `ELSEGATE_CONFIG` environment variable.

## File Structure

```yaml
server:
  host: 0.0.0.0       # bind address
  port: 11434          # listen port (Ollama default)

routes:
  <model-name>:        # the name clients use in the "model" field
    backend: <type>    # openai_compat | claude_code | ollama_passthru
    <key>: <value>     # backend-specific parameters
```

## How Routing Works

When a client sends a request with `{"model": "some-model"}`, Elsegate:

1. Looks for an exact match in `routes`
2. If no match, looks for a wildcard route (`"*"`)
3. If no wildcard, returns HTTP 500 with "No route for model"

The matched route determines which backend handles the request.

## Server Configuration

```yaml
server:
  host: 0.0.0.0       # default: 0.0.0.0 (all interfaces)
  port: 11434          # default: 11434 (Ollama standard)
```

The `server` section is optional. If omitted, defaults are used.

## Route Configuration

Each route maps a model name to a backend with its parameters.

### Common Fields

| Field | Required | Description |
|-------|----------|-------------|
| `backend` | Yes | Backend type: `openai_compat`, `claude_code`, or `ollama_passthru` |
| `provider_model` | No | Override the model name sent to the provider. If omitted, the route's model name is used. |

### API Key Handling

API keys are **never stored in the config file**. Instead, use `api_key_env` to reference an environment variable:

```yaml
routes:
  my-model:
    backend: openai_compat
    api_key_env: MY_API_KEY    # Elsegate reads os.environ["MY_API_KEY"] at startup
```

If the environment variable is not set, Elsegate refuses to start with an error message naming the missing variable.

---

## Backend: `openai_compat`

Routes requests to any API that speaks the OpenAI protocol (`/v1/embeddings`, `/v1/chat/completions`).

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `provider_url` | Yes | — | Base URL of the API (e.g. `https://api.mistral.ai/v1`) |
| `api_key_env` | Yes | — | Environment variable containing the API key |
| `provider_model` | No | route name | Model name sent to the provider |
| `timeout` | No | 60 | Request timeout in seconds |
| `connect_timeout` | No | 10 | Connection timeout in seconds |

### Protocol Translation

| Ollama endpoint | Translated to | Response mapping |
|-----------------|---------------|------------------|
| `POST /api/embed` | `POST /v1/embeddings` | `data[].embedding` → `embeddings[]` |
| `POST /api/embeddings` | `POST /v1/embeddings` | `data[0].embedding` → `embedding` |
| `POST /api/generate` | `POST /v1/chat/completions` | `choices[0].message.content` → `response` |
| `POST /api/chat` | `POST /v1/chat/completions` | `choices[0].message` → `message` |

### Examples

**Mistral (tested):**

```yaml
mistral-embed:
  backend: openai_compat
  provider_url: https://api.mistral.ai/v1
  provider_model: mistral-embed
  api_key_env: MISTRAL_API_KEY

mistral-small:
  backend: openai_compat
  provider_url: https://api.mistral.ai/v1
  provider_model: mistral-small-latest
  api_key_env: MISTRAL_API_KEY
```

**OpenAI (untested, should work):**

```yaml
gpt-4o:
  backend: openai_compat
  provider_url: https://api.openai.com/v1
  provider_model: gpt-4o
  api_key_env: OPENAI_API_KEY
```

**Groq (untested, should work):**

```yaml
llama-groq:
  backend: openai_compat
  provider_url: https://api.groq.com/openai/v1
  provider_model: llama-3.3-70b-versatile
  api_key_env: GROQ_API_KEY
```

**Self-hosted vLLM or LiteLLM (untested, should work):**

```yaml
local-llm:
  backend: openai_compat
  provider_url: http://localhost:8000/v1
  provider_model: my-model
  # no api_key_env needed for local endpoints without auth
```

Note: If no `api_key_env` is specified, no `Authorization` header is sent.

---

## Provider Naming Caveat

Some Ollama clients (notably OpenClaw) register API protocol handlers by **provider name**, not by API type. If your client expects a provider named `ollama`, you must name your Elsegate provider `ollama` in the client config -- even though Elsegate is not Ollama.

Example: OpenClaw requires the provider to be named `ollama` for the Ollama API handler to activate:

```json
{
  "models": {
    "providers": {
      "ollama": {
        "baseUrl": "http://elsegate-host:11434",
        "apiKey": "not-needed",
        "api": "ollama"
      }
    }
  }
}
```

Using a custom provider name like `elsegate` with `"api": "ollama"` will fail with `"No API provider registered for api: ollama"` in such clients. This is a client-side limitation, not an Elsegate issue.

---

## Backend: `claude_code`

Wraps [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) as an Ollama-compatible endpoint. Claude Code executes tools natively (web search, shell, file I/O, etc.) and returns the final result.

### Prerequisites

- Claude Code CLI must be installed and **authenticated** on the machine where it runs
- Authentication: `claude login` (interactive), OAuth, or `ANTHROPIC_API_KEY` env var
- The `claude` binary must be in PATH, or specify its location via `cli_path` / `cli_command`

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `cli_command` | No | — | Full command as list (e.g. `["ssh", "host", "claude"]`). Takes precedence over `cli_path`. |
| `cli_path` | No | `claude` | Path to the `claude` binary. Ignored if `cli_command` is set. |
| `max_turns` | No | 50 | Maximum tool-use turns per invocation |
| `work_dir` | No | `.` | Working directory for Claude Code |
| `timeout` | No | 300 | Max seconds per invocation |
| `stateless` | No | `true` | Fresh session per request (recommended) |

### Where Claude Code Runs

Claude Code CLI must be **authenticated** -- it needs an active login session or API key. Elsegate does not handle authentication; it calls `claude` as a subprocess and expects it to work.

There are three common setups:

**Local: Claude Code on the same machine as Elsegate**

The simplest case. Claude Code is installed and authenticated on the machine where Elsegate runs.

```yaml
claude-opus:
  backend: claude_code
  cli_path: claude             # or /usr/local/bin/claude
  stateless: true
```

**Remote: Claude Code on a different machine (via SSH)**

If Claude Code is authenticated on another server (e.g. a dedicated AI workstation, a VM with an existing login), Elsegate can reach it via SSH. Use `cli_command` to specify the full command:

```yaml
claude-opus:
  backend: claude_code
  cli_command: ["ssh", "ai-server.local", "claude"]
  stateless: true
```

This is useful when:
- Claude Code is already authenticated on a different machine and you don't want to set up a second login
- The machine running Elsegate doesn't have Claude Code installed
- You want to keep Claude Code sessions on a specific host

Requirements: passwordless SSH (key-based auth) from the Elsegate host to the remote.

**Docker: Claude Code outside the container**

If Elsegate runs in Docker but Claude Code is authenticated on the host, use `cli_command` to SSH back to the host (or use Docker's host networking):

```yaml
claude-opus:
  backend: claude_code
  cli_command: ["ssh", "host.docker.internal", "claude"]
  stateless: true
```

Or mount the host's Claude auth config into the container (less recommended):

```yaml
# docker-compose.yml
volumes:
  - ~/.claude:/root/.claude:ro
```

### Session Modes

**Stateless (default, recommended):**

Each request gets a fresh session UUID. No context carries over between requests. Use this when the caller sends full context per request.

```yaml
claude-opus:
  backend: claude_code
  stateless: true
```

**Stateful:**

Persistent session across requests. Context accumulates in Claude Code's session store. First request uses `--session-id`, subsequent requests use `--resume`.

```yaml
claude-interactive:
  backend: claude_code
  stateless: false
```

Warning: In stateful mode, session conflicts ("already in use") can occur if the session is locked by another process. Elsegate retries once with a fresh session.

### Tool Handling

If the caller includes `tools` in the request body, Elsegate converts them to prompt context. Claude Code fulfills the intent using its own native tools (Bash, WebSearch, WebFetch, Read, Write, etc.). The response is always a final text answer -- never `tool_calls`.

This means: Claude Code is the tool executor, not the caller.

### Examples

**Minimal (local Claude Code):**

```yaml
claude-opus:
  backend: claude_code
  stateless: true
```

**Full options (local):**

```yaml
claude-opus:
  backend: claude_code
  cli_path: /home/user/.local/bin/claude
  max_turns: 50
  work_dir: /opt/elsegate/workdir
  timeout: 300
  stateless: true
```

**Remote via SSH:**

```yaml
claude-opus:
  backend: claude_code
  cli_command: ["ssh", "ai-server", "claude"]
  max_turns: 50
  timeout: 600                  # longer timeout for network latency
  stateless: true
```

---

## Backend: `ollama_passthru`

Forwards requests unchanged to a real Ollama instance. Use as the wildcard fallback.

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `ollama_url` | No | `http://localhost:11434` | URL of the Ollama instance |

### Example

```yaml
"*":
  backend: ollama_passthru
  ollama_url: http://gpu-server:11434
```

---

## Wildcard Route

The special route name `"*"` matches any model not explicitly configured. This is useful as a fallback:

```yaml
routes:
  mistral-embed:
    backend: openai_compat
    provider_url: https://api.mistral.ai/v1
    api_key_env: MISTRAL_API_KEY

  # Everything else goes to local Ollama
  "*":
    backend: ollama_passthru
    ollama_url: http://localhost:11434
```

If no wildcard is configured and a request arrives for an unknown model, Elsegate returns an error.

---

## Multiple Providers, Same Backend

You can route different model names to different providers, even if they use the same backend type:

```yaml
routes:
  # Mistral for embeddings (cheap)
  mistral-embed:
    backend: openai_compat
    provider_url: https://api.mistral.ai/v1
    provider_model: mistral-embed
    api_key_env: MISTRAL_API_KEY

  # OpenAI for chat (capable)
  gpt-4o:
    backend: openai_compat
    provider_url: https://api.openai.com/v1
    provider_model: gpt-4o
    api_key_env: OPENAI_API_KEY

  # Claude for complex tasks (tool execution)
  claude-opus:
    backend: claude_code
    stateless: true
```

Clients choose the provider by setting the model name in their request.

---

## Full Example

See [examples/elsegate.yaml](../examples/elsegate.yaml) for an annotated configuration file.
