"""
CineMatch AI — Pipeline Orchestrator

Design patterns:
  - Chain of Responsibility: phases execute sequentially, each passing
    results to the next
  - Strategy: fallback strategies when phases return empty results
  - Facade: run_pipeline() is the single entry point

Pipeline flow:
  Sentiment → NLP Extract → Profile Enrich → Query TMDB → Enrich → Re-rank → Narrative
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional, Tuple

from app.agents.enrichment import enrich_movies
from app.agents.nlp_extractor import extract_entities
from app.agents.profile_recommender import (
    build_narrative_context,
    enrich_query_with_profile,
    personalize_ranking,
)
from app.agents.query_builder import query_tmdb
from app.agents.reranker import (
    generate_narrative,
    rerank_films,
    select_top_n,
)
from app.agents.sentiment import analyze_sentiment
from app.models import (
    EnrichedFilm,
    ExtractedEntities,
    RecommendationItem,
    RecommendFilters,
    RecommendResponse,
)

logger = logging.getLogger(__name__)


# ── Pipeline Orchestrator (Facade) ────────────────────────


async def run_pipeline(
    user_query: str,
    *,
    session_id: str,
    max_results: int = 3,
    language: str = "es",
    filters: Optional[RecommendFilters] = None,
    previous_entities: Optional[ExtractedEntities] = None,
) -> Tuple[RecommendResponse, ExtractedEntities, List[EnrichedFilm]]:
    """
    Execute the full CineMatch recommendation pipeline.

    Returns (response, entities, selected_films) so callers can
    persist state for multi-turn conversation.
    """
    t0 = time.perf_counter()
    filters = filters or RecommendFilters()
    tmdb_lang = f"{language}-{language.upper()}" if len(language) == 2 else language

    # ── Phase 0: Sentiment analysis ───────────────────────
    sentiment = analyze_sentiment(user_query)
    logger.info(
        "Phase 0 — Sentiment: %s intents=%s",
        sentiment["sentiment_label"],
        sentiment["intents"],
    )

    # ── Phase 1: NLP extraction ───────────────────────────
    logger.info("Phase 1 — NLP extraction: query=%r", user_query[:80])
    entities = await extract_entities(user_query)

    # Merge with previous context (Chain of Responsibility)
    if previous_entities:
        entities = _merge_entities(previous_entities, entities)

    # ── Phase 1.5: Profile enrichment ─────────────────────
    entities, profile_hints = enrich_query_with_profile(entities, session_id)
    if profile_hints["has_profile"]:
        logger.info(
            "Phase 1.5 — Profile enrichment: tags=%s",
            profile_hints["archetype_tags"],
        )

    # ── Phase 2: Query TMDB ───────────────────────────────
    logger.info(
        "Phase 2 — TMDB query: %d genres, %d keywords",
        len(entities.genre_ids),
        len(entities.keyword_ids),
    )
    raw_movies = await query_tmdb(
        entities,
        language=tmdb_lang,
        min_year=filters.min_year,
        min_rating=filters.min_rating,
    )
    logger.info("Phase 2 complete: %d raw movies", len(raw_movies))

    if not raw_movies:
        elapsed = int((time.perf_counter() - t0) * 1000)
        return (
            RecommendResponse(
                session_id=session_id,
                narrative=(
                    "No he encontrado películas que encajen exactamente con tu descripción. "
                    "¿Podrías darme más detalles o cambiar algún criterio? "
                    "Por ejemplo, prueba a ser más flexible con el género o la época."
                ),
                recommendations=[],
                processing_time_ms=elapsed,
            ),
            entities,
            [],
        )

    # ── Phase 3: Enrichment ───────────────────────────────
    logger.info("Phase 3 — Enriching top %d movies", min(len(raw_movies), 10))
    enriched = await enrich_movies(raw_movies, language=tmdb_lang, max_enrich=10)

    # ── Phase 4: Re-rank ──────────────────────────────────
    logger.info("Phase 4 — Re-ranking %d enriched movies", len(enriched))
    ranked = await rerank_films(user_query, enriched)

    # ── Phase 5: Select top-N ─────────────────────────────
    selected = select_top_n(ranked, enriched, n=max_results)
    logger.info("Phase 5 — Selected %d movies", len(selected))

    # ── Phase 6: Narrative generation ─────────────────────
    logger.info("Phase 6 — Generating narrative (non-streaming)")
    profile_context = build_narrative_context(session_id)
    narrative = await generate_narrative(
        user_query, selected, ranked, profile_context=profile_context,
    )

    # ── Build response ────────────────────────────────────
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    rank_map = {r.tmdb_id: r for r in ranked}

    recommendations = [
        RecommendationItem(
            tmdb_id=f.tmdb_id,
            title=f.title,
            year=f.release_year,
            score=round(f.relevance_score, 1),
            poster_url=f.poster_url,
            reason=rank_map[f.tmdb_id].reason if f.tmdb_id in rank_map else "",
            genres=f.genres,
            keywords=f.keywords[:8],
            trailer_url=f.trailer_url,
            trailer_embed_url=f.trailer_embed_url,
            trailer_thumbnail=f.trailer_thumbnail,
            imdb_rating=f.imdb_rating,
            rotten_tomatoes=f.rotten_tomatoes,
            metacritic=f.metacritic,
            awards=f.awards,
            director=f.director,
            actors=f.actors,
            trivia=f.trivia,
            wikipedia_url=f.wikipedia_url,
        )
        for f in selected
    ]

    response = RecommendResponse(
        session_id=session_id,
        narrative=narrative,
        recommendations=recommendations,
        processing_time_ms=elapsed_ms,
    )

    logger.info("Pipeline complete in %d ms", elapsed_ms)
    return response, entities, selected


# ── Entity Merge Strategy ─────────────────────────────────


def _merge_entities(prev: ExtractedEntities, new: ExtractedEntities) -> ExtractedEntities:
    """
    Merge previous conversation context with newly extracted entities.
    Strategy: new values override, missing fields are filled from previous.
    """
    return ExtractedEntities(
        genres=new.genres or prev.genres,
        genre_ids=new.genre_ids or prev.genre_ids,
        keywords=list(set(prev.keywords + new.keywords)) if new.keywords else prev.keywords,
        keyword_ids=list(set(prev.keyword_ids + new.keyword_ids)) if new.keyword_ids else prev.keyword_ids,
        region=new.region or prev.region,
        language=new.language or prev.language,
        mood=new.mood or prev.mood,
        era=new.era or prev.era,
        exclude=list(set(prev.exclude + new.exclude)),
    )
