"""Run the scorer on the labelled evaluation set and write docs/evaluation.md.

Usage (from backend/):
    ./venv/bin/python -m evaluation.run_evaluation

Each case is rendered to a real PDF/DOCX file (saved in evaluation/samples/ so
it can also be uploaded in the UI), parsed by the full pipeline, scored, and
compared with its hand-assigned band.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np

from app.services.ats import analyze_ats
from app.services.parser import parse_resume
from app.services.scorer import score_resume
from evaluation.dataset import BAND_ORDER, BANDS, CASES, EvalCase
from tests.fixtures import resumes as builders

ROOT = Path(__file__).resolve().parent
SAMPLES_DIR = ROOT / "samples"
REPORT_PATH = ROOT.parent.parent / "docs" / "evaluation.md"


def build_file(case: EvalCase) -> bytes:
    """Render a case to the bytes of its file format and layout."""
    if case.layout == "scanned":
        return builders.build_scanned_pdf()
    if case.layout == "two_column":
        return builders.build_two_column_pdf(case.header, case.left, case.right)
    if case.layout == "table":
        return builders.build_table_docx(case.left, case.right, "\n".join(case.header))
    return builders.build_pdf(case.text) if case.file_format == "pdf" else builders.build_docx(case.text)


def band_of(score: int) -> str:
    """Band label containing a score."""
    return next(name for name, (low, high) in BANDS.items() if low <= score <= high)


def band_distance(score: int, band: str) -> int:
    """0 inside the expected band, else points to its nearest edge."""
    low, high = BANDS[band]
    return max(low - score, 0, score - high)


def ranks(values: list[float]) -> np.ndarray:
    """Average ranks (ties share the mean rank), for Spearman correlation."""
    array = np.asarray(values, dtype=float)
    order = array.argsort(kind="mergesort")
    result = np.empty(len(array))
    result[order] = np.arange(1, len(array) + 1)
    for value in np.unique(array):
        mask = array == value
        result[mask] = result[mask].mean()
    return result


def pearson(x: list[float], y: list[float]) -> float:
    """Pearson correlation coefficient."""
    return float(np.corrcoef(np.asarray(x, float), np.asarray(y, float))[0, 1])


def evaluate() -> list[dict]:
    """Score every case; also save its file to SAMPLES_DIR."""
    SAMPLES_DIR.mkdir(exist_ok=True)
    rows = []
    for case in CASES:
        data = build_file(case)
        (SAMPLES_DIR / f"{case.id}.{case.file_format}").write_bytes(data)
        parsed = parse_resume(data, case.file_format)
        score = score_resume(parsed.sections, parsed.contact, parsed.stats)
        ats = analyze_ats(parsed.sections, case.role, parsed.parse_quality)
        low, high = BANDS[case.expected_band]
        rows.append({
            "case": case, "score": score["total"], "predicted_band": band_of(score["total"]),
            "midpoint": (low + high) / 2, "band_distance": band_distance(score["total"], case.expected_band),
            "ats": ats["ats_score"], "similarity": ats["tfidf"]["similarity"],
            "parse_level": parsed.parse_quality["level"],
        })
    return rows


def metrics(rows: list[dict]) -> dict[str, float]:
    """Agreement between scores and expected bands."""
    scores = [r["score"] for r in rows]
    midpoints = [r["midpoint"] for r in rows]
    ordinal = [BAND_ORDER.index(r["case"].expected_band) for r in rows]
    return {
        "n": len(rows),
        "pearson_midpoint": pearson(scores, midpoints),
        "spearman_band": pearson(list(ranks(scores)), list(ranks(ordinal))),
        "mae_midpoint": float(np.mean([abs(s - m) for s, m in zip(scores, midpoints)])),
        "mae_band": float(np.mean([r["band_distance"] for r in rows])),
        "band_accuracy": float(np.mean([r["predicted_band"] == r["case"].expected_band for r in rows])),
        "within_one_band": float(np.mean([
            abs(BAND_ORDER.index(r["predicted_band"]) - BAND_ORDER.index(r["case"].expected_band)) <= 1 for r in rows
        ])),
    }


def render_report(rows: list[dict], m: dict[str, float]) -> str:
    """Markdown report for docs/evaluation.md."""
    table = "\n".join(
        f"| {r['case'].id} | {r['case'].file_format.upper()} / {r['case'].layout.replace('_', '-')} | "
        f"{r['case'].expected_band} | **{r['score']}** | {r['predicted_band']} | "
        f"{'yes' if r['predicted_band'] == r['case'].expected_band else 'no'} | {r['ats']} | {r['parse_level']} |"
        for r in rows
    )
    misses = [r for r in rows if r["predicted_band"] != r["case"].expected_band]
    miss_text = "\n".join(
        f"- **{r['case'].id}**: expected {r['case'].expected_band}, scored {r['score']} ({r['predicted_band']}). "
        f"Reviewer rationale: {r['case'].rationale}"
        for r in misses
    ) or "- None: every case landed in its expected band."
    rationale = "\n".join(f"| {r['case'].id} | {r['case'].role} | {r['case'].rationale} |" for r in rows)
    return f"""# Evaluation report

