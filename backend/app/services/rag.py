"""Retrieval-augmented generative feedback (optional AI layer).

Flow:
1. Find weak areas from the deterministic analysis (low parameters, missing
   must-have skills, formatting issues).
2. Retrieve the top-k knowledge-base chunks for the role, boosting chunks that
   cover weak areas and guaranteeing some role-specific job-description chunks.
3. Ask the LLM to rewrite weak bullets and explain skill gaps using ONLY those
   chunks, citing chunk ids.
4. Validate the response: every item must cite retrieved chunk ids, rewrites
   must keep the original bullet's meaning anchor and may not add numbers that
   were not in the original. Invalid items are dropped and counted.

Any missing key, provider error or invalid response yields
``ai_available=False``; the rule-based analysis is never affected. Retrieved
chunks are returned either way so the UI can show relevant guidance offline.

CLI:  ``python -m app.services.rag build``  rebuild the shipped TF-IDF index.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import OrderedDict
from typing import Any

from app import config
from app.services import resume_features as features
from app.services.kb import KnowledgeBase, build_store, get_knowledge_base, load_chunks, make_embedder
from app.services.llm import LLMProvider, ProviderUnavailable, get_provider

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_cache: OrderedDict[str, str] = OrderedDict()


class GenerationRejected(ValueError):
    """The LLM response had no usable, properly cited content."""


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def weak_areas(analysis: dict[str, Any]) -> list[str]:
    """Resume areas needing help, as knowledge-base section tags."""
    areas = [
        name for name, parameter in analysis["score"]["parameters"].items()
        if parameter["score"] < config.RAG_WEAK_PARAMETER_RATIO * parameter["max"]
    ]
    if analysis["ats"]["missing_must_have"]:
        areas.append("skills")
    if analysis["parse_quality"].get("issues"):
        areas.append("ats")
    return list(dict.fromkeys(areas))


def build_query(analysis: dict[str, Any]) -> str:
    """Retrieval query: role, missing skills, top suggestion titles and weak areas."""
    missing = [item["label"] for item in analysis["ats"]["missing_must_have"]]
    titles = [item["title"] for item in analysis["feedback"]["suggestions"][: config.RAG_TOP_K]]
    return " ".join([analysis["role"]["name"], *missing, *titles, *weak_areas(analysis)])


def retrieve(kb: KnowledgeBase, analysis: dict[str, Any]) -> list[tuple[Any, float]]:
    """Top-k chunks for the analysis, deterministic (ties broken by chunk id)."""
    role_id = analysis["role"]["id"]
    areas = set(weak_areas(analysis))
    query_vector = kb.embedder.embed([build_query(analysis)], query=True)[0]
    similarity = kb.store.similarities(query_vector)

    def score(chunk) -> float:

        """Similarity plus the weak-area boost, rounded for stable ordering."""
        boost = config.RAG_SECTION_BOOST if areas & set(chunk.sections) else 0.0
        return round(similarity[chunk.id] + boost, 4)

    candidates = sorted((c for c in kb.chunks.values() if c.applies_to(role_id)),
                        key=lambda c: (-score(c), c.id))
    role_chunks = [c for c in candidates if c.role_specific][: config.RAG_ROLE_CHUNKS]
    rest = [c for c in candidates if c not in role_chunks][: config.RAG_TOP_K - len(role_chunks)]
    chosen = sorted(role_chunks + rest, key=lambda c: (-score(c), c.id))
    return [(chunk, score(chunk)) for chunk in chosen]


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
def weak_bullets(sections: dict[str, str]) -> list[str]:
    """Experience/project bullets lacking a strong opening verb or a metric."""
    lines = [line for name in ("experience", "projects")
             for line in features.description_lines(sections.get(name, ""))]
    weak = [line for line in lines
            if not ((v := features.leading_verb(line)) and v.strength == "strong")
            or not features.find_metrics(line)]
    return weak[: config.RAG_MAX_BULLETS]


def build_prompt(role_name: str, chunks: list, bullets: list[str], skills: list[str]) -> str:
    """Grounded prompt: only the listed chunks may be used, and must be cited."""
    context = "\n".join(f"[{c.id}] {c.title}: {c.text}" for c in chunks)
    bullet_list = "\n".join(f"- {b}" for b in bullets) or "- (none)"
    skill_list = ", ".join(skills) or "(none)"
    return f"""You are a resume coach for students applying to {role_name} roles.
Use ONLY the context chunks below. Do not use outside knowledge. Every item you
write must cite the ids of the chunks it relies on in "chunk_ids".

CONTEXT
{context}

TASK 1: Rewrite each bullet below to start with a strong action verb, name the
method or tool already mentioned, and state the result. Never invent numbers,
tools, employers or facts. Where a metric would help but is unknown, insert a
placeholder in square brackets such as [X%] or [N users]. Keep the "original"
field exactly as given.
BULLETS
{bullet_list}

TASK 2: For each missing skill, explain in at most two sentences why {role_name}
roles expect it and one concrete way a student can demonstrate it.
MISSING SKILLS: {skill_list}

TASK 3: Write a two to three sentence overall summary of the most important next steps.

