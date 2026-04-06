"""Backend implementations for Elsegate.

Each backend translates between Ollama protocol and a specific LLM provider.
New backends are registered in :data:`elsegate.router.BACKEND_TYPES`.

Design Pattern: **Strategy** (Gamma et al., 1994).
Each backend implements the same protocol; the router selects the
appropriate one based on the model name in the request.
"""

from __future__ import annotations

from typing import Protocol, Any


class Backend(Protocol):
    """Protocol for LLM backends (Strategy Pattern).

    Each backend translates Ollama-format requests into provider-specific
    API calls and maps the responses back to Ollama format.
    """

    async def embed(self, model: str, text: str | list[str]) -> list[list[float]]:
        """Generate embeddings.

        Args:
            model: Provider-side model name.
            text: Single string or list of strings to embed.

        Returns:
            List of embedding vectors (one per input string).
        """
        ...

    async def generate(self, model: str, prompt: str, **kwargs: Any) -> str:
        """Generate a text completion.

        Args:
            model: Provider-side model name.
            prompt: The prompt text.

        Returns:
            Generated text.
        """
        ...

    async def chat(self, model: str, messages: list[dict], **kwargs: Any) -> dict:
        """Chat completion.

        Args:
            model: Provider-side model name.
            messages: List of ``{"role": ..., "content": ...}`` dicts.
            tools: Optional list of Ollama tool definitions (via kwargs).

        Returns:
            Dict with at least ``{"role": "assistant", "content": "..."}``.
        """
        ...

    async def models(self) -> list[str]:
        """List available model names for this backend."""
        ...
