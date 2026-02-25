"""
CineMatch AI — TMDB Query Builder (Module 2 / T-200 – T-203)

Takes ExtractedEntities and builds the optimal TMDB API query.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.clients.tmdb import discover_movies, search_movies
from app.models import ExtractedEntities

logger = logging.getLogger(__name__)

# ── Era → date range mapping ─────────────────────────────

_ERA_MAP: Dict[str, Tuple[str, str]] = {
    "20s": ("1920-01-01", "1929-12-31"),
    "30s": ("1930-01-01", "1939-12-31"),
    "40s": ("1940-01-01", "1949-12-31"),
    "50s": ("1950-01-01", "1959-12-31"),
    "60s": ("1960-01-01", "1969-12-31"),
    "70s": ("1970-01-01", "1979-12-31"),
    "80s": ("1980-01-01", "1989-12-31"),
    "90s": ("1990-01-01", "1999-12-31"),
    "2000s": ("2000-01-01", "2009-12-31"),
    "2010s": ("2010-01-01", "2019-12-31"),
    "2020s": ("2020-01-01", "2029-12-31"),
    "clásico": ("1920-01-01", "1979-12-31"),
    "clasico": ("1920-01-01", "1979-12-31"),
    "moderno": ("2000-01-01", "2029-12-31"),
    "reciente": ("2018-01-01", "2029-12-31"),
}

# ── Region keyword → ISO code ─────────────────────────────

_REGION_MAP: Dict[str, str] = {
    "españa": "ES",
    "spain": "ES",
    "francia": "FR",
    "france": "FR",
    "italia": "IT",
    "italy": "IT",
    "alemania": "DE",
    "germany": "DE",
    "uk": "GB",
    "reino unido": "GB",
    "estados unidos": "US",
    "usa": "US",
    "japón": "JP",
    "japan": "JP",
    "corea": "KR",
    "korea": "KR",
}


def _resolve_region(region: Optional[str]) -> Optional[str]:
    """Normalise a region string to ISO 3166-1 alpha-2."""
    if not region:
        return None
    low = region.strip().lower()
    # Already a 2-letter code?
    if len(low) == 2 and low.isalpha():
        return low.upper()
    return _REGION_MAP.get(low)


# ── Build params dict (T-201) ─────────────────────────────


def build_discover_params(
    entities: ExtractedEntities,
    *,
    language: str = "es-ES",
    min_year: Optional[int] = None,
    min_rating: Optional[float] = None,
    page: int = 1,
) -> Dict[str, Any]:
    """Convert ExtractedEntities into TMDB /discover/movie parameters."""

    params: Dict[str, Any] = {
        "language": language,
        "sort_by": "popularity.desc",
        "include_adult": False,
        "page": page,
    }

    # Genres
    if entities.genre_ids:
        params["with_genres"] = ",".join(str(g) for g in entities.genre_ids)

    # Keywords
    if entities.keyword_ids:
        params["with_keywords"] = ",".join(str(k) for k in entities.keyword_ids)

    # Region
    region = _resolve_region(entities.region)
    if region:
        params["region"] = region
        params["watch_region"] = region

    # Language filter
    if entities.language:
        params["with_original_language"] = entities.language

    # Era → date range
    if entities.era:
        era_low = entities.era.strip().lower()
        if era_low in _ERA_MAP:
            gte, lte = _ERA_MAP[era_low]
            params["primary_release_date.gte"] = gte
            params["primary_release_date.lte"] = lte

    # Mood-based quality adjustment
    if entities.mood and any(w in entities.mood.lower() for w in ("oscuro", "autor", "independiente", "indie", "dark")):
        params["vote_average.gte"] = 5.0
    else:
        params["vote_average.gte"] = min_rating or 6.0

    # External filters
    if min_year:
        params.setdefault("primary_release_date.gte", f"{min_year}-01-01")
    if min_rating:
        params["vote_average.gte"] = min_rating

    # Exclude
    # (would need keyword/genre ID resolution for excludes — skipped for MVP)

    return params


# ── Public interface (T-200) ──────────────────────────────


async def query_tmdb(
    entities: ExtractedEntities,
    *,
    language: str = "es-ES",
    min_year: Optional[int] = None,
    min_rating: Optional[float] = None,
    max_pages: int = 2,
) -> List[Dict[str, Any]]:
    """
    Decide which TMDB endpoint to use and fetch results.

    Strategy:
    - If we have genre_ids or keyword_ids → use /discover/movie
    - Otherwise fall back to /search/movie with first keyword
    - If discover returns 0 results → relax filters and retry
    """

    # Route A: discover (preferred)
    if entities.genre_ids or entities.keyword_ids:
        all_results: List[Dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            params = build_discover_params(
                entities,
                language=language,
                min_year=min_year,
                min_rating=min_rating,
                page=page,
            )
            results = await discover_movies(params)
            all_results.extend(results)
            if len(results) < 20:
                break  # no more pages

        # Fallback: relax filters if 0 results
        if not all_results:
            logger.warning("Discover returned 0 results — relaxing filters")
            relaxed = build_discover_params(entities, language=language, page=1)
            relaxed.pop("with_keywords", None)
            relaxed["vote_average.gte"] = 5.0
            all_results = await discover_movies(relaxed)

        if all_results:
            return all_results

    # Route B: keyword search fallback
    search_term = " ".join(entities.keywords[:3]) if entities.keywords else " ".join(entities.genres[:2])
    if search_term.strip():
        logger.info("Falling back to /search/movie with query=%r", search_term)
        return await search_movies(search_term, language=language)

    # Route C: genre-based popularity
    logger.warning("No search criteria — returning popular movies")
    return await discover_movies({"language": language, "sort_by": "popularity.desc", "page": 1})
