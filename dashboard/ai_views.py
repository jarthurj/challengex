"""The AI summaries tab: every stored summary in one place.

Browse them year by year (a slider), as long-term or custom-range summaries, or search them; they are
grouped by category (the topic each subject belongs to). Each one can be copied with its sources,
exported as text, opened on its own page with its provenance, and marked reviewed by staff.

Pages only read the stored files. The one exception is "Create a summary": a POST (CSRF-checked) whose
criteria are picked from fixed lists, so no free text reaches the model; it is rate-limited, makes one
request at a time with a short timeout, and its result goes through the same number check and save
rules as the command line, so text that fails is never shown.
"""
import os
import threading
from datetime import datetime, timezone

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.debug import sensitive_variables
from django.views.decorators.http import require_POST

from . import ai_summary as a
from .overview_views import fiscal_years, year_param

VIEWS = {"year": "Year by year", "long": "Long term", "range": "Custom ranges", "search": "Search results"}
VIEW_KINDS = {"year": ("yearly",), "long": ("comparative",), "range": (a.RANGE,),
              "search": ("yearly", "comparative", a.RANGE)}
KIND_CHOICES = {"": "Any kind", "yearly": "One year", "comparative": "Long term", a.RANGE: "Custom range"}
STATUSES = {"": "Any review status", "reviewed": "Reviewed by a person", "unreviewed": "Not yet reviewed"}
MAX_QUERY = 100
OPEN_ALL_UP_TO = 4               # a results list this short shows every summary unfolded
PER_PAGE = 40                    # summaries per page (a year has at most 35, the long term 35)
_GENERATING = threading.Lock()   # one live request at a time (runserver is threaded)


def _choice(value, allowed, default=""):
    return value if isinstance(value, str) and value in allowed else default


def _filters(request):
    """The page's query parameters, each checked against its fixed list (anything else is ignored)."""
    g = request.GET
    years = sorted(fiscal_years())
    q = " ".join(g.get("q", "").split())[:MAX_QUERY]
    section = _choice(g.get("section"), a.SECTIONS)
    category = _choice(g.get("category"), a.TOPIC_SECTIONS)
    kind = _choice(g.get("kind"), KIND_CHOICES)
    status = _choice(g.get("status"), STATUSES)
    searching = bool(q or section or category or kind or status)
    view = _choice(g.get("view"), VIEWS, "search" if searching else "year")
    raw_year = g.get("year", "").strip()
    year = year_param(raw_year, years)
    latest = raw_year == "latest" and view == "year"   # each subject's own latest year
    return {"q": q, "view": view, "section": section, "category": category, "kind": kind, "status": status,
            "year": year, "years": years, "latest": latest,
            # a typed year that isn't in the data: say so (cut short; escaped by the template)
            "bad_year": raw_year[:12] if raw_year and year is None and raw_year != "latest" else ""}


def _label(record):
    return f'{a.KIND_LABELS.get(record.get("kind"), "Summary")}, {a.years_label(record)}'.strip(", ")


PREVIEW_CHARS = 220   # the first statement, shown under a folded summary's headline


def _preview(record):
    """The first statement: the headlines are often generic, the statements carry the figures."""
    statements = a._statements(record)
    text = " ".join(str(statements[0].get("text", "")).split()) if statements else ""
    return text if len(text) <= PREVIEW_CHARS else text[:PREVIEW_CHARS].rsplit(" ", 1)[0] + " …"


def _status(record):
    """One badge for how a summary was made and whether a person has read it: (text, style)."""
    if not record.get("ai_generated"):
        return "Rule-based, not AI", ""
    return ("AI-generated · reviewed", "badge-ok") if record.get("reviewed") else ("AI-generated · not yet reviewed",
                                                                                  "badge-warn")


def _named(record):
    """A copy of the record whose statements also carry their metric's display name, for the
    citation link (done here, not with a template tag library: a new one needs a server restart)."""
    summary = dict(record.get("summary") or {})
    summary["statements"] = [{**s, "metric_name": a.metric_name(s.get("metric"))} for s in a._statements(record)]
    return {**record, "summary": summary}


