"""
CineMatch AI — LLM Client (LangChain + vLLM)

Factory + Adapter pattern: wraps LangChain's ChatOpenAI to provide
both non-streaming and real token-streaming from the vLLM server.

Design patterns used:
  - Factory: create_llm() builds configured ChatOpenAI instances
  - Adapter: chat_completion() and stream_chat() adapt LangChain to our API
  - Singleton: shared client instance via module-level variable
"""

from __future__ import annotations

import logging
import re
from typing import Any, AsyncIterator, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.config import settings

logger = logging.getLogger(__name__)

# ── LLM Factory ──────────────────────────────────────────

_default_llm: Optional[ChatOpenAI] = None


def create_llm(
    *,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    streaming: bool = False,
    top_p: float = 0.9,
) -> ChatOpenAI:
    """
    Factory: create a ChatOpenAI instance configured for the vLLM server.
    Supports all OpenAI-compatible vLLM endpoints.
    """
    return ChatOpenAI(
        model=settings.vllm_model,
        openai_api_key="EMPTY",
        openai_api_base=settings.vllm_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
        top_p=top_p,
        extra_body={
            "chat_template_kwargs": {"enable_thinking": False},
        },
        http_client=None,  # Let LangChain manage the httpx client
        timeout=120,
    )


def _get_default_llm() -> ChatOpenAI:
    """Singleton accessor for the default non-streaming LLM."""
    global _default_llm
    if _default_llm is None:
        _default_llm = create_llm(streaming=False)
    return _default_llm


# ── Message conversion helper ─────────────────────────────

def _to_langchain_messages(messages: List[Dict[str, str]]) -> list:
    """Convert our dict-based messages to LangChain message objects."""
    lc_msgs = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            lc_msgs.append(SystemMessage(content=content))
        elif role == "user":
            lc_msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_msgs.append(AIMessage(content=content))
        else:
            lc_msgs.append(HumanMessage(content=content))
    return lc_msgs


# ── Core chat completion (non-streaming) ──────────────────


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
    llm = create_llm(
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=False,
        top_p=top_p,
    )

    if stop:
        llm = llm.bind(stop=stop)
    if presence_penalty:
        llm = llm.bind(presence_penalty=presence_penalty)
    if frequency_penalty:
        llm = llm.bind(frequency_penalty=frequency_penalty)

    lc_messages = _to_langchain_messages(messages)

    logger.debug(
        "LLM request: model=%s tokens=%d temp=%.1f",
        settings.vllm_model, max_tokens, temperature,
    )

    response = await llm.ainvoke(lc_messages)
    content = str(response.content)

    # Strip Qwen3 <think>...</think> blocks if present
    content = _strip_thinking(content)

    logger.info("LLM response: %d chars, first 100: %s", len(content), repr(content[:100]))
    return content


# ── Real streaming chat completion ────────────────────────


async def stream_chat(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    top_p: float = 0.9,
    presence_penalty: float = 0.0,
    frequency_penalty: float = 0.0,
) -> AsyncIterator[str]:
    """
    Stream tokens from the LLM in real-time.
    Yields individual token strings as they arrive from vLLM.
    Automatically strips <think>...</think> blocks.
    """
    llm = create_llm(
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=True,
        top_p=top_p,
    )

    if presence_penalty:
        llm = llm.bind(presence_penalty=presence_penalty)
    if frequency_penalty:
        llm = llm.bind(frequency_penalty=frequency_penalty)

    lc_messages = _to_langchain_messages(messages)

    logger.debug("LLM stream: model=%s tokens=%d temp=%.1f", settings.vllm_model, max_tokens, temperature)

    in_think_block = False
    buffer = ""

    async for chunk in llm.astream(lc_messages):
        token = str(chunk.content)
        if not token:
            continue

        buffer += token

        # Handle <think>...</think> stripping in streaming mode
        if "<think>" in buffer and not in_think_block:
            # Yield everything before <think>
            idx = buffer.index("<think>")
            before = buffer[:idx]
            if before:
                yield before
            buffer = buffer[idx:]
            in_think_block = True

        if in_think_block:
            if "</think>" in buffer:
                idx = buffer.index("</think>") + len("</think>")
                # Skip whitespace after </think>
                rest = buffer[idx:].lstrip()
                buffer = rest
                in_think_block = False
                # Continue processing remaining buffer
                if buffer:
                    yield buffer
                    buffer = ""
            # While inside think block, don't yield anything
            continue

        # Normal token — yield and clear buffer
        if buffer:
            yield buffer
            buffer = ""

    # Flush any remaining buffer
    if buffer and not in_think_block:
        yield buffer


# ── Utility ───────────────────────────────────────────────


def _strip_thinking(text: str) -> str:
    """Remove Qwen3 <think>...</think> blocks from the response."""
    text = re.sub(r'<think>.*?</think>\s*', '', text, flags=re.DOTALL)
    text = re.sub(r'<think>.*', '', text, flags=re.DOTALL)
    return text.strip()


# ── Health check ──────────────────────────────────────────

# Keep httpx for health check since LangChain doesn't expose /models
import httpx

_health_client: Optional[httpx.AsyncClient] = None


async def _get_health_client() -> httpx.AsyncClient:
    global _health_client
    if _health_client is None or _health_client.is_closed:
        _health_client = httpx.AsyncClient(
            base_url=settings.vllm_base_url,
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
            verify=False,
        )
    return _health_client


async def check_vllm_health() -> Dict[str, Any]:
    """Return model info from the vLLM server."""
    client = await _get_health_client()
    resp = await client.get("/models")
    resp.raise_for_status()
    return resp.json()


async def close_client() -> None:
    """Clean up any open HTTP connections."""
    global _health_client, _default_llm
    if _health_client and not _health_client.is_closed:
        await _health_client.aclose()
        _health_client = None
    _default_llm = None
