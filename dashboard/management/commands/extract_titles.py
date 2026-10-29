import collections
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from dashboard.titles import assign_report


class Command(BaseCommand):
    help = "Recover table titles/numbers from the PDFs in docs/ and write table_titles.json"

    def add_arguments(self, parser):
        parser.add_argument("--tables", default=str(settings.BASE_DIR / "tables.json"))
        parser.add_argument("--docs", default=str(settings.BASE_DIR / "docs"))
        parser.add_argument("--out", default=str(settings.BASE_DIR / "table_titles.json"))

    def handle(self, *args, **opts):
        try:
            from pypdf import PdfReader
        except ImportError:
            raise CommandError("pypdf is required: pip install -r requirements.txt")

        with open(opts["tables"], encoding="utf-8") as f:
            tables = json.load(f)
        by_year = collections.defaultdict(list)
        for t in tables:
            by_year[t["year"]].append(t)

        records = {}
        for year, year_tables in sorted(by_year.items()):
            path = f"{opts['docs']}/{year}.pdf"
            try:
                reader = PdfReader(path)
            except FileNotFoundError:
                raise CommandError(f"{path} not found. The PDFs are git-ignored; copy them into docs/.")
            wanted = set(range(1, 16)) | {t["page"] for t in year_tables}  # List of Tables + table pages
            pages = {p: (reader.pages[p - 1].extract_text() or "").splitlines()
                     for p in sorted(wanted) if p <= len(reader.pages)}
            records.update(assign_report(year_tables, pages))
            titled = sum(1 for t in year_tables if records[t["id"]].get("title"))
            self.stdout.write(f"  FY{year}: {titled} of {len(year_tables)} tables titled")

        with open(opts["out"], "w", encoding="utf-8") as f:
            json.dump(dict(sorted(records.items())), f, indent=1, ensure_ascii=False)
            f.write("\n")
        methods = collections.Counter(r["method"].split(":")[0] for r in records.values())
        renumbered = sum(1 for r in records.values() if r.get("title") and r["was_number"] != r["table_number"])
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {opts['out']}: {sum(1 for r in records.values() if r.get('title'))} of {len(records)} "
            f"titled, {renumbered} table numbers corrected"
        ))
        for method, n in methods.most_common():
            self.stdout.write(f"    {n:4}  {method}")
