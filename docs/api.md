# API reference

Base URL: `http://localhost:5000/api` in development, `https://<your-render-app>.onrender.com/api`
in production. All responses are JSON.

## Errors

Every error has the same shape and an HTTP status that matches the cause:

```json
{ "error": "unsupported_file_type", "message": "Only PDF and DOCX files are supported." }
```

| Status | `error` | When |
|---|---|---|
| 400 | `missing_file` | No multipart field `file`, or no file selected |
| 400 | `empty_file` | The file has 0 bytes |
| 400 | `missing_role`, `unknown_role`, `invalid_mode` | Bad analysis query parameters |
| 404 | `resume_not_found`, `not_found` | Unknown resume id or route |
| 413 | `file_too_large` | File over 5 MB (`MAX_FILE_SIZE_MB`) |
| 415 | `unsupported_file_type` | Extension is not `.pdf` or `.docx` |
| 415 | `content_mismatch` | Content is not a real PDF/DOCX (magic bytes) |
| 422 | `unreadable_file` | Corrupted, password-protected, or over 10 pages |
| 500 | `internal_error` | Unexpected server error (details are logged, not returned) |

## `GET /api/health`

```json
{ "status": "ok" }
```

## `POST /api/resumes`

Upload and parse a resume. Multipart form with one field, `file` (PDF or DOCX, up to 5 MB).

```bash
curl -F "file=@resume.pdf" http://localhost:5000/api/resumes
```

`201 Created`

```json
{
  "resume_id": 1,
  "filename": "resume.docx",
  "parse_quality": {
    "score": 70, "level": "fair", "ats_risk": true,
    "issues": [{ "code": "too_short", "severity": "high",
                 "message": "Very little text was extracted; the resume looks incomplete.",
                 "evidence": "53 words extracted (minimum 75)." }],
    "metrics": { "word_count": 53, "page_count": null, "sections_found": 4,
                 "multi_column_pages": [], "table_count": 0, "image_count": 0,
                 "extractor": "python-docx", "...": "..." }
  },
  "sections_detected": ["contact", "summary", "education", "skills", "projects"]
}
```

Scanned (image-only) PDFs are accepted with a `non_extractable` issue, so the dashboard can explain
the problem instead of rejecting the upload.

## `GET /api/resumes/{id}`

The stored parse result: `resume_id, filename, file_type, created_at, text, sections` (in document
order), `sections_detected, contact, parse_quality, stats`.

```json
"contact": { "name": "Sneha Patil", "name_source": "heuristic", "email": "sneha.patil@example.com",
             "phone": "+91 97000 33445", "linkedin": null, "github": null }
```

## `GET /api/roles`

```json
{ "roles": [
  { "id": "data_analyst", "name": "Data Analyst", "description": "...",
    "must_have": [{ "label": "SQL", "weight": 3.0,
                    "alternatives": ["SQL", "MySQL", "PostgreSQL", "SQL Server", "SQLite", "BigQuery"] }],
    "nice_to_have": ["Pandas", "NumPy", "A/B testing", "..."] }
] }
```

Role ids: `data_analyst`, `web_developer`, `ai_ml_engineer`, `cloud_engineer`, `full_stack_developer`.

## `GET /api/resumes/{id}/analysis?role={role_id}&mode={rules|ai}`

`role` is required; `mode` defaults to `rules`.

| Field | Content |
|---|---|
| `resume_id`, `filename`, `role {id, name}`, `mode` | Request context |
| `score` | `{total, max, band, parameters}`; each parameter is `{label, score, max, evidence[]}` and each evidence item is `{id, label, points, max, status, detail}` |
| `ats` | `{ats_score, keyword_score, must_have_coverage, nice_to_have_coverage, tfidf {similarity, score}, format_penalty {points, parse_quality_score, issues, detail}, matched[], missing_must_have[], missing_nice_to_have[], ignored[], detected_skills[]}` |
| `feedback` | `{suggestions[], total, shown, by_priority {high, medium, low}}` |
| `parse_quality`, `contact`, `sections_detected` | From the parser |
| `ai_available`, `ai_unavailable_reason`, `generated_feedback`, `retrieved_context` | Only when `mode=ai` |

A score check:

```json
{ "id": "contact.linkedin", "label": "LinkedIn profile", "points": 0, "max": 2,
  "status": "fail", "detail": "Not found" }
```

A suggestion:

```json
{ "rule_id": "K04", "title": "Missing must-have skill: Data cleaning", "category": "skills",
  "priority": "high",
  "suggestion": "Data Analyst roles expect Data cleaning. If you have used Data cleaning or Pandas, add it to your skills and show it in a project. If not, a small project using it closes this gap.",
  "estimated_impact": { "points": 4.3, "target": "ats" },
  "evidence": ["Not found anywhere in the resume (accepted: Data cleaning, Pandas)", "Requirement weight: 1"] }
```

### AI mode (illustrative values)

```json
"ai_available": true,
"ai_unavailable_reason": null,
"generated_feedback": {
  "bullet_rewrites": [{ "original": "Analyzed sales data in Excel and created charts.",
                        "rewritten": "Analyzed sales data in Excel and built charts that [result].",
                        "chunk_ids": ["bp-005", "jd-da-005"] }],
  "skill_gaps": [{ "skill": "Data cleaning", "explanation": "...", "chunk_ids": ["jd-da-002"] }],
  "summary": { "text": "...", "chunk_ids": ["bp-007"] },
  "citations": ["bp-005", "bp-007", "jd-da-002", "jd-da-005"],
  "dropped_items": 0, "provider": "gemini", "model": "gemini-2.5-flash"
},
"retrieved_context": [{ "id": "jd-da-002", "title": "Data analyst: required skills",
                        "source": "self-authored", "score": 0.5, "text": "...", "...": "..." }]
```

Without a key, or on any provider failure:

```json
"ai_available": false,
"ai_unavailable_reason": "No GEMINI_API_KEY configured",
"generated_feedback": null,
"retrieved_context": [ "... still returned ..." ]
```
