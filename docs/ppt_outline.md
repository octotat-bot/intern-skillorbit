# Presentation outline (15 slides, about 12 minutes)

## 1. Smart Resume Analyzer with AI-Based Feedback
- Team names, guide, college, date
- One line: "An explainable resume score, ATS match and fix list in seconds"

## 2. The problem
- Students send resumes without knowing why they are rejected
- Applicant tracking systems filter on keywords and can't read many layouts
- Existing checkers give opaque scores that change between runs

## 3. What we built
- Upload a PDF/DOCX, pick one of five target roles
- Get: a score out of 100, an ATS keyword score, missing skills, prioritized suggestions
- Optional AI-enhanced mode: grounded bullet rewrites with citations
- Screenshot: upload page

## 4. Architecture
- React + Tailwind (Vercel) -> Flask API (Render) -> SQLite
- Deterministic engine: parser, scorer, ATS matcher, 40-rule feedback engine
- Optional RAG layer: knowledge base + Gemini, never affects the score
- Diagram: system overview (Mermaid)

## 5. Reading the resume
- pdfplumber with word positions; PyMuPDF fallback; python-docx with tables and headers
- Two-column pages detected from aligned gaps and re-read column by column
- Parse quality flags scanned files, columns, tables, fragmented text as ATS risks

## 6. Understanding the resume
- Section detection: exact aliases, inline headings, ALL-CAPS keyword headings
- Contact details by regex; name via spaCy PERSON with a fallback rule
- Verb strength, metrics, pronouns, filler, date formats

## 7. The /100 score
- Six parameters: contact 10, structure 20, skills 20, projects 20, education 10, quality 20
- 27 checks, each returns points and the evidence behind them
- Same file, same role: always the same score (deterministic)

## 8. ATS keyword match
- Role catalogue: weighted must-haves with alternatives, nice-to-haves, aliases
- spaCy PhraseMatcher on text and noun lemmas; exact-case handling for R, C, Go
- Score = 70% must-have + 30% nice-to-have coverage, blended with TF-IDF similarity, minus layout penalty
- "A transparent heuristic, not a vendor-verified ATS score"

## 9. Feedback engine
- 40 rules across contact, structure, skills, projects, experience, education, quality, ATS
- Each suggestion: priority, estimated impact (score or ATS points), evidence
- Example: "Missing must-have skill: SQL, +12.9 ATS points"

## 10. AI-enhanced mode (RAG)
- 52 self-authored knowledge-base chunks, TF-IDF retrieval focused on weak areas
- Gemini rewrites weak bullets and explains skill gaps using only retrieved chunks
- Output validated: must cite retrieved chunks, may not invent numbers
- No key or an error: falls back to rules with a clear notice

## 11. Dashboard demo
- Score ring, parameter bars, ATS coverage, matched vs missing skill chips
- Suggestions with expandable evidence; full score breakdown table
- Dark and light themes, mobile layout, keyboard accessible
- Live demo: upload `E06_fresher_average.docx`, switch roles, toggle AI mode

## 12. Testing
- 336 automated tests, about 98% backend coverage
- Fixture resumes: good, weak, two-column, scanned, table, corrupted, password-protected
- Bugs the tests caught: phone numbers vs year ranges, metric parsing, JSON key order

## 13. Evaluation
- 12 labelled resumes across roles and layouts; bands assigned before scoring
- Pearson r 0.955, Spearman 0.966, all within one band, 67% exact band
- Calibration: found and fixed "empty resumes get credit for having no mistakes"

## 14. Deployment
- Backend on Render (gunicorn, health check, Blueprint), frontend on Vercel
- CORS restricted to the frontend; secrets only in environment variables
- Live URLs

## 15. Limitations and future work
- Small, synthetic, self-labelled evaluation set; English only; no OCR
- Next: independent labels on real resumes, custom job-description upload, OCR, more roles
- Thank you / questions
