from django.shortcuts import render
from django.http import HttpResponse

from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from .models import Table
from .tidy import tidy


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

    # Show tidied column names by default; ?raw=1 shows the extraction exactly as stored.
    show_raw = request.GET.get("raw") == "1"
    tidied = None if show_raw else tidy([str(c) for c in table.columns], [row.cells for row in rows], table.title)

    return render(request, "dashboard/table_detail.html", {
        "table": table,
        "rows": rows,
        "show_raw": show_raw,
        "tidied": tidied,
    })


def dashboard(request):
    # Returns a plain text response with an optional 200 OK status
    return HttpResponse("Hello, world! This is a basic Django view.")
