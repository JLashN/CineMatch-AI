"""
CineMatch AI — YouTube Client

Fetches official trailers from YouTube Data API v3.
Free tier: 10,000 units/day (search = 100 units each → ~100 searches/day).

Falls back to a constructed YouTube search URL when no API key is configured.

Design patterns:
  - Repository: abstracts YouTube API behind clean interface
  - Fallback Strategy: API → constructed URL
  - Cache Aside: in-memory TTL cache
"""

from __future__ import annotations

import logging
import time
import urllib.parse
from typing import Any, Dict, Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Cache ─────────────────────────────────────────────────

_cache: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL = 86400 * 7  # 7 days — trailers rarely change


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
            base_url="https://www.googleapis.com/youtube/v3",
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ── Public API ────────────────────────────────────────────


async def get_trailer(title: str, year: int) -> Dict[str, Any]:
    """
    Get a YouTube trailer for a movie.

    Returns dict with:
      - youtube_id: str | None
      - youtube_url: str
      - embed_url: str
      - thumbnail: str
      - source: "api" | "search_url"
    """
    cache_key = f"yt:{title}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    api_key = getattr(settings, "youtube_api_key", "") or ""

    result: Dict[str, Any]

    if api_key:
        result = await _search_via_api(title, year, api_key)
    else:
        result = _build_search_url(title, year)

    _cache[cache_key] = (time.time(), result)
    return result


async def _search_via_api(title: str, year: int, api_key: str) -> Dict[str, Any]:
    """Search YouTube Data API for official trailer."""
    try:
        client = await _get_client()
        params = {
            "part": "snippet",
            "q": f"{title} {year} trailer oficial",
            "type": "video",
            "maxResults": 1,
            "videoCategoryId": "1",  # Film & Animation
            "key": api_key,
        }

        resp = await client.get("/search", params=params)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items", [])
        if items:
            video_id = items[0]["id"]["videoId"]
            return {
                "youtube_id": video_id,
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "source": "api",
            }
    except Exception as exc:
        logger.warning("YouTube API search failed: %s", exc)

    # Fallback
    return _build_search_url(title, year)


def _build_search_url(title: str, year: int) -> Dict[str, Any]:
    """Build a YouTube search URL as a fallback (no API key needed)."""
    query = urllib.parse.quote_plus(f"{title} {year} trailer oficial")
    return {
        "youtube_id": None,
        "youtube_url": f"https://www.youtube.com/results?search_query={query}",
        "embed_url": None,
        "thumbnail": None,
        "source": "search_url",
    }


# ── TMDB Trailer (alternative, free, no API key needed) ──

async def get_trailer_from_tmdb(tmdb_id: int) -> Optional[Dict[str, Any]]:
    """
    Get trailer directly from TMDB videos endpoint (free, no extra API key).
    This is the preferred method as it uses no additional API quota.
    """
    cache_key = f"tmdb_trailer:{tmdb_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        from app.clients.tmdb import _request
        data = await _request("GET", f"/movie/{tmdb_id}/videos", {"language": "es-ES"})
        videos = data.get("results", [])

        # Also check English if no Spanish trailer
        if not any(v.get("type") == "Trailer" for v in videos):
            data_en = await _request("GET", f"/movie/{tmdb_id}/videos", {"language": "en-US"})
            videos.extend(data_en.get("results", []))

        # Prefer: Official Trailer > Trailer > Teaser
        trailers = [v for v in videos if v.get("site") == "YouTube"]
        trailers.sort(key=lambda v: (
            v.get("type") == "Trailer",
            v.get("official", False),
            "oficial" in v.get("name", "").lower() or "official" in v.get("name", "").lower(),
        ), reverse=True)

        if trailers:
            video = trailers[0]
            video_id = video["key"]
            result = {
                "youtube_id": video_id,
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "name": video.get("name", "Trailer"),
                "source": "tmdb",
            }
            _cache[cache_key] = (time.time(), result)
            return result

    except Exception as exc:
        logger.warning("TMDB trailer fetch failed for %d: %s", tmdb_id, exc)

    return None
