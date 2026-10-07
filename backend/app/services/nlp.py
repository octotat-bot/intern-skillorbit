"""Shared spaCy pipeline, loaded once per process."""

from __future__ import annotations

from functools import lru_cache

import spacy
from spacy.language import Language

from app import config


@lru_cache(maxsize=1)
def get_nlp() -> Language:
    """Return the cached spaCy pipeline.

    Raises:
        RuntimeError: If the configured model is not installed.
    """
    try:
        return spacy.load(config.SPACY_MODEL)
    except OSError as exc:
        raise RuntimeError(
            f"spaCy model '{config.SPACY_MODEL}' is not installed. "
            f"Run: python -m spacy download {config.SPACY_MODEL}"
        ) from exc
