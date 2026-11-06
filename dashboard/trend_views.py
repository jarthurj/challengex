from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import urlencode

from .ai_summary import section_for_trend
from .forecast import DECIMALS, forecast
from .models import MethodologyBreak, Metric, Observation, Segment
from .overview_views import csv_response, fiscal_years, observation_row
# from .ai_summary import get_summary

BAND = "rgba(90, 90, 90, 0.18)"
BAND_EDGE = "#767676"  # 4.5:1 on white

CATEGORY_SLUGS = [
    "fcm-received-correspondence",
    "fcm-received-transactions",
    "fcm-received-advertising",
]
COLORS = ["#1756a9", "#a94616", "#247343"]
DASHES = [[], [8, 4], [2, 4]]
PROJECTION_DASH = [10, 3, 2, 3]   # dash-dot, unlike every published line: the category chart's projections


def trend_context(request):
    metrics = list(Metric.objects.order_by("name"))
    options = [(m.slug, m.name) for m in metrics]
    options += [
        ("category_volume", "First-Class Mail received by category"),
        ("mail_delays", "Mail delays per year (data unavailable)"),
    ]
    selected = request.GET.get("trend", "fcm-received-total")
    # Keep old links working, but show the actual scope of the replacement metric.
    if selected == "total_volume":
        selected = "fcm-received-total"
    if selected not in {key for key, label in options}:
        selected = "fcm-received-total"

    context = {
        "trend_options": options,
        "selected_trend": selected,
        "segments": [],
        "selected_segment": None,
        "chart_data": None,
        "observations": [],
        "breaks": [],
        "notice": "",
    }
    if selected == "mail_delays":
        context["notice"] = (
            "Annual delivery-delay measurements have not been mapped into this dataset. "
            "A separate delivery-performance source is needed; missing data is not zero delays."
        )
        return context

    slugs = CATEGORY_SLUGS if selected == "category_volume" else [selected]
    chosen = [m for slug in slugs for m in metrics if m.slug == slug]
    if not chosen or len(chosen) != len(slugs):
        context["notice"] = "This metric has not been loaded. Run manage.py rebuild_db."
        return context
    if len({m.unit for m in chosen}) != 1:
        context["notice"] = "These metrics use different units and cannot share this axis."
        return context

    preferred = Observation.objects.filter(metric__in=chosen, is_preferred=True)
    segments = sorted(Segment.objects.filter(pk__in=preferred.values("segment_id")),
                      key=lambda s: (s.dimension != "all", s.dimension, s.position, s.value))  # all first
    context["segments"] = segments
    segment_id = request.GET.get("segment", "")
    segment = next((s for s in segments if str(s.pk) == segment_id), None)
    if segment is None:
        segment = next((s for s in segments if s.dimension == "all"), None)
    if segment is None and segments:
        segment = segments[0]
    context["selected_segment"] = segment
    if segment is None:
        context["notice"] = "No preferred observations are available for this metric."
        return context

    observations = list(preferred.filter(segment=segment).select_related(
        "metric", "segment", "source_table"
    ).order_by("fiscal_year", "metric__name"))
    context["observations"] = observations
    if not observations:
        context["notice"] = "No observations are available for this selection."
        return context

    first = min(o.fiscal_year for o in observations)
    last = max(o.fiscal_year for o in observations)
    years = list(range(first, last + 1))
    datasets = []
    for index, metric in enumerate(chosen):
        by_year = {o.fiscal_year: o for o in observations if o.metric_id == metric.pk}
        datasets.append({
            "label": metric.name,
            "data": [by_year[y].value if y in by_year else None for y in years],
            "sources": [
                {
                    "report_year": by_year[y].report_year,
                    "page": by_year[y].source_table.page,
                    "verified": by_year[y].verified,
                } if y in by_year else None
                for y in years
            ],
            "borderColor": COLORS[index % len(COLORS)],
            "backgroundColor": COLORS[index % len(COLORS)],
            "borderDash": DASHES[index % len(DASHES)],
            "pointStyle": ["circle", "rect", "triangle"][index % 3],
            "pointRadius": 4,
            "borderWidth": 2,
            "tension": 0,
            "fill": False,
            "spanGaps": False,
        })

    breaks = list(MethodologyBreak.objects.filter(
        Q(metrics__in=chosen) | Q(metrics__isnull=True),
        fiscal_year__gte=first,
        fiscal_year__lte=last,
    ).distinct().prefetch_related("metrics").order_by("fiscal_year"))

    # A projection for every line, each fitted on its own series and its own breaks. A single
    # metric gets its 80% band on the chart; on the category chart three overlapping bands would
    # hide the lines, so each projection is a dashed line in its series' colour and the intervals
    # are in the tables below the chart.
    decimals = DECIMALS[chosen[0].unit]
    projections = []
    for index, metric in enumerate(chosen):
        series = sorted((o.fiscal_year, o.value) for o in observations if o.metric_id == metric.pk)
        if not series:
            continue
        own = [b.fiscal_year for b in breaks
               if not b.metrics.all() or any(m.pk == metric.pk for m in b.metrics.all())]
        projection = forecast([y for y, _ in series], [v for _, v in series], metric.unit, breaks=own)
        projections.append({
            "metric": metric, "forecast": projection, "last_point": series[-1], "index": index,
            "rows": [{key: (f"{p[key]:,.{decimals}f}" if key != "year" else p[key]) for key in p}
                     for p in projection.get("points", [])],
        })
    made = [p for p in projections if "points" in p["forecast"]]
    if made:
        extend_years(years, datasets, max(p["forecast"]["points"][-1]["year"] for p in made))
        for p in made:
            add_projection(years, datasets, p, band=len(chosen) == 1)
    single = projections[0] if len(chosen) == 1 and projections else None
    context.update({
        "forecast": single["forecast"] if single else None,
        "forecast_rows": single["rows"] if single else [],
        "category_projections": projections if len(chosen) > 1 else [],
        "chart_title": (
            "First-Class Mail received by category"
            if selected == "category_volume" else chosen[0].name
        ),
        "unit_label": chosen[0].get_unit_display(),
        "descriptions": [m.description for m in chosen if m.description],
        "breaks": breaks,
        "category_chart": selected == "category_volume",
        "chart_data": {
            "years": years,
            "datasets": datasets,
            "unit": chosen[0].get_unit_display(),
            "breaks": [{"year": b.fiscal_year, "title": b.title} for b in breaks],
        },
    })
    context["projections"] = projections
    context["copy_text"] = copy_text(context, projections)
    return context


