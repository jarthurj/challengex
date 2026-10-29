from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from .models import MethodologyBreak, Metric, Observation, Segment


CATEGORY_SLUGS = [
    "fcm-received-correspondence",
    "fcm-received-transactions",
    "fcm-received-advertising",
]
COLORS = ["#1756a9", "#a94616", "#247343"]
DASHES = [[], [8, 4], [2, 4]]


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
    segments = list(Segment.objects.filter(
        pk__in=preferred.values("segment_id")
    ).order_by("dimension", "position", "value"))
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
    ).distinct().order_by("fiscal_year"))
    context.update({
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
    return context


def trends(request):
    context = trend_context(request)
    context["data_url"] = reverse("trend-data")
    return render(request, "dashboard/trends.html", context)


def trend_data(request):
    context = trend_context(request)
    return JsonResponse({
        "chart": context["chart_data"],
        "notice": context["notice"],
    })
