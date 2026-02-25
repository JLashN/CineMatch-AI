"""
CineMatch AI — Sentiment Analysis Agent

Analyzes user messages to detect emotional intent and satisfaction level.
Uses both regex patterns and an optional LLM call for nuanced understanding.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

from app.clients import chat_completion

logger = logging.getLogger(__name__)

# ── Sentiment Lexicon (Spanish + English) ─────────────────

_INTENSITY_POSITIVE = [
    re.compile(r"\b(me encanta|increíble|maravill|extraordinari|brill|perfecto|genial|fantástic|magnificent|masterpiece|obra maestra)\b", re.I),
]
_MILD_POSITIVE = [
    re.compile(r"\b(bueno|bien|interesante|gust[aó]|ok|vale|correcto|interesting|nice|good|cool)\b", re.I),
]
_MILD_NEGATIVE = [
    re.compile(r"\b(no mucho|regular|meh|flojo|no tanto|not really|mediocre|so-so)\b", re.I),
]
_INTENSITY_NEGATIVE = [
    re.compile(r"\b(odio|horrible|terrible|asco|basura|malísim|hate|awful|worst|garbage|pésim)\b", re.I),
]

_INTENT_PATTERNS = {
    "refine": re.compile(r"\b(pero|aunque|sin embargo|excepto|menos|salvo|no.*sino|quiero.*más|algo.*diferente|cambi)\b", re.I),
    "explore": re.compile(r"\b(qué más|hay más|otra|otro|diferente|nuevo|distint|sorpr|recomienda|suggest|explore|discover)\b", re.I),
    "specific": re.compile(r"\b(exactamente|justo|precisamente|tipo|como|parecida|estilo|similar|igual)\b", re.I),
    "broad": re.compile(r"\b(cualquier|lo que sea|da igual|no importa|whatever|anything|algo|something)\b", re.I),
    "gratitude": re.compile(r"\b(gracias|thanks|thx|genial|perfecto|me encanta|great|awesome)\b", re.I),
}

_DETAIL_LEVEL = {
    "verbose": re.compile(r"\b(cuéntame más|explícame|detall|en profundidad|tell me more|elaborate|por qué|why)\b", re.I),
    "brief": re.compile(r"\b(breve|corto|resumen|rápido|brief|quick|short|solo nombres|just names)\b", re.I),
}


def analyze_sentiment(text: str) -> Dict:
    """
    Analyze user message sentiment and intent using regex patterns.
    Returns a structured analysis dict.
    """
    result = {
        "sentiment_score": 0.0,  # -1.0 to 1.0
        "sentiment_label": "neutral",
        "intensity": "normal",  # low, normal, high
        "intents": [],
        "detail_preference": "normal",  # brief, normal, verbose
        "emotional_signals": [],
    }

    # Score sentiment
    score = 0.0
    for p in _INTENSITY_POSITIVE:
        matches = p.findall(text)
        score += len(matches) * 0.4
    for p in _MILD_POSITIVE:
        matches = p.findall(text)
        score += len(matches) * 0.15
    for p in _MILD_NEGATIVE:
        matches = p.findall(text)
        score -= len(matches) * 0.15
    for p in _INTENSITY_NEGATIVE:
        matches = p.findall(text)
        score -= len(matches) * 0.4

    result["sentiment_score"] = max(-1.0, min(1.0, score))

    if score > 0.3:
        result["sentiment_label"] = "very_positive"
        result["intensity"] = "high"
    elif score > 0.1:
        result["sentiment_label"] = "positive"
    elif score < -0.3:
        result["sentiment_label"] = "very_negative"
        result["intensity"] = "high"
    elif score < -0.1:
        result["sentiment_label"] = "negative"

    # Detect intents
    for intent, pattern in _INTENT_PATTERNS.items():
        if pattern.search(text):
            result["intents"].append(intent)

    # Detail preference
    for level, pattern in _DETAIL_LEVEL.items():
        if pattern.search(text):
            result["detail_preference"] = level
            break

    # Emotional signals
    emotion_map = {
        "excitement": re.compile(r"[!]{2,}|wow|increíble|amazing", re.I),
        "curiosity": re.compile(r"\?|qué|cómo|por qué|dónde|cuándo|what|how|why|where", re.I),
        "nostalgia": re.compile(r"recuerdo|de pequeño|cuando era|infancia|nostalg|remember|childhood", re.I),
        "urgency": re.compile(r"rápido|ya|ahora|hoy|tonight|quick|now|hurry", re.I),
        "frustration": re.compile(r"no entiendes|otra vez|ya te dije|de nuevo|again|already told", re.I),
    }

    for emotion, pattern in emotion_map.items():
        if pattern.search(text):
            result["emotional_signals"].append(emotion)

    return result


async def analyze_with_llm(text: str, context: Optional[str] = None) -> Dict:
    """
    Deep sentiment analysis using the LLM for nuanced understanding.
    Only called for complex or ambiguous messages.
    """
    prompt = f"""Analiza el sentimiento e intención de este mensaje de usuario en una app de recomendación de películas.

Mensaje: "{text}"
{f'Contexto previo: {context}' if context else ''}

Responde SOLO con JSON:
{{
  "satisfaction": "high|medium|low|unknown",
  "wants_more": true/false,
  "wants_different": true/false,
  "specific_feedback": "breve descripción de lo que pide o siente",
  "recommended_tone": "enthusiastic|calm|empathetic|serious"
}}"""

    try:
        raw = await chat_completion(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )

        import json
        clean = raw.strip()
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as exc:
        logger.warning("LLM sentiment analysis failed: %s", exc)

    return {}
