"""
Tests for the enrichment agent (Module 3 / T-306).
"""

from __future__ import annotations

import pytest

from app.agents.enrichment import _best_review, _extract_year, enrich_movie


class TestExtractYear:

    def test_normal_date(self):
        assert _extract_year("2023-05-12") == 2023

    def test_partial_date(self):
        assert _extract_year("1999") == 1999

    def test_none(self):
        assert _extract_year(None) == 0

    def test_empty(self):
        assert _extract_year("") == 0


class TestBestReview:

    def test_no_reviews(self):
        assert _best_review([]) is None

    def test_picks_highest_rated(self):
        reviews = [
            {"content": "Meh", "author_details": {"rating": 4.0}},
            {"content": "Amazing film!", "author_details": {"rating": 9.0}},
        ]
        result = _best_review(reviews)
        assert result is not None
        assert "Amazing" in result

    def test_truncates_long_review(self):
        reviews = [
            {"content": "A " * 500, "author_details": {"rating": 8.0}},
        ]
        result = _best_review(reviews, max_len=100)
        assert result is not None
        assert len(result) <= 110  # some slack for word boundary


@pytest.fixture
def mock_tmdb_calls(monkeypatch):
    """Patch all TMDB calls for enrichment."""

    async def _details(movie_id, language="es-ES"):
        return {
            "id": movie_id,
            "title": "Test Movie",
            "original_title": "Test Movie",
            "overview": "A great test movie.",
            "genres": [{"id": 35, "name": "Comedia"}],
            "release_date": "2023-06-15",
            "vote_average": 7.5,
            "vote_count": 1200,
            "runtime": 120,
            "origin_country": ["US"],
            "poster_path": "/abc.jpg",
            "production_countries": [{"iso_3166_1": "US"}],
        }

    async def _keywords(movie_id):
        return [{"id": 1, "name": "heist"}, {"id": 2, "name": "comedy"}]

    async def _reviews(movie_id, language="en-US"):
        return [{"content": "Brilliant!", "author_details": {"rating": 9.0}}]

    monkeypatch.setattr("app.agents.enrichment.get_movie_details", _details)
    monkeypatch.setattr("app.agents.enrichment.get_movie_keywords", _keywords)
    monkeypatch.setattr("app.agents.enrichment.get_movie_reviews", _reviews)


@pytest.mark.asyncio
async def test_enrich_movie(mock_tmdb_calls):
    basic = {"id": 807, "title": "Heat", "original_title": "Heat", "overview": "...", "release_date": "1995-12-15", "poster_path": "/heat.jpg", "vote_average": 8.3, "vote_count": 5000}
    film = await enrich_movie(basic)
    assert film.tmdb_id == 807
    assert film.title == "Test Movie"  # from mocked details
    assert "heist" in film.keywords
    assert film.top_review is not None
    assert film.poster_url is not None
    assert film.release_year == 2023
