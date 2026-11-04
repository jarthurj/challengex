import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dashboard.crosstab import check_heading, crosstab_values, income_band
from dashboard.metric_sources import SOURCES, CrossTab
from dashboard.models import Observation, Table

from .load_tables import to_num

TAG = "[pdf-check]"
NUM = re.compile(r"N/A|-?[\d,]*\.?\d+%?")
YEAR = re.compile(r"(19|20)\d{2}")
VALUE = re.compile(r"[-–]?(\d[\d,]*)?\.?\d+%?")  # a table value, not "$35" (a label's band)


def norm(text):
    return " ".join(text.split())


def year_header(text):
    """Years from the first line that is (almost) only years.

    From FY2024 the years are followed by "% change 2015-2025" columns; only the years before the
    first "change"/"%" count.
    """
    found = header_line(text)
    return found[1] if found else None


def header_line(text):
    """(line index, years) of the first line that is (almost) only years, or None."""
    for index, line in enumerate(text.splitlines()):
        toks = norm(line).split()
        cut = next((i for i, t in enumerate(toks) if t.lower() in ("change", "%", "%change")), len(toks))
        toks = toks[:cut]
        years = [int(t) for t in toks if YEAR.fullmatch(t)]
        if len(years) >= 2 and len(years) >= len(toks) - 2:
            return index, years
    return None


def label_rows(text, label):
    """Number tokens of each line starting with `label`, in page order.

    Spaces are ignored while matching because PDF text sometimes splits letters ("I nsurance").
    """
    want = label.lower().replace(" ", "")
    hits = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        # A label that wraps ("Some college or technical" / "school graduate 139.5 ...") is tried
        # joined with the next line; the line itself then has no numbers, so it can't match alone.
        if index + 1 < len(lines) and not re.search(r"\d", line):
            line = f"{line} {lines[index + 1]}"
        n = norm(line)
        if not n.lower().replace(" ", "").startswith(want):
            continue
        i = seen = 0
        while i < len(n) and seen < len(want):
            seen += n[i] != " "
            i += 1
        rest = n[i:]
        toks = rest.split()
        if rest.startswith(" ") and toks and NUM.fullmatch(toks[0]):
            hits.append(NUM.findall(rest))
    return hits


def page_series(text, label, nth):
    """{year: raw value} for one row of a page, or (None, reason).

    PDF text can split a number ("554" -> "5 54"). That usually breaks the count and is
    reported; if it doesn't, the bad parse shows up as a MISMATCH against the independently
    extracted loaded value, never as a false match.
    """
    found = header_line(text)
    if not found:
        return None, "no year header in the PDF text"
    # Only rows below the year header: another table above it can share labels (FY2005-FY2006
    # print Table E.1, with its own "Packages" and "Total" rows, above E.2).
    start, years = found
    rows = label_rows("\n".join(text.splitlines()[start + 1:]), label)
    if len(rows) < nth:
        return None, f"row {label!r} not found in the PDF text"
    nums = rows[nth - 1]
    if len(nums) > len(years) and all(t.endswith("%") for t in nums[len(years):]):
        nums = nums[:len(years)]  # trailing "% change" columns
    if len(nums) != len(years):
        return None, f"row {label!r} has {len(nums)} numbers for {len(years)} years in the PDF text"
    return dict(zip(years, nums)), None


def crosstab_page(text, number, title):
    """(rows, heading, problem) for a one-year household-group table on its PDF page.

    `rows` is [(label, [values])] for crosstab_values(), from the first income band to the
    Average/Total row. The table starts at its caption ("Table 4.4:", sometimes printed "Table 5. 4:",
    followed by the title, not a mention in the prose) and ends at the next caption. Some pages print
    the "Source" line above the table. From FY2022 a row label and its values are on separate lines;
    they are joined.
    """
    words = " ".join(re.findall(r"[a-z]+", title.lower())[:4])
    caption = r"\s*".join(map(re.escape, number.replace(" ", ""))) + r"\s*:"
    start = None
    for m in re.finditer(caption, text):
        if words in " ".join(re.findall(r"[a-z]+", text[m.end():m.end() + 300].lower())):
            start = m.end()
            break
    if start is None:
        return None, None, f"caption {number!r} not found in the PDF text"
    after = re.search(r"Table\s*[A-Z]?\d+\s*[.\-]\s*\d+\s*:", text[start:])
    lines = text[start:start + after.start() if after else None].splitlines()[1:]
    rows = []
    for line in lines:
        toks = line.split()
        k = len(toks)
        while k and VALUE.fullmatch(toks[k - 1]):
            k -= 1
        label, values = " ".join(toks[:k]), toks[k:]
        if not label and values and rows and not rows[-1][1]:
            rows[-1] = (rows[-1][0], values)  # the values of the label on the line before
        elif label or values:
            rows.append((label, values))
    first = next((i for i, (label, _) in enumerate(rows) if income_band(label)), None)
    if first is None:
        return None, None, "no table rows in the PDF text (the table may be an image)"
    last = next((i for i in range(first, len(rows))
                 if rows[i][0].strip().lower() in ("average", "total") and rows[i][1]), len(rows) - 1)
    heading = " ".join(f"{label} {' '.join(values)}" for label, values in rows[:first])
    return rows[first:last + 1], heading, None