def extend_years(years, datasets, until):
    """Runs the x axis on to the last projected year; the published lines get gaps there."""
    extra = list(range(years[-1] + 1, until + 1))
    years += extra
    for dataset in datasets:
        dataset["data"] += [None] * len(extra)
        dataset["sources"] += [None] * len(extra)


def add_projection(years, datasets, projection, band=True):
    """Adds one series' projection line (and, for a single metric, its 80% band), labelled as projections."""
    points = projection["forecast"]["points"]
    last_year, last_value = projection["last_point"]

    def line(key):
        # The line starts at the last published value, so it continues the series.
        values = [None] * len(years)
        values[years.index(last_year)] = last_value
        for p in points:
            values[years.index(p["year"])] = p[key]
        return values

    model = projection["forecast"]["model_name"]
    # joinIndex: the point shared with the published line. It is a published value, so its tooltip
    # comes from the published line only (trends.html filters the projection's out).
    common = {"pointRadius": 0, "borderWidth": 1, "borderColor": BAND_EDGE, "tension": 0,
              "spanGaps": False, "sources": [None] * len(years), "projection": True,
              "joinIndex": years.index(last_year)}
    if band:
        # The light fill alone is below 3:1 against white, so the band's edges get a thin line that
        # meets it (WCAG 1.4.11); the same intervals are also in the projection table.
        datasets += [
            {**common, "label": "80% prediction interval (lower)", "data": line("lo80"), "fill": False,
             "legendHidden": True, "backgroundColor": BAND},
            {**common, "label": "80% prediction interval", "data": line("hi80"), "fill": "-1",
             "backgroundColor": BAND},
        ]
        label, color, dash = f"Projection ({model})", "#5a5a5a", [6, 4]
    else:
        label = f"Projection: {projection['metric'].name} – {model}"
        color = COLORS[projection["index"] % len(COLORS)]
        dash = PROJECTION_DASH
    radius = [4] * len(years)
    radius[common["joinIndex"]] = 0   # the joining point shows the published line's own marker
    datasets.append({**common, "label": label, "data": line("value"), "borderColor": color,
                     "backgroundColor": color, "borderDash": dash, "borderWidth": 2,
                     "pointRadius": radius, "pointStyle": "crossRot", "fill": False})


