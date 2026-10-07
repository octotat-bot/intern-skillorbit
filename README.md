# Smart Resume Analyzer with AI-Based Feedback

Upload a resume (PDF/DOCX), pick a target role, and get a /100 score, an ATS
keyword-match score, missing skills, and prioritized, evidence-backed
improvement suggestions on a dashboard.

> **Status:** Phase 0 skeleton. Sections below are completed in Phase 6.

## Stack
- **Backend:** Python 3.11+, Flask, SQLite, spaCy (`en_core_web_sm`), NLTK, scikit-learn
- **Frontend:** React + Vite + Tailwind CSS, Recharts, Axios
- **Optional AI layer:** RAG over a local knowledge base + Gemini (swappable)

## Quick start (development)

### Backend
```bash
cd backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env
pytest
python run.py            # http://localhost:5000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev              # http://localhost:5173
```

## Design principles
- Scoring, ATS matching and feedback are **deterministic and rule-based**. No LLM is used in scoring.
- Every score and suggestion returns the **evidence** that produced it.
- The AI layer is optional. With no key or on failure, the app returns rule-based output with `ai_available=false`.
- The ATS score is a transparent **heuristic**, not a vendor-verified metric.

## Roadmap
| Phase | Scope |
|---|---|
| 0 | Plan, skeleton, requirements |
| 1 | Parser + upload API + tests |
| 2 | Scorer + roles.json + ATS matcher + tests |
| 3 | Feedback engine + analysis API + tests |
| 4 | React dashboard |
| 5 | RAG layer + AI mode |
| 6 | Evaluation, deployment, docs, report and PPT outlines |
