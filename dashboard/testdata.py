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


def load_real_tables(*extra):
    """Load tables.json plus the FY2003-FY2015 tables the metric mapping cites (and any `extra` files).

    Only those few of the 1,933 older tables, so the tests stay fast; they are the real extracted
    tables from tables_2000_2015.json, unchanged.
    """
    global _subset
    if _subset is None:
        with open(settings.BASE_DIR / "tables_2000_2015.json", encoding="utf-8") as f:
            cited = [t for t in json.load(f) if t["id"] in SOURCES]
        fd, _subset = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cited, f)
        atexit.register(os.remove, _subset)
    call_command("load_tables", str(settings.BASE_DIR / "tables.json"), _subset, *map(str, extra),
                 stdout=StringIO())
