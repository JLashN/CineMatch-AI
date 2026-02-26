"""
CineMatch AI — Re-ranker & Narrative Generator (Module 4)

Design patterns:
  - Strategy: scoring strategy (LLM-based vs. fallback)
  - Template Method: narrative prompt construction
  - Iterator: async generator for streaming narrative
"""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator, Dict, List, Set

from app.clients import chat_completion, stream_chat
from app.models import EnrichedFilm, RankedFilm

logger = logging.getLogger(__name__)

# ── Re-ranking prompt ─────────────────────────────────────

_RERANK_SYSTEM = """\
Eres un crítico de cine experto. Evalúa cada película de la lista según lo bien que se ajusta a la petición del usuario.

Para cada película, asigna una puntuación del 0 al 10 y una razón breve (1-2 frases) de por qué se ajusta o no.

Responde ÚNICAMENTE con un array JSON válido, sin markdown ni texto extra:
[{"id": <tmdb_id>, "score": <float>, "reason": "..."}]
"""


def _build_rerank_user_prompt(user_query: str, films: List[EnrichedFilm]) -> str:
    """Build the user prompt with the original query and candidate films."""
    film_descriptions = []
    for f in films:
        desc = (
            f"- ID: {f.tmdb_id} | «{f.title}» ({f.release_year}) | "
            f"Géneros: {', '.join(f.genres)} | Keywords: {', '.join(f.keywords[:8])} | "
            f"Nota: {f.vote_average}/10 | Países: {', '.join(f.origin_countries)}\n"
            f"  Sinopsis: {f.overview[:300]}"
        )
        film_descriptions.append(desc)

    films_text = "\n".join(film_descriptions)
    return (
        f"PETICIÓN DEL USUARIO:\n\"{user_query}\"\n\n"
        f"PELÍCULAS CANDIDATAS:\n{films_text}\n\n"
        f"Evalúa y puntúa cada película. Responde SOLO con JSON."
    )


async def rerank_films(
    user_query: str,
    films: List[EnrichedFilm],
) -> List[RankedFilm]:
    """Score each film using the LLM and return ranked results."""
    if not films:
        return []

    messages = [
        {"role": "system", "content": _RERANK_SYSTEM},
        {"role": "user", "content": _build_rerank_user_prompt(user_query, films)},
    ]

    raw = await chat_completion(
        messages,
        temperature=0.3,
        max_tokens=800,
        top_p=0.9,
    )

    # Parse JSON array
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # Find the JSON array
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        items = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Re-ranker returned invalid JSON: %s", raw[:500])
        # Fallback strategy: rank by TMDB vote_average
        return [
            RankedFilm(tmdb_id=f.tmdb_id, score=f.vote_average, reason="Puntuación de TMDB (fallback)")
            for f in films
        ]

    ranked: List[RankedFilm] = []
    for item in items:
        try:
            ranked.append(RankedFilm(
                tmdb_id=item["id"],
                score=float(item["score"]),
                reason=item.get("reason", ""),
            ))
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping malformed ranking item: %s — %s", item, exc)

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


# ── Top-N selection with diversification ──────────────────


def select_top_n(
    ranked: List[RankedFilm],
    films: List[EnrichedFilm],
    n: int = 3,
) -> List[EnrichedFilm]:
    """
    Select the top-N films, applying light diversification:
    avoid recommending films from the exact same franchise/series.
    """
    film_map = {f.tmdb_id: f for f in films}
    selected: List[EnrichedFilm] = []
    seen_titles: Set[str] = set()

    for r in ranked:
        if len(selected) >= n:
            break
        film = film_map.get(r.tmdb_id)
        if not film:
            continue
        title_root = film.title.split(":")[0].strip().lower()
        if title_root in seen_titles:
            continue
        film.relevance_score = r.score
        selected.append(film)
        seen_titles.add(title_root)

    return selected


# ── Narrative system prompt (Template Method) ─────────────

