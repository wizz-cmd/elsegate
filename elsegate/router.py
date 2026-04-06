"""Elsegate Router -- model-based dispatch to backends.

Implements the Router Pattern: incoming requests are dispatched to the
appropriate backend based on the model name, using the route table from
``elsegate.yaml``.

Design Pattern: **Router / Front Controller** (Fowler, 2002).
"""

from __future__ import annotations

import logging
from typing import Any

from elsegate.config import ElsegateConfig, RouteConfig
from elsegate.backends import Backend
from elsegate.backends.openai_compat import OpenAICompatBackend
from elsegate.backends.claude_code import ClaudeCodeBackend
from elsegate.backends.ollama_passthru import OllamaPassthruBackend

log = logging.getLogger("elsegate.router")

#: Registry of backend type names to their implementation classes.
#: To add a new backend: implement the :class:`Backend` protocol
#: and add an entry here.
BACKEND_TYPES: dict[str, type] = {
    "openai_compat": OpenAICompatBackend,
    "claude_code": ClaudeCodeBackend,
    "ollama_passthru": OllamaPassthruBackend,
}


class Router:
    """Routes Ollama requests to backends based on model name.

    Args:
        config: Parsed Elsegate configuration.
    """

    def __init__(self, config: ElsegateConfig):
        self.config = config
        self._backends: dict[str, Backend] = {}

    async def initialize(self) -> None:
        """Create backend instances for all configured routes."""
        for model, route in self.config.routes.items():
            if route.backend not in BACKEND_TYPES:
                log.error("Unknown backend '%s' for route '%s'", route.backend, model)
                continue
            backend_key = f"{route.backend}:{route.params.get('provider_url', '')}"
            if backend_key not in self._backends:
                cls = BACKEND_TYPES[route.backend]
                self._backends[backend_key] = cls(route.params)
                log.info("Initialized backend '%s' for model '%s'", route.backend, model)
            route.params["_backend_key"] = backend_key

    async def shutdown(self) -> None:
        """Clean up backend resources."""
        for backend in self._backends.values():
            if hasattr(backend, "shutdown"):
                await backend.shutdown()

    def resolve(self, model: str) -> tuple[Backend, RouteConfig]:
        """Find the backend and route config for a model name.

        Args:
            model: Model name from the Ollama request.

        Returns:
            Tuple of ``(backend_instance, route_config)``.

        Raises:
            ValueError: If no route matches the model.
        """
        route = self.config.route_for(model)
        if not route:
            raise ValueError(f"No route for model '{model}'")
        backend_key = route.params.get("_backend_key")
        backend = self._backends.get(backend_key)
        if not backend:
            raise ValueError(f"Backend not initialized for model '{model}'")
        return backend, route

    async def list_models(self) -> list[str]:
        """List all configured model names (excluding wildcard)."""
        return [m for m in self.config.routes.keys() if m != "*"]
