import collections
import json
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from dashboard import context, pdftables
from dashboard.fy2021_quotes import QUOTES as FY2021_QUOTES
from dashboard.models import Table
from dashboard.tidy import tidy

SURVEY_FORM = "Survey form"
NUM = re.compile(r"^-?\(?[\d,]*\.?\d+%?\)?$")


def score(headers, rows):
    """Lower is better: unnamed value columns, rows with numbers but no label, empty columns."""
    unnamed = sum(1 for h in headers[1:] if not h.strip() or h.startswith("Column "))
    nolabel = sum(1 for r in rows if not r[0].strip() and any(NUM.match(x.strip()) for x in r[1:] if x.strip()))
    numlabel = sum(1 for r in rows if NUM.match(r[0].strip() or "x"))
    empty = sum(1 for j in range(1, len(headers)) if not any(r[j].strip() for r in rows))
    return unnamed + nolabel + numlabel + empty


def leaks(rebuilt, title):
    """Caption or page text that ended up in the header: the re-read region was wrong."""
    key = lambda text: re.sub(r"[^a-z0-9]", "", text.lower())
    title_key = key(title)
    texts = rebuilt["headers"] + [g[0] for g in rebuilt["groups"]]
    return any(re.match(r"\s*(\(|(Table|Figure|Source|Note)\b)", t)  # "(" opens a caption's units line
               or re.search(r"\b(Years|Diary Data|Recruitment Data|Satisfied)\b", t)
               or (len(key(t)) >= 12 and key(t) in title_key) for t in texts)


def implausible(rebuilt, tidied):
    """Why a re-read can't be right even though its numbers match, or ""."""
    rows = rebuilt["rows"]
    if len(rows) != len(tidied["rows"]):
        return "a different number of rows than the extraction (a split or merged label)"
    if not rows or not rows[0][0].strip() or NUM.match(rows[0][0].strip()):
        return "a header line was read as a data row"
    if any(not r[0].strip() and any(c.strip() for c in r[1:]) for r in rows):
        return "a row with numbers has no label"
    if any(len(re.findall(r"\d[\d,.]*%?", c)) > 1 for r in rows for c in r[1:]):
        return "two numbers fell into one cell"
    if any(any(c.strip() for c in r[1:]) and all(pdftables.YEAR.match(c.strip()) for c in r[1:] if c.strip())
           for r in rows):
        return "a second header row (years) inside the table"
    if any(re.match(r"(19|20)\d\d \w", h) for h in rebuilt["headers"][1:]):
        return "a year heading was merged into a column name"
    if any(len(r[0].split()) > 8 and not any(c.strip() for c in r[1:]) for r in rows):
        return "text from outside the table was read as a row"
    if sum(1 for r in rows if r[0].strip().lower() == rebuilt["headers"][0].strip().lower()) or \
            any(not h.strip() for h in rebuilt["headers"][1:]):
        return "a repeated or missing column heading"
    return ""


