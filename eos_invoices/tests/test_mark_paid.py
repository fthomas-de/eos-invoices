from datetime import date, datetime

from django.urls import reverse

from allianceauth.eveonline.models import EveAllianceInfo

from eos_invoices.models import InvoiceConfiguration
from eos_invoices.sources import SourceError, mark_paid, paid_marker

from .base import Due, DueTestCase, make_ceo, make_source


class TestPaidMarker(DueTestCase):
    def test_should_set_a_boolean(self):
        self.assertIs(paid_marker(make_source())(), True)

    def test_should_set_the_configured_value(self):
        source = make_source(paid_field="month", paid_mode="equals", paid_value="12")

        self.assertEqual(paid_marker(source)(), 12)

    def test_should_stamp_a_date_or_datetime(self):
        stamp = make_source(name="a", paid_field="paid_at", paid_mode="not_empty")
        day = make_source(name="b", paid_field="created", paid_mode="not_empty")

        self.assertIsInstance(paid_marker(stamp)(), datetime)
        self.assertIsInstance(paid_marker(day)(), date)

    def test_should_refuse_what_has_no_obvious_value(self):
        # no sensible text means "paid"
        text = make_source(name="a", paid_field="state", paid_mode="not_empty")
        # writing across a relation would change a row other payments share
        related = make_source(
            name="b", paid_field="corporation__war_eligible", paid_mode="true"
        )

        self.assertIsNone(paid_marker(text))
        self.assertIsNone(paid_marker(related))


class TestMarkPaid(DueTestCase):
    def test_should_save_the_row_as_paid(self):
        row = Due.objects.create(corp_id=2001, amount=10)

        mark_paid(make_source(), row.pk)

        row.refresh_from_db()
        self.assertTrue(row.paid)

    def test_should_report_a_row_that_is_gone(self):
        with self.assertRaises(SourceError):
            mark_paid(make_source(), 999999)


class TestMarkPaidView(DueTestCase):
    def setUp(self):
        self.source = make_source()
        self.row = Due.objects.create(corp_id=2001, amount=10)
        self.url = reverse("eos_invoices:mark_paid", args=[self.source.pk])

    def test_should_keep_ceos_out(self):
        self.client.force_login(make_ceo())

        response = self.client.post(self.url, {"row": self.row.pk})

        self.assertEqual(response.status_code, 302)
        self.row.refresh_from_db()
        self.assertFalse(self.row.paid)

    def test_should_mark_and_return_to_the_page(self):
        self.client.force_login(make_ceo(perms=("manage_sources",)))
        back = reverse("eos_invoices:index") + "?corp=2001"

        response = self.client.post(self.url, {"row": self.row.pk, "next": back})

        self.assertRedirects(response, back, fetch_redirect_response=False)
        self.row.refresh_from_db()
        self.assertTrue(self.row.paid)

    def test_should_not_redirect_off_site(self):
        self.client.force_login(make_ceo(perms=("manage_sources",)))

        response = self.client.post(self.url, {"row": self.row.pk, "next": "https://evil.example/"})

        self.assertRedirects(response, reverse("eos_invoices:index"), fetch_redirect_response=False)

    def test_should_only_accept_post(self):
        self.client.force_login(make_ceo(perms=("manage_sources",)))

        self.assertEqual(self.client.get(self.url).status_code, 405)


class TestAdminOverview(DueTestCase):
    @classmethod
    def setUpTestData(cls):
        alliance = EveAllianceInfo.objects.create(
            alliance_id=3001, alliance_name="A", alliance_ticker="A", executor_corp_id=1
        )
        InvoiceConfiguration.objects.create(alliance=alliance)
        Due.objects.create(corp_id=2001, amount=111)
        Due.objects.create(corp_id=2002, amount=222)

    def amounts(self, response):
        return [i.amount for r in response.context["overview"].results for i in r.invoices]

    def test_should_show_an_admin_their_own_corporation_with_mark_buttons(self):
        make_source()
        self.client.force_login(make_ceo(perms=("manage_sources",)))

        response = self.client.get(reverse("eos_invoices:index"), {"corp": 2002})

        # a corp parameter from an old link changes nothing
        self.assertEqual(self.amounts(response), [111])
        self.assertContains(response, "Mark as paid")

    def test_should_not_offer_mark_buttons_to_a_ceo(self):
        make_source()
        self.client.force_login(make_ceo())

        self.assertNotContains(self.client.get(reverse("eos_invoices:index")), "Mark as paid")


class TestSearchableDropdowns(DueTestCase):
    def test_should_make_alliance_and_pay_to_searchable(self):
        self.client.force_login(make_ceo(perms=("manage_sources",)))

        for url in (reverse("eos_invoices:settings"), reverse("eos_invoices:source_add")):
            with self.subTest(url):
                response = self.client.get(url)
                self.assertContains(response, "data-eos-invoices-search")
                self.assertContains(response, "tom-select.complete.min.js")
                # the library alone is unreadable on a dark theme
                self.assertContains(response, "eos_invoices/css/tom-select-theme")
