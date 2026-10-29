from django.shortcuts import render
from django.http import HttpResponse

from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from .models import Table


def table_list(request):
    tables = Table.objects.all()

    years = (
        Table.objects.order_by("-year")
        .values_list("year", flat=True)
        .distinct()
    )

    # Read search and filter parameters from the URL
    query = request.GET.get("q", "").strip()
    selected_years = [
        value for value in request.GET.getlist("year")
        if value.isascii() and value.isdigit()
    ]

    if query:
        tables = tables.filter(
            Q(title__icontains=query)
            | Q(source_id__icontains=query)
            | Q(table_number__icontains=query)
        )

    if selected_years:
        tables = tables.filter(year__in=[
            int(value) for value in selected_years
        ])

    return render(request, "dashboard/table_list.html", {
        "tables": tables,
        "query": query,
        "selected_years": selected_years,
        "years": years,
    })


def table_detail(request, pk):
    table = get_object_or_404(
        Table.objects.prefetch_related("rows"),
        pk=pk,
    )

    rows = list(table.rows.all())

    for row in rows:
        row.cells = []

        for column in table.columns:
            cell = row.data.get(column, {})

            if isinstance(cell, dict):
                value = cell.get("raw", "—")
            else:
                value = cell if cell is not None else "—"

            row.cells.append(value)

    return render(request, "dashboard/table_detail.html", {
        "table": table,
        "rows": rows,
    })


def dashboard(request):
    # Returns a plain text response with an optional 200 OK status
    return HttpResponse("Hello, world! This is a basic Django view.")

def build_category_chart():
    # Some extracted headings are shifted. These column keys
    # were checked against the stored row values.
    sources = [
        (2016, "2016-p014-1", "col_6"),
        (2017, "2017-p014-1", "col_6"),
        (2018, "2018-p014-1", "col_6"),
        (2019, "2019-p014-1", "col_6"),
        (2020, "2020-p014-1", "col_6"),
        (2021, "2021-p014-1", "2021"),
        (2022, "2022-p007-1", "2022"),
        (2023, "2023-p015-1", "col_6"),
        (2024, "2024-p012-1", "2024"),
    ]

    categories = [
        (
            "First-Class Mail",
            ["Total First-Class Mail", "First-Class Mail"],
            "#1756a9",
        ),
        (
            "Standard / Marketing Mail",
            ["Total Marketing Mail", "Total Standard Mail"],
            "#c05621",
        ),
        (
            "Periodicals",
            ["Periodicals"],
            "#278047",
        ),
    ]

    tables = {
        table.source_id: table
        for table in Table.objects.filter(
            source_id__in=[source[1] for source in sources]
        ).prefetch_related("rows")
    }

    datasets = []

    for name, labels, color in categories:
        values = []

        for year, source_id, column in sources:
            table = tables.get(source_id)
            value = None

            if table is not None:
                row = next(
                    (
                        row for row in table.rows.all()
                        if row.label.strip() in labels
                    ),
                    None,
                )

                if row is not None:
                    cell = row.data.get(column, {})
                    if isinstance(cell, dict):
                        value = cell.get("num")

            values.append(value)

        datasets.append({
            "label": name,
            "data": values,
            "borderColor": color,
            "backgroundColor": color,
            "borderWidth": 3,
            "pointRadius": 4,
            "tension": 0,
            "spanGaps": False,
            "fill": False,
        })

    return {
        "years": [source[0] for source in sources],
        "datasets": datasets,
    }, list(tables.values())

def trends(request):
    # Explicit sources prevent accidentally selecting a different total.
    trend_options = [
        ("total_volume", "Total mail volume over time"),
        ("category_volume", "Mail volume by category"),
        ("mail_delays", "Mail delays per year"),
    ]

    selected_trend = request.GET.get("trend", "total_volume")

    valid_trends = [value for value, label in trend_options]

    if selected_trend not in valid_trends:
        selected_trend = "total_volume"

    if selected_trend == "category_volume":
        chart_data, category_sources = build_category_chart()

        return render(request, "dashboard/trends.html", {
            "trend_options": trend_options,
            "selected_trend": selected_trend,
            "chart_data": chart_data,
            "category_sources": category_sources,
        })

    if selected_trend == "mail_delays":
        return render(request, "dashboard/trends.html", {
            "trend_options": trend_options,
            "selected_trend": selected_trend,
        })

    sources = [
        (2016, "2016-p009-1", "FY 2016 RPW Total", "Received"),
        (2017, "2017-p009-1", "FY 2017 RPW Total", "Received"),
        (2018, "2018-p009-1", "FY 2018 RPW Total", "Received"),
        (2019, "2019-p009-1", "FY 2019 RPW Total", "Received"),
        (2020, "2020-p009-1", "FY 2020 RPW Total", "Received"),
        (2021, "2021-p014-1", "Total All Mail", "2021"),
        (2022, "2022-p007-1", "Total All Mail", "2022"),
        (2023, "2023-p016-3", "FY 2023 RPW Total", "Received"),
        (2024, "2024-p012-1", "Total All Mail", "2024"),
        (2025, "2025-p015-1", "Total Mail Volume (billions)", "2025"),
    ]

    source_ids = [source[1] for source in sources]

    tables = {
        table.source_id: table
        for table in Table.objects.filter(
            source_id__in=source_ids
        ).prefetch_related("rows")
    }

    points = []

    for year, source_id, label, column in sources:
        table = tables.get(source_id)
        volume = None

        if table is not None:
            row = next(
                (
                    row for row in table.rows.all()
                    if row.label.strip() == label
                ),
                None,
            )

            if row is not None:
                cell = row.data.get(column, {})
                if isinstance(cell, dict):
                    volume = cell.get("num")

        if volume is None:
            status = "Missing value"
        elif year in (2021, 2022):
            status = "Conflicting extracted values—review required"
        else:
            status = "Extracted—PDF verification pending"

        points.append({
            "year": year,
            "volume": volume,
            "table": table,
            "status": status,
        })

    chart_data = {
    "years": [point["year"] for point in points],
    "volumes": [point["volume"] for point in points],
}

    return render(request, "dashboard/trends.html", {
    "points": points,
    "chart_data": chart_data,
    "trend_options": trend_options,
    "selected_trend": selected_trend,
})