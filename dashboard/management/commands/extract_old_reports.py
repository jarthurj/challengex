import collections
import json
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from dashboard import pdftables

# "Table 3.1: Title", "Table A2-38" (title on the next lines), "Table E.2:". Not prose: a sentence
# like "Table 5.2 reveals ..." has words after the number without a colon.
CAPTION = re.compile(r"^\s*Table\s+([A-Z]?\d*[.\-]?\d+[a-z]?\d*)\s*(?::\s*(.*))?$")
NUMBER = re.compile(r"\d")
NUM_TOKEN = re.compile(r"-?\(?\d[\d,]*\.?\d*%?\)?")
YEAR = re.compile(r"^(19|20)\d\d$")


def text_lines(page):
    """(bbox, text) for every text line on the page."""
    return [(line["bbox"], " ".join("".join(s["text"] for s in line["spans"]).split()))
            for block in page.get_text("dict")["blocks"] for line in block.get("lines", [])]


def is_contents_page(page):
    return sum(1 for line in page.get_text().splitlines() if "...." in line) >= 5


def caption_title(lines, caption, grid_top):
    """The caption's own title text plus the lines between it and the table (units, years)."""
    (x0, y0, x1, y1), text = caption
    title = [CAPTION.match(text).group(2) or ""]
    centre = (x0 + x1) / 2
    for (lx0, ly0, lx1, ly1), line in sorted(lines, key=lambda l: l[0][1]):
        if y1 - 1 <= ly0 < grid_top - 1 and abs((lx0 + lx1) / 2 - centre) < 150 and line:
            title.append(line)
    return " ".join(t for t in title if t).strip()


def clean_grid(rows):
    """Cells as strings; drop spacer columns and empty rows that ruled-table detection adds."""
    rows = [[" ".join((c or "").split()) for c in r] for r in rows]
    rows = [r for r in rows if any(r)]
    if not rows:
        return []
    keep = [j for j in range(len(rows[0])) if any(r[j] for r in rows)]
    return [[r[j] for j in keep] for r in rows]


def number_tokens(text):
    return collections.Counter(t.strip("()").replace(",", "") for t in NUM_TOKEN.findall(text.replace(" ,", ",")))


def text_check(rows, page_text):
    """Third check, with a different PDF library (pypdf): do the table's numbers all occur in the
    page's text? Spacing artefacts in that text ("201 4") can cause misses, so a miss means
    "check by eye", not "wrong"."""
    missing = number_tokens(" ".join(c for r in rows for c in r)) - number_tokens(page_text)
    total = sum(number_tokens(" ".join(c for r in rows for c in r)).values())
    return "all numbers found in the page text" if not missing else (
        f"{sum(missing.values())} of {total} numbers not found in the page text")


def split_header(rows):
    """Leading rows without data values are the header; their cells join into column names."""
    def is_data(r):
        return any(NUMBER.search(c) and not YEAR.match(c) for c in r[1:])
    k = 0
    while k < len(rows) - 1 and not is_data(rows[k]):
        k += 1
    columns = [" ".join(r[j] for r in rows[:k] if r[j]) for j in range(len(rows[0]))]
    return columns, rows[k:]


class Command(BaseCommand):
    help = ("Extract the tables of the FY2003-FY2015 reports in docs/ to tables_2000_2015.json: PyMuPDF "
            "ruled-table detection, cross-checked with dashboard/pdftables.py and with pypdf's page text. "
            "FY2000, FY2001 and FY2004 are scanned images (OCR text only) and are not extracted.")

    def add_arguments(self, parser):
        parser.add_argument("--years", nargs="+", type=int,
                            default=[2003, 2005, 2006, 2007, 2008, 2009, 2010, 2012, 2013, 2014, 2015])
        parser.add_argument("--docs", default=str(settings.BASE_DIR / "docs"))
        parser.add_argument("--out", default=str(settings.BASE_DIR / "tables_2000_2015.json"))

    def handle(self, *args, **opts):
        try:
            import pymupdf
        except ImportError:
            raise CommandError("PyMuPDF is required: pip install -r requirements-dev.txt")
        from pypdf import PdfReader
        try:
            with open(opts["out"], encoding="utf-8") as f:
                kept = [t for t in json.load(f) if t["year"] not in opts["years"]]
        except FileNotFoundError:
            kept = []

        extracted = []
        for year in opts["years"]:
            path = f"{opts['docs']}/{year}.pdf"
            try:
                doc = pymupdf.open(path)
                reader = PdfReader(path)
            except Exception:
                raise CommandError(f"{path} not found. The PDFs are git-ignored; copy them into docs/.")
            counts = {"tables": 0, "agree": 0, "pages_without_text": 0}
            for pno, page in enumerate(doc, 1):
                if not page.get_text().strip():
                    counts["pages_without_text"] += 1
                    continue
                if is_contents_page(page):
                    continue
                lines = text_lines(page)
                captions = [(bbox, text) for bbox, text in lines if CAPTION.match(text) and len(text) < 160]
                if not captions:
                    continue
                try:
                    grids = page.find_tables().tables
                except Exception:
                    continue
                used, n = set(), 0
                for grid in sorted(grids, key=lambda g: (g.bbox[1], g.bbox[0])):
                    gx0, gy0, gx1, gy1 = grid.bbox
                    # The nearest caption directly above the grid and overlapping it horizontally.
                    above = [c for c in captions
                             if c[0][3] <= gy0 + 2 and c[0][2] > gx0 - 20 and c[0][0] < gx1 + 20
                             and id(c) not in used]
                    if not above:
                        continue
                    caption = max(above, key=lambda c: c[0][3])
                    if gy0 - caption[0][3] > 120:  # too far below: not this caption's table
                        continue
                    rows = clean_grid(grid.extract())
                    if len(rows) < 2 or len(rows[0]) < 2:
                        continue
                    used.add(id(caption))
                    number = "Table " + CAPTION.match(caption[1]).group(1)
                    title = caption_title(lines, caption, gy0)
                    columns, body = split_header(rows)
                    # Second, independent reader: word positions under the same caption.
                    reread, _ = pdftables.rebuild(page, number, title)
                    agree = bool(reread) and pdftables.consistent(body, reread)
                    n += 1
                    counts["tables"] += 1
                    counts["agree"] += agree
                    extracted.append({
                        "id": f"{year}-p{pno:03d}-{n}", "year": year, "page": pno,
                        "table_number": number, "title": title, "source_file": f"{year}.pdf",
                        "ocr": False, "columns": columns, "rows": body,
                        "check": "two readers agree" if agree else "one reader",
                        "text_check": text_check(body, reader.pages[pno - 1].extract_text() or ""),
                    })
            self.stdout.write(f"  FY{year}: {counts['tables']} tables, {counts['agree']} confirmed by both "
                              f"readers; {counts['pages_without_text']} pages without a text layer skipped")

        tables = sorted(kept + extracted, key=lambda t: (t["year"], t["page"], t["id"]))
        with open(opts["out"], "w", encoding="utf-8") as f:
            json.dump(tables, f, ensure_ascii=False, indent=0)
            f.write("\n")
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(tables)} tables to {opts['out']}"))