class Command(BaseCommand):
    help = ("Find each table's discussion in its report and re-read its layout from the PDF page; "
            "writes table_context.json")

    def add_arguments(self, parser):
        parser.add_argument("--docs", default=str(settings.BASE_DIR / "docs"))
        parser.add_argument("--titles", default=str(settings.BASE_DIR / "table_titles.json"))
        parser.add_argument("--out", default=str(settings.BASE_DIR / "table_context.json"))

    def handle(self, *args, **opts):
        try:
            import pymupdf
        except ImportError:
            raise CommandError("PyMuPDF is required: pip install -r requirements-dev.txt")
        if not Table.objects.exists():
            raise CommandError("No tables loaded. Run `python manage.py rebuild_db` first.")
        with open(opts["titles"], encoding="utf-8") as f:
            titles = json.load(f)

        out, stats = {}, collections.Counter()
        for year in sorted(set(Table.objects.values_list("year", flat=True))):
            path = f"{opts['docs']}/{year}.pdf"
            try:
                doc = pymupdf.open(path)
            except Exception:
                raise CommandError(f"{path} not found. The PDFs are git-ignored; copy them into docs/.")

            # Prose of every page. Scanned FY2021 pages use the hand-checked transcriptions.
            paragraphs, from_image = {}, set()
            for i, page in enumerate(doc, 1):
                blocks = page.get_text("blocks")
                if i <= 12 and any("...." in b[4] for b in blocks):
                    continue  # table of contents / list of tables
                if page.get_text().strip():
                    paragraphs[i] = context.paragraphs_from_blocks(blocks)
                elif year == 2021 and i in FY2021_QUOTES:
                    paragraphs[i] = FY2021_QUOTES[i]
                    from_image.add(i)
            paragraphs = context.stitch(paragraphs)

            tables = Table.objects.filter(year=year).exclude(title__startswith=SURVEY_FORM)
            for t in tables.order_by("page", "source_id").prefetch_related("rows"):
                rec = titles.get(t.source_id, {})
                number, title = rec.get("table_number", ""), rec.get("title", "")
                entry = {"excerpts": [], "why_none": "", "units": "", "structure": None, "structure_note": ""}

                # 1. The report's own sentences about this table.
                if not number:
                    entry["why_none"] = "The table has no number in the report, so no sentence can refer to it."
                else:
                    found = context.excerpts(paragraphs, number, t.page, title)
                    entry["excerpts"] = [{"page": p, "text": s, "from_image": p in from_image} for p, s in found]
                    if not found:
                        entry["why_none"] = f"The report's text never refers to {number}."
                stats["context" if entry["excerpts"] else "no context"] += 1

                page = doc[t.page - 1]
                # 2. Units printed under the caption, when the title doesn't already end with them.
                if number.startswith("Table") and not pdftables.UNITS.search(title):
                    entry["units"] = pdftables.caption_units(page, number, title)

                # 3. The layout re-read from the page, kept only when it is consistent and better.
                columns = [str(c) for c in t.columns]
                extracted = [[r.data.get(c, {}).get("raw", "") for c in t.columns] for r in t.rows.all()]
                td = tidy(columns, extracted, t.title)
                base = score(td["headers"], td["rows"])
                if not page.get_text().strip():
                    note = "extraction already complete" if base == 0 else "scanned page: no text layer to re-read"
                elif not number.startswith("Table"):
                    note = "extraction already complete" if base == 0 else "chart or unnumbered table: not re-read"
                else:
                    rebuilt, why = pdftables.rebuild(page, number, title)
                    # A group heading the extraction lost, or put in a column's place ("Educational
                    # Attainment of Head of Household" over "Less than High School"), counts against it.
                    if rebuilt:
                        tidy_groups = {label for label, _ in td["groups"] or []}
                        base += sum(1 for g in rebuilt["groups"] if g[0] not in tidy_groups)
                    if base == 0:
                        note = "extraction already complete"
                    elif rebuilt is None:
                        note = f"re-read failed: {why}"
                    elif not pdftables.consistent(extracted, rebuilt):
                        note = "re-read rejected: its numbers don't match the extraction"
                    elif leaks(rebuilt, title):
                        note = "re-read rejected: caption text in the header"
                    elif implausible(rebuilt, td):
                        note = f"re-read rejected: {implausible(rebuilt, td)}"
                    elif score(rebuilt["headers"], rebuilt["rows"]) < base:
                        note = "re-read from the PDF page"
                        entry["structure"] = rebuilt
                    else:
                        note = "re-read no better than the extraction"
                entry["structure_note"] = note
                stats[f"structure: {note.split(':')[0]}"] += 1
                out[t.source_id] = entry

            self.stdout.write(f"  FY{year}: {sum(1 for t in tables if out[t.source_id]['excerpts'])} of "
                              f"{tables.count()} tables have context")

        with open(opts["out"], "w", encoding="utf-8") as f:
            json.dump(dict(sorted(out.items())), f, indent=1, ensure_ascii=False)
            f.write("\n")
        self.stdout.write(self.style.SUCCESS(f"Wrote {opts['out']}"))
        for key, n in sorted(stats.items()):
            self.stdout.write(f"    {n:4}  {key}")
