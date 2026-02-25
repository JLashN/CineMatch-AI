"""
CineMatch AI — FastAPI Application (Module 5)

Main API server with REST endpoints and SSE streaming.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

from app import clients
from app.clients import tmdb
from app.config import settings
from app.models import RecommendationItem, RecommendRequest, RecommendResponse
from app.pipeline import run_pipeline
from app.profiler import (
    build_movie_graph,
    get_or_create_profile,
    get_profile,
    update_profile_from_interaction,
)
from app.sessions import (
    cleanup_expired,
    delete_session,
    get_or_create_session,
    get_session,
    save_turn,
)
from app.text_processor import clean_narrative, clean_stream_chunk
from app.agents.text_quality import fix_text_quality
from app.agents.profile_recommender import build_narrative_context
from app.agents.sentiment import analyze_sentiment

logger = logging.getLogger(__name__)


# ── Lifespan: startup/shutdown ────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down shared resources."""
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    logger.info("🎬 CineMatch AI starting up…")
    logger.info("   vLLM: %s  model: %s", settings.vllm_base_url, settings.vllm_model)
    logger.info("   TMDB: %s", settings.tmdb_base_url)

    # Pre-cache genre list
    try:
        genres = await tmdb.get_genre_list("es-ES")
        logger.info("   Cached %d TMDB genres", len(genres))
    except Exception as exc:
        logger.warning("   Could not pre-cache genres: %s", exc)

    yield  # app runs here

    logger.info("🎬 CineMatch AI shutting down…")
    await clients.close_client()
    await tmdb.close_client()


# ── App instance ──────────────────────────────────────────

app = FastAPI(
    title="CineMatch AI",
    version="1.0.0",
    description="Motor de Recomendación Cinematográfica Conversacional",
    lifespan=lifespan,
)

# CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Logging middleware (T-504) ────────────────────────────


@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(
        "%s %s → %d (%.0f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


# ── Health endpoint ───────────────────────────────────────


@app.get("/api/health")
async def health():
    """Health check — verifies vLLM and TMDB connectivity."""
    status = {"status": "ok", "vllm": "unknown", "tmdb": "unknown"}
    try:
        vllm_info = await clients.check_vllm_health()
        status["vllm"] = "ok"
        status["vllm_models"] = [m["id"] for m in vllm_info.get("data", [])]
    except Exception as exc:
        status["vllm"] = f"error: {exc}"

    try:
        genres = await tmdb.get_genre_list()
        status["tmdb"] = "ok"
        status["tmdb_genres"] = len(genres)
    except Exception as exc:
        status["tmdb"] = f"error: {exc}"

    ok = status["vllm"] == "ok" and status["tmdb"] == "ok"
    status["status"] = "ok" if ok else "degraded"
    return status


# ── Main recommendation endpoint (T-501) ─────────────────


@app.post("/api/recommend", response_model=RecommendResponse)
async def recommend(body: RecommendRequest):
    """
    Core recommendation endpoint.

    Accepts a natural-language query and returns justified movie
    recommendations with a narrative explanation.
    """
    # Validate query
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="La query no puede estar vacía")

    # Session handling
    session = get_or_create_session(body.session_id)

    try:
        response, entities, selected = await run_pipeline(
            user_query=body.query,
            session_id=session.session_id,
            max_results=body.max_results,
            language=body.language,
            filters=body.filters,
            previous_entities=session.last_entities,
        )
    except Exception as exc:
        logger.exception("Pipeline failed")
        raise HTTPException(
            status_code=503,
            detail=f"El servicio no pudo completar la petición: {exc}",
        )

    # Post-process narrative text to fix tokenization artifacts
    response.narrative = clean_narrative(response.narrative)

    # If text is still garbled, use LLM rewrite
    response.narrative = await fix_text_quality(response.narrative)

    # Save conversation turn
    save_turn(
        session.session_id,
        body.query,
        response.narrative,
        entities=entities,
        recommendations=response.recommendations,
    )

    # Update user profile
    enriched_genres = []
    enriched_keywords = []
    for film in selected:
        enriched_genres.extend(film.genres)
        enriched_keywords.extend(film.keywords[:5])

    update_profile_from_interaction(
        session.session_id,
        body.query,
        entities,
        response.recommendations,
        enriched_genres=enriched_genres,
        enriched_keywords=enriched_keywords,
    )

    return response


