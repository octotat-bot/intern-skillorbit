# Project report outline

**Title:** Smart Resume Analyzer with AI-Based Feedback
Suggested length: 25-35 pages. Section numbers map to the grading rubric where noted.

## Front matter
- Title page, certificate/declaration, acknowledgements
- Abstract (150-200 words): problem, approach (deterministic NLP scoring + optional RAG), key results
  (12-resume evaluation: Pearson r 0.955, Spearman 0.966, 100% within one band), deployment
- Table of contents, list of figures and tables

## 1. Introduction
- 1.1 Background: how resumes are screened by recruiters and applicant tracking systems (ATS)
- 1.2 Problem statement: students get no specific, explainable feedback on their resumes
- 1.3 Objectives: /100 score, ATS keyword match, missing skills, prioritized suggestions, dashboard
- 1.4 Scope and constraints: no login, no model training, deterministic scoring, AI layer optional
- 1.5 Report organisation

## 2. Literature and tool survey
- 2.1 How ATS parse resumes (text extraction, section headings, keyword search)
- 2.2 Existing resume checkers and their limits (opaque scores, LLM non-determinism)
- 2.3 NLP techniques used: rule-based extraction, phrase matching, lemmatisation, TF-IDF, NER
- 2.4 Retrieval-augmented generation and grounding/citation
- 2.5 Gap addressed: explainable, reproducible scoring plus grounded generative advice

## 3. Requirements and design  _(Functionality, Code Quality)_
- 3.1 Functional requirements (upload, roles, analysis, AI mode) and non-functional (determinism,
  explainability, privacy, 5 MB limit, response time)
- 3.2 System architecture (Mermaid diagram from `docs/architecture.md`)
- 3.3 Request sequence (upload, then analysis)
- 3.4 Data model (SQLite `resumes` table) and role catalogue schema
- 3.5 API design and error model (table from `docs/api.md`)
- 3.6 Key design decisions and trade-offs (decision table)

## 4. AI logic implementation  _(AI Logic, 20%)_
- 4.1 Text extraction: pdfplumber, PyMuPDF fallback, python-docx; two-column detection algorithm
- 4.2 Parse-quality model and ATS formatting risks
- 4.3 Section detection (three heading rules) and contact/name extraction (regex + spaCy NER)
- 4.4 Scoring rubric: six parameters, 27 checks, evidence model (table)
- 4.5 Skill detection: PhraseMatcher on surface and noun lemmas, case-sensitive short names, context filtering
- 4.6 ATS score formula (keyword coverage, TF-IDF similarity, formatting penalty); heuristic disclaimer
- 4.7 Feedback rule engine: 40 rules, priority, impact estimation, ordering
- 4.8 RAG layer: knowledge base, embedding, retrieval with weak-area boost, prompt, citation and
  number validation, fallback

## 5. Implementation  _(Functionality, UI/UX, Code Quality)_
- 5.1 Technology stack and versions
- 5.2 Backend modules and responsibilities
- 5.3 Frontend: pages, components, state, accessibility, dark/light theming, responsive layout
- 5.4 Data visualisation choices (score ring, parameter bars, coverage meters, evidence table)
- 5.5 Configuration and secrets management (`config.py`, `.env.example`)
- 5.6 Screenshots: upload page, dashboard (dark and light), AI mode, mobile view

## 6. Testing  _(Code Quality)_
- 6.1 Strategy: unit, API and pipeline tests; fixture resumes (good, weak, two-column, scanned, table,
  corrupted, encrypted)
- 6.2 Coverage summary (324 tests, about 99% backend line coverage)
- 6.3 Edge cases handled (empty, scanned, corrupted, huge, wrong type, missing sections)
- 6.4 Bugs found by tests and fixed (phone regex, metric regex, JSON key ordering, mobile overflow)

## 7. Evaluation and results
- 7.1 Evaluation set and band definitions
- 7.2 Metrics: Pearson, Spearman, MAE, band accuracy
- 7.3 Results table (from `docs/evaluation.md`)
- 7.4 Calibration: the absence-check flaw found and fixed; why weights were not tuned to the labels
- 7.5 ATS results by role; threats to validity

## 8. Deployment  _(Deployment, 10%)_
- 8.1 Render (gunicorn, Blueprint, health check) and Vercel (SPA rewrites)
- 8.2 Environment variables and CORS
- 8.3 Production smoke test and operational notes (cold starts, ephemeral storage)

## 9. Conclusion and future work
- 9.1 Summary of contributions
- 9.2 Limitations: synthetic evaluation set, self-assigned labels, English-only, heuristic ATS score,
  role catalogue hand-written
- 9.3 Future work: independent labelling of real resumes, more roles, OCR for scanned PDFs, job-
  description upload for custom roles, persistent storage and user accounts, learned weights

## References
- spaCy, pdfplumber, PyMuPDF, python-docx, scikit-learn, NLTK, Flask, React, Recharts, Gemini API docs
- Papers/articles on ATS behaviour and retrieval-augmented generation

## Appendices
- A. Full rule catalogue (from `docs/ai_logic.md`)
- B. Role catalogue (`roles.json` summary)
- C. Knowledge-base chunk list
- D. API examples
- E. Installation guide (from `README.md`)
