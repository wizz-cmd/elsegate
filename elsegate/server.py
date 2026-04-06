"""Elsegate FastAPI server -- Ollama-compatible endpoints.

Exposes ``/api/embed``, ``/api/embeddings``, ``/api/generate``,
``/api/chat``, ``/api/tags``, and ``/health``. Routes requests to
backends based on the model field in each request.

Usage::

    uvicorn elsegate.server:app --host 0.0.0.0 --port 11434

Or set ``ELSEGATE_CONFIG`` to point to your config file.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from elsegate.config import load_config
from elsegate.router import Router

log = logging.getLogger("elsegate")

_router: Router | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize router and backends on startup."""
    global _router
    config_path = os.environ.get("ELSEGATE_CONFIG", "elsegate.yaml")
    log.info("Loading config from %s", config_path)
    config = load_config(config_path)
    _router = Router(config)
    await _router.initialize()
    log.info(
        "Elsegate ready: %d routes (%s)",
        len(config.routes),
        ", ".join(config.routes.keys()),
    )
    yield
    await _router.shutdown()


app = FastAPI(title="Elsegate", version="0.1.0", lifespan=lifespan)


def _get_router() -> Router:
    if _router is None:
        raise HTTPException(503, "Elsegate not initialized")
    return _router


@app.post("/api/embed")
async def api_embed(request: Request) -> JSONResponse:
    """Ollama ``/api/embed`` endpoint (newer format).

    Request: ``{"model": "...", "input": "text" | ["text1", "text2"]}``
    Response: ``{"model": "...", "embeddings": [[...], [...]]}``
    """
    body = await request.json()
    model = body.get("model", "")
    text_input = body.get("input", "")

    router = _get_router()
    backend, route = router.resolve(model)
    provider_model = route.params.get("provider_model", model)

    if isinstance(text_input, str):
        text_input = [text_input]

    embeddings = await backend.embed(provider_model, text_input)
    return JSONResponse({"model": model, "embeddings": embeddings})


@app.post("/api/embeddings")
async def api_embeddings(request: Request) -> JSONResponse:
    """Ollama ``/api/embeddings`` endpoint (older format).

    Request: ``{"model": "...", "prompt": "text"}``
    Response: ``{"model": "...", "embedding": [...]}``
    """
    body = await request.json()
    model = body.get("model", "")
    prompt = body.get("prompt", "")

    router = _get_router()
    backend, route = router.resolve(model)
    provider_model = route.params.get("provider_model", model)

    embeddings = await backend.embed(provider_model, [prompt])
    embedding = embeddings[0] if embeddings else []
    return JSONResponse({"model": model, "embedding": embedding})


@app.post("/api/generate")
async def api_generate(request: Request) -> JSONResponse:
    """Ollama ``/api/generate`` endpoint.

    Request: ``{"model": "...", "prompt": "text", "stream": false}``
    Response: ``{"model": "...", "response": "text", "done": true}``
    """
    body = await request.json()
    model = body.get("model", "")
    prompt = body.get("prompt", "")

    router = _get_router()
    backend, route = router.resolve(model)
    provider_model = route.params.get("provider_model", model)

    start = time.monotonic()
    response_text = await backend.generate(provider_model, prompt)
    elapsed = time.monotonic() - start

    log.info("generate [%s->%s] %.1fs", model, route.backend, elapsed)
    return JSONResponse({
        "model": model,
        "response": response_text,
        "done": True,
        "total_duration": int(elapsed * 1e9),
    })


@app.post("/api/chat")
async def api_chat(request: Request) -> JSONResponse:
    """Ollama ``/api/chat`` endpoint.

    Request: ``{"model": "...", "messages": [...], "tools": [...]}``
    Response: ``{"model": "...", "message": {...}, "done": true}``

    If ``tools`` is present, it is forwarded to the backend. The
    ``claude_code`` backend converts tool definitions into prompt context
    and executes actions via Claude Code's native tools.
    """
    body = await request.json()
    model = body.get("model", "")
    messages = body.get("messages", [])
    tools = body.get("tools")

    router = _get_router()
    backend, route = router.resolve(model)
    provider_model = route.params.get("provider_model", model)

    start = time.monotonic()
    result = await backend.chat(provider_model, messages, tools=tools)
    elapsed = time.monotonic() - start

    log.info("chat [%s->%s] %.1fs", model, route.backend, elapsed)
    return JSONResponse({
        "model": model,
        "message": result,
        "done": True,
        "total_duration": int(elapsed * 1e9),
    })


@app.get("/api/tags")
async def api_tags() -> JSONResponse:
    """Ollama ``/api/tags`` endpoint -- list available models."""
    router = _get_router()
    all_models = await router.list_models()
    return JSONResponse({
        "models": [
            {"name": m, "model": m, "modified_at": "", "size": 0}
            for m in all_models
        ],
    })


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    router = _get_router()
    return JSONResponse({
        "status": "ok",
        "routes": len(router.config.routes),
        "models": list(router.config.routes.keys()),
    })