def _item(entry, record):
    section, key = entry["section"], entry["key"]
    title = a.SECTIONS[section][0]
    status, status_style = _status(record)
    return {
        "section": section, "key": key, "record": _named(record),
        "dom_id": f"s-{section}-{key}".replace(":", "-"),
        "title": title, "label": _label(record),
        # a topic's own summary sits under its own name as the category heading: call it what it is
        "short_title": "Overview" if a.category_of(section) == section else title,
        "preview": _preview(record), "status": status, "status_style": status_style,
        "url": reverse("ai-summary", args=[section, key]),
        "copy": a.plain_text(section, record),
    }


def _status_line(groups):
    """One line for the whole list, so each row needn't repeat it: '12 not yet reviewed, 2 reviewed'."""
    items = [i for g in groups for i in g["items"]]
    if not items:
        return ""
    ai = [i for i in items if i["record"].get("ai_generated")]
    reviewed = sum(1 for i in ai if i["record"].get("reviewed"))
    parts = []
    if ai:
        parts.append(f"{'All' if len(ai) == len(items) else len(ai)} AI-generated, "
                     + ("none reviewed by a person yet" if not reviewed else
                        "all reviewed by a person" if reviewed == len(ai) else f"{reviewed} reviewed by a person"))
    if len(ai) < len(items):
        parts.append(f"{len(items) - len(ai)} rule-based")
    return "; ".join(parts) + "."


def _hidden_reason(entry):
    validation = entry["record"].get("validation")
    if not isinstance(validation, dict) or validation.get("passed") is not True:
        problems = validation.get("problems") if isinstance(validation, dict) else None
        return [str(p) for p in (problems or [])][:3] or ["it failed its check when it was written"]
    return a.current_check(entry["section"], entry["record"])["problems"][:3] or ["its record is malformed"]


