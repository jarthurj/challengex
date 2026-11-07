import unittest
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .display import review_reasons, section_of
from .models import Table


class SectionTests(SimpleTestCase):
    def test_sections_from_corrected_numbers(self):
        cases = {
            ("Table E.2", "Household Mail Volume"): "summary",
            ("Table 1.3", "Total Domestic Mail Flows"): "volumes",
            ("Table 2.4", "Income by Education"): "demographics",
            ("Figure 5.3", "Advertising Mail Behavioral Trends"): "advertising",
            ("Table 7.4", "Satisfaction with Package Delivery"): "packages",
            ("Table A8-1", "First Class Mail Received by Type"): "trends",
            ("Table A-6", "Bills Paid by Method"): "trends",
            ("Table B.12", "Strata and Regions"): "methodology",
            ("", "Survey form (Appendix C: diary letter, instructions, or blank answer sheet)"): "survey_form",
            ("", "Untitled"): "other",
        }
        for (number, title), section in cases.items():
            self.assertEqual(section_of(number, title), section, number or title)

    def test_fy2003_chapters_are_numbered_differently(self):
        self.assertEqual(section_of("Table 5.4", "Transactions Mail Received by Income and Age", 2003), "transactions")
        self.assertEqual(section_of("Table 8.6", "Postal Service Sent and Received Packages", 2003), "packages")
        self.assertEqual(section_of("Table 5.4", "Ad Mail Received by Income and Education", 2005), "advertising")

    def test_review_reasons(self):
        self.assertEqual(review_reasons(False, "Table 3.1", ["Sector", "2021", "2022"]), [])
        reasons = review_reasons(True, "Figure 2.1b", ["", "Column 2"])
        self.assertEqual(len(reasons), 3)
        self.assertIn("OCR", reasons[0])
        self.assertIn("Chart data", reasons[1])
        self.assertIn("Column N", reasons[2])


class BrowserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_tables", str(settings.BASE_DIR / "tables.json"), stdout=StringIO())

    def listing(self, **params):
        response = self.client.get(reverse("table-list"), params)
        self.assertEqual(response.status_code, 200)
        return response

    def test_every_table_gets_a_section_and_ocr_tables_need_review(self):
        self.assertFalse(Table.objects.filter(section__in=["", "other"]).exists())
        self.assertEqual(Table.objects.filter(section="survey_form").count(), 49)
        self.assertEqual(Table.objects.filter(section="trends", year__gte=2016).count(), 154)
        self.assertFalse(Table.objects.filter(ocr=True, needs_review=False).exists())
        self.assertFalse(Table.objects.filter(table_number__startswith="Figure", needs_review=False).exists())

    def test_survey_forms_hidden_unless_asked_for(self):
        default = self.listing()
        self.assertNotIn(Table.objects.filter(section="survey_form").first(), default.context["tables"])
        self.assertContains(default, "49 Appendix C survey forms")
        everything = self.listing(forms="1")
        self.assertEqual(len(everything.context["tables"]), 1095)
        self.assertEqual(len(self.listing(section="survey_form").context["tables"]), 49)

    def test_topic_ocr_and_review_filters(self):
        packages = self.listing(section="packages").context["tables"]
        self.assertTrue(packages and all(t.section == "packages" for t in packages))
        self.assertTrue(all(t.ocr for t in self.listing(ocr="only").context["tables"]))
        self.assertFalse(any(t.ocr for t in self.listing(ocr="exclude").context["tables"]))
        flagged = self.listing(review="only").context["tables"]
        self.assertTrue(flagged and all(t.needs_review for t in flagged))
        self.assertFalse(any(t.needs_review for t in self.listing(review="ok").context["tables"]))
        combined = self.listing(section="advertising", year="2024", review="ok").context["tables"]
        self.assertTrue(all(t.section == "advertising" and t.year == 2024 and not t.needs_review for t in combined))

    def test_unexpected_filter_values_are_ignored(self):
        baseline = len(self.listing().context["tables"])
        odd = self.listing(section="<script>", ocr="x", review="1; DROP TABLE", year="abc")
        self.assertEqual(len(odd.context["tables"]), baseline)
        # nothing from the hostile values reaches the page (the nav's own script is expected)
        self.assertEqual(odd.content.count(b"<script"), self.listing().content.count(b"<script"))
        self.assertNotContains(odd, "DROP TABLE")

    def test_list_shows_text_badges(self):
        page = self.listing(ocr="only").content.decode()
        self.assertIn(">Needs review</span>", page)
        self.assertIn(">OCR</span>", page)

    def test_report_years_filter_is_labelled_like_the_others(self):
        page = self.listing().content.decode()
        # the filter's name sits above the box like the other filters; the box says what to do
        self.assertIn('<span id="year-label">Report years</span>', page)
        self.assertIn('<summary aria-labelledby="year-label year-summary" aria-describedby="year-help">'
                      '<span id="year-summary">Select years</span></summary>', page)
        self.assertIn('<small id="year-help" class="help filter-note">None ticked: every year.</small>', page)
        self.assertIn('<form method="get" class="filters has-notes">', page)
        self.assertNotIn("{#", page)                                   # no template comment leaks
        two = self.client.get(reverse("table-list"), {"year": ["2016", "2017"]}).content.decode()
        self.assertIn('<span id="year-summary">Select years (2 selected)</span>', two)

    def test_table_page_explains_review_and_links_the_pdf_page(self):
        table = Table.objects.filter(ocr=True).first()
        page = self.client.get(reverse("table-detail", args=[table.pk])).content.decode()
        self.assertIn("Check this table against the PDF page", page)
        self.assertIn("Read by OCR from a scanned page", page)
        self.assertIn(f"page {table.page}", page)
        if (settings.BASE_DIR / "docs" / f"{table.year}.pdf").exists():
            self.assertIn(f"{reverse('source-pdf', args=[table.year])}#page={table.page}", page)
        else:
            self.assertIn("isn't in this copy of", page)
        clean = Table.objects.filter(needs_review=False).exclude(section="survey_form").first()
        self.assertNotIn("Check this table against", self.client.get(reverse("table-detail", args=[clean.pk])).content.decode())

    def test_missing_report_pdf_is_a_404(self):
        self.assertEqual(self.client.get(reverse("source-pdf", args=[1999])).status_code, 404)

    @unittest.skipUnless((settings.BASE_DIR / "docs" / "2023.pdf").exists(), "docs/ PDFs are git-ignored")
    def test_report_pdf_is_served_inline(self):
        response = self.client.get(reverse("source-pdf", args=[2023]))
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response["Content-Disposition"].startswith("inline"))
        response.close()
