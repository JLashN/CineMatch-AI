"""
CineMatch AI — OMDb Client

Fetches multi-platform ratings (IMDb, Rotten Tomatoes, Metacritic)
from the Open Movie Database API.

Free tier: 1,000 requests/day with API key.
Fallback: graceful degradation when no API key configured.

Design patterns:
  - Repository: abstracts OMDb API behind clean interface
  - Adapter: normalizes rating data to our internal format
  - Cache Aside: in-memory TTL cache
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Cache ─────────────────────────────────────────────────

_cache: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL = 86400  # 24h — ratings rarely change


def _get_cached(key: str) -> Optional[Any]:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return val
        del _cache[key]
    return None


# ── Shared client ─────────────────────────────────────────

_client: Optional[httpx.AsyncClient] = None


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url="https://www.omdbapi.com",
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ── Public API ────────────────────────────────────────────


async def get_ratings(imdb_id: Optional[str] = None, title: Optional[str] = None, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetch multi-platform ratings from OMDb.

    Returns dict with:
      - imdb_rating: float | None
      - imdb_votes: str | None
      - rotten_tomatoes: int | None  (percentage)
      - metacritic: int | None
      - awards: str | None
      - box_office: str | None
      - rated: str | None  (PG, R, etc.)
    """
    api_key = getattr(settings, "omdb_api_key", "") or ""
    if not api_key:
        return {}

    # Build params
    params: Dict[str, Any] = {"apikey": api_key}
    if imdb_id:
        params["i"] = imdb_id
    elif title:
        params["t"] = title
        if year:
            params["y"] = str(year)
    else:
        return {}

    # Check cache
    cache_key = f"omdb:{imdb_id or title}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        client = await _get_client()
        resp = await client.get("/", params=params)
        resp.raise_for_status()
        data = resp.json()

        if data.get("Response") == "False":
            logger.debug("OMDb: no result for %s", imdb_id or title)
            return {}

        result = _parse_ratings(data)
        _cache[cache_key] = (time.time(), result)
        return result

    except Exception as exc:
        logger.warning("OMDb request failed: %s", exc)
        return {}


def _parse_ratings(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and normalize ratings from OMDb response."""
    result: Dict[str, Any] = {
        "imdb_rating": None,
        "imdb_votes": None,
        "rotten_tomatoes": None,
        "metacritic": None,
        "awards": data.get("Awards"),
        "box_office": data.get("BoxOffice"),
        "rated": data.get("Rated"),
        "director": data.get("Director"),
        "actors": data.get("Actors"),
        "imdb_id": data.get("imdbID"),
    }

    # IMDb rating
    try:
        imdb_r = data.get("imdbRating", "N/A")
        if imdb_r != "N/A":
            result["imdb_rating"] = float(imdb_r)
    except (ValueError, TypeError):
        pass

    result["imdb_votes"] = data.get("imdbVotes")

    # Other sources from Ratings array
    for rating in data.get("Ratings", []):
        source = rating.get("Source", "")
        value = rating.get("Value", "")

        if "Rotten Tomatoes" in source:
            try:
                result["rotten_tomatoes"] = int(value.replace("%", ""))
            except (ValueError, TypeError):
                pass

        if "Metacritic" in source:
            try:
                result["metacritic"] = int(value.split("/")[0])
            except (ValueError, TypeError):
                pass

    return result


async def get_imdb_id_from_tmdb(tmdb_id: int) -> Optional[str]:
    """
    Get IMDb ID for a TMDB movie.
    Uses TMDB external_ids endpoint (already available via our TMDB client).
    """
    try:
        from app.clients.tmdb import _request
        data = await _request("GET", f"/movie/{tmdb_id}/external_ids")
        return data.get("imdb_id")
    except Exception:
        return None
