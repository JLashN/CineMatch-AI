"""
Tests for the FastAPI endpoints (Module 5).
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """Create a test client with mocked pipeline."""

    async def _mock_pipeline(
        user_query, *, session_id, max_results=3, language="es", filters=None, previous_entities=None
    ):
        from app.models import (
            ExtractedEntities,
            RecommendationItem,
            RecommendResponse,
        )

        recs = [
            RecommendationItem(
                tmdb_id=807,
                title="Heat",
                year=1995,
                score=9.1,
                poster_url="https://image.tmdb.org/t/p/w500/test.jpg",
                reason="Great heist film",
            )
        ]
        response = RecommendResponse(
            session_id=session_id,
            narrative="Here is a great movie for you!",
            recommendations=recs,
            processing_time_ms=500,
        )
        return response, ExtractedEntities(genres=["thriller"]), []

    monkeypatch.setattr("app.main.run_pipeline", _mock_pipeline)

    from app.main import app
    return TestClient(app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


def test_recommend_success(client):
    resp = client.post("/api/recommend", json={
        "query": "Quiero una película de atracos con humor",
        "max_results": 3,
        "language": "es",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "narrative" in data
    assert "recommendations" in data
    assert len(data["recommendations"]) >= 1
    assert data["recommendations"][0]["title"] == "Heat"
    assert "session_id" in data


def test_recommend_empty_query(client):
    resp = client.post("/api/recommend", json={
        "query": "   ",
        "max_results": 3,
    })
    assert resp.status_code == 422


def test_recommend_too_long_query(client):
    resp = client.post("/api/recommend", json={
        "query": "x" * 1001,
        "max_results": 3,
    })
    assert resp.status_code == 422


def test_session_not_found(client):
    resp = client.get("/api/session/nonexistent-id")
    assert resp.status_code == 404


def test_root_serves_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "CineMatch" in resp.text
