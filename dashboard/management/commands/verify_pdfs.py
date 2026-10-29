import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dashboard.metric_sources import SOURCES
from dashboard.models import Observation, Table

from .load_tables import to_num

TAG = "[pdf-check]"
NUM = re.compile(r"N/A|-?[\d,]*\.?\d+%?")
YEAR = re.compile(r"(19|20)\d{2}")


def norm(text):
    return " ".join(text.split())


def year_header(text):
    """Years from the first line that is (almost) only years."""
    for line in text.splitlines():
        toks = norm(line).split()
        years = [int(t) for t in toks if YEAR.fullmatch(t)]
        if len(years) >= 2 and len(years) >= len(toks) - 2:
            return years
    return None


def label_rows(text, label):
    """Number tokens of each line starting with `label`, in page order.

    Spaces are ignored while matching because PDF text sometimes splits letters ("I nsurance").
    """
    want = label.lower().replace(" ", "")
    hits = []
    for line in text.splitlines():
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
    years = year_header(text)
    rows = label_rows(text, label)
    if not years:
        return None, "no year header in the PDF text"
    if len(rows) < nth:
        return None, f"row {label!r} not found in the PDF text"
    nums = rows[nth - 1]
    if len(nums) != len(years):
        return None, f"row {label!r} has {len(nums)} numbers for {len(years)} years in the PDF text"
    return dict(zip(years, nums)), None


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
                    elif to_num(found.get(o.fiscal_year, "")) == o.value:
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