def set_note(notes, line):
    kept = [n for n in notes.splitlines() if not n.startswith(TAG)]
    return "\n".join([*kept, f"{TAG} {line}"]).strip()


class Command(BaseCommand):
    help = "Check every loaded Observation against the text of its source PDF page in docs/"

    def add_arguments(self, parser):
        parser.add_argument("--docs", default=str(settings.BASE_DIR / "docs"))

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            from pypdf import PdfReader
        except ImportError:
            raise CommandError("pypdf is required: pip install -r requirements.txt")

        readers = {}
        counts = {"match": 0, "mismatch": 0, "unchecked": 0}
        for source_id, (_, row_maps) in SOURCES.items():
            table = Table.objects.get(source_id=source_id)
            path = f"{opts['docs']}/{table.year}.pdf"
            try:
                reader = readers.setdefault(table.year, PdfReader(path))
                text = reader.pages[table.page - 1].extract_text() or ""
            except FileNotFoundError:
                raise CommandError(f"{path} not found. The PDFs are git-ignored; copy them into docs/.")

            if isinstance(row_maps, CrossTab):
                self.check_crosstab(table, row_maps, text, counts)
                continue
            for rm in row_maps:
                found, problem = page_series(text, rm.label, rm.nth)
                obs = Observation.objects.filter(
                    source_table=table, metric__slug=rm.metric,
                    segment__dimension=rm.segment[0], segment__value=rm.segment[1],
                )
                for o in obs:
                    where = f"docs/{table.year}.pdf p.{table.page}"
                    if problem:
                        o.verified = False
                        o.notes = set_note(o.notes, f"not checked: {problem} ({where}); check by eye")
                        counts["unchecked"] += 1
                    # Compare with the extracted cell, not o.value, which may be converted
                    # (billions -> millions); the conversion itself is tested separately.
                    elif to_num(found.get(o.fiscal_year, "")) == to_num(o.raw_value):
                        o.verified = True
                        o.notes = set_note(o.notes, f"matches {where} ({found[o.fiscal_year]})")
                        counts["match"] += 1
                    else:
                        o.verified = False
                        o.notes = set_note(o.notes, f"MISMATCH: {where} shows {found.get(o.fiscal_year)!r}")
                        counts["mismatch"] += 1
                    o.save(update_fields=["verified", "notes"])

        style = self.style.SUCCESS if counts["mismatch"] == 0 else self.style.ERROR
        self.stdout.write(style(
            f"{counts['match']} match, {counts['mismatch']} mismatch, {counts['unchecked']} could not be checked"
        ))

    def check_crosstab(self, table, ct, text, counts):
        rows, heading, problem = crosstab_page(text, table.table_number, table.title)
        problem = problem or check_heading(heading, ct.columns)
        found = {}
        if not problem:
            try:
                found = dict(crosstab_values(rows, ct.columns, ct.margins))
            except ValueError as e:
                problem = str(e)
        where = f"docs/{table.year}.pdf p.{table.page}"
        for o in Observation.objects.filter(source_table=table, metric__slug=ct.metric).select_related("segment"):
            shown = found.get((o.segment.dimension, o.segment.value))
            if problem:
                o.verified = False
                o.notes = set_note(o.notes, f"not checked: {problem} ({where}); check by eye")
                counts["unchecked"] += 1
            elif to_num(shown or "") == to_num(o.raw_value):
                o.verified = True
                o.notes = set_note(o.notes, f"matches {where} ({shown})")
                counts["match"] += 1
            else:
                o.verified = False
                o.notes = set_note(o.notes, f"MISMATCH: {where} shows {shown!r}")
                counts["mismatch"] += 1
            o.save(update_fields=["verified", "notes"])
