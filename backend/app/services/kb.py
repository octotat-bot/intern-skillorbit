"""Knowledge base: chunk loading, pluggable embedders and a NumPy vector store.

Chunks live in ``data/kb/**/*.md`` with an HTML-comment header per chunk (see
``data/kb/README.md``). The default embedder is TF-IDF, which is local,
deterministic and needs no API key; a Gemini embedder can be selected with
``EMBEDDING_PROVIDER=gemini``. Vectors are L2-normalised so a dot product is
cosine similarity. The TF-IDF index is shipped as ``index.npz`` and verified by
a fingerprint of the chunk texts and embedder name.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app import config
from app.services.ats import tokenize

logger = logging.getLogger(__name__)

_HEADER_RE = re.compile(r"<!--\s*chunk\s+(.*?)\s*-->", re.S)
_REQUIRED_FIELDS = ("id", "title", "topic", "roles", "sections", "source")


class KnowledgeBaseError(ValueError):
    """A knowledge-base file is malformed."""


@dataclass(frozen=True)
class Chunk:
    """One retrievable piece of guidance."""

    id: str
    title: str
    topic: str
    roles: tuple[str, ...]      # ("all",) or role ids
    sections: tuple[str, ...]   # resume areas this chunk helps with
    source: str
    text: str

    def applies_to(self, role_id: str) -> bool:
        """True if the chunk is general or written for ``role_id``."""
        return "all" in self.roles or role_id in self.roles

    @property
    def role_specific(self) -> bool:
        """True for role job-description snippets."""
        return "all" not in self.roles


def _parse_header(raw: str, path: Path) -> dict[str, str]:


    """Parse 'key=value | ...' chunk metadata and check required fields."""
    fields = {}
    for part in raw.split("|"):
        key, _, value = part.partition("=")
        fields[key.strip()] = value.strip()
    missing = [f for f in _REQUIRED_FIELDS if not fields.get(f)]
    if missing:
        raise KnowledgeBaseError(f"{path.name}: chunk header missing {missing}: {raw[:60]}")
    return fields


def parse_chunks(text: str, path: Path) -> list[Chunk]:
    """Split one markdown file into chunks."""
    headers = list(_HEADER_RE.finditer(text))
    chunks = []
    for index, match in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        body = " ".join(text[match.end():end].split())
        if not body:
            raise KnowledgeBaseError(f"{path.name}: chunk has no text: {match.group(1)[:60]}")
        fields = _parse_header(match.group(1), path)
        chunks.append(Chunk(
            id=fields["id"], title=fields["title"], topic=fields["topic"],
            roles=tuple(r.strip() for r in fields["roles"].split(",")),
            sections=tuple(s.strip() for s in fields["sections"].split(",")),
            source=fields["source"], text=body,
        ))
    return chunks


def load_chunks(kb_dir: Path = config.KB_DIR) -> list[Chunk]:
    """Load every chunk (README files excluded), sorted by id, ids unique."""
    chunks = [
        chunk
        for path in sorted(kb_dir.rglob("*.md")) if path.name.lower() != "readme.md"
        for chunk in parse_chunks(path.read_text(encoding="utf-8"), path)
    ]
    ids = [c.id for c in chunks]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise KnowledgeBaseError(f"Duplicate chunk ids: {duplicates}")
    return sorted(chunks, key=lambda c: c.id)


def chunk_document(chunk: Chunk) -> str:
    """Text that gets embedded for a chunk."""
    return f"{chunk.title}. {chunk.text}"


# ---------------------------------------------------------------------------
# Embedders
# ---------------------------------------------------------------------------
class Embedder(Protocol):
    """Turns texts into L2-normalised vectors."""

    name: str

    def embed(self, texts: list[str], *, query: bool = False) -> np.ndarray:
        """Embed texts; ``query`` marks retrieval queries for asymmetric models."""
        ...


def _normalise(vectors: np.ndarray) -> np.ndarray:


    """L2-normalise rows (zero rows stay zero)."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return (vectors / np.where(norms == 0, 1, norms)).astype(np.float32)


