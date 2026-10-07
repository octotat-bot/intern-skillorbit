"""Tests for the knowledge base, retrieval, generation validation and AI fallback."""

from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from app import config
from app.services import kb as kb_module
from app.services import llm, rag
from app.services.analysis import add_ai_layer, build_rule_analysis
from app.services.kb import (
    KnowledgeBaseError, VectorStore, fingerprint, get_knowledge_base, load_chunks, make_embedder, parse_chunks,
)
from app.services.parser import parse_resume
from app.services.roles import load_catalog

KB_SECTION_TAGS = {"contact", "structure", "skills", "projects", "experience", "education", "quality", "ats"}


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------
class TestKnowledgeBase:
    def test_at_least_40_self_authored_chunks(self) -> None:
        chunks = load_chunks()
        assert len(chunks) >= 40
        assert all(c.source == "self-authored" for c in chunks)

    def test_every_role_has_job_description_chunks(self) -> None:
        chunks = load_chunks()
        for role_id in load_catalog().roles:
            assert sum(role_id in c.roles for c in chunks) >= 5

    def test_metadata_is_valid(self) -> None:
        roles = set(load_catalog().roles) | {"all"}
        for chunk in load_chunks():
            assert set(chunk.roles) <= roles, chunk.id
            assert set(chunk.sections) <= KB_SECTION_TAGS, chunk.id

    def test_shipped_index_is_up_to_date(self) -> None:
        chunks = load_chunks()
        store = VectorStore.load(config.KB_INDEX_PATH)
        assert store.fingerprint == fingerprint(chunks, "tfidf"), "run: python -m app.services.rag build"
        assert store.ids == [c.id for c in chunks]

    def test_stale_index_is_rebuilt_in_memory(self, tmp_path: Path, monkeypatch) -> None:
        stale = tmp_path / "index.npz"
        VectorStore(["x"], np.zeros((1, 2), dtype=np.float32), "stale").save(stale)
        monkeypatch.setattr(config, "KB_INDEX_PATH", stale)
        get_knowledge_base.cache_clear()
        try:
            kb = get_knowledge_base()
            assert len(kb.store.ids) == len(load_chunks())
        finally:
            get_knowledge_base.cache_clear()

    @pytest.mark.parametrize("text, message", [
        ("<!-- chunk id=a | title=t | topic=x | roles=all | sections=skills -->\nBody", "missing"),
        ("<!-- chunk id=a | title=t | topic=x | roles=all | sections=skills | source=s -->\n   ", "no text"),
    ])
    def test_malformed_chunks_rejected(self, text: str, message: str) -> None:
        with pytest.raises(KnowledgeBaseError, match=message):
            parse_chunks(text, Path("bad.md"))

    def test_duplicate_ids_rejected(self, tmp_path: Path) -> None:
        header = "<!-- chunk id=dup | title=t | topic=x | roles=all | sections=skills | source=s -->\nText\n"
        (tmp_path / "a.md").write_text(header)
        (tmp_path / "b.md").write_text(header)
        with pytest.raises(KnowledgeBaseError, match="Duplicate"):
            load_chunks(tmp_path)

    def test_embedder_factory(self, monkeypatch) -> None:
        with pytest.raises(KnowledgeBaseError, match="Unknown"):
            make_embedder("word2vec", load_chunks())
        monkeypatch.setattr(config, "GEMINI_API_KEY", "")
        with pytest.raises(KnowledgeBaseError, match="requires GEMINI_API_KEY"):
            make_embedder("gemini", load_chunks())

    def test_tfidf_vectors_are_normalised(self) -> None:
        vectors = get_knowledge_base().store.vectors
        assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def _record(data: bytes, kind: str) -> dict:
    return {**parse_resume(data, kind).to_dict(), "id": 1, "filename": f"r.{kind}"}


@pytest.fixture(scope="module")
def weak_record() -> dict:
    from tests.fixtures import resumes
    return _record(resumes.build_docx(resumes.WEAK_RESUME), "docx")


class TestRetrieval:
    @pytest.mark.parametrize("role_id", ["data_analyst", "web_developer", "ai_ml_engineer",
                                         "cloud_engineer", "full_stack_developer"])
    def test_stays_on_role_and_includes_role_chunks(self, weak_record: dict, role_id: str) -> None:
        analysis = build_rule_analysis(weak_record, role_id)
        retrieved = rag.retrieve(get_knowledge_base(), analysis)
        assert len(retrieved) == config.RAG_TOP_K
        assert all(c.applies_to(role_id) for c, _ in retrieved)
        assert sum(c.role_specific for c, _ in retrieved) >= config.RAG_ROLE_CHUNKS
        scores = [s for _, s in retrieved]
        assert scores == sorted(scores, reverse=True)

    def test_deterministic(self, weak_record: dict) -> None:
        analysis = build_rule_analysis(weak_record, "data_analyst")
        kb = get_knowledge_base()
        assert [c.id for c, _ in rag.retrieve(kb, analysis)] == [c.id for c, _ in rag.retrieve(kb, analysis)]

    def test_weak_areas(self, weak_record: dict) -> None:
        areas = rag.weak_areas(build_rule_analysis(weak_record, "data_analyst"))
        assert {"contact", "projects", "skills", "ats"} <= set(areas)

    def test_weak_bullets(self) -> None:
        sections = {"projects": "App | Python\nBuilt an app for 50 users.\nHelped with the UI.\nDesigned the API."}
        assert rag.weak_bullets(sections) == ["Helped with the UI.", "Designed the API."]


