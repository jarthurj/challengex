import functools
import json

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse

from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from .models import Table
from .tidy import tidy

CONTEXT_FILE = settings.BASE_DIR / "table_context.json"


@functools.lru_cache(maxsize=1)
def _load_context(mtime):
    with open(CONTEXT_FILE, encoding="utf-8") as f:
        return json.load(f)


def table_context(source_id):
    """This table's entry in table_context.json (written by `manage.py extract_context`), or {}."""
    try:
        return _load_context(CONTEXT_FILE.stat().st_mtime).get(source_id, {})
    except FileNotFoundError:
        return {}


def rebuilt_display(structure):
    """A table re-read from its PDF page, in the shape the template draws (like tidy's output)."""
    headers = structure["headers"]
    groups, k = [], 0
    starts = {first: (label, last) for label, first, last in structure["groups"]}
    while structure["groups"] and k < len(headers):
        label, last = starts.get(k, ("", k))
        groups.append((label, last - k + 1))
        k = last + 1
    return {"headers": headers, "groups": groups or None, "rows": structure["rows"], "notes": [], "footnotes": []}


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
    context = table_context(table.source_id)
    reread = not show_raw and bool(context.get("structure"))
    if show_raw:
        tidied = None
    elif reread:
        tidied = rebuilt_display(context["structure"])
    else:
        tidied = tidy([str(c) for c in table.columns], [row.cells for row in rows], table.title)

    return render(request, "dashboard/table_detail.html", {
        "table": table,
        "rows": rows,
        "show_raw": show_raw,
        "tidied": tidied,
        "reread": reread,
        "context": context,
    })


def dashboard(request):
    # Returns a plain text response with an optional 200 OK status
    return HttpResponse("Hello, world! This is a basic Django view.")
