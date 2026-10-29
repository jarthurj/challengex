"""Re-read a table's layout from its PDF page using word positions.

The original extraction sometimes lost row labels, whole columns, or column names (multi-line
and spanning headers). On the PDF page every column name sits above its numbers, so the layout
can be rebuilt from coordinates:

  1. find the table's caption and take the region below it, down to its "Source:" line;
  2. group the region's text spans into rows by vertical position;
  3. find the columns from where the numbers line up;
  4. give each header span to the column under it (a span covering several columns is a group
     heading), and everything left of the first column to the row label.

The result is only used if every number in the original extraction appears in it, in order, so a
re-read can add labels, names, and missing cells but never contradict the extracted values.
Needs PyMuPDF (`pip install -r requirements-dev.txt`); used by `manage.py extract_context`.
"""
import re

# "$35" is never a value here: dollar amounts only appear inside labels ("Under $35").
VALUE = re.compile(r"^(?:\(?-?[\d,]*\.?\d+%?\)?|N/A|n/a|—|–|-|\*)$")
NUMERIC = re.compile(r"\d")
CAPTION_RE = r"^\s*Table\s+{num}\s*:?"
STOP = re.compile(r"^\s*(Source|Sources|Note|Notes)\s*:", re.I)


def _spans(page):
    """Text spans as (x0, y0, x1, y1, text), splitting multi-word spans at large gaps."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                text = span["text"].strip()
                if text:
                    x0, y0, x1, y1 = span["bbox"]
                    out.append((x0, y0, x1, y1, " ".join(text.split())))
    return out


def _cells(page, x_lo, x_hi, y_lo, y_hi):
    """Words in the region, merged into cells (words closer than a few points stay together)."""
    words = [w for w in page.get_text("words")
             if x_lo <= (w[0] + w[2]) / 2 <= x_hi and y_lo < (w[1] + w[3]) / 2 < y_hi]
    words.sort(key=lambda w: (round((w[1] + w[3]) / 2), w[0]))
    rows = []
    for w in words:
        yc = (w[1] + w[3]) / 2
        if rows and abs(rows[-1][0] - yc) <= 3:
            rows[-1][1].append(w)
        else:
            rows.append([yc, [w]])
    out = []
    for yc, ws in rows:
        ws.sort(key=lambda w: w[0])
        cells = []
        for w in ws:
            # a value always starts its own cell; text joins the previous text cell if close
            if (cells and not VALUE.match(w[4]) and not VALUE.match(cells[-1][4])
                    and w[0] - cells[-1][2] < 6):
                c = cells[-1]
                cells[-1] = (c[0], min(c[1], w[1]), w[2], max(c[3], w[3]), f"{c[4]} {w[4]}")
            else:
                cells.append((w[0], w[1], w[2], w[3], w[4]))
        out.append((yc, cells))
    return out


def find_caption(page, number):
    """(x0, y0, x1, y1) of the caption line 'Table <number>:' on the page, or None."""
    pattern = re.compile(CAPTION_RE.format(num=re.escape(number.replace("Table ", ""))))
    for x0, y0, x1, y1, text in _spans(page):
        if pattern.match(text):
            return (x0, y0, x1, y1)
    return None


UNITS = re.compile(r"\((?:[^()]*\b(?:Pieces|Millions|Billions|Thousands|Percent|Percentage|Households|Dollars)\b[^()]*)\)",
                   re.I)


def caption_units(page, number, title):
    """The units line printed under a caption, e.g. "(Millions of Pieces)", or "".

    The reports set it in italics, centred, right after the caption's title line(s). Anything else
    first (a bold "Volume" column heading above "(Billions)") means the caption has no units line.
    """
    cap = find_caption(page, number)
    if cap is None:
        return ""
    centre, title_words = (cap[0] + cap[2]) / 2, set(re.findall(r"[a-z0-9]+", title.lower()))
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            x0, y0, x1, _ = line["bbox"]
            if spans and cap[1] + 2 < y0 <= cap[3] + 45 and abs((x0 + x1) / 2 - centre) < 60:
                text = " ".join("".join(s["text"] for s in spans).split())
                italic = all(s["flags"] & 2 for s in spans)
                bold = any(s["flags"] & 16 or re.search(r"bold|black|heavy|demi", s["font"], re.I) for s in spans)
                lines.append((y0, text, italic, bold))
    for _, text, italic, bold in sorted(lines):
        if italic and UNITS.fullmatch(text):
            return text[1:-1]
        words = re.findall(r"[a-z0-9]+", text.lower())
        # the title's words (the page can word it differently), or a short end of a wrapped title
        title_line = len(words) <= 3 or sum(w in title_words for w in words) >= 0.7 * len(words)
        if italic or bold or not words or NUMERIC.search(text) or not title_line:
            break  # not the caption's title line: the table has started
    return ""


def _value_columns(data_rows, is_value):
    """Value columns: x-clusters of value cells that line up across many data rows.

    Numbers inside left-aligned labels ("Under $35", "$35 to $65") sit at scattered positions,
    so they never form a dense column and stay part of the label.
    """
    cells = sorted(((c[0] + c[2]) / 2, c) for _, row in data_rows for c in row if is_value(c))
    groups = []
    for x, c in cells:
        if groups and x - groups[-1][-1][0] < 14:
            groups[-1].append((x, c))
        else:
            groups.append([(x, c)])
    need = max(2, len(data_rows) // 2) if len(data_rows) > 2 else 1
    dense = [g for g in groups if len({id(c) for _, c in g}) >= need]
    return [sum(x for x, _ in g) / len(g) for g in dense], [min(c[0] for _, c in g) for g in dense]


YEAR = re.compile(r"^(19|20)\d\d[-–]?$")
DEMOGRAPHIC_GROUP = re.compile(r"(Age|Education|Educational Attainment) of (the )?Head of Household", re.I)
SUMMARY_COLUMN = re.compile(r"\s*(Average|Total|All)\b", re.I)


def _norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def rebuild(page, number, title=""):
    """Rebuild a table's headers/rows from its page, or (None, reason)."""
    cap = find_caption(page, number)
    if cap is None:
        return None, "caption not found on the page"
    width = page.rect.width
    mid = width / 2
    centre = (cap[0] + cap[2]) / 2
    if centre < mid - 40:
        x_lo, x_hi = 0, mid
    elif centre > mid + 40:
        x_lo, x_hi = mid, width
    else:
        x_lo, x_hi = 0, width

    # region: below the caption, above the next "Source:" line or caption in the same column
    y_lo, y_hi = cap[3], page.rect.height - 30
    for x0, y0, x1, y1, text in _spans(page):
        if y0 > cap[3] and x_lo <= (x0 + x1) / 2 <= x_hi and (STOP.match(text) or re.match(r"^\s*Table\s+\S+:", text)):
            y_hi = min(y_hi, y0)
    rows = _cells(page, x_lo, x_hi, y_lo, y_hi)
    # the caption's own title lines continue below "Table x.y:" -- they aren't column headings
    title_key = _norm(title)
    centre_of = lambda cells: (min(c[0] for c in cells) + max(c[2] for c in cells)) / 2
    while (rows and title_key and abs(centre_of(rows[0][1]) - centre) < 40  # centred like the caption
           and all(_norm(c[4]) and _norm(c[4]) in title_key for c in rows[0][1])):
        rows.pop(0)
    if not rows:
        return None, "no text in the table region"

    is_value = lambda c: VALUE.match(c[4]) and (NUMERIC.search(c[4]) or c[4] in ("N/A", "n/a", "—", "–", "-", "*"))
    is_years = lambda cells: all(YEAR.match(c[4]) for c in cells if is_value(c))  # a header row of years
    data_idx = [i for i, (_, cells) in enumerate(rows)
                if any(is_value(c) for c in cells) and not is_years(cells)]
    if not data_idx:
        return None, "no numbers in the table region"
    cols, lefts = _value_columns([rows[i] for i in data_idx], is_value)
    if not cols:
        return None, "no value columns found"
    label_right = min(lefts)
    # The first data row fills at least half the value columns; anything above it is header
    # (a wrapped heading like "Under / 35" has a number but isn't data).
    need = (len(cols) + 1) // 2

    def filled(cells):
        return len({min(range(len(cols)), key=lambda k: abs(cols[k] - (c[0] + c[2]) / 2))
                    for c in cells if is_value(c) and c[0] >= label_right - 1})

    def words_in_values(cells):  # header lines have words ("to", "Over") among the value columns
        return any(not is_value(c) for c in cells if c[0] >= label_right - 1)

    first = next((i for i in data_idx if filled(rows[i][1]) >= need and not words_in_values(rows[i][1])),
                 data_idx[0])

    def nearest(x):
        return min(range(len(cols)), key=lambda k: abs(cols[k] - x))

    # Body rows: label text left of the values; values to their nearest column. A label-only line
    # set tighter than the normal row spacing is a wrapped label ("Total" / "Destinating");
    # otherwise it's a section heading row of its own.
    ys = [rows[i][0] for i in data_idx]
    gaps = sorted(b - a for a, b in zip(ys, ys[1:]) if b - a > 1)
    tight = (gaps[len(gaps) // 2] * 0.8) if gaps else 0
    body, body_y = [], []
    for i in range(first, len(rows)):
        yc, cells = rows[i]
        label = " ".join(c[4] for c in cells if c[0] < label_right - 1)
        values = [c for c in cells if c[0] >= label_right - 1]
        if not values:
            if not label:
                continue
            nxt = rows[i + 1][0] if i + 1 < len(rows) else None
            if body and yc - body_y[-1] < tight and (nxt is None or nxt - yc >= tight):
                body[-1][0] = f"{body[-1][0]} {label}".strip()  # continues the row above
            else:
                body.append([label] + [""] * len(cols))
                body_y.append(yc)
            continue
        row = [""] * (len(cols) + 1)
        row[0] = label
        if body and not any(body[-1][1:]) and yc - body_y[-1] < tight:
            row[0] = f"{body.pop()[0]} {label}".strip()  # "Internet using a" / "Computer 2% ..."
            body_y.pop()
        for c in values:
            k = nearest((c[0] + c[2]) / 2) + 1
            row[k] = f"{row[k]} {c[4]}".strip() if row[k] else c[4]
        body.append(row)
        body_y.append(yc)

    # header rows: everything between the caption and the first data row
    headers = [""] * (len(cols) + 1)
    groups = []
    pitch = sorted(b - a for a, b in zip(cols, cols[1:]))[(len(cols) - 1) // 2] if len(cols) > 1 else 0
    for yc, cells in rows[:first]:
        for c in cells:
            covered = [k for k, x in enumerate(cols) if c[0] - 4 <= x <= c[2] + 4]
            if pitch and c[2] - c[0] > 1.1 * pitch:  # wider than a column: a heading over several
                covered = [k for k, x in enumerate(cols) if c[0] - pitch / 2 <= x <= c[2] + pitch / 2]
            if c[2] <= label_right + 2 and not covered:
                headers[0] = f"{headers[0]} {c[4]}".strip()
            elif len(covered) >= 2:
                groups.append((c[4], covered[0] + 1, covered[-1] + 1))
            else:
                k = covered[0] if covered else nearest((c[0] + c[2]) / 2)
                headers[k + 1] = f"{headers[k + 1]} {c[4]}".strip()
    # A demographic heading ("Education of Head of Household") always spans every category column;
    # a closing Average/Total column and a leading measure like "Households (Millions)" sit outside
    # it. Its printed width can be narrower than the columns it covers.
    for i, (label, first_col, last_col) in enumerate(groups):
        if DEMOGRAPHIC_GROUP.search(label):
            first, last = first_col, len(headers) - 1
            while first > 1 and "(" not in headers[first - 1]:
                first -= 1
            while last > first and SUMMARY_COLUMN.match(headers[last]):
                last -= 1
            groups[i] = (label, first, last)
    return {"headers": headers, "groups": groups, "rows": body}, None


def numbers(cells):
    """Number tokens in cells, including inside text ("35 to 54" -> 35, 54)."""
    return [tok for c in cells for tok in c.split() if NUMERIC.search(tok) and VALUE.match(tok)]


def consistent(extracted_rows, rebuilt):
    """Every number from the original extraction appears in the rebuilt table, in order.

    The extraction often kept header numbers (a years row, "35 to 54") as data, so the rebuilt
    header and group headings count too.
    """
    want = [n for r in extracted_rows for n in numbers(r)]
    have = (numbers([g[0] for g in rebuilt["groups"]]) + numbers(rebuilt["headers"])
            + [n for r in rebuilt["rows"] for n in numbers(r)])
    if not want:
        return False
    it = iter(have)
    return all(any(n == h for h in it) for n in want)