# ---------------------------------------------------------------------------
# Validation of model output
# ---------------------------------------------------------------------------
ALLOWED = {"bp-005", "jd-da-002"}
BULLETS = ["Helped with the UI.", "Made a model with 80% accuracy."]


def _raw(**overrides) -> str:
    data = {
        "bullet_rewrites": [{"original": "Helped with the UI.", "rewritten": "Built the UI, improving [X%] of flows.",
                             "chunk_ids": ["bp-005"]}],
        "skill_gaps": [{"skill": "SQL", "explanation": "Analysts query databases.", "chunk_ids": ["jd-da-002"]}],
        "summary": {"text": "Add SQL and metrics.", "chunk_ids": ["bp-005", "jd-da-002"]},
    }
    data.update(overrides)
    return json.dumps(data)


class TestValidation:
    def test_valid_response(self) -> None:
        result = rag.validate_generation(_raw(), ALLOWED, BULLETS, ["SQL"])
        assert len(result["bullet_rewrites"]) == 1 and len(result["skill_gaps"]) == 1
        assert result["citations"] == ["bp-005", "jd-da-002"] and result["dropped_items"] == 0

    @pytest.mark.parametrize("item", [
        {"original": "Helped with the UI.", "rewritten": "Built UI.", "chunk_ids": []},          # no citation
        {"original": "Helped with the UI.", "rewritten": "Built UI.", "chunk_ids": ["bp-999"]},  # not retrieved
        {"original": "Helped with the UI.", "rewritten": "Built UI for 500 users.", "chunk_ids": ["bp-005"]},  # invented number
        {"original": "Something else", "rewritten": "Built UI.", "chunk_ids": ["bp-005"]},       # unknown original
        "not an object",
    ])
    def test_bad_rewrites_are_dropped(self, item) -> None:
        result = rag.validate_generation(_raw(bullet_rewrites=[item]), ALLOWED, BULLETS, ["SQL"])
        assert result["bullet_rewrites"] == [] and result["dropped_items"] == 1

    def test_numbers_from_original_are_allowed(self) -> None:
        item = {"original": BULLETS[1], "rewritten": "Trained a model reaching 80% accuracy.", "chunk_ids": ["bp-005"]}
        result = rag.validate_generation(_raw(bullet_rewrites=[item]), ALLOWED, BULLETS, ["SQL"])
        assert len(result["bullet_rewrites"]) == 1

    def test_unrequested_skill_dropped(self) -> None:
        gap = {"skill": "Rust", "explanation": "x", "chunk_ids": ["jd-da-002"]}
        result = rag.validate_generation(_raw(skill_gaps=[gap]), ALLOWED, BULLETS, ["SQL"])
        assert result["skill_gaps"] == []

    @pytest.mark.parametrize("raw", ["not json", "[1, 2]",
                                     json.dumps({"bullet_rewrites": [], "skill_gaps": [], "summary": None})])
    def test_unusable_responses_rejected(self, raw: str) -> None:
        with pytest.raises(rag.GenerationRejected):
            rag.validate_generation(raw, ALLOWED, BULLETS, ["SQL"])


# ---------------------------------------------------------------------------
# End-to-end AI layer with a fake provider
# ---------------------------------------------------------------------------
class FakeProvider:
    name = "fake"
    model = "fake-1"

    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.calls = 0
        self.response = response
        self.error = error

    def generate_json(self, prompt: str) -> str:
        self.calls += 1
        if self.error:
            raise self.error
        if self.response is not None:
            return self.response
        ids = [line[1:line.index("]")] for line in prompt.splitlines() if line.startswith("[")]
        bullet = next(line[2:] for line in prompt.splitlines() if line.startswith("- "))
        return json.dumps({
            "bullet_rewrites": [{"original": bullet, "rewritten": "Built a website for the college fest.",
                                 "chunk_ids": ids[:1]}],
            "skill_gaps": [{"skill": "SQL", "explanation": "Databases.", "chunk_ids": ids[:1]}],
            "summary": {"text": "Focus on SQL.", "chunk_ids": ids[:2]},
        })


@pytest.fixture(autouse=True)
def _clear_cache():
    rag._cache.clear()
    yield
    rag._cache.clear()


