"""Configuration loader for Elsegate.

Reads elsegate.yaml and resolves environment variable references in
api_key_env fields. Validates route definitions at startup.

Config format::

    server:
      host: 0.0.0.0
      port: 11434

    routes:
      model-name:
        backend: openai_compat | claude_code | ollama_passthru
        ... backend-specific fields ...
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RouteConfig:
    """Configuration for a single model route.

    Attributes:
        model: The model name that triggers this route.
        backend: Backend type (``openai_compat``, ``claude_code``,
            ``ollama_passthru``).
        params: Backend-specific parameters from the config file.
    """

    model: str
    backend: str
    params: dict[str, Any] = field(default_factory=dict)

    def resolve_env(self) -> None:
        """Replace ``api_key_env`` references with values from environment.

        Raises:
            ValueError: If the referenced environment variable is not set.
        """
        key_env = self.params.get("api_key_env")
        if key_env:
            self.params["api_key"] = os.environ.get(key_env, "")
            if not self.params["api_key"]:
                raise ValueError(
                    f"Route '{self.model}': env var '{key_env}' is not set"
                )


@dataclass
class ServerConfig:
    """Server bind configuration.

    Attributes:
        host: Bind address. Default ``0.0.0.0``.
        port: Listen port. Default ``11434`` (Ollama standard).
    """

    host: str = "0.0.0.0"
    port: int = 11434


@dataclass
class ElsegateConfig:
    """Top-level Elsegate configuration.

    Attributes:
        routes: Mapping of model names to route configurations.
        server: Server bind settings.
        default_backend: Backend name for the wildcard route, if any.
    """

    routes: dict[str, RouteConfig] = field(default_factory=dict)
    server: ServerConfig = field(default_factory=ServerConfig)
    default_backend: str | None = None

    def route_for(self, model: str) -> RouteConfig | None:
        """Find the route config for a model name.

        Resolution order:
        1. Exact match (``mistral-small-latest``)
        2. Strip provider prefix (``elsegate/mistral-small-latest`` → ``mistral-small-latest``)
        3. Wildcard (``*``)

        Some clients (e.g. OpenClaw) prefix the model name with the
        provider name (``provider/model``). Step 2 handles this transparently.

        Args:
            model: The model name from the Ollama request.

        Returns:
            Matching :class:`RouteConfig`, or ``None`` if no route matches.
        """
        # 1. Exact match
        if model in self.routes:
            return self.routes[model]
        # 2. Strip provider prefix (e.g. "elsegate/claude-opus" → "claude-opus")
        if "/" in model:
            stripped = model.split("/", 1)[1]
            if stripped in self.routes:
                return self.routes[stripped]
        # 3. Wildcard
        if "*" in self.routes:
            return self.routes["*"]
        return None


def load_config(path: str | Path) -> ElsegateConfig:
    """Load and validate Elsegate configuration from a YAML file.

    Args:
        path: Path to ``elsegate.yaml``.

    Returns:
        Parsed and validated :class:`ElsegateConfig`.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If a required env var is missing or a route has no backend.
    """
    path = Path(path)
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    config = ElsegateConfig()

    srv = raw.get("server", {})
    config.server = ServerConfig(
        host=srv.get("host", "0.0.0.0"),
        port=srv.get("port", 11434),
    )

    for model_name, route_def in raw.get("routes", {}).items():
        backend = route_def.pop("backend", None)
        if not backend:
            raise ValueError(f"Route '{model_name}': missing 'backend' field")
        rc = RouteConfig(model=model_name, backend=backend, params=route_def)
        rc.resolve_env()
        config.routes[model_name] = rc

    if "*" in config.routes:
        config.default_backend = config.routes["*"].backend

    return config
