"""Feedback rule engine.

Each rule is a small function registered with ``@rule``. It inspects a
:class:`FeedbackContext` (parsed resume + score + ATS result) and returns zero
or more :class:`Finding` objects. A finding carries the suggestion text, the
evidence that triggered it, and an estimated impact:

* ``target="score"``: points recoverable on the /100 score, computed from the
  exact scorer checks the rule relates to.
* ``target="ats"``: points the ATS score would gain if the gap were closed,
  computed from the ATS weights.
* ``target="readability"``: no direct score effect; improves human reading.

Output is sorted by priority, then impact, then rule id, so it is stable.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app import config
from app.services import resume_features as features
from app.services.roles import get_role, load_catalog
from app.services.skills import get_skill_matcher

_GPA_RE = re.compile(config.GPA_PATTERN, re.I)


@dataclass
class FeedbackContext:
    """Everything a rule may look at."""

    sections: dict[str, str]
    contact: dict[str, Any]
    stats: dict[str, Any]
    parse_quality: dict[str, Any]
    score: dict[str, Any]
    ats: dict[str, Any]

    def check(self, check_id: str) -> dict[str, Any]:
        """A scorer check by id, e.g. 'contact.email'."""
        parameter = self.score["parameters"][check_id.split(".")[0]]
        return next(c for c in parameter["evidence"] if c["id"] == check_id)

    def gap(self, *check_ids: str) -> float:
        """Points lost on the given scorer checks."""
        return round(sum(self.check(i)["max"] - self.check(i)["points"] for i in check_ids), 1)

    def has(self, section: str) -> bool:
        """True if the section exists with content."""
        return bool(self.sections.get(section, "").strip())


@dataclass
class Finding:
    """One triggered suggestion before rule metadata is attached."""

    suggestion: str
    evidence: list[str]
    impact: float = 0.0
    target: str = "score"   # "score" | "ats" | "readability"
    title: str | None = None   # overrides the rule title (e.g. per missing skill)


@dataclass(frozen=True)
class Rule:
    """Metadata for a registered rule."""

    id: str
    title: str
    category: str
    priority: str
    evaluate: Callable[[FeedbackContext], Finding | list[Finding] | None] = field(compare=False)


RULES: list[Rule] = []


def rule(rule_id: str, title: str, category: str, priority: str):
    """Register a rule function."""
    def register(func: Callable[[FeedbackContext], Finding | list[Finding] | None]):
        """Add the decorated function to RULES."""
        RULES.append(Rule(rule_id, title, category, priority, func))
        return func
    return register


def _evidence(items: list[str]) -> list[str]:
    """Trim evidence to the configured number of items, noting the remainder."""
    shown = items[: config.MAX_EVIDENCE_ITEMS]
    rest = len(items) - len(shown)
    return shown + ([f"... and {rest} more"] if rest > 0 else [])


def _detail(ctx: FeedbackContext, check_id: str) -> list[str]:
    """Evidence line taken from a scorer check."""
    check = ctx.check(check_id)
    return [f"{check['label']}: {check['detail']} ({check['points']}/{check['max']} pts)"]


def _fails(ctx: FeedbackContext, check_id: str) -> bool:


    """True if a scorer check did not earn full points."""
    return ctx.check(check_id)["status"] != "pass"


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------
@rule("C01", "Add an email address", "contact", "high")
def missing_email(ctx: FeedbackContext) -> Finding | None:
    """C01: fires when no email address was found."""
    if ctx.contact.get("email"):
        return None
    return Finding("Put a professional email address in the header so recruiters can reach you.",
                   _detail(ctx, "contact.email"), ctx.gap("contact.email"))


@rule("C02", "Add a phone number", "contact", "high")
def missing_phone(ctx: FeedbackContext) -> Finding | None:
    """C02: fires when no phone number was found."""
    if ctx.contact.get("phone"):
        return None
    return Finding("Add a phone number with country code (e.g. +91) in the header.",
                   _detail(ctx, "contact.phone"), ctx.gap("contact.phone"))


@rule("C03", "Add your LinkedIn profile", "contact", "medium")
def missing_linkedin(ctx: FeedbackContext) -> Finding | None:
    """C03: fires when no LinkedIn URL was found."""
    if ctx.contact.get("linkedin"):
        return None
    return Finding("Add your LinkedIn URL (linkedin.com/in/your-name). Recruiters check it to verify your profile.",
                   _detail(ctx, "contact.linkedin"), ctx.gap("contact.linkedin"))


@rule("C04", "Add your GitHub profile", "contact", "medium")
def missing_github(ctx: FeedbackContext) -> Finding | None:
    """C04: fires when no GitHub URL was found."""
    if ctx.contact.get("github"):
        return None
    return Finding("Add your GitHub URL so reviewers can see the code behind your projects.",
                   _detail(ctx, "contact.github"), ctx.gap("contact.github"))


@rule("C05", "Put your name on the first line", "contact", "medium")
def missing_name(ctx: FeedbackContext) -> Finding | None:
    """C05: fires when no name could be identified at the top."""
    if ctx.contact.get("name"):
        return None
    top = features.lines_of(ctx.sections.get("contact", ""))[:2]
    return Finding("Start the resume with your full name on its own line, so ATS and recruiters capture it.",
                   [f"Top lines: {' / '.join(top)}" if top else "No header lines before the first section"],
                   0.0, "readability")


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------
def _missing_section(ctx: FeedbackContext, name: str, advice: str) -> Finding | None:
    """Finding for an absent required section, or None if present."""
    if ctx.has(name):
        return None
    return Finding(advice, _detail(ctx, f"structure.{name}"), ctx.gap(f"structure.{name}"))


@rule("S01", "Add an Experience / Internships section", "structure", "high")
def missing_experience(ctx: FeedbackContext) -> Finding | None:
    """S01: fires when there is no experience/internship section."""
    return _missing_section(ctx, "experience",
        "Add an 'Experience' or 'Internships' section. Internships, freelance work, research "
        "assistantships and teaching-assistant roles all count.")


@rule("S02", "Add a Projects section", "structure", "high")
def missing_projects(ctx: FeedbackContext) -> Finding | None:
    """S02: fires when there is no projects section."""
    return _missing_section(ctx, "projects",
        "Add a 'Projects' section with 2-4 projects, each naming the tech stack and the result.")


@rule("S03", "Add a Skills section", "structure", "high")
def missing_skills(ctx: FeedbackContext) -> Finding | None:
    """S03: fires when there is no skills section."""
    return _missing_section(ctx, "skills",
        "Add a 'Skills' section. ATS match keywords there first.")


@rule("S04", "Add an Education section", "structure", "high")
def missing_education(ctx: FeedbackContext) -> Finding | None:
    """S04: fires when there is no education section."""
    return _missing_section(ctx, "education",
        "Add an 'Education' section with degree, institution and graduation year.")


@rule("S05", "Add a short professional summary", "structure", "low")
def missing_summary(ctx: FeedbackContext) -> Finding | None:
    """S05: fires when there is no summary or objective."""
    if ctx.has("summary"):
        return None
    role = ctx.ats["role_name"]
    return Finding(f"Add a 2-3 line summary at the top aimed at {role} roles: your focus, strongest skills "
                   "and one achievement.", ["No summary or objective section found"], 0.0, "readability")


@rule("S06", "Reorder your sections", "structure", "medium")
def section_order(ctx: FeedbackContext) -> Finding | None:
    """S06: fires when any section-order rule failed (and order could be judged)."""
    ids = ["structure.order.contact_first", "structure.order.summary_before_core",
           "structure.order.core_before_supporting"]
    failing = [i for i in ids if _fails(ctx, i)]
    judged = ctx.check(ids[0])["detail"].startswith("Order:")
    if not failing or not judged:
        return None
    return Finding("Use a conventional order: name and contact, summary, education, skills, experience, "
                   "projects, then certifications and achievements.",
                   [line for i in failing for line in _detail(ctx, i)], ctx.gap(*failing))


@rule("S07", "Add certifications", "structure", "low")
def missing_certifications(ctx: FeedbackContext) -> Finding | None:
    """S07: fires when there is no certifications section."""
    if ctx.has("certifications"):
        return None
    return Finding(f"Add relevant certifications (free ones count) that support the {ctx.ats['role_name']} role.",
                   ["No certifications section found"], 0.0, "readability")


@rule("S08", "Add achievements", "structure", "low")
def missing_achievements(ctx: FeedbackContext) -> Finding | None:
    """S08: fires when there is no achievements section."""
    if ctx.has("achievements"):
        return None
    return Finding("Add an 'Achievements' section: hackathons, rankings, scholarships, publications or "
                   "open-source contributions.", ["No achievements section found"], 0.0, "readability")


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------
@rule("K01", "Group your skills into categories", "skills", "medium")
def skills_not_categorized(ctx: FeedbackContext) -> Finding | None:
    """K01: fires when skills are not grouped into labelled categories."""
    if not ctx.has("skills") or not _fails(ctx, "skills.categorized"):
        return None
    return Finding("Group skills into labelled lines, e.g. 'Languages: Python, SQL' and 'Tools: Git, Docker'.",
                   _detail(ctx, "skills.categorized"), ctx.gap("skills.categorized"))


@rule("K02", "List more skills", "skills", "high")
def skills_sparse(ctx: FeedbackContext) -> Finding | None:
    """K02: fires when fewer than MIN_SKILLS_COUNT skills are listed."""
    count = len(features.skill_items(ctx.sections.get("skills", "")))
    if not ctx.has("skills") or count >= config.MIN_SKILLS_COUNT:
        return None
    return Finding(f"Your skills section is sparse. List at least {config.MIN_SKILLS_COUNT} concrete tools, "
                   "languages and frameworks you have actually used.",
                   _detail(ctx, "skills.count"), ctx.gap("skills.count"))


@rule("K03", "Trim your skills list", "skills", "medium")
def skills_overstuffed(ctx: FeedbackContext) -> Finding | None:
    """K03: fires when more than MAX_SKILLS_COUNT skills are listed."""
    count = len(features.skill_items(ctx.sections.get("skills", "")))
    if count <= config.MAX_SKILLS_COUNT:
        return None
    return Finding(f"Keep the skills list under {config.MAX_SKILLS_COUNT} items. Remove ones you could "
                   "not discuss in an interview.", _detail(ctx, "skills.count"), ctx.gap("skills.count"))


def _must_have_ats_gain(ctx: FeedbackContext, weight: float) -> float:
    """ATS points gained by covering one must-have requirement of ``weight``."""
    total = sum(req.weight for req in get_role(ctx.ats["role_id"]).must_have)
    share = config.ATS_MUST_HAVE_WEIGHT / (config.ATS_MUST_HAVE_WEIGHT + config.ATS_NICE_TO_HAVE_WEIGHT)
    return round(100 * share * (1 - config.ATS_TFIDF_WEIGHT) * weight / total, 1)


@rule("K04", "Missing must-have skill", "skills", "high")
def missing_must_have(ctx: FeedbackContext) -> list[Finding]:
    """K04: one finding per must-have requirement not found for the role."""
    role = ctx.ats["role_name"]
    return [
        Finding(f"{role} roles expect {item['label']}. If you have used "
                f"{' or '.join(item['alternatives'][:3])}, add it to your skills and show it in a project. "
                "If not, a small project using it closes this gap.",
                [f"Not found anywhere in the resume (accepted: {', '.join(item['alternatives'])})",
                 f"Requirement weight: {item['weight']:g}"],
                _must_have_ats_gain(ctx, item["weight"]), "ats",
                title=f"Missing must-have skill: {item['label']}")
        for item in ctx.ats["missing_must_have"]
    ]


@rule("K05", "Consider adding nice-to-have skills", "skills", "low")
def missing_nice_to_have(ctx: FeedbackContext) -> Finding | None:
    """K05: fires when any nice-to-have skill for the role is missing."""
    missing = [item["label"] for item in ctx.ats["missing_nice_to_have"]]
    if not missing:
        return None
    total = len(get_role(ctx.ats["role_id"]).nice_to_have)
    share = config.ATS_NICE_TO_HAVE_WEIGHT / (config.ATS_MUST_HAVE_WEIGHT + config.ATS_NICE_TO_HAVE_WEIGHT)
    per_skill = 100 * share * (1 - config.ATS_TFIDF_WEIGHT) / total
    listed = missing[: config.MAX_NICE_TO_HAVE_LISTED]
    return Finding(f"Bonus skills for {ctx.ats['role_name']} you could add if you know them: {', '.join(listed)}.",
                   [f"{len(missing)} of {total} nice-to-have skills not found"],
                   round(per_skill * len(listed), 1), "ats")


@rule("K06", "Show your listed skills in action", "skills", "medium")
def skills_not_demonstrated(ctx: FeedbackContext) -> Finding | None:
    """K06: fires when 3+ listed skills never appear in projects/experience."""
    matcher = get_skill_matcher()
    listed = matcher.find_skills(ctx.sections.get("skills", ""))
    used = matcher.find_skills("\n".join(ctx.sections.get(s, "") for s in ("projects", "experience")))
    unused = sorted(load_catalog().display(s) for s in listed - used)
    if not listed or not (ctx.has("projects") or ctx.has("experience")) or len(unused) < 3:
        return None
    return Finding("Several skills appear only in the skills list. Mention them in project or experience "
                   "bullets so reviewers see where you used them.",
                   _evidence([f"Listed but never used: {s}" for s in unused]), 0.0, "readability")


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
def _projects(ctx: FeedbackContext) -> list[features.Entry]:
    """Project entries of the resume."""
    return features.split_entries(ctx.sections.get("projects", ""))


@rule("P01", "Add more projects", "projects", "high")
def too_few_projects(ctx: FeedbackContext) -> Finding | None:
    """P01: fires when fewer than IDEAL_PROJECT_COUNT_MIN projects are listed."""
    count = len(_projects(ctx))
    if not ctx.has("projects") or count >= config.IDEAL_PROJECT_COUNT_MIN:
        return None
    return Finding(f"Show {config.IDEAL_PROJECT_COUNT_MIN}-{config.IDEAL_PROJECT_COUNT_MAX} projects. "
                   f"Pick ones relevant to {ctx.ats['role_name']} and give each a title line.",
                   _detail(ctx, "projects.count"), ctx.gap("projects.count"))


@rule("P02", "Quantify your project results", "projects", "high")
def projects_without_metrics(ctx: FeedbackContext) -> Finding | None:
    """P02: fires when a project has no quantified result."""
    unquantified = [p.name for p in _projects(ctx)
                    if not any(features.find_metrics(line) for line in p.lines)]
    if not unquantified:
        return None
    return Finding("Add a measurable result to each project: accuracy, users, speed-up, data size or time "
                   "saved (e.g. 'reduced load time by 40%').",
                   _evidence([f"No numbers in: {name}" for name in unquantified]), ctx.gap("projects.quantified"))


@rule("P03", "Name the tech stack in each project", "projects", "medium")
def projects_without_tech(ctx: FeedbackContext) -> Finding | None:
    """P03: fires when a project names no recognised technology."""
    matcher = get_skill_matcher()
    missing = [p.name for p in _projects(ctx) if not matcher.find_skills(p.text)]
    if not missing:
        return None
    return Finding("Write the technologies on each project's title line, e.g. 'Churn Predictor | Python, scikit-learn'.",
                   _evidence([f"No technology named in: {name}" for name in missing]), ctx.gap("projects.tech"))


@rule("P04", "Start project bullets with action verbs", "projects", "medium")
def project_bullets_without_verbs(ctx: FeedbackContext) -> Finding | None:
    """P04: fires when project bullets do not open with a strong verb."""
    lines = [line for p in _projects(ctx) for line in p.lines]
    weak = [line for line in lines if not ((v := features.leading_verb(line)) and v.strength == "strong")]
    if not weak:
        return None
    return Finding("Begin each project bullet with a strong past-tense verb such as Built, Designed, "
                   "Automated or Deployed.", _evidence([f"'{line}'" for line in weak]), ctx.gap("projects.action_verbs"))


@rule("P05", "Describe each project", "projects", "medium")
def projects_without_description(ctx: FeedbackContext) -> Finding | None:
    """P05: fires when a project has a title but no bullets."""
    bare = [p.title for p in _projects(ctx) if p.title and not p.lines]
    if not bare:
        return None
    return Finding("Add 1-3 bullets under each project: what you built, how, and the result.",
                   _evidence([f"Title only: {title}" for title in bare]),
                   ctx.gap("projects.action_verbs", "projects.quantified"))


@rule("P06", "Focus on your best projects", "projects", "low")
def too_many_projects(ctx: FeedbackContext) -> Finding | None:
    """P06: fires when more than IDEAL_PROJECT_COUNT_MAX projects are listed."""
    count = len(_projects(ctx))
    if count <= config.IDEAL_PROJECT_COUNT_MAX:
        return None
    return Finding(f"Keep your strongest {config.IDEAL_PROJECT_COUNT_MAX} projects and cut the rest, so each "
                   "gets room for results.", [f"{count} projects listed"], 0.0, "readability")


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------
@rule("X01", "Quantify your experience", "experience", "medium")
def experience_without_metrics(ctx: FeedbackContext) -> Finding | None:
    """X01: fires when no experience bullet contains a number."""
    lines = features.description_lines(ctx.sections.get("experience", ""))
    if not lines or any(features.find_metrics(line) for line in lines):
        return None
    return Finding("Add numbers to internship bullets: volume handled, time saved, users affected or "
                   "accuracy improved.", _evidence([f"'{line}'" for line in lines]), 0.0, "readability")


@rule("X02", "Replace weak verbs in your experience", "experience", "medium")
def weak_verbs(ctx: FeedbackContext) -> Finding | None:
    """X02: fires when experience bullets open with weak verbs or phrases."""
    lines = features.description_lines(ctx.sections.get("experience", ""))
    weak = [line for line in lines if (v := features.leading_verb(line)) and v.strength == "weak"]
    if not weak:
        return None
    return Finding("Swap weak openers like 'helped', 'worked on' or 'responsible for' for verbs that show "
                   "ownership: Led, Built, Implemented, Reduced.",
                   _evidence([f"'{line}'" for line in weak]), ctx.gap("quality.verb_strength"))


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------
@rule("E01", "Complete your education details", "education", "medium")
def education_incomplete(ctx: FeedbackContext) -> Finding | None:
    """E01: fires when degree, institution or year is missing."""
    ids = ["education.degree", "education.institution", "education.year"]
    failing = [i for i in ids if _fails(ctx, i)]
    if not ctx.has("education") or not failing:
        return None
    return Finding("Each education entry needs the degree, the institution's full name and the graduation "
                   "(or expected) year.", [line for i in failing for line in _detail(ctx, i)], ctx.gap(*failing))


@rule("E02", "Add your CGPA", "education", "low")
def missing_gpa(ctx: FeedbackContext) -> Finding | None:
    """E02: fires when the education section has no CGPA/GPA/percentage."""
    text = ctx.sections.get("education", "")
    if not text.strip() or _GPA_RE.search(text):
        return None
    return Finding("Students are usually screened on grades. Add your CGPA or percentage if it is 7/10 "
                   "(or 70%) or higher.", ["No CGPA, GPA or percentage in the education section"], 0.0, "readability")


# ---------------------------------------------------------------------------
# Writing quality
# ---------------------------------------------------------------------------
@rule("Q01", "Add more content", "quality", "high")
def too_short(ctx: FeedbackContext) -> Finding | None:
    """Q01: fires when the resume is under MIN_RESUME_WORDS words."""
    words = ctx.stats.get("word_count", 0)
    if words >= config.MIN_RESUME_WORDS:
        return None
    return Finding(f"The resume is too short to show your ability. Aim for {config.MIN_RESUME_WORDS}-600 "
                   "words on one page with project and experience details.",
                   _detail(ctx, "quality.length"), ctx.gap("quality.length"))


@rule("Q02", "Shorten the resume", "quality", "medium")
def too_long(ctx: FeedbackContext) -> Finding | None:
    """Q02: fires when the resume exceeds the word or page limit."""
    words = ctx.stats.get("word_count", 0)
    pages = ctx.parse_quality.get("metrics", {}).get("page_count") or 0
    if words <= config.MAX_RESUME_WORDS and pages <= config.PARSE_MAX_PAGES:
        return None
    return Finding("Keep a student resume to one page (two at most). Cut older or less relevant items first.",
                   [f"{words} words, {pages or 'unknown'} page(s)"], ctx.gap("quality.length"))


@rule("Q03", "Remove first-person pronouns", "quality", "medium")
def first_person(ctx: FeedbackContext) -> Finding | None:
    """Q03: fires when first-person pronouns are used."""
    if not _fails(ctx, "quality.first_person"):
        return None
    return Finding("Drop 'I', 'my' and 'me'. Write 'Built a dashboard' instead of 'I built a dashboard'.",
                   _detail(ctx, "quality.first_person"), ctx.gap("quality.first_person"))


@rule("Q04", "Cut filler phrases", "quality", "medium")
def filler(ctx: FeedbackContext) -> Finding | None:
    """Q04: fires when cliché filler phrases are used."""
    if not _fails(ctx, "quality.filler"):
        return None
    return Finding("Replace clichés like 'hard worker' or 'team player' with evidence, e.g. 'Led a 4-person "
                   "team to ship X'.", _detail(ctx, "quality.filler"), ctx.gap("quality.filler"))


@rule("Q05", "Use one bullet style", "quality", "low")
def inconsistent_bullets(ctx: FeedbackContext) -> Finding | None:
    """Q05: fires when more than one bullet symbol is used."""
    if not _fails(ctx, "quality.bullet_consistency"):
        return None
    return Finding("Use a single bullet symbol throughout.", _detail(ctx, "quality.bullet_consistency"),
                   ctx.gap("quality.bullet_consistency"))


@rule("Q06", "Use one date format", "quality", "low")
def inconsistent_dates(ctx: FeedbackContext) -> Finding | None:
    """Q06: fires when more than one date format is used."""
    if not _fails(ctx, "quality.date_consistency"):
        return None
    return Finding("Write every date the same way, e.g. 'Jun 2024 - Aug 2024'.",
                   _detail(ctx, "quality.date_consistency"), ctx.gap("quality.date_consistency"))


@rule("Q07", "Shorten long bullets", "quality", "low")
def long_bullets(ctx: FeedbackContext) -> Finding | None:
    """Q07: fires when a bullet exceeds BULLET_MAX_WORDS words."""
    lines = [line for s in ("experience", "projects") for line in features.description_lines(ctx.sections.get(s, ""))]
    long = [line for line in lines if len(line.split()) > config.BULLET_MAX_WORDS]
    if not long:
        return None
    return Finding(f"Keep bullets under {config.BULLET_MAX_WORDS} words: one action, one method, one result.",
                   _evidence([f"{len(line.split())} words: '{' '.join(line.split()[:8])} ...'" for line in long]),
                   0.0, "readability")


@rule("Q08", "Vary your action verbs", "quality", "low")
def repeated_verbs(ctx: FeedbackContext) -> Finding | None:
    """Q08: fires when one opening verb starts REPEATED_VERB_MIN_COUNT+ bullets."""
    lines = [line for s in ("experience", "projects") for line in features.description_lines(ctx.sections.get(s, ""))]
    counts = Counter(v.word.lower() for line in lines if (v := features.leading_verb(line)))
    repeated = [f"'{verb}' opens {n} bullets" for verb, n in counts.most_common() if n >= config.REPEATED_VERB_MIN_COUNT]
    if not repeated:
        return None
    return Finding("Vary your opening verbs (Built, Designed, Automated, Optimized...) so bullets read distinctly.",
                   repeated, 0.0, "readability")


# ---------------------------------------------------------------------------
# ATS / formatting
# ---------------------------------------------------------------------------
_FORMAT_ADVICE: dict[str, str] = {
    "non_extractable": "The file has no selectable text (likely a scan or image export). Export the resume "
                       "from Word or Google Docs as a text-based PDF or DOCX.",
    "multi_column": "Switch to a single-column layout. Many ATS read straight across columns and mix up your content.",
    "tables": "Move content out of tables into plain paragraphs and bullets; some ATS skip table cells.",
    "fragmented_text": "Avoid text boxes and decorative layouts; the extracted text came out fragmented.",
    "images": "Keep information out of images, icons and charts. ATS cannot read them.",
}


@rule("A01", "Fix ATS formatting risk", "ats", "high")
def format_risks(ctx: FeedbackContext) -> list[Finding]:
    """A01: one finding per parse-quality formatting issue (scan, columns, tables...)."""
    penalty = ctx.ats["format_penalty"]["points"]
    issues = [i for i in ctx.parse_quality.get("issues", []) if i["code"] in config.FORMAT_ISSUE_PRIORITY]
    return [
        Finding(_FORMAT_ADVICE[issue["code"]], [issue["message"], issue["evidence"]],
                round(penalty * config.PARSE_ISSUES[issue["code"]]["penalty"]
                      / max(1, 100 - ctx.parse_quality.get("score", 100)), 1),
                "ats", title=f"ATS formatting risk: {issue['code'].replace('_', ' ')}")
        for issue in issues
    ]


@rule("A02", "Mirror the role's wording", "ats", "medium")
def low_similarity(ctx: FeedbackContext) -> Finding | None:
    """A02: fires when TF-IDF similarity to the role is below TFIDF_LOW_SIMILARITY."""
    tfidf = ctx.ats["tfidf"]
    if tfidf["similarity"] >= config.TFIDF_LOW_SIMILARITY:
        return None
    gain = round(config.ATS_TFIDF_WEIGHT * (100 - tfidf["score"]) / 2, 1)
    return Finding(f"Your wording is far from typical {ctx.ats['role_name']} job descriptions. Use the same "
                   "terms postings use (where true for you) in your summary and bullets.",
                   [f"Text similarity to the role: {tfidf['similarity']:.2f} (low below {config.TFIDF_LOW_SIMILARITY})"],
                   gain, "ats")


@rule("A03", "State skills you actually have", "ats", "low")
def intention_mentions(ctx: FeedbackContext) -> Finding | None:
    """A03: fires when skills were ignored as intentions or hobbies."""
    ignored = ctx.ats.get("ignored", [])
    if not ignored:
        return None
    return Finding("Skills mentioned as goals ('want to learn X') or only under hobbies are not counted. "
                   "List a skill only once you have used it, and show where.",
                   _evidence([f"'{i['surface']}' in {i['section']}: {i['reason']}" for i in ignored]), 0.0, "ats")


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
def _sort_key(item: dict[str, Any]) -> tuple:
    """Ordering: priority, then larger impact, then rule id and title."""
    return (config.PRIORITY_ORDER[item["priority"]], -item["estimated_impact"]["points"], item["rule_id"], item["title"])


def _to_item(rule_def: Rule, finding: Finding) -> dict[str, Any]:


    """Attach rule metadata to a finding."""
    return {
        "rule_id": rule_def.id,
        "title": finding.title or rule_def.title,
        "category": rule_def.category,
        "priority": rule_def.priority,
        "suggestion": finding.suggestion,
        "estimated_impact": {"points": finding.impact, "target": finding.target},
        "evidence": finding.evidence,
    }


def run_rules(ctx: FeedbackContext) -> list[dict[str, Any]]:
    """Evaluate all rules and return every triggered suggestion, sorted.

    When no text could be extracted, only the formatting rule runs: every
    content rule would fire and bury the one fix that matters.
    """
    unreadable = any(i["code"] == "non_extractable" for i in ctx.parse_quality.get("issues", []))
    active = [r for r in RULES if r.id == "A01"] if unreadable else RULES
    items: list[dict[str, Any]] = []
    for rule_def in active:
        result = rule_def.evaluate(ctx)
        findings = result if isinstance(result, list) else [result] if result else []
        items.extend(_to_item(rule_def, finding) for finding in findings)
    return sorted(items, key=_sort_key)


def generate_feedback(
    sections: dict[str, str], contact: dict[str, Any], stats: dict[str, Any],
    parse_quality: dict[str, Any], score: dict[str, Any], ats: dict[str, Any],
) -> dict[str, Any]:
    """Return prioritised, evidence-backed suggestions.

    Returns:
        ``{suggestions[], total, shown, by_priority}``; ``suggestions`` is capped
        at FEEDBACK_MAX_SUGGESTIONS, ``total`` counts all triggered findings.
    """
    ctx = FeedbackContext(sections, contact, stats, parse_quality, score, ats)
    items = run_rules(ctx)
    shown = items[: config.FEEDBACK_MAX_SUGGESTIONS]
    by_priority = Counter(item["priority"] for item in items)
    return {
        "suggestions": shown,
        "total": len(items),
        "shown": len(shown),
        "by_priority": {p: by_priority.get(p, 0) for p in config.PRIORITY_ORDER},
    }


def rule_catalogue() -> list[dict[str, str]]:
    """Metadata for every registered rule (used for documentation)."""
    return [{"id": r.id, "title": r.title, "category": r.category, "priority": r.priority} for r in RULES]
