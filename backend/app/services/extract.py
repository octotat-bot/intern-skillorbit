"""Low-level text extraction from PDF and DOCX bytes.

PDFs are read with pdfplumber, which exposes word positions used to detect
two-column layouts. If pdfplumber fails or finds no text, PyMuPDF is used as a
fallback. DOCX files are read with python-docx in document order, including
table cells and page headers.
"""

from __future__ import annotations

import io
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from statistics import median
from typing import Any

import docx
import pdfplumber
import pymupdf
from docx.table import Table

from app import config

logger = logging.getLogger(__name__)

Word = dict[str, Any]  # pdfplumber word: {"text", "x0", "x1", "top", ...}


class ParseError(Exception):
    """The file cannot be read: corrupted, encrypted, empty, or too long."""


@dataclass
class ExtractionResult:
    """Raw text plus the layout signals needed for parse-quality checks."""

    text: str
    extractor: str
    page_count: int | None = None          # None for DOCX (no fixed pagination)
    image_count: int = 0
    table_count: int = 0
    links: list[str] = field(default_factory=list)
    multi_column_pages: list[int] = field(default_factory=list)


def extract(file_bytes: bytes, file_type: str) -> ExtractionResult:
    """Extract text from a PDF or DOCX file.

    Raises:
        ParseError: If the file is unreadable or the type is unsupported.
    """
    if file_type == "pdf":
        return extract_pdf(file_bytes)
    if file_type == "docx":
        return extract_docx(file_bytes)
    raise ParseError(f"Unsupported file type: {file_type}")


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def extract_pdf(file_bytes: bytes) -> ExtractionResult:
    """Extract a PDF with pdfplumber, falling back to PyMuPDF.

    The fallback is used when pdfplumber raises or returns no text, so a
    scanned PDF still reports its image count from PyMuPDF.
    """
    with _open_validated_pdf(file_bytes) as document:
        try:
            result = _extract_with_pdfplumber(file_bytes)
        except Exception as exc:  # pdfplumber raises many unrelated types
            logger.warning("pdfplumber failed, falling back to PyMuPDF: %s", exc)
            return _extract_with_pymupdf(document)
        if result.text.strip():
            return result
        return _extract_with_pymupdf(document)


def _open_validated_pdf(file_bytes: bytes) -> pymupdf.Document:
    """Open a PDF with PyMuPDF and reject unreadable, locked or oversized files."""
    try:
        document = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise ParseError("The PDF is corrupted or unreadable.") from exc
    if document.needs_pass:
        document.close()
        raise ParseError("The PDF is password-protected. Upload an unlocked copy.")
    if document.page_count == 0:
        document.close()
        raise ParseError("The PDF has no readable pages.")
    if document.page_count > config.MAX_PDF_PAGES:
        pages = document.page_count
        document.close()
        raise ParseError(
            f"The PDF has {pages} pages; resumes longer than "
            f"{config.MAX_PDF_PAGES} pages are not accepted."
        )
    return document


def _extract_with_pdfplumber(file_bytes: bytes) -> ExtractionResult:
    """Read every page with pdfplumber, splitting two-column pages by column."""
    texts: list[str] = []
    result = ExtractionResult(text="", extractor="pdfplumber")
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        result.page_count = len(pdf.pages)
        for number, page in enumerate(pdf.pages, start=1):
            words = page.extract_words()
            gutter = detect_column_gutter(words)
            if gutter is None:
                texts.append(page.extract_text() or "")
            else:
                result.multi_column_pages.append(number)
                texts.append(split_columns_text(group_lines(words), gutter))
            result.links.extend(link["uri"] for link in page.hyperlinks if link.get("uri"))
            result.image_count += len(page.images)
            result.table_count += len(page.find_tables())
    result.text = "\n".join(texts)
    return result


def _extract_with_pymupdf(document: pymupdf.Document) -> ExtractionResult:
    """Read every page with PyMuPDF.

    No column or table analysis: the fallback only runs when pdfplumber could
    not read the file, and its job is to recover text and count images.
    """
    result = ExtractionResult(text="", extractor="pymupdf", page_count=document.page_count)
    texts: list[str] = []
    for page in document:
        texts.append(page.get_text("text"))
        result.links.extend(link["uri"] for link in page.get_links() if link.get("uri"))
        result.image_count += len(page.get_images(full=True))
    result.text = "\n".join(texts)
    return result


