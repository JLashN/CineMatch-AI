"""
CineMatch AI — Wikipedia Client

Fetches trivia, director bios, and fun facts from Wikipedia API.
Completely free, no API key needed, rate limit: ~200 req/s.

Design patterns:
  - Repository: abstracts Wikipedia API
  - Cache Aside: TTL cache for expensive summaries
  - Adapter: normalizes Wikipedia content to our format
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# ── Cache ─────────────────────────────────────────────────

_cache: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL = 86400  # 24h


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
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0),
            headers={"User-Agent": "CineMatchAI/2.0 (movie recommendation bot)"},
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ── Movie summary ─────────────────────────────────────────


async def get_movie_summary(title: str, year: int, language: str = "es") -> Optional[Dict[str, Any]]:
    """
    Fetch a Wikipedia summary for a movie.

    Returns dict with:
      - extract: str  (plain text summary)
      - url: str  (Wikipedia article URL)
      - thumbnail: str | None
    """
    cache_key = f"wiki:movie:{title}:{year}:{language}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # Try movie-specific search queries
    queries = [
        f"{title} (película de {year})",
        f"{title} ({year} film)",
        f"{title} película",
        title,
    ]

    for query in queries:
        result = await _search_and_extract(query, language)
        if result and _is_movie_article(result.get("extract", "")):
            _cache[cache_key] = (time.time(), result)
            return result

    return None


async def get_person_summary(name: str, language: str = "es") -> Optional[Dict[str, Any]]:
    """
    Fetch a Wikipedia summary for a director/actor.
    """
    cache_key = f"wiki:person:{name}:{language}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    result = await _search_and_extract(name, language)
    if result:
        _cache[cache_key] = (time.time(), result)
        return result

    # Fallback to English
    if language != "en":
        result = await _search_and_extract(name, "en")
        if result:
            _cache[cache_key] = (time.time(), result)
            return result

    return None


# ── Fun facts extraction ─────────────────────────────────


async def get_movie_trivia(title: str, year: int) -> List[str]:
    """
    Extract interesting trivia/facts about a movie from Wikipedia.
    Returns a list of short fact strings.
    """
    cache_key = f"wiki:trivia:{title}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    summary = await get_movie_summary(title, year, "es")
    if not summary:
        summary = await get_movie_summary(title, year, "en")

    if not summary or not summary.get("extract"):
        return []

    facts = _extract_facts(summary["extract"])
    _cache[cache_key] = (time.time(), facts)
    return facts


# ── Internal helpers ──────────────────────────────────────


async def _search_and_extract(query: str, language: str = "es") -> Optional[Dict[str, Any]]:
    """Search Wikipedia and get the best matching article summary."""
    client = await _get_client()

    try:
        # Step 1: Search for the article
        search_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
        resp = await client.get(search_url)

        if resp.status_code == 404:
            # Try search API
            search_api = f"https://{language}.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 3,
                "format": "json",
            }
            resp = await client.get(search_api, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("query", {}).get("search", [])

            if not results:
                return None

            # Get summary of best result
            page_title = results[0]["title"].replace(" ", "_")
            summary_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{page_title}"
            resp = await client.get(summary_url)

        if resp.status_code != 200:
            return None

        data = resp.json()
        extract = data.get("extract", "")

        if not extract or len(extract) < 50:
            return None

        return {
            "extract": extract,
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "thumbnail": data.get("thumbnail", {}).get("source"),
            "title": data.get("title", ""),
        }

    except Exception as exc:
        logger.debug("Wikipedia search failed for '%s': %s", query, exc)
        return None


def _is_movie_article(text: str) -> bool:
    """Check if a Wikipedia extract is about a movie."""
    movie_indicators = [
        "película", "film", "dirigida", "directed",
        "estrenó", "released", "taquilla", "box office",
        "reparto", "cast", "guion", "screenplay",
        "protagonizada", "starring",
    ]
    text_lower = text.lower()
    return any(ind in text_lower for ind in movie_indicators)


def _extract_facts(text: str) -> List[str]:
    """Extract interesting facts from a movie summary."""
    facts: List[str] = []
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Look for interesting patterns
    fact_patterns = [
        re.compile(r"(?:recaud|taquilla|box.?office|ganó|won|nominad|nominated|premio|award|oscar|golden|cannes|palma)", re.I),
        re.compile(r"(?:presupuesto|budget|cost|mill[oó]n|billion)", re.I),
        re.compile(r"(?:basada?|adapted|inspir|based.?on|novela|book)", re.I),
        re.compile(r"(?:primer[oa]|first|récord|record|hist[oó]ri|debut)", re.I),
        re.compile(r"(?:rodaje|filmed|filmación|rodó|shot.?in|location)", re.I),
        re.compile(r"(?:secuela|sequel|precuela|prequel|trilogía|trilogy|saga|franchise)", re.I),
    ]

    for sentence in sentences:
        if len(sentence) < 20 or len(sentence) > 300:
            continue
        for pattern in fact_patterns:
            if pattern.search(sentence):
                clean = sentence.strip()
                if clean and clean not in facts:
                    facts.append(clean)
                break

    return facts[:5]  # Max 5 facts
