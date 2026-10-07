"""Unit tests for two-column detection over synthetic pdfplumber words."""

from __future__ import annotations

from app.services.extract import detect_column_gutter, group_lines, split_columns_text


def _word(text: str, x0: float, top: float, width: float | None = None) -> dict:
    return {"text": text, "x0": x0, "x1": x0 + (width or 6 * len(text)), "top": top}


def _two_column_words(rows: int = 12) -> list[dict]:
    words = []
    for i in range(rows):
        top = 100 + i * 14
        words += [_word(f"left{i}", 50, top), _word("text", 90, top)]
        words += [_word(f"right{i}", 300, top), _word("more", 345, top)]
    return words


def test_detects_gutter_between_aligned_columns() -> None:
    gutter = detect_column_gutter(_two_column_words())
    assert gutter is not None and 120 < gutter < 300


def test_single_column_with_right_aligned_dates_is_not_multi_column() -> None:
    words = []
    for i in range(20):
        top = 100 + i * 14
        words += [_word("Built", 50, top), _word("a", 85, top), _word("thing", 95, top)]
        if i % 6 == 0:  # an occasional right-aligned date line
            words.append(_word("2023", 500, top))
    assert detect_column_gutter(words) is None


def test_too_few_lines_are_not_analysed() -> None:
    assert detect_column_gutter(_two_column_words(rows=3)) is None


def test_no_words() -> None:
    assert detect_column_gutter([]) is None


def test_group_lines_merges_words_within_tolerance() -> None:
    lines = group_lines([_word("b", 60, 100.5), _word("a", 50, 100), _word("c", 50, 120)])
    assert [[w["text"] for w in line] for line in lines] == [["a", "b"], ["c"]]


def test_split_keeps_full_width_header_and_orders_left_then_right() -> None:
    header = [_word("jane@x.com", 50, 80), _word("|", 120, 80), _word("+91", 130, 80),
              _word("98765", 160, 80), _word("43210", 200, 80), _word("|", 240, 80),
              _word("github.com/jane", 250, 80)]
    words = header + _two_column_words()
    gutter = detect_column_gutter(words)
    text = split_columns_text(group_lines(words), gutter)
    lines = text.split("\n")
    assert lines[0] == "jane@x.com | +91 98765 43210 | github.com/jane"
    assert lines.index("left11 text") < lines.index("right0 more")
