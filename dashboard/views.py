from django.conf import settings
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import render, get_object_or_404

from .display import SECTIONS, cells, display_table, table_context
from .models import Table

OCR_CHOICES = [("", "Any"), ("exclude", "Hide OCR tables"), ("only", "OCR tables only")]
REVIEW_CHOICES = [("", "Any"), ("ok", "Hide tables that need review"), ("only", "Only tables that need review")]


def table_list(request):
    tables = Table.objects.all()

    years = (
        Table.objects.order_by("-year")
        .values_list("year", flat=True)
        .distinct()
    )

    # Read search and filter parameters from the URL; anything unexpected is ignored.
    query = request.GET.get("q", "").strip()
    selected_years = [
        value for value in request.GET.getlist("year")
        if value.isascii() and value.isdigit()
    ]
    section = request.GET.get("section", "")
    section = section if section in dict(SECTIONS) else ""
    ocr = request.GET.get("ocr", "")
    ocr = ocr if ocr in dict(OCR_CHOICES) else ""
    review = request.GET.get("review", "")
    review = review if review in dict(REVIEW_CHOICES) else ""
    include_forms = request.GET.get("forms") == "1"

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

    # Appendix C survey forms (cover letters, blank diaries) aren't data; hidden unless asked for.
    hidden_forms = 0
    if section:
        tables = tables.filter(section=section)
    elif not include_forms:
        hidden_forms = tables.filter(section="survey_form").count()
        tables = tables.exclude(section="survey_form")
    if ocr == "exclude":
        tables = tables.filter(ocr=False)
    elif ocr == "only":
        tables = tables.filter(ocr=True)
    if review == "ok":
        tables = tables.filter(needs_review=False)
    elif review == "only":
        tables = tables.filter(needs_review=True)

    return render(request, "dashboard/table_list.html", {
        "tables": tables,
        "query": query,
        "selected_years": selected_years,
        "years": years,
        "sections": SECTIONS,
        "section": section,
        "ocr_choices": OCR_CHOICES,
        "ocr": ocr,
        "review_choices": REVIEW_CHOICES,
        "review": review,
        "include_forms": include_forms,
        "hidden_forms": hidden_forms,
    })


def table_detail(request, pk):
    table = get_object_or_404(
        Table.objects.prefetch_related("rows"),
        pk=pk,
    )

    rows = list(table.rows.all())
    for row in rows:
        row.cells = cells(table.columns, row.data)

    # Show tidied column names by default; ?raw=1 shows the extraction exactly as stored.
    show_raw = request.GET.get("raw") == "1"
    context = table_context(table.source_id)
    if show_raw:
        tidied, reread = None, False
    else:
        tidied, reread = display_table(table.source_id, table.columns, [row.cells for row in rows], table.title)

    return render(request, "dashboard/table_detail.html", {
        "table": table,
        "rows": rows,
        "show_raw": show_raw,
        "tidied": tidied,
        "reread": reread,
        "context": context,
        "pdf_available": (settings.BASE_DIR / "docs" / f"{table.year}.pdf").exists(),
    })


def source_pdf(request, year):
    """A report PDF from the local docs/ folder (git-ignored), for "open the source page" links."""
    path = settings.BASE_DIR / "docs" / f"{year}.pdf"
    if not path.is_file():
        raise Http404("That report PDF isn't in this copy of docs/. The PDFs are git-ignored; copy them in.")
    return FileResponse(open(path, "rb"), content_type="application/pdf", filename=f"{year}.pdf")
