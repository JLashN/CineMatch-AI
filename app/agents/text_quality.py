"""
CineMatch AI — Text Quality Agent

Uses a secondary LLM call to fix garbled/concatenated text output.
Acts as a post-processing safety net when the primary narrative
comes out with missing spaces or broken words.
"""

from __future__ import annotations

import logging
import re

from app.clients import chat_completion

logger = logging.getLogger(__name__)

_REWRITE_SYSTEM = """\
Eres un corrector de texto experto. Tu ÚNICA tarea es corregir el texto que te dan.

El texto puede tener estos problemas:
1. Palabras pegadas sin espacios (ej: "mealegroque" → "me alegro que")
2. Sílabas separadas por espacios (ej: "pel í cula" → "película")
3. Puntuación mal espaciada (ej: "algo,que" → "algo, que")
4. Signos de apertura pegados (ej: "¡Hola" está bien, pero "texto¡Hola" → "texto ¡Hola")

Reglas ESTRICTAS:
- Devuelve SOLO el texto corregido, nada más.
- Mantén el significado exacto, NO cambies ni añadas contenido.
- Mantén el formato markdown (**, *, etc.) tal como está.
- Mantén los párrafos y saltos de línea.
- NO agregues ningún comentario, explicación ni nota.
- Si el texto ya está bien, devuélvelo tal cual.
"""


def _is_text_garbled(text: str) -> bool:
    """
    Heuristic to detect if text has missing spaces / concatenated words.
    Returns True if the text appears garbled and needs LLM rewriting.
    """
    if not text or len(text) < 50:
        return False

    # Count words: if text is mostly one giant word, it's garbled
    words = text.split()
    if not words:
        return False

    avg_word_len = sum(len(w) for w in words) / len(words)

    # Normal Spanish text has avg word length ~4-6 chars
    # Garbled text like "Oye,¡mealegraquehayaspedido..." has avg > 15
    if avg_word_len > 12:
        return True

    # Check for very long "words" (>30 chars without spaces)
    long_words = sum(1 for w in words if len(w) > 30)
    if long_words > 2:
        return True

    # Check for common concatenation patterns
    # e.g., lowercase followed by uppercase without space
    concat_pattern = re.findall(r'[a-záéíóú][A-ZÁÉÍÓÚ]', text)
    if len(concat_pattern) > 5:
        return True

    # Check for punctuation-letter concatenation (e.g., ".Esto" or ",que")
    punct_concat = re.findall(r'[.!?][a-záéíóúA-Z]', text)
    if len(punct_concat) > 3:
        return True

    return False


def _attempt_space_insertion(text: str) -> str:
    """
    Algorithmic attempt to insert spaces in concatenated text.
    Uses regex patterns to detect word boundaries.
    """
    if not text:
        return text

    # Insert space before uppercase letter after lowercase
    text = re.sub(r'([a-záéíóúüñ])([A-ZÁÉÍÓÚÜÑ])', r'\1 \2', text)

    # Insert space after sentence-ending punctuation followed by a letter
    text = re.sub(r'([.!?])([A-ZÁÉÍÓÚÜÑa-záéíóúüñ])', r'\1 \2', text)

    # Insert space after comma/semicolon followed by a letter (not number)
    text = re.sub(r'([,;:])([A-ZÁÉÍÓÚÜÑa-záéíóúüñ])', r'\1 \2', text)

    # Insert space before opening exclamation/question marks if preceded by letter
    text = re.sub(r'([a-záéíóúüñA-ZÁÉÍÓÚÜÑ])([¡¿])', r'\1 \2', text)

    # Insert space after closing punctuation followed by letter
    text = re.sub(r'([!?»"])([a-záéíóúüñA-ZÁÉÍÓÚÜÑ])', r'\1 \2', text)

    # Fix "que" and common conjunctions stuck to other words
    # Common Spanish words that should be separate
    common_words = [
        'que', 'de', 'del', 'en', 'el', 'la', 'los', 'las', 'un', 'una',
        'con', 'por', 'para', 'como', 'pero', 'sino', 'cuando', 'donde',
        'porque', 'aunque', 'mientras', 'también', 'además', 'entonces',
        'sin', 'sobre', 'entre', 'hasta', 'desde', 'durante', 'hacia',
        'según', 'contra', 'tras', 'mediante', 'se', 'te', 'me', 'le',
        'no', 'ya', 'más', 'muy', 'tan', 'bien', 'mal', 'así', 'aún',
        'es', 'son', 'fue', 'ser', 'hay', 'tiene', 'puede', 'hace',
    ]

    for word in common_words:
        # Word stuck after another word: "algoque" → "algo que"
        pattern = rf'([a-záéíóúüñ])({word})([^a-záéíóúüñ]|$)'
        text = re.sub(pattern, rf'\1 \2\3', text, flags=re.IGNORECASE)

    return text


async def fix_text_quality(text: str) -> str:
    """
    Fix garbled text output from the LLM.

    First tries algorithmic fixes, then falls back to LLM rewriting
    if the text is still garbled.
    """
    if not text:
        return text

    # Check if text needs fixing
    if not _is_text_garbled(text):
        logger.debug("Text quality OK, no fix needed")
        return text

    logger.warning("Garbled text detected (avg word len too high), attempting fix...")

    # Step 1: Algorithmic space insertion
    fixed = _attempt_space_insertion(text)

    # Check if that was enough
    if not _is_text_garbled(fixed):
        logger.info("Text fixed algorithmically")
        return fixed

    # Step 2: LLM rewrite as fallback
    logger.info("Algorithmic fix insufficient, using LLM rewrite...")
    try:
        messages = [
            {"role": "system", "content": _REWRITE_SYSTEM},
            {"role": "user", "content": f"Corrige este texto:\n\n{text[:3000]}"},
        ]

        rewritten = await chat_completion(
            messages,
            temperature=0.1,
            max_tokens=2000,
            top_p=0.9,
        )

        # Verify the rewrite is better
        if rewritten and len(rewritten) > len(text) * 0.5 and not _is_text_garbled(rewritten):
            logger.info("Text successfully rewritten by LLM")
            return rewritten.strip()
        else:
            logger.warning("LLM rewrite didn't improve text, using algorithmic version")
            return fixed

    except Exception as exc:
        logger.error("LLM rewrite failed: %s", exc)
        return fixed
