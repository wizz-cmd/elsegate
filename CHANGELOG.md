# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-04-06

### Added

- Initial release
- Three backends: `openai_compat`, `claude_code`, `ollama_passthru`
- YAML-based route configuration
- Ollama-compatible endpoints: `/api/embed`, `/api/embeddings`, `/api/generate`, `/api/chat`, `/api/tags`, `/health`
- Tool definitions converted to prompt context in `claude_code` backend
- Stateless and stateful session modes for `claude_code` backend
- 24 unit tests (config, message consolidation, tool handling)
- Docker support
- Configuration reference and Docker deployment guide

### Tested With

- Mistral API (`mistral-embed`, `mistral-small-latest`) via `openai_compat`
- Claude Code CLI v2.1.92 via `claude_code`
