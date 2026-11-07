"""The welcome page: what the site is and how to find your way around it (the logo's link)."""
from django.db.models import Max, Min
from django.shortcuts import render

from .models import Observation, Table
from .overview_views import fiscal_years


def site_facts():
    """What the welcome page's text needs from the loaded data: the years covered and the table count."""
    span = Observation.objects.filter(is_preferred=True).aggregate(first=Min("fiscal_year"), last=Max("fiscal_year"))
    return {
        "first_year": span["first"],
        "last_year": span["last"],
        "tables": f"{Table.objects.exclude(section='survey_form').count():,}",
    }


def welcome(request):
    return render(request, "dashboard/welcome.html", {
        "facts": site_facts(),
        "years": fiscal_years(),   # the navigation's "By year" link
    })
