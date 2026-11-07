"""The Settings page: display options for this browser, kept in its session (no account needed)."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .context_processors import ADVANCED_KEY, advanced_enabled
from .overview_views import fiscal_years


@require_http_methods(["GET", "POST"])
def settings_page(request):
    if request.method == "POST":
        # Only the checkbox's own value turns it on; anything else (or nothing) turns it off.
        on = request.POST.get("advanced") == "1"
        request.session[ADVANCED_KEY] = on
        messages.success(request, "Settings saved: advanced settings are " + ("on." if on else "off."))
        return redirect("settings")
    return render(request, "dashboard/settings.html", {
        "advanced": advanced_enabled(request),
        "years": sorted(fiscal_years(), reverse=True),   # the navigation's "By year" link
    })