class TfidfEmbedder:
    """Local, deterministic embedder fitted on the knowledge base itself."""

    name = "tfidf"

    def __init__(self, corpus: list[str]) -> None:
        self._vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False,
                                           ngram_range=(1, 2), sublinear_tf=True)
        self._vectorizer.fit(corpus)

    def embed(self, texts: list[str], *, query: bool = False) -> np.ndarray:
        """TF-IDF vectors as dense, normalised arrays."""
        return _normalise(self._vectorizer.transform(texts).toarray())


class GeminiEmbedder:
    """Gemini embedding API (requires GEMINI_API_KEY)."""

    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai  # optional dependency, imported only when selected
        from google.genai import types

        self._types = types
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=config.AI_TIMEOUT_SECONDS * 1000)
        )
        self._model = model

    def embed(self, texts: list[str], *, query: bool = False) -> np.ndarray:
        """Embed via the API, using retrieval task types."""
        task = "RETRIEVAL_QUERY" if query else "RETRIEVAL_DOCUMENT"
        result = self._client.models.embed_content(
            model=self._model, contents=texts, config=self._types.EmbedContentConfig(task_type=task)
        )
        return _normalise(np.array([e.values for e in result.embeddings], dtype=np.float32))


def make_embedder(name: str, chunks: list[Chunk]) -> Embedder:
    """Embedder factory selected by ``EMBEDDING_PROVIDER``."""
    if name == "tfidf":
        return TfidfEmbedder([chunk_document(c) for c in chunks])
    if name == "gemini":
        if not config.GEMINI_API_KEY:
            raise KnowledgeBaseError("EMBEDDING_PROVIDER=gemini requires GEMINI_API_KEY")
        return GeminiEmbedder(config.GEMINI_API_KEY, config.GEMINI_EMBEDDING_MODEL)
    raise KnowledgeBaseError(f"Unknown EMBEDDING_PROVIDER '{name}' (use tfidf or gemini)")


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------
def fingerprint(chunks: list[Chunk], embedder_name: str) -> str:
    """Hash of embedder + chunk ids and texts; changes whenever the KB changes."""
    digest = hashlib.sha256(embedder_name.encode())
    for chunk in chunks:
        digest.update(f"{chunk.id}\x00{chunk_document(chunk)}\x00".encode())
    return digest.hexdigest()


@dataclass
class VectorStore:
    """Chunk ids and their vectors (row i belongs to ids[i])."""

    ids: list[str]
    vectors: np.ndarray
    fingerprint: str

    def save(self, path: Path) -> None:
        """Write the store as a compressed .npz file."""
        np.savez_compressed(path, ids=np.array(self.ids), vectors=self.vectors,
                            fingerprint=np.array(self.fingerprint))

    @classmethod
    def load(cls, path: Path) -> VectorStore:
        """Read a store written by :meth:`save`."""
        with np.load(path, allow_pickle=False) as data:
            return cls(list(data["ids"]), data["vectors"], str(data["fingerprint"]))

    def similarities(self, query_vector: np.ndarray) -> dict[str, float]:
        """Cosine similarity of the query to every chunk."""
        scores = self.vectors @ query_vector
        return {chunk_id: float(score) for chunk_id, score in zip(self.ids, scores)}


def build_store(chunks: list[Chunk], embedder: Embedder) -> VectorStore:
    """Embed every chunk."""
    vectors = embedder.embed([chunk_document(c) for c in chunks])
    return VectorStore([c.id for c in chunks], vectors, fingerprint(chunks, embedder.name))


@dataclass
class KnowledgeBase:
    """Loaded chunks, their embedder and vector store."""

    chunks: dict[str, Chunk]
    embedder: Embedder
    store: VectorStore


@lru_cache(maxsize=1)
def get_knowledge_base() -> KnowledgeBase:
    """Load chunks and the shipped index, rebuilding in memory if it is stale."""
    chunks = load_chunks()
    embedder = make_embedder(config.EMBEDDING_PROVIDER, chunks)
    expected = fingerprint(chunks, embedder.name)
    store = None
    if config.KB_INDEX_PATH.exists():
        store = VectorStore.load(config.KB_INDEX_PATH)
        if store.fingerprint != expected:
            logger.warning("Shipped KB index is stale or for another embedder; rebuilding in memory")
            store = None
    if store is None:
        store = build_store(chunks, embedder)
    return KnowledgeBase({c.id: c for c in chunks}, embedder, store)
