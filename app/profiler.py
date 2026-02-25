"""
CineMatch AI — User Profiler (Module 7)

Builds and maintains a dynamic user taste profile based on interactions.
Uses regex patterns + LLM analysis to detect preferences.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional
from collections import Counter

from app.models import (
    ConversationTurn,
    ExtractedEntities,
    RecommendationItem,
)

logger = logging.getLogger(__name__)

# ── Regex-based sentiment / preference detectors ──────────

_POSITIVE_PATTERNS = [
    re.compile(r"\b(me encant[óa]|genial|perfecto|buena|excelente|increíble|gran(?:de)?|fantástic[oa]|me gust[óa])\b", re.IGNORECASE),
    re.compile(r"\b(loved?|great|amazing|awesome|perfect|fantastic|excellent|wonderful)\b", re.IGNORECASE),
    re.compile(r"\b(sí|claro|exacto|vale|por supuesto|definitivamente)\b", re.IGNORECASE),
]

_NEGATIVE_PATTERNS = [
    re.compile(r"\b(no me gust[óa]|abort|horribl[e]|mala|aburrida|no quiero|nada de|ni hablar)\b", re.IGNORECASE),
    re.compile(r"\b(hate[ds]?|boring|terrible|awful|dislike[ds]?|worst|overrated)\b", re.IGNORECASE),
    re.compile(r"\b(no(?:pe)?|never|jamás|nah|para nada)\b", re.IGNORECASE),
]

_MOOD_PATTERNS = {
    "intelectual": re.compile(r"\b(pens(?:ar|ativo)|reflexi[óo]n|filosóf|profund[oa]|cerebral|complej[oa]|think|thought)\b", re.IGNORECASE),
    "emocional": re.compile(r"\b(llor(?:ar|é)|emoci[oó]n|conmov|sentiment|triste|heart|cry|tears|feel)\b", re.IGNORECASE),
    "adrenalina": re.compile(r"\b(acción|adrenalina|explosion|tir[oa]|pelea|fight|action|thrilling|chase)\b", re.IGNORECASE),
    "humor": re.compile(r"\b(risa|gracioso|comedia|humor|funny|laugh|hilarious|comedy)\b", re.IGNORECASE),
    "oscuro": re.compile(r"\b(oscur[oa]|dark|noir|perturbad|inquietante|macabr|creepy|disturbing)\b", re.IGNORECASE),
    "nostálgico": re.compile(r"\b(nostalgi|retro|clásic|vintage|old.?school|classic|remember)\b", re.IGNORECASE),
    "romántico": re.compile(r"\b(rom[aá]ntic|amor|love|pareja|couple|relationship|passion)\b", re.IGNORECASE),
    "familiar": re.compile(r"\b(famili|niños|kids|infantil|child|family|todos|all.?ages)\b", re.IGNORECASE),
}

_ERA_PATTERNS = {
    "clásico": re.compile(r"\b(clásic[oa]s?|classic|antigua|old)\b", re.IGNORECASE),
    "80s": re.compile(r"\b(80s?|ochenta|eighties)\b", re.IGNORECASE),
    "90s": re.compile(r"\b(90s?|noventa|nineties)\b", re.IGNORECASE),
    "2000s": re.compile(r"\b(2000s?|dos.?mil)\b", re.IGNORECASE),
    "reciente": re.compile(r"\b(reciente|nueva|actual|recent|new|latest|2020|2021|2022|2023|2024|2025|2026)\b", re.IGNORECASE),
}


# ── User Profile Model ───────────────────────────────────

class UserProfile:
    """Dynamic user preference profile built from interactions."""

    def __init__(self) -> None:
        self.genre_affinity: Counter = Counter()        # genre → score
        self.keyword_affinity: Counter = Counter()      # keyword → score
        self.mood_affinity: Counter = Counter()          # mood → score
        self.era_preference: Counter = Counter()         # era → score
        self.director_affinity: Counter = Counter()      # director → score
        self.country_preference: Counter = Counter()     # country → score
        self.liked_movies: List[int] = []                # tmdb_ids
        self.disliked_movies: List[int] = []             # tmdb_ids
        self.interaction_count: int = 0
        self.avg_preferred_rating: float = 7.0
        self.tags: List[str] = []                         # computed archetype tags

    def to_dict(self) -> Dict[str, Any]:
        return {
            "genre_affinity": dict(self.genre_affinity.most_common(10)),
            "keyword_affinity": dict(self.keyword_affinity.most_common(15)),
            "mood_affinity": dict(self.mood_affinity.most_common(5)),
            "era_preference": dict(self.era_preference.most_common(3)),
            "director_affinity": dict(self.director_affinity.most_common(5)),
            "country_preference": dict(self.country_preference.most_common(5)),
            "liked_movies": self.liked_movies[-20:],
            "disliked_movies": self.disliked_movies[-10:],
            "interaction_count": self.interaction_count,
            "avg_preferred_rating": round(self.avg_preferred_rating, 1),
            "archetype_tags": self.tags,
        }

    def top_genres(self, n: int = 5) -> List[str]:
        return [g for g, _ in self.genre_affinity.most_common(n)]

    def top_moods(self, n: int = 3) -> List[str]:
        return [m for m, _ in self.mood_affinity.most_common(n)]

    def compute_archetype_tags(self) -> List[str]:
        """Compute user archetype tags based on accumulated profile data."""
        tags: List[str] = []

        top_genres = self.top_genres(3)
        top_moods = self.top_moods(2)

        # Genre-based archetypes
        genre_archetypes = {
            "Ciencia ficción": "Explorador Cósmico",
            "Science Fiction": "Explorador Cósmico",
            "Drama": "Alma Sensible",
            "Thriller": "Buscador de Tensión",
            "Comedia": "Cazador de Risas",
            "Comedy": "Cazador de Risas",
            "Terror": "Amante del Miedo",
            "Horror": "Amante del Miedo",
            "Animación": "Espíritu Creativo",
            "Animation": "Espíritu Creativo",
            "Documental": "Mente Curiosa",
            "Documentary": "Mente Curiosa",
            "Acción": "Adicto a la Adrenalina",
            "Action": "Adicto a la Adrenalina",
            "Romance": "Corazón Romántico",
            "Fantasía": "Soñador Eterno",
            "Fantasy": "Soñador Eterno",
        }

        for g in top_genres:
            if g in genre_archetypes:
                tags.append(genre_archetypes[g])

        # Mood-based archetypes
        mood_archetypes = {
            "intelectual": "Pensador Profundo",
            "emocional": "Empático Natural",
            "adrenalina": "Amante de la Acción",
            "humor": "Espíritu Alegre",
            "oscuro": "Explorador Oscuro",
            "nostálgico": "Viajero del Tiempo",
            "romántico": "Corazón Abierto",
            "familiar": "Alma Familiar",
        }

        for m in top_moods:
            if m in mood_archetypes and mood_archetypes[m] not in tags:
                tags.append(mood_archetypes[m])

        # Special combos
        if self.interaction_count > 5:
            tags.append("Cinéfilo Activo")
        if len(self.liked_movies) > 8:
            tags.append("Coleccionista")

        self.tags = tags[:5]
        return self.tags


# ── Profile Store ─────────────────────────────────────────

_profiles: Dict[str, UserProfile] = {}


def get_or_create_profile(session_id: str) -> UserProfile:
    if session_id not in _profiles:
        _profiles[session_id] = UserProfile()
    return _profiles[session_id]


def get_profile(session_id: str) -> Optional[UserProfile]:
    return _profiles.get(session_id)


def delete_profile(session_id: str) -> None:
    _profiles.pop(session_id, None)


# ── Profile Update Logic ─────────────────────────────────


def analyze_user_message(text: str) -> Dict[str, Any]:
    """
    Analyze a user message using regex patterns to extract
    sentiment signals, mood preferences, and era interests.
    """
    analysis: Dict[str, Any] = {
        "sentiment": "neutral",
        "detected_moods": [],
        "detected_eras": [],
        "positive_score": 0,
        "negative_score": 0,
    }

    # Sentiment
    pos_score = sum(len(p.findall(text)) for p in _POSITIVE_PATTERNS)
    neg_score = sum(len(p.findall(text)) for p in _NEGATIVE_PATTERNS)
    analysis["positive_score"] = pos_score
    analysis["negative_score"] = neg_score

    if pos_score > neg_score:
        analysis["sentiment"] = "positive"
    elif neg_score > pos_score:
        analysis["sentiment"] = "negative"

    # Moods
    for mood, pattern in _MOOD_PATTERNS.items():
        if pattern.search(text):
            analysis["detected_moods"].append(mood)

    # Eras
    for era, pattern in _ERA_PATTERNS.items():
        if pattern.search(text):
            analysis["detected_eras"].append(era)

    return analysis


def update_profile_from_interaction(
    session_id: str,
    user_query: str,
    entities: Optional[ExtractedEntities],
    recommendations: Optional[List[RecommendationItem]],
    enriched_genres: Optional[List[str]] = None,
    enriched_keywords: Optional[List[str]] = None,
) -> UserProfile:
    """
    Update the user profile after each interaction.
    Combines regex analysis of the user's message with
    entity data and recommendation feedback.
    """
    profile = get_or_create_profile(session_id)
    profile.interaction_count += 1

    # Analyze user message
    analysis = analyze_user_message(user_query)

    # Update mood affinity from regex detection
    for mood in analysis["detected_moods"]:
        profile.mood_affinity[mood] += 2

    # Update era preferences
    for era in analysis["detected_eras"]:
        profile.era_preference[era] += 2

    # Update from extracted entities
    if entities:
        for g in entities.genres:
            profile.genre_affinity[g] += 3  # explicit mention = strong signal
        for kw in entities.keywords:
            profile.keyword_affinity[kw] += 2
        if entities.mood:
            # Match mood to our categories
            mood_low = entities.mood.lower()
            for mood_cat, pattern in _MOOD_PATTERNS.items():
                if pattern.search(mood_low):
                    profile.mood_affinity[mood_cat] += 1
        if entities.era:
            profile.era_preference[entities.era] += 1

    # Update from enriched movie data (implicit feedback - user saw these)
    if enriched_genres:
        for g in enriched_genres:
            profile.genre_affinity[g] += 1
    if enriched_keywords:
        for kw in enriched_keywords:
            profile.keyword_affinity[kw] += 1

    # Track recommended movies
    if recommendations:
        for rec in recommendations:
            profile.liked_movies.append(rec.tmdb_id)
            if rec.score >= 8:
                profile.avg_preferred_rating = (
                    profile.avg_preferred_rating * 0.7 + rec.score * 0.3
                )

    # Recompute archetype tags
    profile.compute_archetype_tags()

    logger.info(
        "Profile updated for session %s: %d interactions, top_genres=%s, tags=%s",
        session_id,
        profile.interaction_count,
        profile.top_genres(3),
        profile.tags,
    )

    return profile


# ── Graph Data Builder ────────────────────────────────────


def build_movie_graph(
    session_id: str,
    all_recommendations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a graph structure for D3.js visualization.

    Nodes: movies, genres, keywords, moods, user profile archetypes
    Edges: relationships between them (weighted by affinity)

    Uses a simple adjacency representation compatible with D3 force layout.
    """
    profile = get_or_create_profile(session_id)

    nodes: List[Dict[str, Any]] = []
    links: List[Dict[str, Any]] = []
    node_ids: Dict[str, int] = {}
    idx = 0

    def add_node(nid: str, label: str, ntype: str, **extra: Any) -> int:
        nonlocal idx
        if nid in node_ids:
            return node_ids[nid]
        node: Dict[str, Any] = {
            "id": nid,
            "label": label,
            "type": ntype,
            "index": idx,
            **extra,
        }
        nodes.append(node)
        node_ids[nid] = idx
        idx += 1
        return node_ids[nid]

    def add_link(source: str, target: str, rel: str, weight: float = 1.0) -> None:
        links.append({
            "source": source,
            "target": target,
            "relation": rel,
            "weight": weight,
        })

    # ── User node (center of the graph) ───────────────────
    add_node("user", "Tú", "user", tags=profile.tags)

    # ── Archetype tag nodes ───────────────────────────────
    for tag in profile.tags:
        tag_id = f"tag:{tag}"
        add_node(tag_id, tag, "archetype")
        add_link("user", tag_id, "es", weight=2.0)

    # ── Genre nodes (from profile) ────────────────────────
    for genre, score in profile.genre_affinity.most_common(8):
        genre_id = f"genre:{genre}"
        add_node(genre_id, genre, "genre", score=score)
        add_link("user", genre_id, "prefiere", weight=min(score / 3.0, 3.0))

    # ── Mood nodes ────────────────────────────────────────
    for mood, score in profile.mood_affinity.most_common(5):
        mood_id = f"mood:{mood}"
        add_node(mood_id, mood, "mood", score=score)
        add_link("user", mood_id, "busca", weight=min(score / 2.0, 3.0))

    # ── Movie nodes ───────────────────────────────────────
    for rec in all_recommendations:
        movie_id = f"movie:{rec['tmdb_id']}"
        add_node(
            movie_id,
            rec.get("title", "?"),
            "movie",
            year=rec.get("year", 0),
            score=rec.get("score", 0),
            poster_url=rec.get("poster_url"),
            reason=rec.get("reason", ""),
        )

        # Link movie to its genres
        for genre in rec.get("genres", []):
            genre_id = f"genre:{genre}"
            add_node(genre_id, genre, "genre")
            add_link(movie_id, genre_id, "pertenece_a", weight=1.5)

        # Link movie to keywords
        for kw in rec.get("keywords", [])[:5]:
            kw_id = f"keyword:{kw}"
            add_node(kw_id, kw, "keyword")
            add_link(movie_id, kw_id, "trata_de", weight=1.0)

    # ── Cross-movie links (shared genres/keywords = edges) ─
    # Dijkstra-friendly: movies sharing genres/keywords get linked
    movie_nodes = [n for n in nodes if n["type"] == "movie"]
    for i, m1 in enumerate(movie_nodes):
        for m2 in movie_nodes[i + 1:]:
            # Find shared neighbors (genres, keywords)
            m1_neighbors = {
                l["target"] for l in links
                if l["source"] == m1["id"] and l["relation"] in ("pertenece_a", "trata_de")
            }
            m2_neighbors = {
                l["target"] for l in links
                if l["source"] == m2["id"] and l["relation"] in ("pertenece_a", "trata_de")
            }
            shared = m1_neighbors & m2_neighbors
            if shared:
                add_link(
                    m1["id"], m2["id"],
                    "relacionada",
                    weight=len(shared) * 0.8,
                )

    # ── Keyword cluster nodes ─────────────────────────────
    for kw, score in profile.keyword_affinity.most_common(10):
        kw_id = f"keyword:{kw}"
        if kw_id not in node_ids:
            add_node(kw_id, kw, "keyword", score=score)
        add_link("user", kw_id, "interés", weight=min(score / 2.0, 2.5))

    return {
        "nodes": nodes,
        "links": links,
        "profile": profile.to_dict(),
        "stats": {
            "total_nodes": len(nodes),
            "total_links": len(links),
            "movie_count": len(movie_nodes),
            "genre_count": len([n for n in nodes if n["type"] == "genre"]),
            "keyword_count": len([n for n in nodes if n["type"] == "keyword"]),
        },
    }
