"""
Tests for the TMDB query builder (Module 2 / T-205).
"""

from __future__ import annotations

import pytest

from app.agents.query_builder import (
    _ERA_MAP,
    _resolve_region,
    build_discover_params,
)
from app.models import ExtractedEntities


class TestResolveRegion:

    def test_iso_code(self):
        assert _resolve_region("ES") == "ES"
        assert _resolve_region("fr") == "FR"

    def test_name_spanish(self):
        assert _resolve_region("España") == "ES"
        assert _resolve_region("Francia") == "FR"

    def test_name_english(self):
        assert _resolve_region("Germany") == "DE"

    def test_none(self):
        assert _resolve_region(None) is None

    def test_unknown(self):
        assert _resolve_region("Atlantis") is None


class TestEraMap:

    def test_80s(self):
        assert _ERA_MAP["80s"] == ("1980-01-01", "1989-12-31")

    def test_clasico(self):
        assert "clásico" in _ERA_MAP


class TestBuildDiscoverParams:

    def test_basic_genres(self):
        entities = ExtractedEntities(genre_ids=[35, 53])
        params = build_discover_params(entities)
        assert params["with_genres"] == "35,53"
        assert "vote_average.gte" in params

    def test_keywords(self):
        entities = ExtractedEntities(keyword_ids=[9951, 1234])
        params = build_discover_params(entities)
        assert params["with_keywords"] == "9951,1234"

    def test_region(self):
        entities = ExtractedEntities(region="ES")
        params = build_discover_params(entities)
        assert params["region"] == "ES"
        assert params["watch_region"] == "ES"

    def test_era_80s(self):
        entities = ExtractedEntities(era="80s")
        params = build_discover_params(entities)
        assert params["primary_release_date.gte"] == "1980-01-01"
        assert params["primary_release_date.lte"] == "1989-12-31"

    def test_dark_mood_relaxes_rating(self):
        entities = ExtractedEntities(mood="oscuro, denso")
        params = build_discover_params(entities)
        assert params["vote_average.gte"] == 5.0

    def test_min_year_filter(self):
        entities = ExtractedEntities(genre_ids=[28])
        params = build_discover_params(entities, min_year=1990)
        assert params["primary_release_date.gte"] == "1990-01-01"

    def test_min_rating_filter(self):
        entities = ExtractedEntities(genre_ids=[28])
        params = build_discover_params(entities, min_rating=7.5)
        assert params["vote_average.gte"] == 7.5

    def test_language_filter(self):
        entities = ExtractedEntities(language="fr")
        params = build_discover_params(entities)
        assert params["with_original_language"] == "fr"
