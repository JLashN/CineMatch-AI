"""
CineMatch AI — TMDB Client (Module 3)

Design patterns:
  - Repository: abstracts TMDB API behind a clean interface
  - Singleton: shared httpx client with connection pooling
  - Cache Aside: in-memory TTL cache to avoid redundant API calls
  - Retry with Backoff: exponential backoff on rate limits / failures
  - Semaphore: rate-limited concurrent requests (max 8)

Async HTTP client with retry, rate-limiting and backoff for TMDB API v3.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Simple in-memory cache ────────────────────────────────

_cache: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour for discover results
_GENRE_CACHE_TTL = 86400  # 24 h for genre list


def _cache_key(path: str, params: dict) -> str:
    raw = f"{path}:{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(raw.encode()).hexdigest()


def _get_cached(key: str, ttl: float) -> Optional[Any]:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < ttl:
            return val
        del _cache[key]
    return None


def _set_cached(key: str, val: Any) -> None:
    _cache[key] = (time.time(), val)


# ── Shared client ─────────────────────────────────────────

_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.tmdb_base_url,
            headers=settings.tmdb_headers,
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
            verify=False,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ── Rate-limited request with exponential backoff (T-305) ─


_RATE_SEMAPHORE = asyncio.Semaphore(8)  # max concurrent requests
_MAX_RETRIES = 3


async def _request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    cache_ttl: Optional[float] = _CACHE_TTL_SECONDS,
) -> Dict[str, Any]:
    """Execute an HTTP request against TMDB with retry + cache."""
    params = params or {}
    ckey = _cache_key(path, params)

    if cache_ttl:
        cached = _get_cached(ckey, cache_ttl)
        if cached is not None:
            logger.debug("TMDB cache HIT: %s", path)
            return cached

    client = await get_client()

    for attempt in range(1, _MAX_RETRIES + 1):
        async with _RATE_SEMAPHORE:
            try:
                resp = await client.request(method, path, params=params)
                if resp.status_code == 429:
                    wait = float(resp.headers.get("Retry-After", 2 ** attempt))
                    logger.warning("TMDB rate-limited, waiting %.1fs", wait)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if cache_ttl:
                    _set_cached(ckey, data)
                return data
            except httpx.HTTPStatusError:
                raise
            except httpx.HTTPError as exc:
                if attempt == _MAX_RETRIES:
                    raise
                wait = 2 ** attempt
                logger.warning("TMDB request error (attempt %d/%d): %s – retrying in %ds", attempt, _MAX_RETRIES, exc, wait)
                await asyncio.sleep(wait)

    raise RuntimeError("TMDB request failed after retries")  # unreachable


# ── Public helpers ────────────────────────────────────────


async def get_genre_list(language: str = "es-ES") -> Dict[int, str]:
    """Return {genre_id: genre_name} map. Cached for 24 h."""
    ckey = f"genres:{language}"
    cached = _get_cached(ckey, _GENRE_CACHE_TTL)
    if cached:
        return cached

    data = await _request("GET", "/genre/movie/list", {"language": language}, cache_ttl=None)
    mapping = {g["id"]: g["name"] for g in data.get("genres", [])}
    _set_cached(ckey, mapping)
    return mapping


async def search_keyword(text: str) -> List[Dict[str, Any]]:
    """Search TMDB keyword IDs by text. Returns list of {id, name}."""
    data = await _request("GET", "/search/keyword", {"query": text}, cache_ttl=_CACHE_TTL_SECONDS)
    return data.get("results", [])


async def discover_movies(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute /discover/movie with given params."""
    data = await _request("GET", "/discover/movie", params)
    return data.get("results", [])


async def search_movies(query: str, language: str = "es-ES", page: int = 1) -> List[Dict[str, Any]]:
    """Execute /search/movie."""
    data = await _request("GET", "/search/movie", {"query": query, "language": language, "page": page})
    return data.get("results", [])


async def get_movie_details(movie_id: int, language: str = "es-ES") -> Dict[str, Any]:
    """Fetch full details for a single movie."""
    return await _request("GET", f"/movie/{movie_id}", {"language": language})


async def get_movie_keywords(movie_id: int) -> List[Dict[str, Any]]:
    """Fetch official TMDB keywords for a movie."""
    data = await _request("GET", f"/movie/{movie_id}/keywords")
    return data.get("keywords", [])


async def get_movie_reviews(movie_id: int, language: str = "en-US") -> List[Dict[str, Any]]:
    """Fetch reviews for a movie. Default to English for wider coverage."""
    data = await _request("GET", f"/movie/{movie_id}/reviews", {"language": language})
    return data.get("results", [])