Return JSON only, in exactly this shape:
{{"bullet_rewrites": [{{"original": "...", "rewritten": "...", "chunk_ids": ["..."]}}],
 "skill_gaps": [{{"skill": "...", "explanation": "...", "chunk_ids": ["..."]}}],
 "summary": {{"text": "...", "chunk_ids": ["..."]}}}}"""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _cited(item: dict[str, Any], allowed: set[str]) -> list[str] | None:
    """The item's chunk ids if non-empty and all retrieved, else None."""
    ids = item.get("chunk_ids")
    if not isinstance(ids, list) or not ids or not all(isinstance(i, str) and i in allowed for i in ids):
        return None
    return sorted(set(ids))


def _numbers(text: str) -> set[str]:


    """Numbers appearing in a text."""
    return set(_NUMBER_RE.findall(text))


def validate_generation(raw: str, allowed: set[str], bullets: list[str], skills: list[str]) -> dict[str, Any]:
    """Keep only well-formed, properly cited items.

    Raises:
        GenerationRejected: If the JSON is invalid or nothing usable remains.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GenerationRejected("Response was not valid JSON") from exc
    if not isinstance(data, dict):
        raise GenerationRejected("Response was not a JSON object")

    dropped = 0
    rewrites = []
    for item in data.get("bullet_rewrites") or []:
        ids = _cited(item, allowed) if isinstance(item, dict) else None
        original, rewritten = (item.get("original", ""), item.get("rewritten", "")) if ids else ("", "")
        if ids and original in bullets and rewritten.strip() and _numbers(rewritten) <= _numbers(original):
            rewrites.append({"original": original, "rewritten": rewritten.strip(), "chunk_ids": ids})
        else:
            dropped += 1

    wanted = {s.casefold() for s in skills}
    gaps = []
    for item in data.get("skill_gaps") or []:
        ids = _cited(item, allowed) if isinstance(item, dict) else None
        if ids and str(item.get("skill", "")).casefold() in wanted and str(item.get("explanation", "")).strip():
            gaps.append({"skill": item["skill"], "explanation": item["explanation"].strip(), "chunk_ids": ids})
        else:
            dropped += 1

    summary_item = data.get("summary")
    summary_ids = _cited(summary_item, allowed) if isinstance(summary_item, dict) else None
    summary = ({"text": summary_item["text"].strip(), "chunk_ids": summary_ids}
               if summary_ids and str(summary_item.get("text", "")).strip() else None)
    if summary_item and summary is None:
        dropped += 1

    if not (rewrites or gaps or summary):
        raise GenerationRejected("No item cited the retrieved context correctly")
    citations = sorted({i for item in [*rewrites, *gaps, *([summary] if summary else [])] for i in item["chunk_ids"]})
    return {"bullet_rewrites": rewrites, "skill_gaps": gaps, "summary": summary,
            "citations": citations, "dropped_items": dropped}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def _generate_cached(provider: LLMProvider, prompt: str) -> str:
    """Call the provider once per distinct prompt (bounded in-process cache)."""
    key = hashlib.sha256(f"{provider.name}|{provider.model}|{prompt}".encode()).hexdigest()
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    raw = provider.generate_json(prompt)
    _cache[key] = raw
    if len(_cache) > config.AI_CACHE_SIZE:
        _cache.popitem(last=False)
    return raw


def _context_item(chunk, score: float) -> dict[str, Any]:


    """Serialisable view of a retrieved chunk."""
    return {"id": chunk.id, "title": chunk.title, "topic": chunk.topic, "source": chunk.source,
            "role_specific": chunk.role_specific, "score": score, "text": chunk.text}


def generate_ai_feedback(analysis: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """Generate grounded feedback, or explain why AI is unavailable.

    Returns:
        ``{ai_available, reason, generated_feedback, retrieved_context}``.
    """
    kb = get_knowledge_base()
    retrieved = retrieve(kb, analysis)
    result: dict[str, Any] = {"retrieved_context": [_context_item(c, s) for c, s in retrieved],
                              "generated_feedback": None}
    try:
        provider = get_provider()
    except ProviderUnavailable as exc:
        return {**result, "ai_available": False, "reason": str(exc)}

    bullets = weak_bullets(record["sections"])
    skills = [item["label"] for item in analysis["ats"]["missing_must_have"]][: config.RAG_MAX_SKILL_GAPS]
    chunks = [chunk for chunk, _ in retrieved]
    prompt = build_prompt(analysis["role"]["name"], chunks, bullets, skills)
    try:
        generated = validate_generation(_generate_cached(provider, prompt), {c.id for c in chunks}, bullets, skills)
    except Exception as exc:  # network, quota, timeout, invalid output: never break analysis
        reason = f"{provider.name} generation failed ({type(exc).__name__}: {exc})"
        return {**result, "ai_available": False, "reason": reason[:300]}
    generated.update(provider=provider.name, model=provider.model)
    return {**result, "ai_available": True, "reason": None, "generated_feedback": generated}


def build_shipped_index() -> str:
    """Rebuild ``index.npz`` with the TF-IDF embedder; returns a status line."""
    chunks = load_chunks()
    store = build_store(chunks, make_embedder("tfidf", chunks))
    store.save(config.KB_INDEX_PATH)
    return f"Wrote {config.KB_INDEX_PATH} ({len(chunks)} chunks, {store.vectors.shape[1]} dims)"


if __name__ == "__main__":
    if sys.argv[1:] == ["build"]:
        print(build_shipped_index())
    else:
        print("usage: python -m app.services.rag build")
        sys.exit(2)
