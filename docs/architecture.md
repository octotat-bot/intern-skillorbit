# Architecture

## System overview

```mermaid
flowchart LR
    U[Student's browser] -->|React + Vite + Tailwind<br/>Vercel| FE[Frontend SPA]
    FE -->|Axios, JSON over HTTPS| API[Flask API<br/>gunicorn on Render]
    API --> UP[routes/upload.py]
    API --> RO[routes/roles.py]
    API --> AN[routes/analysis.py]
    UP --> EX[services/extract.py<br/>pdfplumber / PyMuPDF / python-docx]
    EX --> PA[services/parser.py<br/>normalise, sections, contact, parse quality]
    PA --> DB[(SQLite<br/>resumes table)]
    AN --> DB
    AN --> ORC[services/analysis.py]
    ORC --> SC[services/scorer.py]
    ORC --> ATS[services/ats.py]
    ORC --> FB[services/feedback.py]
    SC --> SK[services/skills.py<br/>spaCy PhraseMatcher]
    ATS --> SK
    ATS --> ROLES[(data/roles.json)]
    ORC -.mode=ai.-> RAG[services/rag.py]
    RAG --> KB[(data/kb/*.md<br/>+ index.npz)]
    RAG -.optional.-> LLM[Gemini API]
```

Solid arrows are the deterministic path, which always runs. Dotted arrows are the optional AI
layer, which runs only in `mode=ai` and degrades to `ai_available: false` on any failure.

## Request flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant F as Flask API
    participant P as Parser
    participant D as SQLite
    participant E as Engine (score, ATS, rules)
    participant R as RAG + LLM (optional)

    B->>F: POST /api/resumes (multipart file)
    F->>F: validate type, size, magic bytes
    F->>P: parse_resume(bytes, type)
    P-->>F: text, sections, contact, parse_quality, stats
    F->>D: insert row (file itself is not stored)
    F-->>B: 201 {resume_id, parse_quality, sections_detected}
    B->>F: GET /api/resumes/{id}/analysis?role=..&mode=rules|ai
    F->>D: load parsed resume
    F->>E: score + ATS + feedback (deterministic)
    opt mode = ai
        F->>R: retrieve chunks, generate, validate citations
        R-->>F: generated_feedback or ai_available=false
    end
    F-->>B: 200 analysis JSON
```

## Backend layout

```
backend/
  app/
    __init__.py        app factory: CORS, JSON errors, blueprints, DB init
    config.py          every weight, threshold, limit and word list
    db.py              sqlite3 persistence (one table)
    errors.py          ApiError + JSON error handlers
    routes/            upload.py (POST/GET resumes), roles.py, analysis.py
    services/
      extract.py       PDF/DOCX text extraction, two-column detection
      parser.py        normalisation, sections, contact, parse quality
      nlp.py           shared spaCy pipeline
      roles.py         roles.json loader + validation
      skills.py        skill matcher (PhraseMatcher + regex)
      resume_features.py  verbs, entries, metrics, pronouns, dates
      scorer.py        /100 rubric
      ats.py           ATS keyword match + TF-IDF
      feedback.py      40-rule engine
      analysis.py      orchestration + AI fallback
      kb.py, rag.py, llm.py   optional RAG layer
    data/              roles.json, kb/ (chunks + index.npz)
  evaluation/          labelled evaluation set + runner
  tests/               pytest suite (unit + API)
```

## Data model

One SQLite table, `resumes`:

| Column | Content |
|---|---|
| id | integer primary key, exposed as `resume_id` |
| filename, file_type | sanitised name, `pdf` or `docx` |
| raw_text | text exactly as extracted |
| clean_text | normalised text used for analysis |
| sections, contact, parse_quality, stats | JSON produced by the parser |
| created_at | timestamp |

Analysis results are not stored: they are recomputed on request, which keeps them consistent with
the current rules and costs about 100 ms.

## Design decisions

| Decision | Why |
|---|---|
| Rule-based, deterministic core | Grading requires the same input to give the same score, and every point must be explainable. |
| LLM only in an optional layer, after scoring | The app must work with no API key; generated text can never change a score. |
| Citation and number validation of LLM output | Prevents ungrounded advice and invented metrics. |
| Uploaded files are not stored | Privacy; only extracted text is needed. |
| `sqlite3` instead of an ORM | One table, no migrations; fewer dependencies. |
| TF-IDF embeddings + NumPy store | 52 chunks need no vector database; works offline and ships in an 11 KB file. |
| All tunables in `config.py` | Weights can be calibrated in one place; `config.py` asserts each parameter's checks sum to its weight. |
| Layout risk lowers the ATS score, not the resume score | Separates "is the content good" from "can a machine read it". |
