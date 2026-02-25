"""
CineMatch AI — vLLM Client (Module 1 / T-101)

Async HTTP client that talks to the vLLM OpenAI-compatible server.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Shared httpx client (reuse connections) ───────────────

_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.vllm_base_url,
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
            verify=False,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ── Core chat completion ──────────────────────────────────


async def chat_completion(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    top_p: float = 0.9,
    stop: Optional[List[str]] = None,
    presence_penalty: float = 0.0,
    frequency_penalty: float = 0.0,
) -> str:
    """Send a chat completion request and return the text content."""
    client = await get_client()

    payload: Dict[str, Any] = {
        "model": settings.vllm_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
    }
    if stop:
        payload["stop"] = stop
    if presence_penalty:
        payload["presence_penalty"] = presence_penalty
    if frequency_penalty:
        payload["frequency_penalty"] = frequency_penalty

    logger.debug("vLLM request: model=%s tokens=%d temp=%.1f", settings.vllm_model, max_tokens, temperature)

    resp = await client.post("/chat/completions", json=payload)
    resp.raise_for_status()

    data = resp.json()
    content: str = data["choices"][0]["message"]["content"]
    logger.debug("vLLM response length: %d chars", len(content))
    return content


# ── Streaming chat completion (SSE) ───────────────────────


async def chat_completion_stream(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 1200,
    top_p: float = 0.9,
    presence_penalty: float = 0.0,
    frequency_penalty: float = 0.0,
) -> AsyncIterator[str]:
    """Yield text chunks from a streaming chat completion."""
    client = await get_client()

    payload: Dict[str, Any] = {
        "model": settings.vllm_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "stream": True,
    }
    if presence_penalty:
        payload["presence_penalty"] = presence_penalty
    if frequency_penalty:
        payload["frequency_penalty"] = frequency_penalty

    async with client.stream("POST", "/chat/completions", json=payload) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[len("data: "):]
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk["choices"][0].get("delta", {})
                text = delta.get("content", "")
                if text:
                    yield text
            except (json.JSONDecodeError, KeyError, IndexError):
                continue


# ── Health check ──────────────────────────────────────────


async def check_vllm_health() -> Dict[str, Any]:
    """Return model info from the vLLM server."""
    client = await get_client()
    resp = await client.get("/models")
    resp.raise_for_status()
    return resp.json()