# ── Streaming SSE endpoint (T-502) ───────────────────────


@app.post("/api/recommend/stream")
async def recommend_stream(body: RecommendRequest):
    """
    Streaming recommendation endpoint (Server-Sent Events).

    Sends structured data first, then streams the narrative text.
    """
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="La query no puede estar vacía")

    session = get_or_create_session(body.session_id)

    from app.agents.enrichment import enrich_movies
    from app.agents.nlp_extractor import extract_entities
    from app.agents.query_builder import query_tmdb
    from app.agents.reranker import (
        generate_narrative_stream,
        rerank_films,
        select_top_n,
    )
    from app.agents.profile_recommender import build_narrative_context as _build_ctx

    async def event_generator() -> AsyncIterator[dict]:
        tmdb_lang = f"{body.language}-{body.language.upper()}" if len(body.language) == 2 else body.language

        # Phase 1: NLP
        yield {"event": "status", "data": json.dumps({"phase": "extracting"})}
        entities = await extract_entities(body.query)

        # Phase 2: Query
        yield {"event": "status", "data": json.dumps({"phase": "searching"})}
        raw = await query_tmdb(entities, language=tmdb_lang, min_year=body.filters.min_year, min_rating=body.filters.min_rating)

        if not raw:
            yield {"event": "done", "data": json.dumps({"narrative": "No encontré películas. Intenta con otra descripción.", "recommendations": []})}
            return

        # Phase 3: Enrich
        yield {"event": "status", "data": json.dumps({"phase": "enriching"})}
        enriched = await enrich_movies(raw, language=tmdb_lang)

        # Phase 4: Re-rank
        yield {"event": "status", "data": json.dumps({"phase": "ranking"})}
        ranked = await rerank_films(body.query, enriched)
        selected = select_top_n(ranked, enriched, n=body.max_results)

        # Send film data
        rank_map = {r.tmdb_id: r for r in ranked}
        recs = [
            {
                "tmdb_id": f.tmdb_id,
                "title": f.title,
                "year": f.release_year,
                "score": round(f.relevance_score, 1),
                "poster_url": f.poster_url,
                "reason": rank_map[f.tmdb_id].reason if f.tmdb_id in rank_map else "",
                "genres": f.genres,
                "keywords": f.keywords[:8],
            }
            for f in selected
        ]
        yield {"event": "recommendations", "data": json.dumps(recs, ensure_ascii=False)}

        # Phase 5: Stream narrative
        yield {"event": "status", "data": json.dumps({"phase": "narrating"})}
        full_narrative = ""
        _profile_ctx = _build_ctx(session.session_id)
        async for chunk in generate_narrative_stream(body.query, selected, ranked, profile_context=_profile_ctx):
            cleaned = clean_stream_chunk(chunk)
            full_narrative += cleaned
            yield {"event": "token", "data": cleaned}

        # Post-process full narrative
        full_narrative = clean_narrative(full_narrative)

        # If text is garbled, attempt LLM rewrite and send corrected version
        fixed_narrative = await fix_text_quality(full_narrative)
        if fixed_narrative != full_narrative:
            yield {"event": "narrative_replace", "data": fixed_narrative}
            full_narrative = fixed_narrative

        yield {"event": "done", "data": json.dumps({"session_id": session.session_id})}

        # Save session
        save_turn(session.session_id, body.query, full_narrative, entities=entities)

        # Update user profile
        enriched_genres = []
        enriched_keywords = []
        for film in selected:
            enriched_genres.extend(film.genres)
            enriched_keywords.extend(film.keywords[:5])

        recs_models = [
            RecommendationItem(
                tmdb_id=f.tmdb_id,
                title=f.title,
                year=f.release_year,
                score=round(f.relevance_score, 1),
                poster_url=f.poster_url,
                reason=rank_map[f.tmdb_id].reason if f.tmdb_id in rank_map else "",
            )
            for f in selected
        ]
        update_profile_from_interaction(
            session.session_id,
            body.query,
            entities,
            recs_models,
            enriched_genres=enriched_genres,
            enriched_keywords=enriched_keywords,
        )

    return EventSourceResponse(event_generator())


