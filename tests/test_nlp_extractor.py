"""
Tests for the NLP extraction agent (Module 1 / T-104).
"""

from __future__ import annotations

import json

import pytest

from app.agents.nlp_extractor import (
    _GENRE_NAME_MAP,
    _resolve_genre_ids,
    _resolve_keyword_ids,
    extract_entities,
)
from app.models import ExtractedEntities


# ── Unit tests (no external calls) ───────────────────────


class TestGenreNameMap:
    """Verify the Spanish→English genre mapping is sane."""

    def test_common_genres_present(self):
        assert "comedia" in _GENRE_NAME_MAP
        assert "thriller" in _GENRE_NAME_MAP
        assert "acción" in _GENRE_NAME_MAP
        assert "ciencia ficción" in _GENRE_NAME_MAP

    def test_maps_to_english(self):
        assert _GENRE_NAME_MAP["comedia"] == ["Comedy"]
        assert _GENRE_NAME_MAP["thriller"] == ["Thriller"]


class TestExtractedEntitiesModel:
    """Verify the Pydantic model accepts expected shapes."""

    def test_empty(self):
        e = ExtractedEntities()
        assert e.genres == []
        assert e.region is None

    def test_full(self):
        e = ExtractedEntities(
            genres=["comedia", "thriller"],
            genre_ids=[35, 53],
            keywords=["atraco"],
            keyword_ids=[1234],
            region="ES",
            mood="divertido",
            era="90s",
        )
        assert e.genre_ids == [35, 53]
        assert e.mood == "divertido"

    def test_from_json(self):
        raw = '{"genres": ["drama"], "keywords": ["amor"], "region": null, "mood": "triste"}'
        data = json.loads(raw)
        e = ExtractedEntities(**data)
        assert e.genres == ["drama"]
        assert e.region is None


# ── Integration-like tests (mock LLM / TMDB in fixtures) ─


@pytest.fixture
def mock_genre_list(monkeypatch):
    """Patch TMDB genre list calls to return a fixed map."""

    async def _fake_genre_list(lang="es-ES"):
        return {
            28: "Acción",
            35: "Comedia",
            53: "Thriller",
            18: "Drama",
            878: "Ciencia ficción",
        }

    monkeypatch.setattr("app.agents.nlp_extractor.get_genre_list", _fake_genre_list)


@pytest.fixture
def mock_keyword_search(monkeypatch):
    """Patch TMDB keyword search to return fixed results."""

    async def _fake_search(text: str):
        return [{"id": 9951, "name": text}]

    monkeypatch.setattr("app.agents.nlp_extractor.search_keyword", _fake_search)


@pytest.mark.asyncio
async def test_resolve_genre_ids(mock_genre_list):
    ids = await _resolve_genre_ids(["comedia", "thriller"])
    assert 35 in ids
    assert 53 in ids


@pytest.mark.asyncio
async def test_resolve_genre_ids_case_insensitive(mock_genre_list):
    ids = await _resolve_genre_ids(["COMEDIA", "Thriller"])
    assert 35 in ids


@pytest.mark.asyncio
async def test_resolve_keyword_ids(mock_keyword_search):
    ids = await _resolve_keyword_ids(["atraco", "banco"])
    assert len(ids) == 2
    assert all(kid == 9951 for kid in ids)


@pytest.fixture
def mock_llm_extraction(monkeypatch):
    """Patch the LLM call to return a known JSON response."""

    async def _fake_chat(messages, **kwargs):
        return json.dumps({
            "genres": ["comedia", "thriller"],
            "keywords": ["atraco", "banco"],
            "region": "ES",
            "language": None,
            "mood": "divertido",
            "era": None,
            "exclude": [],
        })

    monkeypatch.setattr("app.agents.nlp_extractor.chat_completion", _fake_chat)


@pytest.mark.asyncio
async def test_extract_entities_full(mock_llm_extraction, mock_genre_list, mock_keyword_search):
    entities = await extract_entities("Quiero una comedia de atracos en España")
    assert "comedia" in entities.genres
    assert 35 in entities.genre_ids
    assert len(entities.keyword_ids) > 0
    assert entities.region == "ES"
    assert entities.mood == "divertido"
