import re
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dashboard.metric_sources import BREAKS, CONVERSIONS, METRICS, SOURCES
from dashboard.models import MethodologyBreak, Metric, Observation, Segment, Table

from .load_tables import to_num

YEAR = re.compile(r"(19|20)\d{2}")


def norm(text):
    return " ".join((text or "").split())


def row_cells(table, row):
    return [row.data.get(c, {}).get("raw", "") for c in table.columns]


def year_header(lines):
    """Years, in column order, from the first line that lists at least two of them."""
    for cells in lines:
        years = [int(c.strip()) for c in cells[1:] if YEAR.fullmatch(c.strip())]
        if len(years) >= 2:
            return years
    return None


def row_values(cells):
    """Non-empty cells after the label, in order.

    Reports lay out year columns differently (aligned, or values and blanks interleaved and
    shifted from their headers), but the order of values always matches the order of years.
    """
    return [c.strip() for c in cells[1:] if c.strip()]


def find_row(rows, label, nth):
    matches = [r for r in rows if norm(r.label) == norm(label)]
    return matches[nth - 1] if len(matches) >= nth else None


def mark_preferred(observations):
    """One preferred value per metric, segment and year: the latest non-OCR report wins."""
    groups = defaultdict(list)
    for o in observations:
        groups[(o.metric_id, o.segment_id, o.fiscal_year)].append(o)
    for group in groups.values():
        best = max(group, key=lambda o: (not o.source_table.ocr, o.report_year))
        for o in group:
            o.is_preferred = o is best


class Command(BaseCommand):
    help = "Build Metric/Observation data from loaded tables using dashboard/metric_sources.py"

    @transaction.atomic
    def handle(self, *args, **opts):
        # Keep reviewers' work across reloads.
        kept = {
            (o.metric.slug, o.segment.dimension, o.segment.value, o.fiscal_year, o.report_year):
                (o.verified, o.notes)
            for o in Observation.objects.select_related("metric", "segment")
            if o.verified or o.notes
        }
        Observation.objects.all().delete()
        MethodologyBreak.objects.all().delete()

        metrics = {}
        for m in METRICS:
            fields = {k: v for k, v in m.items() if k != "slug"}
            metrics[m["slug"]], _ = Metric.objects.update_or_create(slug=m["slug"], defaults=fields)

        segments = {}
        positions = defaultdict(int)

        def segment(dimension, value):
            if (dimension, value) not in segments:
                segments[dimension, value], _ = Segment.objects.update_or_create(
                    dimension=dimension, value=value,
                    defaults={"position": positions[dimension]},
                )
                positions[dimension] += 1
            return segments[dimension, value]

        observations = []
        for source_id, (raw_unit, row_maps) in SOURCES.items():
            table = Table.objects.filter(source_id=source_id).first()
            if table is None:
                raise CommandError(f"{source_id} not found. Run `manage.py load_tables tables.json` first.")
            if table.ocr:
                self.stdout.write(self.style.WARNING(f"{source_id} is OCR; its values are unverified."))

            rows = list(table.rows.all())
            years = year_header([table.columns, *(row_cells(table, r) for r in rows)])
            if not years:
                raise CommandError(f"{source_id}: no year header found.")

            for rm in row_maps:
                row = find_row(rows, rm.label, rm.nth)
                if row is None:
                    raise CommandError(f"{source_id}: row {rm.label!r} (occurrence {rm.nth}) not found.")
                values = row_values(row_cells(table, row))
                if len(values) != len(years):
                    raise CommandError(
                        f"{source_id}: row {rm.label!r} has {len(values)} values for {len(years)} years "
                        f"{years}: {values}"
                    )

                metric = metrics[rm.metric]
                convert = (lambda v: v) if raw_unit == metric.unit else CONVERSIONS.get((raw_unit, metric.unit))
                if convert is None:
                    raise CommandError(f"{source_id}: no conversion from {raw_unit} to {metric.unit}.")

                seg = segment(*rm.segment)
                for year, raw in zip(years, values):
                    num = to_num(raw)
                    if num is None:  # "N/A" etc.: leave a gap rather than guess
                        continue
                    verified, notes = kept.get(
                        (metric.slug, seg.dimension, seg.value, year, table.year), (False, "")
                    )
                    observations.append(Observation(
                        metric=metric, segment=seg, fiscal_year=year,
                        value=convert(num), raw_value=raw, raw_unit=raw_unit,
                        source_table=table, report_year=table.year,
                        verified=verified, notes=notes,
                    ))

        mark_preferred(observations)
        Observation.objects.bulk_create(observations)

        for b in BREAKS:
            MethodologyBreak.objects.create(**b)

        for m in metrics.values():
            preferred = m.observations.filter(is_preferred=True, segment__dimension="all")
            years = sorted(preferred.values_list("fiscal_year", flat=True))
            span = f"{years[0]}-{years[-1]}" if years else "no data"
            self.stdout.write(f"  {m.slug}: {m.observations.count()} values, preferred series {span}")
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(metrics)} metrics, {len(observations)} observations, {len(BREAKS)} methodology breaks"
        ))
