"""How a table is shown to a reader, and whether it needs a second look.

`display_table()` is the one place that decides what the table page draws: the layout re-read
from the PDF when table_context.json has one, otherwise the tidied extraction (tidy.py) with
wrapped labels joined. `load_tables` uses the same function to set `needs_review`, so the badge in
the browser always describes what a reader actually sees.
"""
import functools
import json
import re

from django.conf import settings

from .models import SECTIONS
from .tidy import tidy

CONTEXT_FILE = settings.BASE_DIR / "table_context.json"

CHAPTER_SECTIONS = {"E": "summary", "1": "volumes", "2": "demographics", "3": "correspondence",
                    "4": "transactions", "5": "advertising", "6": "periodicals", "7": "packages",
                    "A": "trends", "B": "methodology"}
SURVEY_FORM = "Survey form"


@functools.lru_cache(maxsize=1)
def _load_context(mtime):
    with open(CONTEXT_FILE, encoding="utf-8") as f:
        return json.load(f)


def table_context(source_id):
    """This table's entry in table_context.json (written by `manage.py extract_context`), or {}."""
    try:
        return _load_context(CONTEXT_FILE.stat().st_mtime).get(source_id, {})
    except FileNotFoundError:
        return {}


def chapter_of(table_number):
    match = re.match(r"(?:Table|Figure)\s+(?:([A-Z])\d*[.\-]|(\d+)\.)", table_number)  # A8-1, A-1, E.2, 7.4
    return (match.group(1) or match.group(2)) if match else None


# Reports whose chapters are numbered differently. Every report from FY2005 to FY2025 follows
# CHAPTER_SECTIONS (checked by voting on table-title keywords per chapter); FY2003 adds a mail-
# volume chapter, shifting the rest by one (read from its table titles).
REPORT_CHAPTERS = {
    2003: {"1": "volumes", "2": "volumes", "3": "demographics", "4": "correspondence", "5": "transactions",
           "6": "advertising", "7": "periodicals", "8": "packages", "9": "methodology"},
}


def section_of(table_number, title, year=None):
    """The report section a table belongs to, from its corrected number ("Table 7.4" -> packages)."""
    if title.startswith(SURVEY_FORM):
        return "survey_form"
    chapter = chapter_of(table_number)
    return REPORT_CHAPTERS.get(year, {}).get(chapter) or CHAPTER_SECTIONS.get(chapter, "other")


def join_wrapped_labels(tidied, joins):
    """Join a label printed on two lines back into one row (see pdftables.wrapped_labels)."""
    rows = tidied["rows"]
    for join in sorted(joins, key=lambda j: -j["row"]):
        i, k = join["row"], join["rows"]
        parts = rows[i:i + k + 1]
        if (len(parts) == k + 1 and not any(c.strip() for r in parts[1:] for c in r[1:])
                and " ".join(r[0] for r in parts).split() == join["label"].split()):
            rows[i:i + k + 1] = [[join["label"]] + rows[i][1:]]
            tidied["notes"].append(f"Joined a row label printed on two lines: “{join['label']}”.")
    return tidied


def rebuilt_display(structure):
    """A table re-read from its PDF page, in the shape the template draws (like tidy's output)."""
    headers = structure["headers"]
    groups, k = [], 0
    starts = {first: (label, last) for label, first, last in structure["groups"]}
    while structure["groups"] and k < len(headers):
        label, last = starts.get(k, ("", k))
        groups.append((label, last - k + 1))
        k = last + 1
    return {"headers": headers, "groups": groups or None, "rows": structure["rows"], "notes": [], "footnotes": []}


def cells(columns, data):
    """A stored row's cells in column order, as the raw table shows them ("—" when missing)."""
    out = []
    for column in columns:
        cell = data.get(column, {})
        out.append(cell.get("raw", "—") if isinstance(cell, dict) else ("—" if cell is None else cell))
    return out


def display_table(source_id, columns, rows, title):
    """(tidied, reread) for a table: what the page draws, and whether it came from the PDF re-read.

    `rows` are lists of cell strings in column order (see `cells`).
    """
    context = table_context(source_id)
    if context.get("structure"):
        return rebuilt_display(context["structure"]), True
    tidied = tidy([str(c) for c in columns], rows, title)
    return join_wrapped_labels(tidied, context.get("label_joins", [])), False


def review_reasons(ocr, table_number, headers):
    """Why a reader should check this table against the PDF before using it, or []."""
    reasons = []
    if ocr:
        reasons.append("Read by OCR from a scanned page; the values are unverified and often wrong.")
    if table_number.startswith("Figure"):
        reasons.append("Chart data, not a printed table: values were read off a chart and may be inaccurate.")
    if any(h.startswith("Column ") for h in headers):
        reasons.append("Some column names couldn't be recovered (shown as “Column N”).")
    return reasons
