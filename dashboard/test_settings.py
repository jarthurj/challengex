"""The Settings page and what "Enable advanced settings" shows on Browse tables, Trends and By year."""
import re
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from .context_processors import ADVANCED_KEY
from .models import Observation
from .testdata import load_real_tables

STATUS_TH = '<th scope="col" class="nowrap">Status</th>'
SOURCE_ID_TH = '<th scope="col" class="nowrap">Source ID</th>'
VERIFICATION_TH = '<th scope="col">Verification</th>'
NOTES_TH = '<th scope="col">Notes</th>'
ROW_NOTE = '<details class="row-note"><summary>Note'


def checkbox(page):
    """The advanced-settings <input> tag alone, so other text on the page can't affect a check."""
    return re.search(r'<input type="checkbox" name="advanced"[^>]*>', page).group(0)


class SettingsPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_real_tables()
        call_command("load_metrics", stdout=StringIO())

    def advanced_on(self):
        self.client.post(reverse("settings"), {"advanced": "1"})

    def test_page_is_in_the_navigation_and_off_by_default(self):
        page = self.client.get(reverse("settings")).content.decode()
        self.assertIn('aria-current="page">Settings</a>', page)
        self.assertNotIn("checked", checkbox(page))
        self.assertIn('>Settings</a>', self.client.get(reverse("dashboard")).content.decode())
        # at the right end of the navigation bar
        self.assertIn(f'<a class="nav-end" href="{reverse("settings")}"', page)

    def test_ai_list_shows_the_unreviewed_tag_only_in_advanced_mode(self):
        tag = "AI-generated · not yet reviewed</span>"
        url = reverse("ai-summaries") + "?view=long"
        page = self.client.get(url).content.decode()
        self.assertIn('class="ai-item"', page)
        self.assertNotIn(tag, page)
        self.assertIn("AI-generated, none reviewed by a person yet", page)   # the list's status line still says so
        self.advanced_on()
        self.assertIn(tag, self.client.get(url).content.decode())

    def test_saving_turns_it_on_and_off(self):
        response = self.client.post(reverse("settings"), {"advanced": "1"}, follow=True)
        self.assertRedirects(response, reverse("settings"))
        self.assertIs(self.client.session[ADVANCED_KEY], True)
        self.assertContains(response, "advanced settings are on")
        self.assertIn("checked", checkbox(response.content.decode()))
        self.client.post(reverse("settings"), {})            # an unticked checkbox sends nothing
        self.assertIs(self.client.session[ADVANCED_KEY], False)

    def test_only_the_checkbox_value_turns_it_on(self):
        for odd in ("yes", "true", "<script>", "11"):
            self.client.post(reverse("settings"), {"advanced": odd})
            self.assertIs(self.client.session[ADVANCED_KEY], False, odd)

    def test_csrf_is_required_and_other_methods_refused(self):
        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(strict.post(reverse("settings"), {"advanced": "1"}).status_code, 403)
        self.assertNotIn(ADVANCED_KEY, strict.session)
        self.assertEqual(self.client.put(reverse("settings")).status_code, 405)

    def test_browse_tables_hides_status_and_source_id_but_keeps_the_badges(self):
        url = reverse("table-list") + "?ocr=only"
        page = self.client.get(url).content.decode()
        self.assertNotIn(STATUS_TH, page)
        self.assertNotIn(SOURCE_ID_TH, page)
        self.assertNotIn("2021-p009-1</td>", page)
        self.assertIn(">Needs review</span>", page)    # still flagged, next to the title
        self.assertIn(">OCR</span>", page)
        self.advanced_on()
        page = self.client.get(url).content.decode()
        self.assertIn(STATUS_TH, page)
        self.assertIn(SOURCE_ID_TH, page)
        self.assertIn('<td class="nowrap">2021-p009-1</td>', page)       # one line, not "2021-" / "p009-1"
        self.assertIn('<th scope="col" class="fill">Title</th>', page)    # Title takes the spare width
        self.assertEqual(page.count(">Needs review</span>"), page.count("<tr>") - 1)   # once per row, not twice

    def test_empty_listing_spans_every_column(self):
        url = reverse("table-list") + "?q=no-table-is-called-this"
        self.assertContains(self.client.get(url), '<td colspan="5">No matching tables found.</td>')
        self.advanced_on()
        self.assertContains(self.client.get(url), '<td colspan="7">No matching tables found.</td>')

    def test_trends_folds_verification_and_notes_into_the_source_cell(self):
        series = Observation.objects.filter(metric__slug="fcm-received-total")
        series.update(notes="")
        series.filter(fiscal_year=2007).update(notes="USPS's parts exceed the printed total")
        url, params = reverse("trends"), {"trend": "fcm-received-total"}
        page = self.client.get(url, params).content.decode()
        self.assertNotIn(VERIFICATION_TH, page)
        self.assertNotIn(NOTES_TH, page)
        self.assertIn('<span class="review">(unverified)</span>', page)
        self.assertEqual(page.count(ROW_NOTE), 1)            # only the row that has a note
        self.assertIn('<span class="sr-only"> on FY2007</span>', page)
        self.assertIn("USPS&#x27;s parts exceed the printed total", page)
        self.advanced_on()
        page = self.client.get(url, params).content.decode()
        self.assertIn(VERIFICATION_TH, page)
        self.assertIn(NOTES_TH, page)
        self.assertNotIn(ROW_NOTE, page)
        self.assertIn("USPS&#x27;s parts exceed the printed total", page)
        self.assertNotIn("(unverified)", page)

    def test_notes_are_escaped_in_the_folded_view(self):
        Observation.objects.filter(metric__slug="fcm-received-total").update(notes="<script>bad()</script>")
        page = self.client.get(reverse("trends"), {"trend": "fcm-received-total"}).content.decode()
        self.assertIn("&lt;script&gt;bad()&lt;/script&gt;", page)
        self.assertNotIn("<script>bad()</script>", page)

    def test_verified_values_get_no_tag(self):
        Observation.objects.update(verified=True)
        page = self.client.get(reverse("trends"), {"trend": "fcm-received-total"}).content.decode()
        self.assertNotIn("(unverified)", page)

    def test_year_page_folds_verification_and_notes_for_all_households_and_groups(self):
        Observation.objects.filter(fiscal_year=2025).update(notes="A reviewer's note")
        url = reverse("year-detail", args=[2025])
        page = self.client.get(url).content.decode()
        self.assertNotIn(VERIFICATION_TH, page)
        self.assertNotIn(NOTES_TH, page)
        self.assertIn('<span class="review">(unverified)</span>', page)
        self.assertEqual(page.count(ROW_NOTE), page.count('<th scope="row">'))   # every row has a note here
        self.assertIn("A reviewer&#x27;s note", page)
        self.advanced_on()
        page = self.client.get(url).content.decode()
        tables = page.count("<table>")
        self.assertGreater(tables, 1)                     # all households plus household groups
        self.assertEqual(page.count(VERIFICATION_TH), tables)
        self.assertEqual(page.count(NOTES_TH), tables)
        self.assertNotIn(ROW_NOTE, page)
        self.assertIn("A reviewer&#x27;s note", page)
        self.assertNotIn("(unverified)", page)

    def test_exports_keep_verification_whatever_the_setting(self):
        trend = {"trend": "fcm-received-total"}
        csv_before = self.client.get(reverse("year-csv", args=[2025])).content
        copy_before = self.copy_text(trend)
        self.assertIn(b"erif", csv_before.splitlines()[0])
        self.assertIn("Verified against the PDF", copy_before)
        self.advanced_on()
        self.assertEqual(self.client.get(reverse("year-csv", args=[2025])).content, csv_before)
        self.assertEqual(self.copy_text(trend), copy_before)

    def copy_text(self, params):
        page = self.client.get(reverse("trends"), params).content.decode()
        start = page.index('id="chart-copy">')
        return page[start:page.index("</pre>", start)]