# ---------------------------------------------------------------------------
# Two-column layout analysis (pure functions over pdfplumber words)
# ---------------------------------------------------------------------------
def group_lines(words: list[Word]) -> list[list[Word]]:
    """Group words into visual lines by vertical position, each sorted left to right."""
    lines: list[list[Word]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(word["top"] - lines[-1][0]["top"]) <= config.LINE_TOP_TOLERANCE_PT:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def widest_gap_start(line: list[Word]) -> float | None:
    """Return the x0 of the word after the line's widest gap, if wide enough."""
    best_gap, start = 0.0, None
    for left, right in zip(line, line[1:]):
        gap = right["x0"] - left["x1"]
        if gap > best_gap:
            best_gap, start = gap, right["x0"]
    return start if best_gap >= config.MULTI_COLUMN_MIN_GAP_PT else None


def detect_column_gutter(words: list[Word]) -> float | None:
    """Detect a two-column page and return the x position separating the columns.

    A page is two-column when many lines contain a wide gap and the text after
    those gaps starts at the same x position. Right-aligned dates in a
    single-column resume produce wide gaps on only a few lines, so they fail the
    line-ratio test.
    """
    lines = group_lines(words)
    if len(lines) < config.MULTI_COLUMN_MIN_LINES:
        return None
    starts = [s for s in map(widest_gap_start, lines) if s is not None]
    if len(starts) / len(lines) < config.MULTI_COLUMN_LINE_RATIO:
        return None
    anchor = median(starts)
    aligned = [s for s in starts if abs(s - anchor) <= config.MULTI_COLUMN_ALIGN_TOLERANCE_PT]
    if len(aligned) / len(starts) < config.MULTI_COLUMN_ALIGN_SHARE:
        return None
    return min(aligned) - 1.0


def _line_side(line: list[Word], gutter: float) -> str:
    """Classify a line as 'left', 'right', 'split' (both columns) or 'full' width."""
    if all(w["x0"] >= gutter for w in line):
        return "right"
    if all(w["x1"] <= gutter for w in line):
        return "left"
    start = widest_gap_start(line)
    if start is not None and gutter <= start <= gutter + 2 * config.MULTI_COLUMN_ALIGN_TOLERANCE_PT:
        return "split"
    return "full"


def _join(words: list[Word]) -> str:
    """Join words into one line of text."""
    return " ".join(w["text"] for w in words)


def split_columns_text(lines: list[list[Word]], gutter: float) -> str:
    """Rebuild page text column by column: full-width header, then left, then right."""
    header: list[str] = []
    left: list[str] = []
    right: list[str] = []
    for line in lines:
        side = _line_side(line, gutter)
        if side == "full":
            (header if not (left or right) else left).append(_join(line))
        elif side == "left":
            left.append(_join(line))
        elif side == "right":
            right.append(_join(line))
        else:
            left.append(_join([w for w in line if w["x0"] < gutter]))
            right.append(_join([w for w in line if w["x0"] >= gutter]))
    return "\n".join(header + left + right)


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------
def extract_docx(file_bytes: bytes) -> ExtractionResult:
    """Extract DOCX text in document order, including headers and table cells."""
    try:
        document = docx.Document(io.BytesIO(file_bytes))
    except Exception as exc:  # zipfile, lxml and KeyError variants
        raise ParseError("The DOCX file is corrupted or unreadable.") from exc

    lines = _docx_header_lines(document) + list(_docx_body_lines(document))
    links = [
        rel.target_ref
        for rel in document.part.rels.values()
        if rel.reltype.endswith("/hyperlink")
    ]
    return ExtractionResult(
        text="\n".join(lines),
        extractor="python-docx",
        image_count=len(document.inline_shapes),
        table_count=len(document.tables),
        links=links,
    )


def _docx_header_lines(document: Any) -> list[str]:
    """Text from page headers, where templates often put contact details."""
    lines: list[str] = []
    for section in document.sections:
        if section.header.is_linked_to_previous:
            continue
        lines.extend(p.text for p in section.header.paragraphs if p.text.strip())
    return lines


def _docx_body_lines(document: Any) -> Iterator[str]:
    """Yield paragraph text and table-cell text in reading order."""
    for block in document.iter_inner_content():
        if isinstance(block, Table):
            yield from _docx_table_lines(block)
        else:
            yield block.text


def _docx_table_lines(table: Table) -> Iterator[str]:
    """Yield each distinct cell's text once (merged cells repeat in python-docx)."""
    seen: set[int] = set()
    for row in table.rows:
        for cell in row.cells:
            if id(cell._tc) in seen:
                continue
            seen.add(id(cell._tc))
            yield from (p.text for p in cell.paragraphs)
