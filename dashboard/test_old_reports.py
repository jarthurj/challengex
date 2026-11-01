"""FY2003-FY2015 extraction helpers (extract_old_reports) and loading a second tables file.

The extraction itself needs PyMuPDF and the git-ignored PDFs; these tests cover the parts that
decide what counts as a caption, how grids are cleaned, and how review flags are set.
"""
import json
import tempfile
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from .management.commands import extract_old_reports as old
from .models import Observation, Table


class CaptionTests(SimpleTestCase):
    def test_captions_but_not_prose(self):
        self.assertEqual(old.CAPTION.match("Table 3.1: Correspondence Sent").group(1), "3.1")
        self.assertEqual(old.CAPTION.match("Table A2-38").group(1), "A2-38")
        self.assertEqual(old.CAPTION.match("Table E.2:").group(1), "E.2")
        self.assertIsNone(old.CAPTION.match("Table 5.2 reveals that households..."))
        self.assertIsNone(old.CAPTION.match("Table of Contents"))


class GridTests(SimpleTestCase):
    def test_spacer_columns_and_empty_rows_dropped(self):
        rows = [["", "Mail", None, "2009", None, "2010"], [None] * 6, ["", "Bills", "", "1.2", "", "1.3"]]
        self.assertEqual(old.clean_grid(rows), [["Mail", "2009", "2010"], ["Bills", "1.2", "1.3"]])

    def test_header_rows_join_into_column_names(self):
        rows = [["Deductions", "Percent", ""], ["", "2009", "2010"], ["0", "52.2", "46.4"], ["1", "14.3", "16.9"]]
        columns, body = old.split_header(rows)
        self.assertEqual(columns, ["Deductions", "Percent 2009", "2010"])
        self.assertEqual(body, [["0", "52.2", "46.4"], ["1", "14.3", "16.9"]])

    def test_text_check(self):
        rows = [["Total", "1,234", "56.7%"]]
        self.assertEqual(old.text_check(rows, "Total 1,234 56.7%"), "all numbers found in the page text")
        self.assertEqual(old.text_check(rows, "Total 1,234 56.8%"), "1 of 2 numbers not found in the page text")


class LoadTwoFilesTests(TestCase):
    OLD = [
        {"id": "2010-p084-1", "year": 2010, "page": 84, "table_number": "Table A1-2",
         "title": "Mail Received by Households by Class (Diary Data)", "source_file": "2010.pdf", "ocr": False,
         "columns": ["Class", "1987", "2009", "2010"], "rows": [["First-Class", "42.1", "38.0", "36.8"]],
         "check": "two readers agree", "text_check": "all numbers found in the page text"},
        {"id": "2010-p120-1", "year": 2010, "page": 120, "table_number": "Table A2-38",
         "title": "Use of Automatic Deductions", "source_file": "2010.pdf", "ocr": False,
         "columns": ["Deductions", "1987", "2009", "2010"], "rows": [["0", "78.1", "52.2", "46.4"]],
         "check": "one reader", "text_check": "1 of 3 numbers not found in the page text"},
    ]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_path = Path(self.tmp.name) / "old.json"
        self.old_path.write_text(json.dumps(self.OLD), encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)

    def test_both_files_load_and_flags_follow_the_checks(self):
        call_command("load_tables", str(settings.BASE_DIR / "tables.json"), str(self.old_path), stdout=StringIO())
        self.assertEqual(Table.objects.count(), 1095 + 2)
        agreed = Table.objects.get(source_id="2010-p084-1")
        self.assertEqual((agreed.section, agreed.needs_review), ("trends", False))
        single = Table.objects.get(source_id="2010-p120-1")
        self.assertTrue(single.needs_review)
        self.assertIn("Only one of the two extraction methods", single.review_reason)
        self.assertIn("1 of 3 numbers not found", single.review_reason)

    def test_reloading_keeps_metrics_linked_to_their_tables(self):
        call_command("load_tables", str(settings.BASE_DIR / "tables.json"), stdout=StringIO())
        call_command("load_metrics", stdout=StringIO())
        before = Observation.objects.count()
        call_command("load_tables", str(settings.BASE_DIR / "tables.json"), str(self.old_path), stdout=StringIO())
        self.assertEqual(Observation.objects.count(), before)  # the new tables don't disturb old ones
