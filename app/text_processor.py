"""
CineMatch AI — Text Post-Processor (v5)

Minimal post-processing for LLM narrative output.
The LLM (Qwen3) produces clean text with proper spacing when using
non-streaming mode. This module only performs SAFE, light cleanup:
- Unicode normalization
- Collapse multiple spaces/newlines
- Strip leading/trailing whitespace

NOTE: Previous versions (v1-v4) had aggressive regex passes (_fix_split_words,
      _fix_missing_spaces) that BROKE properly-spaced text by removing spaces
      between short words like "de", "me", "que", etc.
      Those have been removed. DO NOT re-add them.
"""

from __future__ import annotations

import re
import unicodedata


def clean_narrative(text: str) -> str:
    """
    Light post-processing for LLM narrative output.
    Only performs safe operations that cannot break properly-spaced text.
    """
    if not text:
        return text

    # Normalize unicode (NFC form)
    text = unicodedata.normalize("NFC", text)

    # Collapse multiple spaces into one (but preserve newlines)
    text = re.sub(r'[^\S\n]+', ' ', text)

    # Collapse 3+ newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text