class TestGenerateAiFeedback:
    def test_success_with_citations(self, weak_record: dict, monkeypatch) -> None:
        provider = FakeProvider()
        monkeypatch.setattr(rag, "get_provider", lambda: provider)
        out = add_ai_layer(build_rule_analysis(weak_record, "data_analyst"), weak_record)
        assert out["ai_available"] is True and out["ai_unavailable_reason"] is None
        generated = out["generated_feedback"]
        assert generated["provider"] == "fake" and generated["citations"]
        retrieved_ids = {c["id"] for c in out["retrieved_context"]}
        assert set(generated["citations"]) <= retrieved_ids

    def test_responses_are_cached(self, weak_record: dict, monkeypatch) -> None:
        provider = FakeProvider()
        monkeypatch.setattr(rag, "get_provider", lambda: provider)
        analysis = build_rule_analysis(weak_record, "data_analyst")
        rag.generate_ai_feedback(analysis, weak_record)
        rag.generate_ai_feedback(analysis, weak_record)
        assert provider.calls == 1

    def test_missing_key_reports_reason_and_keeps_context(self, weak_record: dict, monkeypatch) -> None:
        monkeypatch.setattr(config, "LLM_PROVIDER", "gemini")
        monkeypatch.setattr(config, "GEMINI_API_KEY", "")
        out = rag.generate_ai_feedback(build_rule_analysis(weak_record, "data_analyst"), weak_record)
        assert out["ai_available"] is False and out["reason"] == "No GEMINI_API_KEY configured"
        assert len(out["retrieved_context"]) == config.RAG_TOP_K

    @pytest.mark.parametrize("provider", [
        FakeProvider(error=TimeoutError("deadline")),
        FakeProvider(response="this is not json"),
        FakeProvider(response=json.dumps({"bullet_rewrites": [{"original": "x", "rewritten": "y", "chunk_ids": ["nope"]}]})),
    ])
    def test_failures_fall_back(self, weak_record: dict, monkeypatch, provider: FakeProvider) -> None:
        monkeypatch.setattr(rag, "get_provider", lambda: provider)
        out = rag.generate_ai_feedback(build_rule_analysis(weak_record, "data_analyst"), weak_record)
        assert out["ai_available"] is False and "fake generation failed" in out["reason"]
        assert out["generated_feedback"] is None

    def test_api_ai_mode(self, client, monkeypatch) -> None:
        from tests.fixtures import resumes
        monkeypatch.setattr(rag, "get_provider", lambda: FakeProvider())
        upload = client.post("/api/resumes", data={"file": (io.BytesIO(resumes.build_docx(resumes.WEAK_RESUME)), "w.docx")},
                             content_type="multipart/form-data").get_json()
        body = client.get(f"/api/resumes/{upload['resume_id']}/analysis?role=data_analyst&mode=ai").get_json()
        assert body["mode"] == "ai" and body["ai_available"] is True
        assert body["generated_feedback"]["skill_gaps"][0]["skill"] == "SQL"


# ---------------------------------------------------------------------------
# Provider wiring (SDK client stubbed; no network)
# ---------------------------------------------------------------------------
class TestProviders:
    @pytest.mark.parametrize("provider, key, message", [
        ("none", "k", "disabled"), ("openai", "k", "Unknown"), ("gemini", "", "No GEMINI_API_KEY"),
    ])
    def test_unavailable(self, monkeypatch, provider: str, key: str, message: str) -> None:
        monkeypatch.setattr(config, "LLM_PROVIDER", provider)
        monkeypatch.setattr(config, "GEMINI_API_KEY", key)
        with pytest.raises(llm.ProviderUnavailable, match=message):
            llm.get_provider()

    def test_gemini_provider_calls_sdk(self, monkeypatch) -> None:
        captured = {}

        class FakeModels:
            def generate_content(self, **kwargs):
                captured.update(kwargs)
                return SimpleNamespace(text='{"ok": true}')

        class FakeClient:
            def __init__(self, **kwargs):
                captured["client"] = kwargs
                self.models = FakeModels()

        from google import genai
        monkeypatch.setattr(genai, "Client", FakeClient)
        monkeypatch.setattr(config, "LLM_PROVIDER", "gemini")
        monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
        provider = llm.get_provider()
        assert provider.generate_json("hello") == '{"ok": true}'
        assert captured["model"] == config.GEMINI_MODEL and captured["contents"] == "hello"
        assert captured["config"].response_mime_type == "application/json"
        assert captured["client"]["http_options"].timeout == config.AI_TIMEOUT_SECONDS * 1000

    def test_gemini_embedder_calls_sdk(self, monkeypatch) -> None:
        class FakeModels:
            def embed_content(self, **kwargs):
                assert kwargs["config"].task_type == "RETRIEVAL_QUERY"
                return SimpleNamespace(embeddings=[SimpleNamespace(values=[3.0, 4.0])])

        class FakeClient:
            def __init__(self, **kwargs):
                self.models = FakeModels()

        from google import genai
        monkeypatch.setattr(genai, "Client", FakeClient)
        vectors = kb_module.GeminiEmbedder("k", "m").embed(["q"], query=True)
        assert np.allclose(vectors, [[0.6, 0.8]])
