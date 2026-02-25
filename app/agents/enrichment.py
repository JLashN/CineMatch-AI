"""
CineMatch AI — Data Enrichment Agent (Module 3 / T-301 – T-306)

Fetches additional TMDB data for each candidate movie and builds
an EnrichedFilm model.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.clients.tmdb import get_movie_details, get_movie_keywords, get_movie_reviews
from app.config import settings
from app.models import EnrichedFilm

logger = logging.getLogger(__name__)


def _extract_year(date_str: Optional[str]) -> int:
    if date_str and len(date_str) >= 4:
        try:
            return int(date_str[:4])
        except ValueError:
            pass
    return 0


def _best_review(reviews: List[Dict[str, Any]], max_len: int = 400) -> Optional[str]:
    """Pick the most helpful review and truncate."""
    if not reviews:
        return None
    # Sort by rating (if present) or author_details.rating
    rated = [r for r in reviews if r.get("author_details", {}).get("rating")]
    rated.sort(key=lambda r: r["author_details"]["rating"], reverse=True)
    best = rated[0] if rated else reviews[0]
    content = best.get("content", "")
    if len(content) > max_len:
        content = content[:max_len].rsplit(" ", 1)[0] + "…"
    return content or None


# ── Enrich a single movie ────────────────────────────────


async def enrich_movie(
    basic: Dict[str, Any],
    *,
    language: str = "es-ES",
    fetch_reviews: bool = True,
) -> EnrichedFilm:
    """
    Given a basic movie dict from /discover or /search, fetch details,
    keywords and (optionally) reviews, then return an EnrichedFilm.
    """
    movie_id: int = basic["id"]

    # Parallel fetches
    tasks = [
        get_movie_details(movie_id, language=language),
        get_movie_keywords(movie_id),
    ]
    if fetch_reviews:
        tasks.append(get_movie_reviews(movie_id))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    details: Dict[str, Any] = results[0] if not isinstance(results[0], Exception) else {}
    kw_list: List[Dict] = results[1] if not isinstance(results[1], Exception) else []
    reviews_raw: List[Dict] = results[2] if len(results) > 2 and not isinstance(results[2], Exception) else []

    if isinstance(details, Exception):
        logger.warning("Failed to fetch details for movie %d: %s", movie_id, details)
        details = basic  # fallback to basic data

    poster_path = details.get("poster_path") or basic.get("poster_path")

    return EnrichedFilm(
        tmdb_id=movie_id,
        title=details.get("title", basic.get("title", "Unknown")),
        original_title=details.get("original_title", basic.get("original_title", "")),
        overview=details.get("overview", basic.get("overview", "")),
        genres=[g["name"] for g in details.get("genres", [])],
        keywords=[k["name"] for k in kw_list],
        release_year=_extract_year(details.get("release_date") or basic.get("release_date")),
        vote_average=details.get("vote_average", basic.get("vote_average", 0.0)),
        vote_count=details.get("vote_count", basic.get("vote_count", 0)),
        runtime=details.get("runtime") or 0,
        origin_countries=details.get("origin_country", []) or details.get("production_countries", []) and [c.get("iso_3166_1", "") for c in details.get("production_countries", [])],
        top_review=_best_review(reviews_raw),
        poster_url=f"{settings.tmdb_image_base}{poster_path}" if poster_path else None,
        relevance_score=0.0,
    )


# ── Batch enrichment ─────────────────────────────────────


async def enrich_movies(
    movie_list: List[Dict[str, Any]],
    *,
    language: str = "es-ES",
    max_enrich: int = 10,
    fetch_reviews: bool = True,
) -> List[EnrichedFilm]:
    """
    Enrich a batch of movies in parallel.
    Limits to `max_enrich` to avoid excessive TMDB calls.
    """
    to_process = movie_list[:max_enrich]
    enriched = await asyncio.gather(
        *[
            enrich_movie(m, language=language, fetch_reviews=fetch_reviews)
            for m in to_process
        ],
        return_exceptions=True,
    )

    results: List[EnrichedFilm] = []
    for item in enriched:
        if isinstance(item, Exception):
            logger.warning("Enrichment failed for a movie: %s", item)
        else:
            results.append(item)

    logger.info("Enriched %d / %d movies", len(results), len(to_process))
    return results