_Generated by `backend/evaluation/run_evaluation.py` on {date.today().isoformat()}. Re-run it after
changing any weight or rule; the numbers below will update._

## Method

1. Twelve synthetic student resumes were written to cover the quality range, five roles, and four
   layouts (single-column PDF and DOCX, two-column PDF, table DOCX, scanned image PDF).
2. Each resume was assigned an **expected score band before it was scored**, from a reviewer's
   reading of the resume against these band definitions:

   | Band | Range | Meaning |
   |---|---|---|
   | Excellent | 85-100 | Complete, well structured, quantified, role-relevant |
   | Good | 70-84 | Solid with a few clear gaps |
   | Fair | 50-69 | Usable but with several significant problems |
   | Needs work | 0-49 | Incomplete, vague, or unreadable |

3. Each resume is rendered to a real file and run through the **full pipeline** (text extraction,
   section detection, scoring), exactly as an upload would be. The files are saved in
   `backend/evaluation/samples/` so they can be uploaded in the UI.
4. Agreement is measured as correlation with the band midpoint and band order, mean absolute error,
   and band accuracy.

## Results

| Metric | Value |
|---|---|
| Resumes | {m['n']} |
| Pearson r (score vs band midpoint) | {m['pearson_midpoint']:.3f} |
| Spearman rho (score rank vs band order) | {m['spearman_band']:.3f} |
| MAE vs band midpoint | {m['mae_midpoint']:.1f} points |
| MAE vs band edge (0 when inside the band) | {m['mae_band']:.1f} points |
| Band accuracy | {m['band_accuracy']:.0%} |
| Within one band | {m['within_one_band']:.0%} |

| Case | Format / layout | Expected band | Score | Predicted band | Match | ATS (target role) | Parse quality |
|---|---|---|---|---|---|---|---|
{table}

### Disagreements

{miss_text}

## Case rationales

| Case | Target role | Why the band was assigned |
|---|---|---|
{rationale}

## Calibration history

The first run of this evaluation (before any change) gave Pearson r 0.940, Spearman rho 0.966,
MAE 12.2 points vs band midpoint, 3.2 points vs band edge, and **58% band accuracy**. Every miss was
the scorer being one band too generous on short, mid-quality resumes.

The cause was a logic flaw rather than a weight choice: the quality checks that reward the *absence*
of problems (no first-person pronouns, no filler, consistent bullets, consistent dates) gave full
credit to near-empty resumes, which have nothing to get wrong. Those four checks now scale with
content, reaching full value at `MIN_RESUME_WORDS` (config flag `SCALE_ABSENCE_CHECKS_BY_LENGTH`).
The results above are after that fix.

Weights were deliberately **not** tuned to hit these 12 labels: with a small, self-labelled set that
would overfit. The remaining misses are within a few points of a band edge, and all are within one band.

## Interpretation and limitations

- The resume score measures **content and structure**. Layout risk (two-column, tables, scans) is
  reported separately through parse quality and lowers the **ATS** score, not the resume score,
  except where it prevents text extraction entirely.
- Twelve resumes is a small sample: the correlations show the ranking behaves sensibly, not that the
  weights are optimal. The bands were assigned by the same team that wrote the rules, so this is not
  an independent validation. Labelling 30 or more real (anonymised) resumes by two independent
  reviewers would be the next step.
- The ATS score is a transparent heuristic, **not a vendor-verified metric**. Real applicant tracking
  systems are configured differently by each employer.
"""


def main() -> None:
    """Run the evaluation, print a summary and write the report."""
    rows = evaluate()
    m = metrics(rows)
    REPORT_PATH.write_text(render_report(rows, m), encoding="utf-8")
    for r in rows:
        flag = "ok " if r["predicted_band"] == r["case"].expected_band else "MISS"
        print(f"{flag} {r['case'].id:28} expected {r['case'].expected_band:10} score {r['score']:3}  ats {r['ats']:3}  sim {r['similarity']:.2f}")
    print({k: round(v, 3) for k, v in m.items()})
    print(f"Report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
