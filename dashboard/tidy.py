"""Tidy an extracted table's columns for display. The stored data is never changed.

The PDF extraction often gets column names wrong in a few predictable ways:
  * names sit one column to the right of their numbers, with empty spacer columns in between
    (and a group heading such as "Educational Attainment of Head of Household" takes a slot);
  * the real header is the first data row (e.g. the years in Appendix A tables), and
    `columns[0]` holds the table caption instead;
  * the header row is repeated as the first data row;
  * a column has no name in the PDF either (a single value column under the table's units).
`tidy()` undoes these and reports what it changed, so the page can say so.
"""
import re

UNNAMED = re.compile(r"col_\d+")
YEARISH = re.compile(r"(FY\s*)?(19|20)\d\d([-–]\s*((19|20)?\d\d)?)?")
PLACEHOLDER = {"n/a", "na", "—", "–", "-", "*", "--"}
CAPTION = re.compile(r"Table\s+[A-Z]?\d*[.\-]?\d")
UNITS = re.compile(r"\(([^()]+)\)\s*$")
GROUP_ONLY = re.compile(r"(Age|Educational Attainment|Education) of (the )?(Head of Household|Householder)", re.I)
SUMMARY = re.compile(r"(Average|Total|All\b|Overall)", re.I)
FOOTNOTE = re.compile(r"(Sources?|Notes?)\s*:|\*\s*\w|\d\s+[A-Z][a-z]")


def _name(column):
    column = re.sub(r" \(\d+\)$", "", column or "")  # load_tables' de-duplication suffix
    return "" if UNNAMED.fullmatch(column) else " ".join(column.split())


def _is_header_row(cells):
    """Text or years only (no data values), and not just placeholders."""
    rest = [c.strip() for c in cells[1:] if c.strip()]
    if not rest or all(c.lower() in PLACEHOLDER for c in rest):
        return False
    return all(not re.search(r"\d", c) or YEARISH.fullmatch(c) for c in rest)


def tidy(columns, rows, title=""):
    """Return {"headers", "groups", "rows", "notes"} for display.

    `columns`: Table.columns; `rows`: lists of raw cell strings in the same order.
    `groups`: None, or [(label, colspan), ...] for a heading row above `headers`.
    """
    n = len(columns)
    header = [_name(c) for c in columns]
    body = [list(r) + [""] * (n - len(r)) for r in rows]
    notes = []

    named = [h for h in header if h]
    if len(named) == 1 and CAPTION.match(named[0]):
        header = [""] * n  # Appendix A tables: the only "name" is the table caption

    # 0. An entirely empty first column: the row labels are in the next column.
    if n > 1 and not header[0] and not any(r[0].strip() for r in body):
        header, body, n = header[1:], [r[1:] for r in body], n - 1
        notes.append("Hid an empty first column.")

    # "Source: ..." / "Note: ..." lines extracted as rows become footnotes under the table.
    footnotes = []
    for r in list(body):
        filled = [c.strip() for c in r if c.strip()]
        if len(filled) == 1 and FOOTNOTE.match(filled[0]):
            footnotes.append(filled[0])
            body.remove(r)

    # 1. Header rows that ended up in the body: exact repeats, then text/year rows.
    promoted = 0
    while body and promoted < 3:
        first = [c.strip() for c in body[0]]
        if [" ".join(c.split()) for c in first] == header and any(header):
            body.pop(0)
            notes.append("Removed a repeated header row.")
            continue
        if not _is_header_row(first):
            break
        body.pop(0)
        if first[0] and header[0]:
            # The label cell is a section heading ("Financial") sharing the row with column
            # names: keep it in the data as its own row.
            body.insert(0, [first[0]] + [""] * (n - 1))
            first[0] = ""
        header = [" ".join(f"{h} {c}".split()) if c and c not in h else h for h, c in zip(header, first)]
        promoted += 1
    if promoted:
        notes.append(f"Moved {promoted} header row{'s' if promoted > 1 else ''} out of the data.")

    has_val = [any(r[i].strip() for r in body) for i in range(n)]

    # 2. Names one column right of their numbers: join numbers-only column i with the
    #    names-only column i+1. If column i had its own name, that was a group heading.
    keep, group_of, merged = list(range(n)), {}, []
    i = 1
    while i < n - 1:
        if has_val[i] and not has_val[i + 1] and header[i + 1]:
            if header[i]:
                group_of[i] = header[i]
            header[i] = header[i + 1]
            keep.remove(i + 1)
            merged.append(i)
            i += 2
        else:
            i += 1
    if merged:
        notes.append(f"Re-aligned {len(merged)} column name(s) that sat one column to the right of the values.")

    # 2b. A name one column LEFT of unnamed values. Right after the label column, it is the label
    #     column's own heading ("Household Size | 9.6"); further right, it names those values.
    moved_left = 0
    for pos in range(1, len(keep) - 1):
        i, j = keep[pos], keep[pos + 1]
        if header[i] and not has_val[i] and has_val[j] and not header[j]:
            if pos == 1 and not header[keep[0]]:
                header[keep[0]] = header[i]
            else:
                header[j] = header[i]
            header[i] = ""
            moved_left += 1
    if moved_left:
        notes.append(f"Re-aligned {moved_left} column name(s) that sat one column to the left of the values.")

    # 2c. A group heading ("Age of Head of Household") sitting over the first value column of its
    #     group: the column's own name was lost, so show the heading as a group, not as that name.
    for i in keep[1:]:
        if has_val[i] and i not in group_of and GROUP_ONLY.fullmatch(header[i]):
            group_of[i] = header[i]
            header[i] = ""
            notes.append("A group heading took the place of a column name; that column's own name is missing.")

    # 3. Hide columns with neither a name nor any values.
    empty = [i for i in keep if i > 0 and not has_val[i] and not header[i]]
    keep = [i for i in keep if i not in empty]
    if empty:
        notes.append(f"Hid {len(empty)} empty column(s).")

    # 4. A single unnamed value column takes the units from the title, e.g. "(Millions of Households)".
    unnamed = [i for i in keep if i > 0 and not header[i]]
    units = UNITS.search(title or "")
    if len(unnamed) == 1 and len(keep) == 2 and units:
        header[unnamed[0]] = units.group(1)
        notes.append("Named the value column from the title's units (it has no name in the report).")
        unnamed = []
    for i in unnamed:
        header[i] = f"Column {keep.index(i) + 1}"
    if unnamed:
        notes.append(f"{len(unnamed)} column(s) have no name in the extraction; shown as “Column N”.")

    # A group heading spans the following columns up to the next group, or an Average/Total column.
    groups = None
    if group_of:
        groups, k = [], 0
        while k < len(keep):
            if keep[k] in group_of:
                span = 1
                while (k + span < len(keep) and keep[k + span] not in group_of
                       and not SUMMARY.match(header[keep[k + span]])):
                    span += 1
                groups.append((group_of[keep[k]], span))
                k += span
            else:
                groups.append(("", 1))
                k += 1

    return {
        "headers": [header[i] for i in keep],
        "groups": groups,
        "rows": [[r[i] for i in keep] for r in body],
        "footnotes": footnotes,
        "notes": notes,
    }
