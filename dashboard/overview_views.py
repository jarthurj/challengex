"""Overview (KPI cards) and Year pages, plus CSV export of a year's values.

Every number shown is a preferred, published observation, with its source report and page; the
only derived numbers are changes between two such values and market shares, and the page says so.
"""
import csv

from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .forecast import DECIMALS
from .models import Metric, Observation, Table

# Headline series for the cards, in display order.
KPIS = [
    "household-mail-per-household",
    "fcm-received-total",
    "fcm-sent-total",
    "packages-per-household",
    "bills-paid-by-mail-share",
    "bills-paid-electronic-share",
]
# Markets that make up all household mail per household (Table E.2, FY2024/FY2025).
MARKETS = [
    ("correspondence-per-household", "Correspondence"),
    ("transactions-per-household", "Transactions"),
    ("advertising-per-household", "Advertising"),
    ("periodicals-per-household", "Periodicals"),
    ("packages-per-household", "Packages"),
]
UNIT_SUFFIX = {"millions": " million pieces", "per_household_year": " pieces per household per year",
               "percent": "%"}


def decimals(value, unit):
    """Display precision; whole-number percentages (as USPS publishes them) stay whole."""
    return 0 if unit == "percent" and float(value).is_integer() else DECIMALS[unit]


def fmt(value, unit):
    return f"{value:,.{decimals(value, unit)}f}{UNIT_SUFFIX[unit]}"


def fmt_change(new, old, unit):
    """'-14.2% (-6,730 million pieces)', or percentage points for a percent metric."""
    diff = new - old
    if unit == "percent":
        return f"{diff:+,.{decimals(diff, unit)}f} percentage points"
    pct = f"{100 * diff / old:+.1f}%" if old else "n/a"
    return f"{pct} ({diff:+,.{DECIMALS[unit]}f}{UNIT_SUFFIX[unit]})"


def source_of(o):
    return {
        "text": f"FY{o.report_year} report, page {o.source_table.page}",
        "url": reverse("table-detail", args=[o.source_table.pk]),
        "verified": o.verified,
    }


def preferred(metric, dimension="all"):
    return {o.fiscal_year: o for o in Observation.objects.filter(
        metric=metric, segment__dimension=dimension, is_preferred=True,
    ).select_related("source_table")}


def kpi_card(metric):
    series = preferred(metric)
    if not series:
        return None
    latest = max(series)
    o = series[latest]
    comparisons = []
    for span in (5, 10):
        before = series.get(latest - span)
        if before is not None:
            comparisons.append({
                "label": f"vs. FY{latest - span}",
                "value": fmt(before.value, metric.unit),
                "change": fmt_change(o.value, before.value, metric.unit),
                "source": source_of(before),
            })
    return {
        "metric": metric,
        "year": latest,
        "value": fmt(o.value, metric.unit),
        "source": source_of(o),
        "comparisons": comparisons,
        "trend_url": f"{reverse('trends')}?trend={metric.slug}",
    }


def market_mix():
    """Market volumes per household for the latest year all of them share, with computed shares."""
    total_metric = Metric.objects.filter(slug="household-mail-per-household").first()
    metrics = {m.slug: m for m in Metric.objects.filter(slug__in=[s for s, _ in MARKETS])}
    if total_metric is None or len(metrics) != len(MARKETS):
        return None
    total_series = preferred(total_metric)
    series = {slug: preferred(metrics[slug]) for slug, _ in MARKETS}
    years = set(total_series).intersection(*[set(s) for s in series.values()])
    if not years:
        return None
    year = max(years)
    # The published markets don't add up to the published total (USPS counts some pieces in more
    # than one market, and an "Other" market isn't mapped), so shares are of the markets shown.
    shown = sum(series[slug][year].value for slug, _ in MARKETS)
    rows = [{
        "name": name,
        "value": f"{series[slug][year].value:,.1f}",
        "share": 100 * series[slug][year].value / shown,
        "source": source_of(series[slug][year]),
    } for slug, name in MARKETS]
    return {"year": year, "total": f"{total_series[year].value:,.1f}", "shown": f"{shown:,.1f}",
            "rows": rows, "source": source_of(total_series[year])}


def overview(request):
    by_slug = {m.slug: m for m in Metric.objects.filter(slug__in=KPIS)}
    cards = [card for card in (kpi_card(by_slug[s]) for s in KPIS if s in by_slug) if card]
    return render(request, "dashboard/overview.html", {
        "cards": cards,
        "mix": market_mix(),
        "years": fiscal_years(),
        "notice": "" if cards else "No metrics are loaded yet. Run python manage.py rebuild_db.",
    })


def fiscal_years():
    return sorted(set(Observation.objects.filter(is_preferred=True).values_list("fiscal_year", flat=True)),
                  reverse=True)


def year_rows(year):
    """Preferred values for one fiscal year: all households, then household groups."""
    observations = Observation.objects.filter(fiscal_year=year, is_preferred=True).select_related(
        "metric", "segment", "source_table").order_by("metric__market", "metric__name",
                                                      "segment__dimension", "segment__position")
    headline, groups = [], {}
    for o in observations:
        row = {"observation": o, "value": fmt(o.value, o.metric.unit), "source": source_of(o),
               "number": f"{o.value:,.{decimals(o.value, o.metric.unit)}f}"}  # unit is in the caption
        if o.segment.dimension == "all":
            headline.append(row)
        else:
            groups.setdefault(o.metric, []).append(row)
    return headline, groups


def year_pick(request):
    """The year form's target: validate ?year= and go to that year's page (or the latest)."""
    years = fiscal_years()
    value = request.GET.get("year", "")
    year = int(value) if value.isascii() and value.isdigit() and int(value) in years else (years[0] if years else None)
    if year is None:
        raise Http404("No published values yet.")
    return redirect("year-detail", year=year)


def year_detail(request, year):
    years = fiscal_years()
    if year not in years:
        raise Http404("No published values for that fiscal year.")
    headline, groups = year_rows(year)
    return render(request, "dashboard/year.html", {
        "year": year,
        "years": years,
        "headline": headline,
        "groups": list(groups.items()),
        "report_tables": Table.objects.filter(year=year).exclude(title__startswith="Survey form").count(),
        "tables_url": f"{reverse('table-list')}?year={year}",
    })


def safe_cell(value):
    """Text that a spreadsheet would run as a formula ("=...", "+...", "@...") is quoted."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


CSV_HEADER = ["fiscal_year", "metric", "metric_slug", "household_group", "kind", "value", "unit",
              "low_80", "high_80", "low_95", "high_95", "model", "source_report_year", "source_page",
              "source_table", "verified_against_pdf"]


def csv_response(filename, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(CSV_HEADER)
    for row in rows:
        writer.writerow([safe_cell(row.get(column, "")) for column in CSV_HEADER])
    return response


def observation_row(o):
    return {
        "fiscal_year": o.fiscal_year, "metric": o.metric.name, "metric_slug": o.metric.slug,
        "household_group": str(o.segment), "kind": "published", "value": o.value,
        "unit": o.metric.get_unit_display(), "source_report_year": o.report_year,
        "source_page": o.source_table.page, "source_table": o.source_table.source_id,
        "verified_against_pdf": "yes" if o.verified else "no",
    }


def year_csv(request, year):
    if year not in fiscal_years():
        raise Http404("No published values for that fiscal year.")
    observations = Observation.objects.filter(fiscal_year=year, is_preferred=True).select_related(
        "metric", "segment", "source_table").order_by("metric__name", "segment__dimension", "segment__position")
    return csv_response(f"usps-household-mail-FY{year}.csv", [observation_row(o) for o in observations])
