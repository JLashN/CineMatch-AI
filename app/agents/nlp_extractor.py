"""
CineMatch AI — NLP Extraction Agent (Module 1)

Design patterns:
  - Strategy: extraction via LLM with retry fallback
  - Mapper: genre/keyword name → TMDB ID resolution
  - Builder: constructs ExtractedEntities step by step

Takes free-text from the user and produces structured ExtractedEntities
via the Qwen3 LLM through LangChain.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List

from app.clients import chat_completion
from app.clients.tmdb import get_genre_list, search_keyword
from app.models import ExtractedEntities

logger = logging.getLogger(__name__)

# ── System prompt for entity extraction ───────────────────

_SYSTEM_PROMPT = """\
Eres un asistente experto en cine. Tu ÚNICA tarea es analizar la petición del usuario y extraer entidades relevantes para buscar películas.

Responde ÚNICAMENTE con un objeto JSON válido, sin explicaciones, sin markdown, sin texto adicional.

Esquema exacto de salida:
{
  "genres": ["comedia", "thriller"],
  "keywords": ["atraco", "banco"],
  "region": "ES",
  "language": null,
  "mood": "ligero, divertido",
  "era": null,
  "exclude": []
}

Reglas:
- "genres": lista de nombres de género cinematográfico en español. Si no se menciona, lista vacía.
- "keywords": palabras clave temáticas extraídas de la petición (máx. 5). No repitas géneros.
- "region": código ISO 3166-1 alpha-2 si el usuario menciona un país/región. Si dice "Europa" usa null (se resolverá luego). Si no, null.
- "language": código ISO 639-1 si el usuario pide un idioma original. Si no, null.
- "mood": tono emocional que transmite la petición (ej: "oscuro", "nostálgico", "divertido"). Si no es claro, null.
- "era": década o rango (ej: "80s", "2010s", "clásico"). Si no se menciona, null.
- "exclude": géneros o temas que el usuario dice que NO quiere. Si no, lista vacía.

Responde SOLO con el JSON.
"""

# ── Genre Mapper (Mapper pattern) ─────────────────────────

_GENRE_NAME_MAP: Dict[str, List[str]] = {
    "acción": ["Action"],
    "aventura": ["Adventure"],
    "animación": ["Animation"],
    "comedia": ["Comedy"],
    "crimen": ["Crime"],
    "documental": ["Documentary"],
    "drama": ["Drama"],
    "familia": ["Family"],
    "fantasía": ["Fantasy"],
    "historia": ["History"],
    "terror": ["Horror"],
    "música": ["Music"],
    "misterio": ["Mystery"],
    "romance": ["Romance"],
    "ciencia ficción": ["Science Fiction"],
    "sci-fi": ["Science Fiction"],
    "película de tv": ["TV Movie"],
    "thriller": ["Thriller"],
    "suspense": ["Thriller"],
    "bélica": ["War"],
    "guerra": ["War"],
    "western": ["Western"],
}


async def _resolve_genre_ids(genre_names: List[str]) -> List[int]:
    """Map genre names (Spanish or English) to TMDB genre IDs."""
    genre_map = await get_genre_list("es-ES")
    inv = {v.lower(): k for k, v in genre_map.items()}
    genre_map_en = await get_genre_list("en-US")
    inv_en = {v.lower(): k for k, v in genre_map_en.items()}
    inv.update(inv_en)

    ids: List[int] = []
    for name in genre_names:
        low = name.strip().lower()
        if low in inv:
            ids.append(inv[low])
        else:
            for en_name in _GENRE_NAME_MAP.get(low, []):
                if en_name.lower() in inv:
                    ids.append(inv[en_name.lower()])
                    break
    return list(set(ids))


async def _resolve_keyword_ids(keywords: List[str]) -> List[int]:
    """Resolve text keywords to TMDB keyword IDs via search."""
    ids: List[int] = []
    for kw in keywords[:5]:
        results = await search_keyword(kw)
        if results:
            ids.append(results[0]["id"])
    return ids


# ── Extraction with retry (Strategy pattern) ─────────────


async def extract_entities(user_query: str, *, retry: int = 0) -> ExtractedEntities:
    """
    Send the user query to the LLM and return structured entities.
    Uses retry strategy: up to 3 attempts, lowering temperature on failure.
    """
    temperature = 0.1 if retry == 0 else 0.0
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    raw = await chat_completion(
        messages,
        temperature=temperature,
        max_tokens=512,
        top_p=0.9,
    )

    # Strip markdown fences
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # Find JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        if retry < 2:
            logger.warning("LLM returned invalid JSON (attempt %d), retrying…", retry + 1)
            return await extract_entities(user_query, retry=retry + 1)
        logger.error("LLM failed to produce valid JSON after 3 attempts. Raw: %s", raw[:500])
        return ExtractedEntities()

    # Build entities (Builder pattern)
    entities = ExtractedEntities(
        genres=data.get("genres", []),
        keywords=data.get("keywords", []),
        region=data.get("region"),
        language=data.get("language"),
        mood=data.get("mood"),
        era=data.get("era"),
        exclude=data.get("exclude", []),
    )

    # Resolve IDs via TMDB
    entities.genre_ids = await _resolve_genre_ids(entities.genres)
    entities.keyword_ids = await _resolve_keyword_ids(entities.keywords)

    logger.info(
        "Extracted entities: genres=%s keyword_ids=%s region=%s mood=%s era=%s",
        entities.genre_ids,
        entities.keyword_ids,
        entities.region,
        entities.mood,
        entities.era,
    )
    return entities
