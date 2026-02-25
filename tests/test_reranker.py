"""
Tests for the re-ranker agent (Module 4 / T-406).
"""

from __future__ import annotations

import json

import pytest

from app.agents.reranker import rerank_films, select_top_n
from app.models import EnrichedFilm, RankedFilm


def _make_film(tmdb_id: int, title: str, genres: list[str] | None = None) -> EnrichedFilm:
    return EnrichedFilm(
        tmdb_id=tmdb_id,
        title=title,
        original_title=title,
        overview=f"Overview of {title}",
        genres=genres or ["Drama"],
        release_year=2020,
        vote_average=7.0,
        vote_count=1000,
        runtime=120,
    )


@pytest.fixture
def mock_llm_rerank(monkeypatch):
    """Patch LLM to return a known ranking JSON."""

    async def _fake_chat(messages, **kwargs):
        return json.dumps([
            {"id": 1, "score": 9.5, "reason": "Perfect match"},
            {"id": 2, "score": 7.0, "reason": "Good match"},
            {"id": 3, "score": 4.0, "reason": "Weak match"},
        ])

    monkeypatch.setattr("app.agents.reranker.chat_completion", _fake_chat)


@pytest.mark.asyncio
async def test_rerank_films(mock_llm_rerank):
    films = [_make_film(1, "Film A"), _make_film(2, "Film B"), _make_film(3, "Film C")]
    ranked = await rerank_films("comedia de atracos", films)
    assert len(ranked) == 3
    assert ranked[0].tmdb_id == 1
    assert ranked[0].score == 9.5
    assert ranked[-1].score == 4.0


class TestSelectTopN:

    def test_selects_top_3(self):
        films = [_make_film(i, f"Film {i}") for i in range(1, 6)]
        ranked = [
            RankedFilm(tmdb_id=3, score=9.0, reason="Best"),
            RankedFilm(tmdb_id=1, score=8.0, reason="Good"),
            RankedFilm(tmdb_id=5, score=7.0, reason="OK"),
            RankedFilm(tmdb_id=2, score=5.0, reason="Meh"),
            RankedFilm(tmdb_id=4, score=3.0, reason="Bad"),
        ]
        selected = select_top_n(ranked, films, n=3)
        assert len(selected) == 3
        assert selected[0].tmdb_id == 3
        assert selected[2].tmdb_id == 5

    def test_deduplication(self):
        """Films with the same title root should be deduplicated."""
        films = [
            _make_film(1, "The Matrix"),
            _make_film(2, "The Matrix: Reloaded"),
            _make_film(3, "Inception"),
        ]
        ranked = [
            RankedFilm(tmdb_id=1, score=9.0, reason="Classic"),
            RankedFilm(tmdb_id=2, score=8.5, reason="Sequel"),
            RankedFilm(tmdb_id=3, score=8.0, reason="Great"),
        ]
        selected = select_top_n(ranked, films, n=3)
        titles = [f.title for f in selected]
        # Should pick Matrix and Inception, skipping Matrix: Reloaded
        assert "The Matrix" in titles
        assert "Inception" in titles
        assert len(selected) == 2  # only 2 unique title roots from 3 candidates