# ── Session endpoints (T-503) ────────────────────────────


@app.get("/api/session/{session_id}")
async def get_session_info(session_id: str):
    """Retrieve session history."""
    ctx = get_session(session_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return ctx


@app.delete("/api/session/{session_id}")
async def delete_session_endpoint(session_id: str):
    """Delete a conversation session."""
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {"status": "deleted"}


@app.post("/api/sessions/cleanup")
async def cleanup_sessions():
    """Remove expired sessions."""
    count = cleanup_expired()
    return {"removed": count}


# ── Sentiment analysis endpoint ───────────────────────────


@app.post("/api/analyze/sentiment")
async def analyze_sentiment_endpoint(body: dict):
    """Analyze the sentiment of a text message."""
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=422, detail="Text is required")
    result = analyze_sentiment(text)
    return result


# ── User Profile endpoint ────────────────────────────────


@app.get("/api/profile/{session_id}")
async def get_user_profile(session_id: str):
    """Return the user taste profile for a session."""
    profile = get_profile(session_id)
    if not profile:
        return {
            "session_id": session_id,
            "profile": None,
            "message": "No profile yet. Start a conversation first.",
        }
    return {
        "session_id": session_id,
        "profile": profile.to_dict(),
    }


# ── Graph data endpoint for D3.js ────────────────────────


@app.get("/api/graph/{session_id}")
async def get_graph_data(session_id: str):
    """
    Return graph data (nodes + links) for D3.js force-directed layout.
    Includes movies, genres, keywords, moods, and user archetype tags.
    """
    ctx = get_session(session_id)
    if not ctx:
        return {"nodes": [], "links": [], "profile": None, "stats": {}}

    # Build recommendation list with genres/keywords for graph
    all_recs: List[Dict[str, Any]] = []
    for rec in ctx.last_recommendations:
        all_recs.append({
            "tmdb_id": rec.tmdb_id,
            "title": rec.title,
            "year": rec.year,
            "score": rec.score,
            "poster_url": rec.poster_url,
            "reason": rec.reason,
            "genres": [],
            "keywords": [],
        })

    # Try to get enriched data from the graph endpoint body
    graph = build_movie_graph(session_id, all_recs)
    return graph


@app.post("/api/graph/{session_id}")
async def post_graph_data(session_id: str, body: dict = {}):
    """
    Build graph data with enriched movie information.
    Accepts movie data with genres and keywords in the request body.
    """
    movies = body.get("movies", [])
    graph = build_movie_graph(session_id, movies)
    return graph


# ── Serve frontend (T-505) ───────────────────────────────
# In production, Next.js is served by its own container.
# This fallback serves a redirect to the frontend.

@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to the Next.js frontend or show API info."""
    return HTMLResponse(
        content="""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>CineMatch AI API</title>
<style>body{font-family:system-ui;background:#0f172a;color:#e2e8f0;display:flex;
justify-content:center;align-items:center;height:100vh;margin:0}
.card{text-align:center;padding:2rem;border-radius:1rem;background:#1e293b}
a{color:#60a5fa;text-decoration:none}h1{color:#f59e0b}</style></head>
<body><div class="card">
<h1>🎬 CineMatch AI</h1>
<p>Motor de Recomendación Cinematográfica</p>
<p><a href="/docs">📖 API Docs</a> · <a href="http://localhost:3000">🖥 Frontend</a></p>
</div></body></html>"""
    )