def copy_text(context, projections):
    """
    The chart as text for a report: a tab-separated table (it pastes into a spreadsheet or a Word
    table) of every published value with its source report, page, table and verification, the
    missing years, the methodology changes, and any projection, labelled as one, with its intervals.
    """
    observations = context["observations"]
    unit = context["unit_label"]
    decimals = DECIMALS[observations[0].metric.unit]
    lines = [f"{context['chart_title']}: {context['selected_segment']} ({unit})",
             "Source: USPS Household Diary Study / Household Mail Survey. Each year's value is from the "
             "most recent report that publishes it (not OCR).",
             "",
             "\t".join(["Fiscal year", "Metric", f"Value ({unit})", "Source report", "Page", "Table",
                        "Verified against the PDF"])]
    for o in observations:
        lines.append("\t".join([f"FY{o.fiscal_year}", o.metric.name, f"{o.value:,.{decimals}f}",
                                f"FY{o.report_year}", str(o.source_table.page), o.source_table.source_id,
                                "yes" if o.verified else "no"]))
    metrics = sorted({o.metric for o in observations}, key=lambda m: m.name)
    for metric in metrics:
        have = {o.fiscal_year for o in observations if o.metric_id == metric.pk}
        missing = [y for y in range(min(have), max(have) + 1) if y not in have]
        if missing:
            lines.append(f"No published value for {metric.name} in "
                         + ", ".join(f"FY{y}" for y in missing) + " (left as gaps, not filled in).")
    if context["breaks"]:
        lines += ["", "Methodology changes (values on either side may not be comparable):"]
        lines += [f"FY{b.fiscal_year}: {b.title}" for b in context["breaks"]]
    made = [p for p in projections if "points" in p["forecast"]]
    if made:
        lines += ["", "Projections: statistical estimates made by this dashboard, not published USPS figures.",
                  "\t".join(["Fiscal year", "Metric", f"Projection ({unit})", "80% interval",
                             "95% interval", "Model", "Fitted on", f"Backtest mean absolute error ({unit})"])]
        for p in made:
            f = p["forecast"]
            fitted = f"FY{f['fit_years'][0]}-FY{f['fit_years'][1]}"
            if f["after_break"]:
                fitted += f", from the FY{f['after_break']} methodology change"
            mae = next(f"{b['mae']:,.{decimals}f}" for b in f["backtest"] if b["chosen"])
            if f["crossed_breaks"]:
                fitted += " (crosses the " + ", ".join(f"FY{y}" for y in f["crossed_breaks"]) + " changes)"
            for row in p["rows"]:
                lines.append("\t".join([f"FY{row['year']}", p["metric"].name, row["value"],
                                        f"{row['lo80']} to {row['hi80']}", f"{row['lo95']} to {row['hi95']}",
                                        f["model_name"], fitted, mae]))
    return "\n".join(lines) + "\n"


def trends(request):
    context = trend_context(request)
    context["data_url"] = reverse("trend-data")
    context["years"] = fiscal_years()  # for the "By year" link in the navigation
    # The AI summaries are on their own tab (ai_views); this page links to the selected metric's.
    context["ai_section"] = section_for_trend(context["selected_trend"])
    if context["ai_section"]:
        context["ai_url"] = f"{reverse('ai-summaries')}?{urlencode({'section': context['ai_section']})}"

    # --- OPTIONAL: real-time generation when "Show trend" is pressed (currently switched off) ---
    # Uncomment to call Gemini on every Show trend instead of reading the stored files. Each page
    # load then spends tokens and waits up to ~60 s, and anyone who can open the page can trigger it.
    # CLAUDE.md says pages must not call the API on every load; prefer a POST button with a rate
    # limit. Also add `from .ai_summary import get_summary` at the top of this file.
    
    # if context["ai_section"] and context["chart_data"]:  # only after the form is submitted
    #     live = []
    #     for label, kind in (("Long-term summary", "comparative"), ("Latest-year summary", "yearly")):
    #         record = get_summary(context["ai_section"], kind, live=True)  # None if the API fails or the check fails
    #         if record:
    #             live.append({"label": label, "record": record})
    #     if live:                                  # otherwise keep the stored summaries above
    #         context["ai_summaries"] = live
    return render(request, "dashboard/trends.html", context)


def trend_data(request):
    context = trend_context(request)
    return JsonResponse({
        "chart": context["chart_data"],
        "notice": context["notice"],
        "forecast": context.get("forecast"),
        # The category chart: one projection per line (or the reason it has none).
        "projections": [{"metric": p["metric"].slug, **p["forecast"]}
                        for p in context.get("category_projections", [])],
    })


def trend_csv(request):
    """The selected series as CSV: published values with sources, then each line's projection."""
    context = trend_context(request)
    rows = [observation_row(o) for o in context["observations"]]
    for projection in context.get("projections", []):
        f = projection["forecast"]
        for p in f.get("points", []):
            rows.append({
                "fiscal_year": p["year"], "metric": projection["metric"].name,
                "metric_slug": projection["metric"].slug, "household_group": str(context["selected_segment"]),
                "kind": "projection (not a published figure)", "value": round(p["value"], 3),
                "unit": context["unit_label"], "model": f["model_name"],
                "low_80": round(p["lo80"], 3), "high_80": round(p["hi80"], 3),
                "low_95": round(p["lo95"], 3), "high_95": round(p["hi95"], 3),
            })
    return csv_response(f"usps-trend-{context['selected_trend']}.csv", rows)
