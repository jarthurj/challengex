import json
import re

from django.core.management.base import BaseCommand
from django.db import transaction




from dashboard.models import Row, Table  # change "reports" to your app name


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
        parser.add_argument("path")

    @transaction.atomic
    def handle(self, *args, **opts):
        with open(opts["path"], encoding="utf-8") as f:
            items = json.load(f)

        Row.objects.all().delete()
        Table.objects.all().delete()

        rows = []
        for t in items:
            cols = unique_columns(t["columns"])
            table = Table.objects.create(
                source_id=t["id"], year=t["year"], page=t["page"],
                table_number=t["table_number"], title=t["title"],
                columns=cols, ocr=t["ocr"],
            )
            for pos, r in enumerate(t["rows"]):
                rows.append(Row(
                    table=table, position=pos, label=r[0],
                    data={c: {"raw": v, "num": to_num(v)} for c, v in zip(cols, r)},
                ))
        Row.objects.bulk_create(rows, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(items)} tables, {len(rows)} rows"))
