"""
CineMatch AI — Pydantic Models

Shared data models used across the entire pipeline.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ── Module 1: NLP Extraction ─────────────────────────────


class ExtractedEntities(BaseModel):
    """Output produced by the NLP intent-extraction agent."""

    genres: List[str] = Field(default_factory=list, description="Genre names in Spanish/English")
    genre_ids: List[int] = Field(default_factory=list, description="Resolved TMDB genre IDs")
    keywords: List[str] = Field(default_factory=list, description="Semantic keyword terms")
    keyword_ids: List[int] = Field(default_factory=list, description="Resolved TMDB keyword IDs")
    region: Optional[str] = Field(default=None, description="ISO 3166-1 region code (ES, FR, …)")
    language: Optional[str] = Field(default=None, description="ISO 639-1 language code (en, es, …)")
    mood: Optional[str] = Field(default=None, description="Emotional tone the user wants")
    era: Optional[str] = Field(default=None, description="Decade or year range (e.g. '80s')")
    exclude: List[str] = Field(default_factory=list, description="Genres/keywords to exclude")


# ── Module 3: Enriched Film ──────────────────────────────


class EnrichedFilm(BaseModel):
    """A fully-enriched movie record ready for re-ranking."""

    tmdb_id: int
    title: str
    original_title: str
    overview: str
    genres: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    release_year: int = 0
    vote_average: float = 0.0
    vote_count: int = 0
    runtime: int = 0
    origin_countries: List[str] = Field(default_factory=list)
    top_review: Optional[str] = None
    poster_url: Optional[str] = None
    relevance_score: float = 0.0


# ── Module 4: Ranked Result ──────────────────────────────


class RankedFilm(BaseModel):
    """A film after the LLM re-ranker has scored it."""

    tmdb_id: int
    score: float
    reason: str


# ── Module 5: API Contract ───────────────────────────────


class RecommendFilters(BaseModel):
    min_year: Optional[int] = None
    min_rating: Optional[float] = None


class RecommendRequest(BaseModel):
    query: str = Field(..., max_length=1000)
    session_id: Optional[str] = None
    max_results: int = Field(default=3, ge=1, le=10)
    language: str = "es"
    filters: RecommendFilters = Field(default_factory=RecommendFilters)


class RecommendationItem(BaseModel):
    tmdb_id: int
    title: str
    year: int
    score: float
    poster_url: Optional[str]
    reason: str
    genres: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class RecommendResponse(BaseModel):
    session_id: str
    narrative: str
    recommendations: List[RecommendationItem]
    processing_time_ms: int


# ── Module 6: Conversation Context ───────────────────────


class ConversationTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class SessionContext(BaseModel):
    session_id: str
    turns: List[ConversationTurn] = Field(default_factory=list)
    last_entities: Optional[ExtractedEntities] = None
    last_recommendations: List[RecommendationItem] = Field(default_factory=list)
