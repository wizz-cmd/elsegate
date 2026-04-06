"""Ollama passthrough backend for Elsegate.

Forwards requests unchanged to a real Ollama instance. Used as the
default/fallback route for models not explicitly configured, or for
local models running on a GPU machine.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger("elsegate.backends.ollama_passthru")


class OllamaPassthruBackend:
    """Passthrough backend to a real Ollama instance.

    Args:
        params: Route params from config. Expected keys:

            - ``ollama_url``: Base URL (default: ``http://localhost:11434``)
    """

    def __init__(self, params: dict[str, Any]):
        self._url = params.get("ollama_url", "http://localhost:11434").rstrip("/")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(300, connect=10))

    async def embed(self, model: str, text: str | list[str]) -> list[list[float]]:
        """Forward embed request to Ollama."""
        if isinstance(text, str):
            text = [text]

        for endpoint, key in [("/api/embed", "input"), ("/api/embeddings", "prompt")]:
            try:
                payload = {"model": model, key: text[0] if key == "prompt" else text}
                resp = await self._client.post(f"{self._url}{endpoint}", json=payload)
                resp.raise_for_status()
                data = resp.json()
                if "embeddings" in data:
                    return data["embeddings"]
                if "embedding" in data:
                    return [data["embedding"]]
            except httpx.HTTPStatusError:
                continue
        return []

    async def generate(self, model: str, prompt: str, **kwargs: Any) -> str:
        """Forward generate request to Ollama."""
        resp = await self._client.post(
            f"{self._url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, **kwargs},
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    async def chat(self, model: str, messages: list[dict], **kwargs: Any) -> dict:
        """Forward chat request to Ollama."""
        resp = await self._client.post(
            f"{self._url}/api/chat",
            json={"model": model, "messages": messages, "stream": False, **kwargs},
        )
        resp.raise_for_status()
        return resp.json().get("message", {"role": "assistant", "content": ""})

    async def models(self) -> list[str]:
        """List models from Ollama."""
        try:
            resp = await self._client.get(f"{self._url}/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []

    async def shutdown(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
