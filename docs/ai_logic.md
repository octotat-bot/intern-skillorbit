# AI logic: how the analysis works

The core of the system is **deterministic and rule-based**: the same file and role always produce the
same score, ATS result and suggestions, and every number carries the evidence that produced it. An
optional retrieval-augmented generation (RAG) layer adds AI-written rewrites on top, and can never
change the score.

| Stage | Module | Technique |
|---|---|---|
| Text extraction | `services/extract.py` | pdfplumber (word positions), PyMuPDF fallback, python-docx |
| Parsing | `services/parser.py` | Unicode normalisation, heading detection, regex + spaCy NER |
| Scoring | `services/scorer.py` | Weighted rubric of 27 explainable checks |
| Skill detection | `services/skills.py` | spaCy PhraseMatcher (surface + noun-lemma) and boundary regexes |
| ATS match | `services/ats.py` | Weighted keyword coverage + TF-IDF cosine similarity (NLTK Porter stemming) |
| Feedback | `services/feedback.py` | 40-rule engine with priority and impact estimation |
| AI layer (optional) | `services/kb.py`, `rag.py`, `llm.py` | TF-IDF retrieval over a 52-chunk knowledge base + Gemini, citation-validated |

All weights, thresholds and word lists live in `backend/app/config.py`.

## 1. Extraction and parse quality

- **PDF**: pdfplumber reads words with coordinates. If many lines contain a wide horizontal gap whose
  right-hand text starts at the same x position, the page is **two-column**; it is re-read column by
  column (header first, then left, then right) so sections are not interleaved. Right-aligned dates
  in a single-column resume fail the "many lines" test, so they are not mistaken for columns. If
  pdfplumber fails or finds no text, PyMuPDF takes over.
- **DOCX**: paragraphs and table cells in document order, plus page headers (where templates often
  hide contact details) and hyperlink targets.
- **Rejected**: corrupted, password-protected, empty, or over-10-page files (HTTP 422).
- **Parse quality** starts at 100 and subtracts a penalty per detected issue: non-extractable
  (scanned) text, multi-column layout, tables, fragmented text (many very short lines or lines
  starting mid-sentence), too few recognised sections, too short or too long, images. Level is
  good (>= 85), fair (>= 60) or poor. Anything below good is flagged as an **ATS formatting risk**.

## 2. Section detection and contact extraction

After normalisation (NFKC, ligatures, invisible and private-use characters removed, quotes
straightened, bullets stripped and counted), each line is tested as a heading in three ways:

1. **Inline heading** such as `Skills: Python, SQL`, only for aliases that contain a section
   keyword, so sub-labels like `Languages: Python` stay inside the skills section.
2. **Exact alias** in any case (70+ aliases, e.g. "Work Experience", "Academic Projects").
3. **Keyword heading**: an ALL-CAPS or colon-terminated short line containing a section stem, e.g.
   "TECHNICAL SKILLS & PROFICIENCIES". Title Case is excluded so a project called "Skill Matcher App"
   is not taken for a heading.

Text before the first heading is the contact block. Email, phone, LinkedIn and GitHub use regexes
(phone candidates made only of years, like "2019 - 2023 2020", are rejected). The name is taken from
spaCy `PERSON` entities on the top lines, falling back to a "2-4 capitalised words" heuristic; the
response says which method found it.

## 3. Resume score (/100)

| Parameter | Max | Checks |
|---|---|---|
| Contact | 10 | email 3, phone 3, LinkedIn 2, GitHub 2 |
| Structure | 20 | education, skills, projects, experience present with content (4 each); order rules 4 |
| Skills | 20 | section present 5; grouped into >= 2 labelled categories 5; 5-30 skills listed 10 (scaled) |
| Projects | 20 | count vs ideal 3 6; share naming a technology 5; share of bullets opening with a strong verb 5; share with a metric 4 |
| Education | 10 | degree 4, institution 3 (keyword or spaCy ORG), year 3 |
| Quality | 20 | length 150-1500 words 5; strong vs weak verbs 5; no first person 4; no filler 3; one bullet style 2; one date format 1 |

Notes on the logic:

- **Projects and experience** are split into entries: a title line ("Churn Model | Python") starts an
  entry, and description lines (open with a verb, end with a period, are long, or are "Label: value")
  attach to it.
- **Verb strength** uses base-form verb lists with generated inflections (develop, developed,
  developing, optimise...). Verbs that are also nouns (engineer, design, lead) only count in
  past-tense or -ing form, so "Engineer at Google" is not an action verb.
- **Metrics** are numbers that are not bare years and not glued to letters ("EC2" is not a metric).
- **Absence checks scale with content.** "No pronouns", "no filler" and the consistency checks are
  scaled by `words / 150`, because a near-empty resume has nothing to get wrong. This change came
  out of the evaluation (see `evaluation.md`).
- Every check returns `{id, label, points, max, status, detail}`; the dashboard's score breakdown
  shows all of them.

## 4. ATS keyword match

Each role in `data/roles.json` has weighted **must-have** requirements (each satisfied by any of
several equivalent skills, e.g. SQL / PostgreSQL / BigQuery), unweighted **nice-to-have** skills,
and aliases (`js` -> JavaScript, `ml` -> machine learning).

Skills are detected by three strategies, unioned:

1. spaCy `PhraseMatcher` on lower-cased text (names and aliases);
2. a second `PhraseMatcher` over **noun lemmas**, so "dashboards" and "REST APIs" match while verbs
   keep their form ("excelled" never becomes Excel);
3. exact-case boundary regexes for ambiguous short names (R, C, Go, Excel) that reject "R&D", "C#",
   "C++" and "Go-to".

Mentions under hobbies, or after intention cues such as "want to learn", are **ignored** and
reported as such.

```
keyword   = 100 * (0.7 * must_have_coverage + 0.3 * nice_to_have_coverage)
tfidf     = 100 * min(1, cosine(resume, role_document) / 0.35)
blended   = 0.8 * keyword + 0.2 * tfidf
penalty   = 15 * (100 - parse_quality) / 100
ats_score = clamp(round(blended - penalty), 0, 100)
```

The TF-IDF model is fitted on the five role documents (description + skills), with NLTK's Porter
stemmer and unigrams + bigrams. **The ATS score is a transparent heuristic, not a vendor-verified
metric**: real applicant tracking systems are configured differently by each employer.

## 5. Feedback rule engine

Each rule is a function registered with `@rule(id, title, category, priority)` that inspects the
parsed resume, score and ATS result and returns findings with **evidence** and an **estimated
impact**:

- `score` impact = exact points lost on the related scorer checks;
- `ats` impact = ATS points the gap is worth under the formula above;
- `readability` = no direct score effect.

Suggestions are sorted by priority (high, medium, low), then impact, then rule id, and capped at 25
(the total is still reported). When no text could be extracted, only the formatting rule runs, so
the one fix that matters is not buried.

| ID | Rule | Category | Priority |
|---|---|---|---|
| C01 | Add an email address | contact | high |
| C02 | Add a phone number | contact | high |
| C03 | Add your LinkedIn profile | contact | medium |
| C04 | Add your GitHub profile | contact | medium |
| C05 | Put your name on the first line | contact | medium |
| S01 | Add an Experience / Internships section | structure | high |
| S02 | Add a Projects section | structure | high |
| S03 | Add a Skills section | structure | high |
| S04 | Add an Education section | structure | high |
| S05 | Add a short professional summary | structure | low |
| S06 | Reorder your sections | structure | medium |
| S07 | Add certifications | structure | low |
| S08 | Add achievements | structure | low |
| K01 | Group your skills into categories | skills | medium |
| K02 | List more skills | skills | high |
| K03 | Trim your skills list | skills | medium |
| K04 | Missing must-have skill | skills | high |
| K05 | Consider adding nice-to-have skills | skills | low |
| K06 | Show your listed skills in action | skills | medium |
| P01 | Add more projects | projects | high |
| P02 | Quantify your project results | projects | high |
| P03 | Name the tech stack in each project | projects | medium |
| P04 | Start project bullets with action verbs | projects | medium |
| P05 | Describe each project | projects | medium |
| P06 | Focus on your best projects | projects | low |
| X01 | Quantify your experience | experience | medium |
| X02 | Replace weak verbs in your experience | experience | medium |
| E01 | Complete your education details | education | medium |
| E02 | Add your CGPA | education | low |
| Q01 | Add more content | quality | high |
| Q02 | Shorten the resume | quality | medium |
| Q03 | Remove first-person pronouns | quality | medium |
| Q04 | Cut filler phrases | quality | medium |
| Q05 | Use one bullet style | quality | low |
| Q06 | Use one date format | quality | low |
| Q07 | Shorten long bullets | quality | low |
| Q08 | Vary your action verbs | quality | low |
| A01 | Fix ATS formatting risk | ats | high |
| A02 | Mirror the role's wording | ats | medium |
| A03 | State skills you actually have | ats | low |

## 6. Optional AI layer (RAG)

1. **Knowledge base**: 52 self-authored chunks in `backend/app/data/kb/` (19 resume guidelines, 8
   ATS guidelines, 25 role snippets, 5 per role). Each chunk declares the roles and resume areas it
   applies to.
2. **Embedding and store**: TF-IDF vectors (local, no key) stored in a 11 KB NumPy file shipped in
   the repo, verified by a fingerprint of the chunks; a Gemini embedder can be selected with
   `EMBEDDING_PROVIDER=gemini`.
3. **Retrieval**: the query is built from the role, missing must-haves, top suggestion titles and
   weak areas (parameters under 75% of their max). Chunks for other roles are excluded, chunks
   covering weak areas get a +0.15 boost, and at least 2 role-specific chunks are always included
   (top 6 in total).
4. **Generation**: Gemini (`gemini-2.5-flash`, temperature 0.2, JSON output, 25 s timeout) rewrites
   up to 4 weak bullets and explains up to 4 missing skills **using only the retrieved chunks** and
   must cite chunk ids. The provider sits behind an `LLMProvider` interface, so it can be swapped.
5. **Validation**: an item is kept only if every cited id was retrieved, its "original" bullet is one
   that was sent, and a rewrite adds no number absent from the original (unknown metrics must be
   placeholders like `[X%]`). Dropped items are counted and shown.
6. **Fallback**: no key, timeout, quota error or invalid output returns `ai_available: false` with
   the reason; the retrieved guidance is still returned, and the rule-based analysis is untouched.
   Responses are cached per prompt to avoid repeated paid calls.