_NARRATIVE_SYSTEM = """\
Eres CineMatch AI, un asistente cinéfilo apasionado y culto.

REGLAS DE FORMATO (CRÍTICAS — CUMPLE TODAS):
1. SIEMPRE pon un ESPACIO entre cada palabra. Ejemplo correcto: "me alegro que hayas pedido". Ejemplo INCORRECTO: "mealegroque".
2. SIEMPRE pon un ESPACIO después de comas, puntos y signos de puntuación. Ejemplo: "Hola, ¿qué tal?" NO "Hola,¿quétal?"
3. SIEMPRE pon un ESPACIO antes de signos de apertura ¿ y ¡. Ejemplo: "texto ¡genial!" NO "texto¡genial!"
4. Escribe palabras COMPLETAS. NUNCA separes sílabas: "película" NO "pel í cula".
5. Usa **negrita** para títulos de películas.
6. Usa *cursiva* para citas textuales.
7. Separa los párrafos con una línea en blanco.

REGLAS DE CONTENIDO:
1. Tutea al usuario, sé cercano y amigable.
2. Explica POR QUÉ cada película encaja con su petición.
3. Incluye datos curiosos o contexto cultural cuando aporten valor.
4. Estructura: intro breve → cada película con justificación → cierre invitando a refinar.
5. Escribe de forma narrativa y fluida, no listas secas.
6. Responde en español (o el idioma del usuario).

PERSONALIZACIÓN:
{profile_context}
"""


def _get_narrative_system(profile_context: str = "") -> str:
    """Build the narrative system prompt, optionally with profile context."""
    if not profile_context:
        profile_context = "Sin datos de perfil aún — responde de forma general."
    return _NARRATIVE_SYSTEM.replace("{profile_context}", profile_context)


def _build_narrative_user_prompt(
    user_query: str,
    films: List[EnrichedFilm],
    ranked: List[RankedFilm],
) -> str:
    """Build the prompt for narrative generation with all film data."""
    rank_map = {r.tmdb_id: r for r in ranked}

    film_blocks = []
    for i, f in enumerate(films, 1):
        r = rank_map.get(f.tmdb_id)
        reason = r.reason if r else ""
        block = (
            f"PELÍCULA {i}:\n"
            f"  Título: {f.title} ({f.release_year})\n"
            f"  Título original: {f.original_title}\n"
            f"  Géneros: {', '.join(f.genres)}\n"
            f"  Keywords: {', '.join(f.keywords[:6])}\n"
            f"  Sinopsis: {f.overview}\n"
            f"  Nota TMDB: {f.vote_average}/10 ({f.vote_count} votos)\n"
            f"  Duración: {f.runtime} min\n"
            f"  Países: {', '.join(f.origin_countries)}\n"
            f"  Razón de selección: {reason}\n"
        )
        if f.top_review:
            block += f"  Extracto de reseña: {f.top_review}\n"
        film_blocks.append(block)

    films_text = "\n".join(film_blocks)
    return (
        f"El usuario pidió: \"{user_query}\"\n\n"
        f"Has seleccionado estas películas:\n{films_text}\n\n"
        f"Genera una respuesta conversacional presentando estas recomendaciones."
    )


# ── Non-streaming narrative (fallback) ────────────────────


async def generate_narrative(
    user_query: str,
    films: List[EnrichedFilm],
    ranked: List[RankedFilm],
    profile_context: str = "",
) -> str:
    """Generate the final narrative response (non-streaming)."""
    messages = [
        {"role": "system", "content": _get_narrative_system(profile_context)},
        {"role": "user", "content": _build_narrative_user_prompt(user_query, films, ranked)},
    ]

    return await chat_completion(
        messages,
        temperature=0.3,
        max_tokens=1500,
        presence_penalty=0.4,
        frequency_penalty=0.3,
    )


# ── Real streaming narrative (LangChain astream) ─────────


async def stream_narrative(
    user_query: str,
    films: List[EnrichedFilm],
    ranked: List[RankedFilm],
    profile_context: str = "",
) -> AsyncIterator[str]:
    """
    Stream the narrative response token-by-token from the LLM.
    Uses LangChain's astream() for real token streaming via vLLM.
    Yields individual token strings as they arrive.
    """
    messages = [
        {"role": "system", "content": _get_narrative_system(profile_context)},
        {"role": "user", "content": _build_narrative_user_prompt(user_query, films, ranked)},
    ]

    async for token in stream_chat(
        messages,
        temperature=0.3,
        max_tokens=1500,
        presence_penalty=0.4,
        frequency_penalty=0.3,
    ):
        yield token
