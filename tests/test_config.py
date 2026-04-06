"""Tests for Elsegate configuration loading."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from elsegate.config import load_config, RouteConfig, ElsegateConfig


def _write_config(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "elsegate.yaml"
    p.write_text(yaml.dump(data))
    return p


def test_load_minimal_config(tmp_path):
    cfg_path = _write_config(tmp_path, {
        "routes": {
            "test-model": {"backend": "openai_compat", "provider_url": "http://example.com"}
        }
    })
    config = load_config(cfg_path)
    assert "test-model" in config.routes
    assert config.routes["test-model"].backend == "openai_compat"


def test_server_defaults(tmp_path):
    cfg_path = _write_config(tmp_path, {"routes": {}})
    config = load_config(cfg_path)
    assert config.server.host == "0.0.0.0"
    assert config.server.port == 11434


def test_server_custom(tmp_path):
    cfg_path = _write_config(tmp_path, {
        "server": {"host": "127.0.0.1", "port": 8080},
        "routes": {},
    })
    config = load_config(cfg_path)
    assert config.server.host == "127.0.0.1"
    assert config.server.port == 8080


def test_route_for_exact_match(tmp_path):
    cfg_path = _write_config(tmp_path, {
        "routes": {
            "model-a": {"backend": "openai_compat"},
            "model-b": {"backend": "claude_code"},
        }
    })
    config = load_config(cfg_path)
    assert config.route_for("model-a").backend == "openai_compat"
    assert config.route_for("model-b").backend == "claude_code"


def test_route_for_wildcard(tmp_path):
    cfg_path = _write_config(tmp_path, {
        "routes": {
            "specific": {"backend": "openai_compat"},
            "*": {"backend": "ollama_passthru"},
        }
    })
    config = load_config(cfg_path)
    assert config.route_for("specific").backend == "openai_compat"
    assert config.route_for("unknown-model").backend == "ollama_passthru"


def test_route_for_no_match(tmp_path):
    cfg_path = _write_config(tmp_path, {
        "routes": {"only-this": {"backend": "openai_compat"}}
    })
    config = load_config(cfg_path)
    assert config.route_for("something-else") is None


def test_missing_backend_raises(tmp_path):
    cfg_path = _write_config(tmp_path, {
        "routes": {"bad-route": {"provider_url": "http://example.com"}}
    })
    with pytest.raises(ValueError, match="missing 'backend'"):
        load_config(cfg_path)


def test_env_var_resolution(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret123")
    cfg_path = _write_config(tmp_path, {
        "routes": {
            "test": {"backend": "openai_compat", "api_key_env": "TEST_API_KEY"}
        }
    })
    config = load_config(cfg_path)
    assert config.routes["test"].params["api_key"] == "secret123"


def test_missing_env_var_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("NONEXISTENT_KEY", raising=False)
    cfg_path = _write_config(tmp_path, {
        "routes": {
            "test": {"backend": "openai_compat", "api_key_env": "NONEXISTENT_KEY"}
        }
    })
    with pytest.raises(ValueError, match="NONEXISTENT_KEY"):
        load_config(cfg_path)


def test_params_passed_through(tmp_path):
    cfg_path = _write_config(tmp_path, {
        "routes": {
            "test": {
                "backend": "claude_code",
                "cli_path": "/usr/bin/claude",
                "max_turns": 25,
                "stateless": True,
            }
        }
    })
    config = load_config(cfg_path)
    params = config.routes["test"].params
    assert params["cli_path"] == "/usr/bin/claude"
    assert params["max_turns"] == 25
    assert params["stateless"] is True
