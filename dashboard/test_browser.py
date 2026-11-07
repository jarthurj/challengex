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

    def test_the_list_is_split_into_pages_of_100(self):
        response = self.listing()
        total = len(response.context["tables"])                  # every match, as before
        self.assertGreater(total, 200)
        page = response.content.decode()
        self.assertEqual(page.count("<tr>") - 1, 100)            # header row + one page of rows
        self.assertIn(f"<caption>Tables 1–100 of {total}</caption>", page)
        self.assertIn('<nav class="pagination" aria-label="Table pages">', page)
        self.assertIn('href="?page=2" aria-label="Page 2"', page)
        self.assertIn('aria-current="page">1</a>', page)
        second = self.listing(page="2").content.decode()
        self.assertIn(f"<caption>Tables 101–200 of {total}</caption>", second)
        self.assertIn('href="?page=1">Previous</a>', second)
        self.assertIn('href="?page=3">Next</a>', second)

    def test_page_links_keep_the_filters_and_only_checked_values(self):
        page = self.client.get(reverse("table-list"), {"year": ["2016", "2017"], "ocr": "exclude",
                                                       "q": "mail", "section": "<script>"}).content.decode()
        if 'class="pagination"' in page:
            self.assertIn("?q=mail&amp;year=2016&amp;year=2017&amp;ocr=exclude&amp;page=2", page)
        self.assertNotIn("%3Cscript", page)                       # an unknown topic never reaches a link
        self.assertNotIn("<script>", page.split("</nav>", 1)[0].split('class="pagination"')[-1])

    def test_odd_page_numbers_show_a_real_page(self):
        total = len(self.listing().context["tables"])
        last = (total + 99) // 100
        for odd, expected in (("abc", 1), ("-1", 1), ("0", 1), ("", 1), ("99999", last)):
            response = self.listing(page=odd)
            self.assertEqual(response.status_code, 200, odd)
            self.assertEqual(response.context["page"].number, expected, odd)

    def test_one_page_of_results_has_no_page_links(self):
        page = self.listing(section="packages").content.decode()
        self.assertNotIn('class="pagination"', page)
        self.assertRegex(page, r"<caption>\d+ tables?</caption>")

    def test_report_years_filter_is_labelled_like_the_others(self):
        page = self.listing().content.decode()
        # the filter's name sits above the box like the other filters; the box says what to do
        self.assertIn('<span id="year-label">Report years</span>', page)
        self.assertIn('<summary aria-labelledby="year-label year-summary" aria-describedby="year-help">'
                      '<span id="year-summary">Select years</span></summary>', page)
        self.assertIn('<small id="year-help" class="help filter-note">None ticked: every year.</small>', page)
        self.assertIn('<form method="get" class="filters has-notes">', page)
        self.assertNotIn("{#", page)                                   # no template comment leaks
        # each year's checkbox sits beside it: this rule must outrank "form.filters label" (flex-col)
        self.assertIn("form.filters .year-options label, .year-options label { @apply flex-row items-center", page)
        # the survey-forms checkbox, Filter and Clear sit in one row, centred on each other
        self.assertRegex(page, r'<div class="filter-actions">\s*<label class="inline">\s*<input type="checkbox" '
                               r'name="forms"[^>]*>\s*Include Appendix C survey forms\s*</label>\s*'
                               r'<button type="submit">Filter</button>\s*<a href="[^"]+">Clear</a>\s*</div>')
        # short option names keep OCR and Review status narrow, so all five filters share one row
        for option in ("Hide OCR", "OCR only", "Hide needs review", "Needs review only"):
            self.assertIn(f">{option}</option>", page)
        two = self.client.get(reverse("table-list"), {"year": ["2016", "2017"]}).content.decode()
        self.assertIn('<span id="year-summary">2 selected</span>', two)   # the count alone once years are ticked
        self.assertIn(".year-dropdown summary { @apply w-40 ", page)         # same width either way

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
