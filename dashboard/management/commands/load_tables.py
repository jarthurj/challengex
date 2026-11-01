import json
import re

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard.display import cells, display_table, review_reasons, section_of
from dashboard.models import Row, Table


def to_num(raw):
    s = raw.strip()
    neg = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[$,%()\s]", "", s)
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def unique_columns(cols):
    seen, out = {}, []
    for i, c in enumerate(cols):
        c = c or f"col_{i + 1}"
        seen[c] = seen.get(c, 0) + 1
        out.append(c if seen[c] == 1 else f"{c} ({seen[c]})")
    return out


class Command(BaseCommand):
    help = "Load tables.json into Table and Row"

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="+", help="tables.json, and optionally tables_2000_2015.json")

    @transaction.atomic
    def handle(self, *args, **opts):
        items = []
        for path in opts["paths"]:
            with open(path, encoding="utf-8") as f:
                items += json.load(f)

        # Titles and numbers recovered from the PDFs by `manage.py extract_titles`.
        titles = {}
        titles_path = settings.BASE_DIR / "table_titles.json"
        if titles_path.exists():
            with open(titles_path, encoding="utf-8") as f:
                titles = {k: v for k, v in json.load(f).items() if v.get("title")}

        # Update tables in place (keyed by source_id) rather than wiping them, so Observations that
        # point at a table, and their reviewers' flags and notes, survive a reload.
        removed, _ = Table.objects.exclude(source_id__in=[t["id"] for t in items]).delete()
        Row.objects.all().delete()

        rows = []
        for t in items:
            cols = unique_columns(t["columns"])
            fixed = titles.get(t["id"], {})
            number = fixed.get("table_number", t["table_number"])
            title = fixed.get("title", t["title"])
            table_rows = [{c: {"raw": v, "num": to_num(v)} for c, v in zip(cols, r)} for r in t["rows"]]
            # Review status describes what the table page shows (the same display_table call).
            tidied, _ = display_table(t["id"], cols, [cells(cols, data) for data in table_rows], title)
            reasons = review_reasons(t["ocr"], number, tidied["headers"])
            if t.get("check") == "one reader":  # FY2000-FY2015 extraction (extract_old_reports)
                reasons.append("Only one of the two extraction methods could read this table; "
                               "its layout may be off.")
            if t.get("text_check", "").endswith("not found in the page text"):
                reasons.append(f"Cross-check: {t['text_check']} (often a spacing quirk; check by eye).")
            table, _ = Table.objects.update_or_create(
                source_id=t["id"],
                defaults={
                    "year": t["year"], "page": t["page"],
                    "table_number": number, "title": title,
                    "columns": cols, "ocr": t["ocr"],
                    "section": section_of(number, title, t["year"]),
                    "needs_review": bool(reasons), "review_reason": "\n".join(reasons),
                },
            )
            for pos, (r, data) in enumerate(zip(t["rows"], table_rows)):
                rows.append(Row(table=table, position=pos, label=r[0], data=data))
        Row.objects.bulk_create(rows, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(items)} tables, {len(rows)} rows ({len(titles)} titles from table_titles.json)"
            + (f"; removed {removed} objects no longer in {', '.join(opts['paths'])}" if removed else "")
        ))
