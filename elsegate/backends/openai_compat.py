"""OpenAI-compatible backend for Elsegate.

Translates Ollama-format requests to OpenAI API format and maps responses
back. Works with any OpenAI-compatible provider: Mistral, OpenAI, Groq,
Together, Fireworks, etc.

Protocol mapping:
    Ollama ``/api/embed``       → ``POST /v1/embeddings``
    Ollama ``/api/embeddings``  → ``POST /v1/embeddings``
    Ollama ``/api/generate``    → ``POST /v1/chat/completions``
    Ollama ``/api/chat``        → ``POST /v1/chat/completions``
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger("elsegate.backends.openai_compat")


class OpenAICompatBackend:
    """Backend for OpenAI-compatible APIs.

    Args:
        params: Route params from config. Expected keys:

            - ``provider_url``: Base URL (e.g. ``https://api.mistral.ai/v1``)
            - ``api_key``: Bearer token (resolved from ``api_key_env``)
            - ``provider_model``: Model name override for the provider
            - ``timeout``: Request timeout in seconds (default 60)
            - ``connect_timeout``: Connection timeout in seconds (default 10)
    """

    def __init__(self, params: dict[str, Any]):
        self._url = params.get("provider_url", "").rstrip("/")
        self._api_key = params.get("api_key", "")
        self._timeout = httpx.Timeout(
            params.get("timeout", 60),
            connect=params.get("connect_timeout", 10),
        )
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )

    async def embed(self, model: str, text: str | list[str]) -> list[list[float]]:
        """Generate embeddings via ``/v1/embeddings``.

        Args:
            model: Provider model name (e.g. ``mistral-embed``).
            text: Single string or list of strings.

        Returns:
            List of embedding vectors.
        """
        if isinstance(text, str):
            text = [text]

        resp = await self._client.post(
            f"{self._url}/embeddings",
            json={"model": model, "input": text},
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data.get("data", [])]

    async def generate(self, model: str, prompt: str, **kwargs: Any) -> str:
        """Generate text via ``/v1/chat/completions``.

        Wraps the prompt as a user message.

        Args:
            model: Provider model name.
            prompt: Text prompt.

        Returns:
            Generated text.
        """
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat(model, messages, **kwargs)
        return result.get("content", "")

    async def chat(self, model: str, messages: list[dict], **kwargs: Any) -> dict:
        """Chat completion via ``/v1/chat/completions``.

        Args:
            model: Provider model name.
            messages: OpenAI-format messages.

        Returns:
            Dict with ``role`` and ``content``.
        """
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]

        resp = await self._client.post(
            f"{self._url}/chat/completions",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        return {"role": msg.get("role", "assistant"), "content": msg.get("content", "")}

    async def models(self) -> list[str]:
        """List models (not typically used for remote APIs)."""
        return []

    async def shutdown(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
