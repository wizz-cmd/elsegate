"""Elsegate -- Ollama-compatible LLM Gateway.

Route requests to multiple LLM backends through a single Ollama-compatible
API. Add providers via YAML config, no code changes required.

Backends:
    - openai_compat: Any OpenAI-compatible API (Mistral, OpenAI, Groq, etc.)
    - claude_code: Anthropic's Claude Code CLI (full tool execution)
    - ollama_passthru: Forward to a real Ollama instance

Named after the Elsecallers' ability to open portals between worlds
in Brandon Sanderson's Stormlight Archive.
"""

__version__ = "0.1.0"
