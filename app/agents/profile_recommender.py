"""
CineMatch AI — Profile-Aware Recommendation Agent

Design patterns:
  - Decorator: enriches entities and rankings with profile data
  - Strategy: profile-based bias vs neutral recommendations
  - Builder: constructs narrative context from profile data

Uses the accumulated user profile to bias and personalize recommendations.
Acts as a pre-filter and post-filter around the main pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.models import ExtractedEntities, RecommendationItem
from app.profiler import UserProfile, get_profile

logger = logging.getLogger(__name__)


def enrich_query_with_profile(
    entities: ExtractedEntities,
    session_id: str,
) -> Tuple[ExtractedEntities, Dict[str, Any]]:
    """
    Enrich extracted entities with profile-derived preferences.
    Returns (modified_entities, profile_hints) where profile_hints
    contains metadata for the narrative generator.
    """
    profile = get_profile(session_id)
    hints: Dict[str, Any] = {
        "has_profile": False,
        "preferred_genres": [],
        "preferred_moods": [],
        "archetype_tags": [],
        "avoid_movies": [],
        "personality_note": "",
    }

    if not profile or profile.interaction_count < 1:
        return entities, hints

    hints["has_profile"] = True
    hints["preferred_genres"] = profile.top_genres(5)
    hints["preferred_moods"] = profile.top_moods(3)
    hints["archetype_tags"] = profile.tags
    hints["avoid_movies"] = profile.liked_movies[-10:]  # avoid re-recommending

    # Build personality note for narrative
    if profile.tags:
        hints["personality_note"] = (
            f"El usuario tiene un perfil de tipo: {', '.join(profile.tags)}. "
            f"Sus géneros favoritos son: {', '.join(profile.top_genres(3))}."
        )

    # If user didn't specify genres but we know their preferences, suggest them
    if not entities.genre_ids and profile.interaction_count >= 2:
        # Don't override, just note it
        hints["suggest_from_profile"] = True

    # If user didn't specify mood, use their top mood
    if not entities.mood and profile.top_moods(1):
        hints["default_mood"] = profile.top_moods(1)[0]

    return entities, hints


def personalize_ranking(
    recommendations: List[RecommendationItem],
    session_id: str,
) -> List[RecommendationItem]:
    """
    Post-process recommendations to factor in user profile.
    Boosts scores for movies matching profile preferences and
    penalizes already-recommended movies.
    """
    profile = get_profile(session_id)
    if not profile or profile.interaction_count < 2:
        return recommendations

    already_seen = set(profile.liked_movies)

    for rec in recommendations:
        # Penalize if already recommended
        if rec.tmdb_id in already_seen:
            rec.score = max(0, rec.score - 2.0)

        # Boost if genres match profile
        matching_genres = set(rec.genres) & set(profile.top_genres(5))
        if matching_genres:
            rec.score = min(10, rec.score + len(matching_genres) * 0.3)

    # Re-sort
    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations


def build_narrative_context(session_id: str) -> str:
    """
    Build additional narrative context from the user profile.
    This is injected into the narrative generation prompt.
    """
    profile = get_profile(session_id)
    if not profile or profile.interaction_count < 2:
        return ""

    parts = []

    if profile.tags:
        parts.append(f"PERFIL DEL USUARIO: {', '.join(profile.tags)}")

    if profile.top_genres(3):
        parts.append(f"Géneros favoritos: {', '.join(profile.top_genres(3))}")

    if profile.top_moods(2):
        parts.append(f"Estados de ánimo preferidos: {', '.join(profile.top_moods(2))}")

    if profile.interaction_count > 3:
        parts.append(f"Este usuario lleva {profile.interaction_count} interacciones, personaliza más la respuesta.")

    return "\n".join(parts)
