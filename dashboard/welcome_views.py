"""The welcome page: what the site is and how to find your way around it (the logo's link)."""
from django.shortcuts import render

from .models import Table
from .overview_views import fiscal_years


def site_facts(years):
    """What the welcome page's text needs: the years covered (`years` is fiscal_years(), latest
    first) and the table count."""
    return {
        "first_year": years[-1] if years else None,
        "last_year": years[0] if years else None,
        "tables": f"{Table.objects.exclude(section='survey_form').count():,}",
    }


def welcome(request):
    years = fiscal_years()
    return render(request, "dashboard/welcome.html", {
        "facts": site_facts(years),
        "years": years,   # also the navigation's "By year" link
    })
