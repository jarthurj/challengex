from django.shortcuts import render
from django.http import HttpResponse

from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from .models import Table


def table_list(request):
    tables = Table.objects.all()

    # Read search and filter parameters from the URL
    query = request.GET.get("q", "").strip()
    year = request.GET.get("year", "").strip()

    if query:
        tables = tables.filter(
            Q(title__icontains=query)
            | Q(source_id__icontains=query)
            | Q(table_number__icontains=query)
        )

    if year.isdigit():
        tables = tables.filter(year=int(year))

    return render(request, "dashboard/table_list.html", {
        "tables": tables,
        "query": query,
        "year": year,
    })



def table_detail(request, pk):
    table = get_object_or_404(
        Table.objects.prefetch_related("rows"),
        pk=pk,
    )

    rows = list(table.rows.all())

    print("COLUMNS:", table.columns)

    for row in rows[:3]:
        print("POSITION:", row.position)
        print("LABEL:", row.label)
        print("DATA:", row.data)

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
