"""Central configuration for the Resume Analyzer.

Every tunable number — score weights, thresholds, limits, word lists — lives
here. Service modules import from this file and never hard-code magic numbers.
Values that may differ per environment are read from ``.env`` via python-dotenv.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
APP_DIR = Path(__file__).resolve().parent                  # backend/app/
DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "instance/resumes.db")
DATA_DIR = APP_DIR / "data"
ROLES_FILE = DATA_DIR / "roles.json"
KB_DIR = DATA_DIR / "kb"

# ---------------------------------------------------------------------------
# Upload constraints
# ---------------------------------------------------------------------------
MAX_FILE_SIZE_BYTES: int = int(os.getenv("MAX_FILE_SIZE_MB", "5")) * 1024 * 1024
# Flask rejects whole requests above this; the slack covers multipart framing so
# a file of exactly MAX_FILE_SIZE_BYTES is still accepted and checked precisely.
MULTIPART_OVERHEAD_BYTES: int = 64 * 1024
MAX_REQUEST_BYTES: int = MAX_FILE_SIZE_BYTES + MULTIPART_OVERHEAD_BYTES
ALLOWED_EXTENSIONS: set[str] = {"pdf", "docx"}
PDF_SIGNATURE_SEARCH_BYTES: int = 1024   # "%PDF" must appear within this prefix
MAX_PDF_PAGES: int = 10                  # longer documents are rejected as non-resumes

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 100)
# ---------------------------------------------------------------------------
SCORE_WEIGHTS: dict[str, int] = {
    "contact": 10,
    "structure": 20,
    "skills": 20,
    "projects": 20,
    "education": 10,
    "quality": 20,
}
assert sum(SCORE_WEIGHTS.values()) == 100, "Score weights must sum to 100"

# Total-score bands, highest first: (minimum score, label).
SCORE_BANDS: list[tuple[int, str]] = [(85, "Excellent"), (70, "Good"), (50, "Fair"), (0, "Needs work")]
SCORE_DECIMALS: int = 1   # parameter scores are rounded to this many decimals

# ---- Contact (10) -----------------------------------------------------------
CONTACT_EMAIL_POINTS: int = 3
CONTACT_PHONE_POINTS: int = 3
CONTACT_LINKEDIN_POINTS: int = 2
CONTACT_GITHUB_POINTS: int = 2

# ---- Structure (20) ---------------------------------------------------------
REQUIRED_SECTIONS: list[str] = ["education", "skills", "projects", "experience"]
CORE_SECTIONS: list[str] = ["education", "skills", "experience", "projects"]
SUPPORTING_SECTIONS: list[str] = ["certifications", "achievements"]
SECTION_PRESENT_POINTS: int = 4      # per required section (4 x 4 = 16)
SECTION_ORDER_POINTS: dict[str, int] = {
    "contact_first": 2,              # contact block before any heading
    "summary_before_core": 1,        # summary, if present, precedes core sections
    "core_before_supporting": 1,     # certifications/achievements come after core sections
}
MIN_CORE_SECTIONS_FOR_ORDER: int = 2  # fewer core sections -> order cannot be judged

# ---- Skills (20) ------------------------------------------------------------
MIN_SKILLS_COUNT: int = 5
MAX_SKILLS_COUNT: int = 30
SKILL_ITEM_MAX_CHARS: int = 40       # longer fragments are sentences, not skills
SKILLS_MIN_CATEGORIES: int = 2       # "Languages: ..." style labelled lines
SKILLS_SECTION_EXISTS_POINTS: int = 5
SKILLS_CATEGORIZED_POINTS: int = 5
SKILLS_COUNT_POINTS: int = 10

# ---- Projects (20) ----------------------------------------------------------
IDEAL_PROJECT_COUNT_MIN: int = 3
IDEAL_PROJECT_COUNT_MAX: int = 5
DESCRIPTION_MIN_WORDS: int = 12      # lines this long are descriptions, not titles
ENTRY_NAME_MAX_WORDS: int = 6        # untitled entries are named by their first words
PROJECT_COUNT_POINTS: int = 6
PROJECT_TECH_NAMED_POINTS: int = 5
PROJECT_ACTION_VERB_POINTS: int = 5
PROJECT_QUANTIFIED_POINTS: int = 4

# ---- Education (10) ---------------------------------------------------------
EDUCATION_DEGREE_POINTS: int = 4
EDUCATION_INSTITUTION_POINTS: int = 3
EDUCATION_YEAR_POINTS: int = 3
# Degree names matched case-insensitively as whole words (dots and spaces optional).
DEGREE_TERMS: list[str] = [
    "btech", "b tech", "mtech", "m tech", "bsc", "b sc", "msc", "m sc", "bca", "mca",
    "bba", "mba", "bcom", "b com", "phd", "ph d", "bachelor", "bachelors", "master",
    "masters", "diploma", "associate degree", "doctorate", "beng", "meng",
]
# Short degree abbreviations matched case-sensitively, to avoid words like "be"/"me".
DEGREE_ABBREVIATIONS: list[str] = ["B.E.", "B.E", "BE", "M.E.", "M.E", "B.S.", "BS", "M.S.", "MS", "B.A.", "BA", "M.A.", "MA"]
INSTITUTION_KEYWORDS: list[str] = [
    "university", "institute", "college", "school", "academy", "polytechnic",
    "iit", "nit", "iiit", "bits", "vidyalaya", "vidyapeeth", "vidyapith",
]

# ---- Quality / completeness (20) -------------------------------------------
MIN_RESUME_WORDS: int = 150
MAX_RESUME_WORDS: int = 1500
QUALITY_LENGTH_POINTS: int = 5
QUALITY_VERB_STRENGTH_POINTS: int = 5
QUALITY_NO_FIRST_PERSON_POINTS: int = 4
QUALITY_NO_FILLER_POINTS: int = 3
QUALITY_BULLET_CONSISTENCY_POINTS: int = 2
QUALITY_DATE_CONSISTENCY_POINTS: int = 1
# "Absence" checks (no pronouns, no filler, consistent bullets/dates) prove little
# on a near-empty resume, so their points scale with content up to MIN_RESUME_WORDS.
SCALE_ABSENCE_CHECKS_BY_LENGTH: bool = True
FIRST_PERSON_PARTIAL_MAX: int = 2    # 1-2 pronouns -> half points; more -> zero
FILLER_PARTIAL_MAX: int = 1          # 1 filler phrase -> half points; more -> zero

_PARAMETER_POINTS: dict[str, int] = {
    "contact": CONTACT_EMAIL_POINTS + CONTACT_PHONE_POINTS + CONTACT_LINKEDIN_POINTS + CONTACT_GITHUB_POINTS,
    "structure": SECTION_PRESENT_POINTS * len(REQUIRED_SECTIONS) + sum(SECTION_ORDER_POINTS.values()),
    "skills": SKILLS_SECTION_EXISTS_POINTS + SKILLS_CATEGORIZED_POINTS + SKILLS_COUNT_POINTS,
    "projects": PROJECT_COUNT_POINTS + PROJECT_TECH_NAMED_POINTS + PROJECT_ACTION_VERB_POINTS + PROJECT_QUANTIFIED_POINTS,
    "education": EDUCATION_DEGREE_POINTS + EDUCATION_INSTITUTION_POINTS + EDUCATION_YEAR_POINTS,
    "quality": QUALITY_LENGTH_POINTS + QUALITY_VERB_STRENGTH_POINTS + QUALITY_NO_FIRST_PERSON_POINTS
    + QUALITY_NO_FILLER_POINTS + QUALITY_BULLET_CONSISTENCY_POINTS + QUALITY_DATE_CONSISTENCY_POINTS,
}
assert _PARAMETER_POINTS == SCORE_WEIGHTS, f"Check points must match weights: {_PARAMETER_POINTS}"

# ---------------------------------------------------------------------------
# Word lists used by scorer / feedback
# ---------------------------------------------------------------------------
# Verbs are base forms; inflections (-s, -ed, -ing, ...) are generated in code.
STRONG_ACTION_VERBS: list[str] = [
    "develop", "implement", "design", "build", "engineer", "optimize", "automate",
    "deploy", "integrate", "architect", "lead", "manage", "create", "establish",
    "launch", "improve", "reduce", "increase", "streamline", "deliver", "analyze",
    "configure", "migrate", "refactor", "scale", "spearhead", "orchestrate", "mentor",
    "collaborate", "resolve", "train", "forecast", "visualize", "cut", "boost",
    "accelerate", "achieve", "conduct", "publish", "win", "secure", "debug", "test",
    "model", "program", "coordinate", "organize", "present", "research",
]
WEAK_VERBS: list[str] = [
    "do", "make", "work", "help", "use", "be", "have", "get", "go", "try",
    "assist", "participate", "handle", "learn", "want",
]
# Verbs that are also common nouns ("Engineer at X", "Design Intern"): only
# their past-tense and -ing forms count, never the bare or plural form.
NOUN_LIKE_VERBS: list[str] = [
    "engineer", "architect", "lead", "model", "program", "mentor", "test", "design",
    "train", "forecast", "secure", "scale", "cut", "conduct", "present", "research",
]
WEAK_PHRASES: list[str] = ["responsible for", "involved in", "duties included", "tasked with"]
IRREGULAR_VERB_FORMS: dict[str, list[str]] = {
    "build": ["built"], "lead": ["led"], "make": ["made"], "do": ["did", "done", "does"],
    "win": ["won"], "cut": ["cut"], "have": ["had", "has"], "get": ["got"],
    "go": ["went", "gone"], "be": ["was", "were", "is", "am", "are"], "learn": ["learnt"],
    "forecast": ["forecast", "forecasted"],
}
FIRST_PERSON_PRONOUNS: list[str] = ["I", "me", "my", "myself", "mine"]
FILLER_PHRASES: list[str] = [
    "hard worker", "hard working", "hardworking", "team player", "fast learner",
    "quick learner", "self-motivated", "detail-oriented", "results-driven", "go-getter",
    "synergy", "think outside the box", "passionate about", "guru", "ninja",
    "rockstar", "references available", "dynamic individual", "good company",
]

# ---------------------------------------------------------------------------
# ATS scoring (a transparent heuristic, not a vendor-verified metric)
# ---------------------------------------------------------------------------
ATS_MUST_HAVE_WEIGHT: float = 0.7
ATS_NICE_TO_HAVE_WEIGHT: float = 0.3
ATS_TFIDF_WEIGHT: float = 0.2          # share of the blend taken by TF-IDF similarity
ATS_TFIDF_SIMILARITY_CEILING: float = 0.35  # raw cosine at/above this maps to 100
ATS_FORMAT_PENALTY_MAX: int = 15       # points deducted at parse-quality score 0
ATS_IGNORED_SECTIONS: list[str] = ["other"]  # hobbies, interests, ...
# A keyword after one of these cues on the same line is an intention, not a skill.
IRRELEVANT_CONTEXT_CUES: list[str] = [
    "want to learn", "wants to learn", "plan to learn", "planning to learn",
    "hope to learn", "eager to learn", "interested in learning", "would like to learn",
    "looking to learn", "aspire to learn", "no experience with", "not familiar with",
]

# ---------------------------------------------------------------------------
# NLP
# ---------------------------------------------------------------------------
SPACY_MODEL: str = "en_core_web_sm"

# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------
# Canonical section -> heading aliases (matched case-insensitively after
# punctuation is stripped and "&" becomes "and"). "other" captures headings we
# recognise but do not score, so their content does not leak into a real section.
SECTION_HEADINGS: dict[str, list[str]] = {
    "contact": ["contact", "contact information", "contact details", "personal details",
                "personal information"],
    "summary": ["summary", "professional summary", "career summary", "objective",
                "career objective", "profile", "professional profile", "about me"],
    "education": ["education", "academic background", "academics", "academic details",
                  "educational qualifications", "academic qualifications",
                  "educational background", "qualifications"],
    "skills": ["skills", "technical skills", "key skills", "core competencies",
               "skills and tools", "technologies", "tech stack", "technical proficiency",
               "skills and technologies", "skill set", "skillset"],
    "projects": ["projects", "academic projects", "personal projects", "key projects",
                 "project work", "project experience", "major projects"],
    "experience": ["experience", "work experience", "professional experience",
                   "internships", "internship", "internship experience",
                   "employment history", "work history", "relevant experience"],
    "certifications": ["certifications", "certification", "certificates",
                       "licenses and certifications", "courses and certifications",
                       "certifications and courses", "courses"],
    "achievements": ["achievements", "awards", "honors", "honours", "accomplishments",
                     "awards and achievements", "achievements and awards"],
    "other": ["hobbies", "interests", "hobbies and interests", "languages",
              "extracurricular activities", "extra curricular activities",
              "positions of responsibility", "volunteering", "volunteer experience",
              "references", "declaration", "publications"],
}
# Keyword stems that mark an unrecognised ALL-CAPS or colon-terminated line as a
# heading (e.g. "TECHNICAL SKILLS & TOOLS"). Checked left to right.
SECTION_KEYWORDS: dict[str, str] = {
    "skill": "skills", "educat": "education", "academic": "education",
    "project": "projects", "experience": "experience", "internship": "experience",
    "certific": "certifications", "achievement": "achievements", "award": "achievements",
    "objective": "summary", "summary": "summary",
}
MAX_HEADING_WORDS: int = 5          # longer lines are never treated as headings
MAX_KEYWORD_HEADING_WORDS: int = 4  # stricter cap for keyword-only matches

# ---------------------------------------------------------------------------
# Contact extraction
# ---------------------------------------------------------------------------
NAME_SCAN_LINES: int = 5            # name is guessed from the first N header lines
NAME_MIN_WORDS: int = 2
NAME_MAX_WORDS: int = 4
PHONE_MIN_DIGITS: int = 10
PHONE_MAX_DIGITS: int = 13

# ---------------------------------------------------------------------------
# Layout analysis (PDF multi-column detection)
# ---------------------------------------------------------------------------
LINE_TOP_TOLERANCE_PT: float = 3.0       # words within this vertical distance share a line
MULTI_COLUMN_MIN_GAP_PT: float = 40.0    # horizontal gap that can separate two columns
MULTI_COLUMN_MIN_LINES: int = 8          # pages with fewer lines are not analysed
MULTI_COLUMN_LINE_RATIO: float = 0.3     # share of lines that must contain such a gap
MULTI_COLUMN_ALIGN_TOLERANCE_PT: float = 12.0  # right-column starts must align within this
MULTI_COLUMN_ALIGN_SHARE: float = 0.6    # share of gap lines that must align to one gutter

# ---------------------------------------------------------------------------
# Parse-quality assessment
# ---------------------------------------------------------------------------
MIN_TEXT_LENGTH: int = 100               # chars; below this the file is non-extractable
PARSE_MIN_WORDS: int = 75                # fewer words -> "too short" warning
PARSE_MAX_WORDS: int = 2000
PARSE_MAX_PAGES: int = 3
MIN_SECTIONS_FOR_GOOD_PARSE: int = 3     # scored sections (excludes contact/other)
SCRAMBLE_MIN_LINES: int = 15             # fragmentation checks need enough lines
SCRAMBLE_SHORT_LINE_THRESHOLD: int = 15  # chars; a "very short" line
SCRAMBLE_SHORT_LINE_RATIO: float = 0.5
SCRAMBLE_LOWERCASE_START_RATIO: float = 0.3  # lines starting lowercase = broken sentences
# Each issue deducts its penalty from 100. Severity drives UI emphasis.
PARSE_ISSUES: dict[str, dict[str, int | str]] = {
    "non_extractable": {"penalty": 80, "severity": "high"},
    "multi_column": {"penalty": 25, "severity": "high"},
    "too_short": {"penalty": 30, "severity": "high"},
    "few_sections": {"penalty": 20, "severity": "medium"},
    "fragmented_text": {"penalty": 20, "severity": "medium"},
    "tables": {"penalty": 20, "severity": "medium"},
    "too_long": {"penalty": 10, "severity": "low"},
    "images": {"penalty": 5, "severity": "low"},
}
PARSE_QUALITY_LEVELS: dict[str, int] = {"good": 85, "fair": 60}  # else "poor"

# ---------------------------------------------------------------------------
# Feedback rule engine
# ---------------------------------------------------------------------------
FEEDBACK_MAX_SUGGESTIONS: int = 25        # cap on returned suggestions (total is still reported)
PRIORITY_ORDER: dict[str, int] = {"high": 0, "medium": 1, "low": 2}
MAX_EVIDENCE_ITEMS: int = 5               # evidence lines shown per suggestion
MAX_NICE_TO_HAVE_LISTED: int = 6          # nice-to-have skills named in one suggestion
BULLET_MAX_WORDS: int = 30                # longer bullets are hard to scan
REPEATED_VERB_MIN_COUNT: int = 3          # same opening verb this often -> vary wording
TFIDF_LOW_SIMILARITY: float = 0.12        # below this, wording is far from the role
GPA_PATTERN: str = r"\b(?:c?gpa|cpi|sgpa|percentage)\b|\d{1,2}(?:\.\d+)?\s?%|\d(?:\.\d+)?\s?/\s?(?:10|4)(?:\.0)?\b"
# Parse-quality issues that get their own suggestion (others are covered by
# content rules, e.g. too_short -> Q01).
FORMAT_ISSUE_PRIORITY: dict[str, str] = {
    "non_extractable": "high", "multi_column": "high", "tables": "medium",
    "fragmented_text": "medium", "images": "low",
}

# ---------------------------------------------------------------------------
# PDF report
# ---------------------------------------------------------------------------
REPORT_PAGE_SIZE: str = "a4"
REPORT_MARGIN_PT: int = 48               # page margin in points (1/72 inch)
REPORT_FOOTER_OFFSET_PT: int = 24        # footer baseline distance from the page bottom
REPORT_MAX_SUGGESTIONS: int = 25         # suggestions printed (all returned ones, by default)

# ---------------------------------------------------------------------------
# RAG / AI layer (optional at runtime)
# ---------------------------------------------------------------------------
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")        # "gemini" | "none"
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "tfidf")   # "tfidf" | "gemini"
GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
AI_TIMEOUT_SECONDS: int = int(os.getenv("AI_TIMEOUT_SECONDS", "25"))
AI_TEMPERATURE: float = 0.2
AI_CACHE_SIZE: int = 64                  # cached generations per process
KB_INDEX_PATH = KB_DIR / "index.npz"     # shipped vector store (TF-IDF)
RAG_TOP_K: int = 6                       # chunks given to the LLM
RAG_ROLE_CHUNKS: int = 2                 # of which at least this many are role-specific
RAG_SECTION_BOOST: float = 0.15          # added to similarity when a chunk covers a weak area
RAG_WEAK_PARAMETER_RATIO: float = 0.75   # parameter below this share of its max is "weak"
RAG_MAX_BULLETS: int = 4                 # weak bullets sent for rewriting
RAG_MAX_SKILL_GAPS: int = 4              # missing skills sent for explanation
