"""Claude Code CLI backend for Elsegate.

Wraps Anthropic's Claude Code CLI as an Ollama-compatible endpoint. This
gives any Ollama-native application access to Claude's full capabilities,
including native tool execution (web search, shell, file I/O, etc.).

Two modes:

- **stateless** (default): Each request gets a fresh session. The caller
  sends full context per request. No session continuity.
- **stateful**: Persistent session across requests. Context accumulates
  in Claude Code's session store.

Tool handling:
    If the caller sends Ollama tool definitions (``tools`` field), they
    are converted to prompt context. Claude Code executes equivalent
    actions using its native tools (Bash, WebSearch, Read, Write, etc.)
    and returns the final result as text. No ``tool_calls`` are returned.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

log = logging.getLogger("elsegate.backends.claude_code")


class ClaudeCodeBackend:
    """Backend wrapping Claude Code CLI for Ollama-compatible access.

    Args:
        params: Route params from config. Expected keys:

            - ``cli_path``: Path to ``claude`` binary (default: ``claude``)
            - ``max_turns``: Max tool-use turns per invocation (default: 50)
            - ``work_dir``: Working directory for Claude Code (default: ``.``)
            - ``timeout``: Max seconds per invocation (default: 300)
            - ``stateless``: Fresh session per request (default: ``true``)
    """

    def __init__(self, params: dict[str, Any]):
        self._cli_path = params.get("cli_path", "claude")
        self._max_turns = str(params.get("max_turns", 50))
        self._work_dir = params.get("work_dir", ".")
        self._timeout = params.get("timeout", 300)
        self._stateless = params.get("stateless", True)
        self._session_id: str = str(uuid.uuid4())
        self._is_first: bool = True

    async def embed(self, model: str, text: str | list[str]) -> list[list[float]]:
        """Not supported -- Claude Code CLI cannot generate embeddings.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError("Claude Code CLI does not support embeddings")

    async def generate(self, model: str, prompt: str, **kwargs: Any) -> str:
        """Generate text by invoking Claude Code CLI.

        Args:
            model: Ignored (route already selected this backend).
            prompt: Text prompt.

        Returns:
            Claude's response text.
        """
        return await self._invoke(prompt)

    async def chat(self, model: str, messages: list[dict], **kwargs: Any) -> dict:
        """Chat completion via Claude Code CLI.

        Consolidates all messages into a single prompt. If tool definitions
        are present, they are converted to prompt context -- Claude Code
        executes equivalent actions using its native tools.

        Args:
            model: Ignored.
            messages: Ollama-format message list.
            tools: Optional tool definitions (via kwargs).

        Returns:
            Dict with ``role`` and ``content``. Never contains
            ``tool_calls`` -- Claude Code executes tools internally.
        """
        tools = kwargs.get("tools")
        tools_context = self._tools_to_context(tools) if tools else ""
        prompt = self._consolidate_messages(messages)

        if tools_context:
            prompt = tools_context + "\n\n---\n\n" + prompt

        if not prompt:
            return {"role": "assistant", "content": ""}

        response = await self._invoke(prompt)
        return {"role": "assistant", "content": response}

    @staticmethod
    def _tools_to_context(tools: list[dict]) -> str:
        """Convert Ollama tool definitions into prompt context.

        Claude Code has native tools (Bash, WebSearch, Read, Write, etc.)
        that cover most common tool definitions. External definitions
        become documentation so Claude knows the caller's intent and can
        fulfill it using native equivalents.

        Args:
            tools: Ollama-format tool definitions.

        Returns:
            Formatted prompt section, or empty string if no tools.
        """
        if not tools:
            return ""

        lines = [
            "## Caller's Tool Definitions",
            "",
            "The caller expects you to have these capabilities.",
            "Use your native tools (Bash, WebSearch, WebFetch, Read, Write,",
            "Edit, Glob, Grep, etc.) to fulfill the intent directly.",
            "Do NOT output tool_call JSON -- execute actions and report results.",
            "",
        ]

        for tool in tools:
            func = tool.get("function", tool)
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            lines.append(f"- **{name}**: {desc}")

        return "\n".join(lines)

    @staticmethod
    def _consolidate_messages(messages: list[dict]) -> str:
        """Consolidate chat messages into a single prompt string.

        Preserves all message roles (system, user, assistant, tool) so
        that no context is lost. Tool result messages from previous
        relay cycles are rendered as inline context.

        Args:
            messages: Ollama-format message list.

        Returns:
            Consolidated prompt string.
        """
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, (dict, list)):
                content = json.dumps(content, ensure_ascii=False)
            if not content:
                continue

            if role == "tool":
                tool_name = msg.get("name", msg.get("tool_name", "tool"))
                parts.append(f"[Tool result from {tool_name}]: {content}")
            else:
                parts.append(f"{role.capitalize()}: {content}")
        return "\n\n".join(parts)

    async def models(self) -> list[str]:
        """List available models."""
        return ["claude-opus"]

    async def _invoke(self, prompt: str) -> str:
        """Invoke Claude Code CLI and return the response text.

        In stateless mode, every call gets a fresh session ID.
        In stateful mode, uses ``--resume`` for continuity.

        Args:
            prompt: The consolidated prompt string.

        Returns:
            Claude's response text, or an error message.
        """
        for attempt in range(2):
            cmd = [
                self._cli_path,
                "--print",
                "--output-format", "json",
                "--dangerously-skip-permissions",
                "--allow-dangerously-skip-permissions",
                "--max-turns", self._max_turns,
            ]

            if self._stateless:
                session_id = str(uuid.uuid4())
                cmd.extend(["--session-id", session_id])
            else:
                if self._is_first:
                    cmd.extend(["--session-id", self._session_id])
                else:
                    cmd.extend(["--resume", self._session_id])

            # Pass prompt via stdin to avoid ARG_MAX limits.
            # OpenClaw sends full context (SOUL.md + tools + memory) which
            # can exceed Linux's ~2MB command-line argument limit.
            cmd.extend(["-p", "-"])

            log.info(
                "Invoking Claude Code (stateless=%s, attempt=%d, prompt=%dB)",
                self._stateless, attempt + 1, len(prompt.encode("utf-8")),
            )

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self._work_dir,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(input=prompt.encode("utf-8")),
                        timeout=self._timeout,
                    )
                except asyncio.TimeoutError:
                    log.error("Claude Code timed out after %ds", self._timeout)
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.communicate(), timeout=10)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.communicate()
                    return f"Timeout after {self._timeout}s."
            except FileNotFoundError:
                log.error("Claude CLI not found at '%s'", self._cli_path)
                return "Error: Claude CLI not found."
            except Exception as e:
                log.error("Failed to invoke Claude Code: %s", e)
                return f"Error: {e}"

            returncode = proc.returncode
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

            if not self._stateless and returncode != 0 and (
                "already in use" in stderr_text or "Invalid session ID" in stderr_text
            ):
                log.warning("Session error, resetting: %s", stderr_text.strip()[:200])
                self._session_id = str(uuid.uuid4())
                self._is_first = True
                continue

            if stdout:
                try:
                    data = json.loads(stdout.decode("utf-8"))
                    result = data.get("result", "")
                    cost = data.get("total_cost_usd", 0)
                    if cost:
                        log.info("Cost: $%.4f", cost)
                    if result:
                        if not self._stateless:
                            self._is_first = False
                        return result
                    if data.get("is_error"):
                        errors = data.get("errors", [])
                        return f"Error: {'; '.join(errors)}" if errors else "Unknown error."
                except json.JSONDecodeError:
                    log.error("Failed to parse Claude output")

            if returncode != 0:
                log.error("Claude Code failed (exit=%d): %s", returncode, stderr_text[:500])
                return f"Claude Code error (exit {returncode})."

            if not self._stateless:
                self._is_first = False
            return "Done."

        return "Session error could not be resolved."

    async def shutdown(self) -> None:
        """No persistent resources to clean up."""
        pass
