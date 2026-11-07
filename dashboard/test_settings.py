"""The Settings page and what "Enable advanced settings" shows on Browse tables, Trends and By year."""
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from .context_processors import ADVANCED_KEY
from .models import Observation
from .testdata import load_real_tables

STATUS_TH = '<th scope="col">Status</th>'
SOURCE_ID_TH = '<th scope="col">Source ID</th>'
VERIFICATION_TH = '<th scope="col">Verification</th>'
NOTES_TH = '<th scope="col">Notes</th>'


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
        self.assertIn('name="advanced" value="1"', page)
        self.assertNotIn("checked", page)
        self.assertIn('>Settings</a>', self.client.get(reverse("dashboard")).content.decode())

    def test_saving_turns_it_on_and_off(self):
        response = self.client.post(reverse("settings"), {"advanced": "1"}, follow=True)
        self.assertRedirects(response, reverse("settings"))
        self.assertIs(self.client.session[ADVANCED_KEY], True)
        self.assertContains(response, "advanced settings are on")
        self.assertContains(response, "checked")
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
        self.assertNotIn("<td>2021-p009-1</td>", page)
        self.assertIn(">Needs review</span>", page)    # still flagged, next to the title
        self.assertIn(">OCR</span>", page)
        self.advanced_on()
        page = self.client.get(url).content.decode()
        self.assertIn(STATUS_TH, page)
        self.assertIn(SOURCE_ID_TH, page)
        self.assertIn("<td>2021-p009-1</td>", page)
        self.assertEqual(page.count(">Needs review</span>"), page.count("<tr>") - 1)   # once per row, not twice

    def test_trends_hides_verification_and_notes_but_tags_unverified_values(self):
        Observation.objects.filter(metric__slug="fcm-received-total").update(notes="Checked by hand")
        page = self.client.get(reverse("trends"), {"trend": "fcm-received-total"}).content.decode()
        self.assertNotIn(VERIFICATION_TH, page)
        self.assertNotIn(NOTES_TH, page)
        self.assertNotIn("Checked by hand", page)
        self.assertIn('<span class="review">(unverified)</span>', page)
        self.advanced_on()
        page = self.client.get(reverse("trends"), {"trend": "fcm-received-total"}).content.decode()
        self.assertIn(VERIFICATION_TH, page)
        self.assertIn(NOTES_TH, page)
        self.assertIn("Checked by hand", page)
        self.assertNotIn("(unverified)", page)

    def test_verified_values_get_no_tag(self):
        Observation.objects.update(verified=True)
        page = self.client.get(reverse("trends"), {"trend": "fcm-received-total"}).content.decode()
        self.assertNotIn("(unverified)", page)

    def test_year_page_hides_verification_and_notes_for_all_households_and_groups(self):
        Observation.objects.filter(fiscal_year=2025).update(notes="A reviewer's note")
        url = reverse("year-detail", args=[2025])
        page = self.client.get(url).content.decode()
        self.assertNotIn(VERIFICATION_TH, page)
        self.assertNotIn(NOTES_TH, page)
        self.assertNotIn("A reviewer&#x27;s note", page)
        self.assertIn('<span class="review">(unverified)</span>', page)
        self.advanced_on()
        page = self.client.get(url).content.decode()
        tables = page.count("<table>")
        self.assertGreater(tables, 1)                     # all households plus household groups
        self.assertEqual(page.count(VERIFICATION_TH), tables)
        self.assertEqual(page.count(NOTES_TH), tables)
        self.assertIn("A reviewer&#x27;s note", page)
        self.assertNotIn("(unverified)", page)

    def test_exports_keep_verification_whatever_the_setting(self):
        csv = self.client.get(reverse("year-csv", args=[2025])).content.decode()
        self.assertIn("erif", csv.splitlines()[0])
        page = self.client.get(reverse("trends"), {"trend": "fcm-received-total"}).content.decode()
        self.assertIn("Verified against the PDF", page)     # the copy-with-sources header
