"""The real extracted tables, for tests that run load_metrics."""
import atexit
import json
import os
import tempfile
from io import StringIO

from django.conf import settings
from django.core.management import call_command

from .metric_sources import SOURCES

_subset = None


def cited_old_tables():
    """The FY2003-FY2015 tables (from tables_2000_2015.json, unchanged) that the metric mapping cites."""
    with open(settings.BASE_DIR / "tables_2000_2015.json", encoding="utf-8") as f:
        return [t for t in json.load(f) if t["id"] in SOURCES]


def cited_old_tables_path():
    """A temporary file holding cited_old_tables(), written once per test run."""
    global _subset
    if _subset is None:
        fd, _subset = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cited_old_tables(), f)
        atexit.register(os.remove, _subset)
    return _subset


def load_real_tables(*extra):
    """Load tables.json plus the older tables the metric mapping cites (and any `extra` files).

    Only those few of the 1,933 older tables, so the tests stay fast.
    """
    call_command("load_tables", str(settings.BASE_DIR / "tables.json"), cited_old_tables_path(),
                 *map(str, extra), stdout=StringIO())
