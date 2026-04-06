"""Tests for Elsegate backends."""

import json

import pytest

from elsegate.backends.claude_code import ClaudeCodeBackend


class TestClaudeCodeConsolidate:
    """Tests for message consolidation logic."""

    def test_simple_messages(self):
        msgs = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        result = ClaudeCodeBackend._consolidate_messages(msgs)
        assert "System: You are helpful." in result
        assert "User: Hello" in result

    def test_preserves_all_roles(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
            {"role": "assistant", "content": "ast"},
            {"role": "user", "content": "usr2"},
        ]
        result = ClaudeCodeBackend._consolidate_messages(msgs)
        assert result.count("System:") == 1
        assert result.count("User:") == 2
        assert result.count("Assistant:") == 1

    def test_tool_role_messages(self):
        msgs = [
            {"role": "user", "content": "search for weather"},
            {"role": "tool", "name": "web_search", "content": "15°C, cloudy"},
            {"role": "user", "content": "summarize that"},
        ]
        result = ClaudeCodeBackend._consolidate_messages(msgs)
        assert "[Tool result from web_search]: 15°C, cloudy" in result

    def test_tool_role_without_name(self):
        msgs = [{"role": "tool", "content": "some result"}]
        result = ClaudeCodeBackend._consolidate_messages(msgs)
        assert "[Tool result from tool]:" in result

    def test_tool_name_from_tool_name_field(self):
        msgs = [{"role": "tool", "tool_name": "exec", "content": "done"}]
        result = ClaudeCodeBackend._consolidate_messages(msgs)
        assert "[Tool result from exec]:" in result

    def test_skips_empty_content(self):
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "world"},
        ]
        result = ClaudeCodeBackend._consolidate_messages(msgs)
        assert "Assistant:" not in result
        assert "User: hello" in result
        assert "User: world" in result

    def test_handles_dict_content(self):
        msgs = [{"role": "tool", "name": "api", "content": {"key": "value"}}]
        result = ClaudeCodeBackend._consolidate_messages(msgs)
        assert '"key": "value"' in result

    def test_empty_messages(self):
        assert ClaudeCodeBackend._consolidate_messages([]) == ""


class TestClaudeCodeToolsToContext:
    """Tests for tool definition conversion."""

    def test_no_tools(self):
        assert ClaudeCodeBackend._tools_to_context(None) == ""
        assert ClaudeCodeBackend._tools_to_context([]) == ""

    def test_single_tool(self):
        tools = [{
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web",
            },
        }]
        result = ClaudeCodeBackend._tools_to_context(tools)
        assert "**web_search**" in result
        assert "Search the web" in result
        assert "native tools" in result.lower()

    def test_multiple_tools(self):
        tools = [
            {"function": {"name": "search", "description": "Search"}},
            {"function": {"name": "exec", "description": "Execute command"}},
            {"function": {"name": "read", "description": "Read file"}},
        ]
        result = ClaudeCodeBackend._tools_to_context(tools)
        assert "**search**" in result
        assert "**exec**" in result
        assert "**read**" in result

    def test_flat_tool_format(self):
        """Some callers send tools without the function wrapper."""
        tools = [{"name": "fetch", "description": "Fetch a URL"}]
        result = ClaudeCodeBackend._tools_to_context(tools)
        assert "**fetch**" in result

    def test_no_tool_call_instruction(self):
        tools = [{"function": {"name": "x", "description": "y"}}]
        result = ClaudeCodeBackend._tools_to_context(tools)
        assert "Do NOT output tool_call JSON" in result


class TestClaudeCodeEmbed:
    """Test that embed raises NotImplementedError."""

    @pytest.mark.asyncio
    async def test_embed_not_supported(self):
        backend = ClaudeCodeBackend({})
        with pytest.raises(NotImplementedError):
            await backend.embed("model", "text")
