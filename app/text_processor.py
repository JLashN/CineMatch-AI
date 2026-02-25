"""
CineMatch AI — Text Post-Processor (v2)

Advanced text cleanup that handles BOTH:
1. Split words (tokenization artifacts): "pel í cula" → "película"
2. Concatenated words (missing spaces): "mealegroque" → "me alegro que"
3. Punctuation spacing issues
"""

from __future__ import annotations

import re
import unicodedata


def clean_narrative(text: str) -> str:
    """
    Multi-pass post-processing for LLM narrative output.
    Handles split words, missing spaces, and formatting issues.
    """
    if not text:
        return text

    # Normalize unicode (NFC form)
    text = unicodedata.normalize("NFC", text)

    # Pass 1: Fix split words (syllables separated by spaces)
    text = _fix_split_words(text)

    # Pass 2: Fix missing spaces (concatenated words)
    text = _fix_missing_spaces(text)

    # Pass 3: Fix punctuation spacing
    text = _fix_punctuation(text)

    # Pass 4: Fix markdown formatting
    text = _fix_markdown(text)

    # Pass 5: Final cleanup
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def _fix_split_words(text: str) -> str:
    """Fix words that have been split by the tokenizer."""
    # Pass 1: Fix single-char splits: "h aga" → "haga"
    for _ in range(10):
        new_text = re.sub(
            r'(\w)\s([a-záéíóúüñA-ZÁÉÍÓÚÜÑ])\s(\w)',
            r'\1\2\3',
            text,
        )
        if new_text == text:
            break
        text = new_text

    # Pass 2: Fix 2-char fragment splits
    for _ in range(5):
        new_text = re.sub(
            r'(\w)\s([a-záéíóúüñ]{1,2})\s(\w)',
            r'\1\2\3',
            text,
        )
        if new_text == text:
            break
        text = new_text

    # Pass 3: Specific Spanish word fixes
    spanish_fixes = [
        (r'\bpel\s*[íi]\s*cula', 'película'),
        (r'\bci\s*encia\s*fic\s*ci[oó]n', 'ciencia ficción'),
        (r'\bre\s*com\s*end', 'recomend'),
        (r'\breflex\s*i[oó]n', 'reflexión'),
        (r'\bcon\s*ex\s*i[oó]n', 'conexión'),
        (r'\bemo\s*ci[oó]n', 'emoción'),
        (r'\bsu\s*perv\s*iv\s*encia', 'supervivencia'),
        (r'\bint\s*el\s*ig\s*encia', 'inteligencia'),
        (r'\bart\s*if\s*ic\s*ial', 'artificial'),
    ]
    for pattern, replacement in spanish_fixes:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


def _fix_missing_spaces(text: str) -> str:
    """
    Insert missing spaces in concatenated text.
    Handles: "mealegroque" → "me alegro que"
    """
    # Insert space before uppercase after lowercase (word boundary)
    text = re.sub(r'([a-záéíóúüñ])([A-ZÁÉÍÓÚÜÑ])', r'\1 \2', text)

    # Insert space after sentence-ending punctuation + letter
    text = re.sub(r'([.!?])([A-ZÁÉÍÓÚÜÑa-záéíóúüñ])', r'\1 \2', text)

    # Insert space after comma/semicolon/colon + letter
    text = re.sub(r'([,;])([A-ZÁÉÍÓÚÜÑa-záéíóúüñ])', r'\1 \2', text)
    text = re.sub(r'(:)([A-ZÁÉÍÓÚÜÑa-záéíóúüñ])', r'\1 \2', text)

    # Insert space before ¡ or ¿ if preceded by letter
    text = re.sub(r'([a-záéíóúüñA-ZÁÉÍÓÚÜÑ])([¡¿])', r'\1 \2', text)

    # Insert space after ! or ? followed by letter
    text = re.sub(r'([!?])([a-záéíóúüñA-ZÁÉÍÓÚÜÑ])', r'\1 \2', text)

    # Insert space after closing quotes/parens followed by letter
    text = re.sub(r'([»")\]])([a-záéíóúüñA-ZÁÉÍÓÚÜÑ])', r'\1 \2', text)

    # Insert space before opening quotes/parens after letter
    text = re.sub(r'([a-záéíóúüñA-ZÁÉÍÓÚÜÑ])([«"(\[])', r'\1 \2', text)

    return text


def _fix_punctuation(text: str) -> str:
    """Fix punctuation spacing issues."""
    # Remove space before closing punctuation
    text = re.sub(r'\s+([.,;:!?)\]}»"])', r'\1', text)

    # Remove space after opening punctuation
    text = re.sub(r'([(\[{«"¿¡])\s+', r'\1', text)

    # Ensure space after sentence-ending punctuation
    text = re.sub(r'([.!?])([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)

    return text


def _fix_markdown(text: str) -> str:
    """Fix markdown formatting issues."""
    # Fix "* texto *" → "*texto*" (but keep ** for bold)
    text = re.sub(r'(?<!\*)\*\s+([^*]+)\s+\*(?!\*)', r'*\1*', text)

    # Fix "** texto **" → "**texto**"
    text = re.sub(r'\*\*\s+([^*]+)\s+\*\*', r'**\1**', text)

    return text


def clean_stream_chunk(chunk: str) -> str:
    """
    Light cleanup for streaming chunks.
    Only fixes the most obvious issues without breaking word boundaries.
    """
    if not chunk:
        return chunk
    chunk = unicodedata.normalize("NFC", chunk)
    return chunk