def _results(f, page=1, per_page=None):
    """(groups by category, hidden entries, the year shown, the years that have yearly summaries, the
    page info). Only the page's summaries are re-checked: a cold check of all of them takes seconds."""
    sections = [f["section"]] if f["section"] else [
        k for k in a.SECTIONS if not f["category"] or a.category_of(k) == f["category"]]
    kinds = (f["kind"],) if f["view"] == "search" and f["kind"] else VIEW_KINDS[f["view"]]
    entries = [e for e in a.stored_entries(sections) if e["record"].get("kind") in kinds]
    yearly_years = sorted({e["record"]["fiscal_year"] for e in entries
                           if e["record"].get("kind") == "yearly" and a.is_year(e["record"].get("fiscal_year"))})
    year = f["year"]
    if f["view"] == "year" and not f["latest"]:
        year = year or (yearly_years[-1] if yearly_years else (f["years"][-1] if f["years"] else None))
        entries = [e for e in entries if e["record"].get("fiscal_year") == year]
    elif f["view"] == "search" and year is not None:
        entries = [e for e in entries if a.covers_year(e["record"], year)]   # summaries about that year
    terms = a.search_terms(f["q"])
    entries = [e for e in entries if a.matches(e, terms)]
    if f["status"]:
        entries = [e for e in entries if bool(e["record"].get("reviewed")) == (f["status"] == "reviewed")]
    if f["view"] == "year" and f["latest"]:
        groups, hidden = _latest_by_subject(entries)
        count = sum(len(g["items"]) for g in groups)
        return groups, hidden, None, yearly_years, {"page": 1, "pages": 1, "matching": count, "first": 1,
                                                    "last": count}
    entries.sort(key=lambda e: (a.CATEGORY_ORDER.index(a.category_of(e["section"])),
                                a.entry_order(e["section"], e["record"])))
    pages = max(1, -(-len(entries) // per_page)) if per_page else 1
    page = min(max(page, 1), pages)
    info = {"page": page, "pages": pages, "matching": len(entries),
            "first": (page - 1) * per_page + 1 if per_page else 1}
    if per_page:
        entries = entries[(page - 1) * per_page:page * per_page]
    shown, hidden = [], []
    with a.check_batch():
        for e in entries:
            record = a.shown(e["section"], e["record"])
            if record:
                shown.append(_item(e, record))
            else:
                hidden.append({"title": a.SECTIONS[e["section"]][0], "label": _label(e["record"]),
                               "url": reverse("ai-summary", args=[e["section"], e["key"]])})
    groups = []
    for category in a.CATEGORY_ORDER:
        items = [i for i in shown if a.category_of(i["section"]) == category]   # already in order
        if items:
            groups.append({"key": category, "title": a.TOPIC_SECTIONS[category][0], "items": items})
    info["last"] = info["first"] + len(entries) - 1
    return groups, hidden, year, yearly_years, info


def _latest_by_subject(entries):
    """Each subject's yearly summary for the latest fiscal year it has one that passes its check for
    (an earlier year when the latest one is hidden), grouped by category. The series end in different
    years (First-Class Mail received in FY2023, the per-household ones in FY2024 or FY2025), so each
    subject shows its own latest. Only the summaries looked at are re-checked. Returns (groups, each
    with "years", the fiscal years it shows; hidden entries looked at)."""
    by_section = {}
    for e in entries:
        if e["record"].get("kind") == "yearly" and a.is_year(e["record"].get("fiscal_year")):
            by_section.setdefault(e["section"], []).append(e)
    latest, hidden = [], []
    with a.check_batch():
        for section, candidates in by_section.items():
            for e in sorted(candidates, key=lambda e: -e["record"]["fiscal_year"]):
                record = a.shown(section, e["record"])
                if record:
                    latest.append(_item(e, record))
                    break
                hidden.append({"title": a.SECTIONS[section][0], "label": _label(e["record"]),
                               "url": reverse("ai-summary", args=[section, e["key"]])})
    groups = []
    for category in a.CATEGORY_ORDER:
        items = sorted((i for i in latest if a.category_of(i["section"]) == category),
                       key=lambda i: a.entry_order(i["section"], i["record"]))
        if items:
            years = sorted({i["record"]["fiscal_year"] for i in items})
            groups.append({"key": category, "title": a.TOPIC_SECTIONS[category][0], "items": items,
                           "years": a.year_spans(years)})
    return groups, hidden


def _suggestion(f, year):
    """Criteria for the "Create a summary" form, guessed from the search: a subject its words name
    and a fiscal year written in it, else the filters and the year shown."""
    section = f["section"] or a.section_for_words(f["q"]) or f["category"]
    asked = f["year"] or a.year_in_words(f["q"], f["years"]) or (year if f["view"] == "year" else None)
    if f["kind"]:
        kind = f["kind"]
    elif f["view"] == "range":
        kind = a.RANGE
    elif asked or f["view"] == "year":
        kind = "yearly"
    else:
        kind = "comparative"
    latest = f["years"][-1] if f["years"] else None
    return {"section": section, "kind": kind, "year": asked or latest,
            "from_year": f["years"][0] if f["years"] else None, "to_year": latest}


@sensitive_variables("value")   # the key: never on a Django error page
def _dotenv(name):
    """A setting from the environment or the git-ignored .env, read without loading .env into
    os.environ (so nothing else in the process, tests included, picks it up)."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        from dotenv import dotenv_values
    except ImportError:
        return None
    return dotenv_values(settings.BASE_DIR / ".env").get(name) or None


def gemini_key():
    return _dotenv("GEMINI_API_KEY")


def live_unavailable():
    """Why "Create a summary" is off, or None when it is on."""
    if not getattr(settings, "AI_LIVE_GENERATION", True):
        return "Creating summaries from this page is switched off (AI_LIVE_GENERATION in settings)."
    if not gemini_key():
        return "Creating summaries needs a Gemini API key in .env (GEMINI_API_KEY; see .env.example)."
    return None


def _limits():
    return {"per_client_per_hour": 5, "per_day": 30, **getattr(settings, "AI_LIVE_LIMITS", {})}


def _counters(request):
    client = request.META.get("REMOTE_ADDR") or "unknown"
    now = datetime.now(timezone.utc)
    limits = _limits()
    return ((f"ai-live:{client}:{now:%Y%m%d%H}", limits["per_client_per_hour"], 3600),
            (f"ai-live:all:{now:%Y%m%d}", limits["per_day"], 86400))


def _left(request):
    return max(min(limit - (cache.get(key) or 0) for key, limit, _ in _counters(request)), 0)


def _take_one(request):
    """Counts one live request against the hourly (per client) and daily limits; False if either is used up."""
    counters = _counters(request)
    if any((cache.get(key) or 0) >= limit for key, limit, _ in counters):
        return False
    for key, _, ttl in counters:
        cache.add(key, 0, ttl)
        cache.incr(key)
    return True


def _subjects():
    """The subjects for the form's select, by category: [(category title, [(key, title)])]."""
    return [(a.TOPIC_SECTIONS[c][0], [(k, a.SECTIONS[k][0]) for k in a.SECTIONS if a.category_of(k) == c])
            for c in a.CATEGORY_ORDER]


def ai_summaries(request):
    f = _filters(request)
    asked_page = request.GET.get("page", "")
    page = int(asked_page) if asked_page.isascii() and asked_page.isdigit() and len(asked_page) < 5 else 1
    groups, hidden, year, yearly_years, pages = _results(f, page, PER_PAGE)
    count = sum(len(g["items"]) for g in groups)
    picker = None   # the year view's dropdown: each subject's latest year, then the fiscal years
    if f["view"] == "year" and f["years"]:
        # the years that have a stored yearly summary (all loaded years if none is stored yet), latest first
        choices = sorted(yearly_years or f["years"], reverse=True)
        picker = {"year": year, "min": f["years"][0], "max": f["years"][-1], "latest": f["latest"],
                  "choices": choices,
                  "previous": max((y for y in choices if y < year), default=None) if year else None,
                  "next": min((y for y in choices if y > year), default=None) if year else None,
                  "stored": a.year_spans(yearly_years)}
    query = {k: v for k, v in {"q": f["q"], "view": f["view"], "section": f["section"], "category": f["category"],
                               "kind": f["kind"], "status": f["status"],
                               "year": "latest" if f["latest"] else (year or "")}.items() if v}
    if pages["pages"] > 1:
        pages["previous_url"] = f"?{urlencode({**query, 'page': pages['page'] - 1})}" if pages["page"] > 1 else None
        pages["next_url"] = (f"?{urlencode({**query, 'page': pages['page'] + 1})}"
                             if pages["page"] < pages["pages"] else None)
    return render(request, "dashboard/ai_summaries.html", {
        "f": f, "groups": groups, "hidden": hidden, "count": count, "year": year, "picker": picker, "pages": pages,
        "status_line": _status_line(groups),
        "mixed_years": f["view"] != "year" or f["latest"],   # rows show their year only where years differ
        "open_all": count <= OPEN_ALL_UP_TO,
        "views": VIEWS, "kinds": KIND_CHOICES, "statuses": STATUSES,
        "categories": [(k, a.TOPIC_SECTIONS[k][0]) for k in a.CATEGORY_ORDER],
        "subjects": _subjects(), "suggest": _suggestion(f, year), "form_years": sorted(f["years"], reverse=True),
        "live_unavailable": live_unavailable(), "live_left": _left(request),
        "export_url": f"{reverse('ai-export')}?{urlencode(query)}",
        "years": sorted(f["years"], reverse=True),   # the navigation's "By year" link
    })


def ai_export(request):
    """The summaries the page shows for the same parameters, as plain text with their sources."""
    groups, _hidden, _year, _, _pages = _results(_filters(request))   # every match, not one page
    blocks = [i["copy"] for g in groups for i in g["items"]]
    head = ("USPS household mail: AI summaries\n"
            f"Exported {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC from the dashboard ({len(blocks)} summaries). "
            "Every number was checked automatically against the published values; one marked 'Not yet "
            "reviewed by a person' has not been read by anyone.\n")
    body = head + "\n\n" + ("\n\n----\n\n".join(blocks) if blocks else "No summaries match.") + "\n"
    response = HttpResponse(body, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="usps-ai-summaries.txt"'
    return response


def ai_summary_detail(request, section, key):
    if section not in a.SECTIONS:
        raise Http404("No such subject.")
    stored = a._load_file(section)["summaries"].get(key)
    if not isinstance(stored, dict) or not isinstance(stored.get("summary"), dict):
        raise Http404("No such summary.")
    record = a.shown(section, stored)
    entry = {"section": section, "key": key, "record": stored}
    category = a.category_of(section)
    sources = a.source_rows(record) if record else []
    for row in sources:   # the source page in the report PDF, where docs/ has it (git-ignored)
        year, page = row["report_year"], row["page"]
        has_pdf = a.is_year(year) and (settings.BASE_DIR / "docs" / f"{year}.pdf").exists()
        row["pdf_url"] = f"{reverse('source-pdf', args=[year])}#page={page}" if has_pdf and a.is_year(page) else None
    return render(request, "dashboard/ai_summary_detail.html", {
        "item": _item(entry, record) if record else None,
        "title": a.SECTIONS[section][0], "section": section, "key": key, "label": _label(stored),
        "category": a.TOPIC_SECTIONS[category][0], "category_key": category,
        "problems": None if record else _hidden_reason(entry),
        "sources": sources,
        "trend_metrics": [(slug, a.metric_name(slug)) for slug in sorted(
            {s.get("metric") for s in a._statements(record or {})
             if isinstance(s.get("metric"), str) and s.get("metric") in a.METRIC_SECTIONS})],
        "can_review": request.user.is_staff,
        "years": sorted(fiscal_years(), reverse=True),
    })


@require_POST
def ai_review(request, section, key):
    """Staff only: mark a shown summary reviewed (or not), with who and when."""
    if not request.user.is_staff:
        return HttpResponseForbidden("Log in as staff (at /admin/) to mark summaries reviewed.")
    if section not in a.SECTIONS:
        raise Http404("No such subject.")
    reviewed = request.POST.get("reviewed") == "1"
    if not a.set_reviewed(section, key, reviewed, request.user.get_username()):
        raise Http404("No such summary, or it fails its check and can't be marked reviewed.")
    messages.success(request, "Marked as reviewed." if reviewed else "The reviewed mark was removed.")
    return redirect("ai-summary", section=section, key=key)


@require_POST
def ai_generate(request):
    """Asks Gemini for one summary the user picked (subject, kind and years, all from fixed lists)."""
    p = request.POST
    years = fiscal_years()
    section = _choice(p.get("section"), a.SECTIONS)
    kind = _choice(p.get("kind"), ("yearly", "comparative", a.RANGE))
    year = year_param(p.get("year", ""), years)
    first, last = year_param(p.get("from_year", ""), years), year_param(p.get("to_year", ""), years)
    back = f"{reverse('ai-summaries')}?{urlencode({'section': section} if section else {'view': 'search'})}"
    if not section or not kind:
        messages.error(request, "Pick a subject and a kind of summary.")
        return redirect(back)
    if kind == "yearly" and year is None:
        messages.error(request, "Pick the fiscal year for a one-year summary.")
        return redirect(back)
    if kind == a.RANGE and not (first and last and first < last):
        messages.error(request, "Pick two fiscal years, the first one earlier than the second.")
        return redirect(back)
    year = year if kind == "yearly" else None
    span = (first, last) if kind == a.RANGE else None
    key = a.record_key(kind, span, year)
    if a.shown(section, a._load_file(section)["summaries"].get(key)):
        messages.info(request, "That summary already exists, so no new one was requested.")
        return redirect("ai-summary", section=section, key=key)
    if not a.collect_section(section, kind, year, span)["series"]:
        messages.error(request, f"There are no published values for {a.SECTIONS[section][0]} in that period, "
                                "so there is nothing to summarise.")
        return redirect(back)
    reason = live_unavailable()
    if reason:
        messages.error(request, reason)
        return redirect(back)
    if not _GENERATING.acquire(blocking=False):   # before counting: a busy refusal costs no quota
        messages.error(request, "Another summary is being written right now. Try again in a minute.")
        return redirect(back)
    try:
        if not _take_one(request):
            messages.error(request, "The limit for new summaries has been reached (it resets every hour, and the "
                                    "daily one at midnight UTC). Try again later.")
            return redirect(back)
        try:
            record = a.make_summary(section, kind, year, model=_dotenv("GEMINI_MODEL"), span=span,
                                    budget={"left": a.LIVE_MAX_CALLS}, timeout=a.LIVE_TIMEOUT, api_key=gemini_key())
        except Exception:   # anything unexpected on the way: say so, never an error page (it could show the key)
            record = None
    finally:
        _GENERATING.release()
    if record is None:
        messages.error(request, "Gemini didn't answer in time (or was busy), so nothing was saved. Try again later.")
        return redirect(back)
    outcome = a.save_summary(section, record)
    if outcome == "kept reviewed":
        messages.info(request, "The reviewed summary for the same data was kept.")
        return redirect("ai-summary", section=section, key=record["key"])
    if record["validation"]["passed"]:
        messages.success(request, "Gemini wrote a new summary and it passed the number check. It is labelled "
                                  "'Not yet reviewed' until a person has read it.")
        return redirect("ai-summary", section=section, key=record["key"])
    count = len(record["validation"]["problems"])
    messages.warning(request, f"Gemini wrote a summary, but it failed the number check ({count} "
                              f"problem{'s' if count != 1 else ''}), so it isn't shown. You can try again; each try "
                              "counts against the limit.")
    return redirect(back)
