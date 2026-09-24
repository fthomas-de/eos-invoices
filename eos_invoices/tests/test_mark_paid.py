from datetime import date, datetime

from django.contrib.messages import get_messages
from django.urls import reverse

from unittest.mock import patch

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo

from eos_invoices.models import InvoiceConfiguration, PaymentLog
from eos_invoices.overview import build_admin_overview
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

        self.assertRedirects(response, reverse("eos_invoices:admin"), fetch_redirect_response=False)

    def test_should_only_accept_post(self):
        self.client.force_login(make_ceo(perms=("manage_sources",)))

        self.assertEqual(self.client.get(self.url).status_code, 405)


class TestAdminOverview(DueTestCase):
    @classmethod
    def setUpTestData(cls):
        alliance = EveAllianceInfo.objects.create(
            alliance_id=3001, alliance_name="A", alliance_ticker="A", executor_corp_id=1
        )
        other = EveAllianceInfo.objects.create(
            alliance_id=3002, alliance_name="B", alliance_ticker="B", executor_corp_id=2
        )
        for corporation_id, name, member_of in (
            (2001, "Alpha", alliance),
            (2002, "Beta", alliance),
            (2003, "Gamma", alliance),
            (2009, "Stranger", other),
        ):
            EveCorporationInfo.objects.create(
                corporation_id=corporation_id, corporation_name=name,
                corporation_ticker=name[:3].upper(), member_count=1, alliance=member_of,
            )
        InvoiceConfiguration.objects.create(alliance=alliance)
        Due.objects.create(corp_id=2001, amount=111)
        Due.objects.create(corp_id=2002, amount=222)
        Due.objects.create(corp_id=2002, amount=5, paid=True)
        Due.objects.create(corp_id=2009, amount=999)

    def test_should_list_every_alliance_corporation_with_open_payments(self):
        make_source()
        self.client.force_login(make_ceo(perms=("manage_sources",)))

        overview = self.client.get(reverse("eos_invoices:admin")).context["overview"]

        self.assertEqual(
            [(b.corporation.corporation_name, b.open_total) for b in overview.corporations],
            [("Alpha", 111), ("Beta", 222)],
        )
        # Gamma has nothing open; Stranger is outside the Alliance
        self.assertEqual(overview.settled_count, 1)
        self.assertEqual(overview.open_total, 333)

    def test_should_offer_the_mark_button_there(self):
        make_source()
        self.client.force_login(make_ceo(perms=("manage_sources",)))

        self.assertContains(self.client.get(reverse("eos_invoices:admin")), "Mark as paid")

    def test_should_read_each_source_once_for_all_corporations(self):
        # one query per Corporation would be 30+ queries in a real Alliance
        make_source()

        # configuration, Corporations, sources, then one query for the source
        with self.assertNumQueries(4):
            build_admin_overview()

    def test_should_say_when_a_source_was_cut_short(self):
        make_source()
        self.client.force_login(make_ceo(perms=("manage_sources",)))

        with patch("eos_invoices.overview.ADMIN_MAX_ROWS", 1):
            overview = self.client.get(reverse("eos_invoices:admin")).context["overview"]

        self.assertEqual(len(overview.problems), 1)

    def test_should_keep_ceos_out(self):
        self.client.force_login(make_ceo())

        self.assertEqual(self.client.get(reverse("eos_invoices:admin")).status_code, 302)

    def test_should_not_offer_mark_buttons_on_the_normal_overview(self):
        make_source()
        self.client.force_login(make_ceo(perms=("basic_access", "manage_sources")))

        self.assertNotContains(self.client.get(reverse("eos_invoices:index")), "Mark as paid")


class TestPaymentLog(DueTestCase):
    def setUp(self):
        self.source = make_source(name="PvE Tax", reason_template="{corp_id}/{month:02d}/{year}")
        self.row = Due.objects.create(corp_id=2001, amount=1500000, month=7)
        self.admin = make_ceo(perms=("manage_sources",))
        self.url = reverse("eos_invoices:mark_paid", args=[self.source.pk])

    def test_should_record_who_marked_what(self):
        self.client.force_login(self.admin)

        self.client.post(self.url, {"row": self.row.pk})

        entry = PaymentLog.objects.get()
        self.assertEqual(entry.user, self.admin)
        self.assertEqual(entry.user_name, "ceo main")
        self.assertEqual(entry.source_name, "PvE Tax")
        self.assertEqual(entry.row_pk, str(self.row.pk))
        self.assertEqual(entry.corporation_id, 2001)
        self.assertEqual(entry.amount, 1500000)
        self.assertEqual(entry.reason, "2001/07/2026")

    def test_should_refuse_a_row_that_is_already_paid(self):
        # a second click must not leave a second entry for nothing
        self.client.force_login(self.admin)

        self.client.post(self.url, {"row": self.row.pk})
        self.client.post(self.url, {"row": self.row.pk})

        self.assertEqual(PaymentLog.objects.count(), 1)

    def test_should_keep_the_entry_when_the_source_is_deleted(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, {"row": self.row.pk})

        self.source.delete()

        self.assertEqual(PaymentLog.objects.get().source_name, "PvE Tax")

    def test_should_show_the_log_to_admins_only(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, {"row": self.row.pk})

        self.assertContains(self.client.get(reverse("eos_invoices:log")), "2001/07/2026")

        self.client.force_login(make_ceo("other"))
        self.assertEqual(self.client.get(reverse("eos_invoices:log")).status_code, 302)

    def test_should_wire_up_the_filter_dropdown(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, {"row": self.row.pk})  # the table needs a row to render

        response = self.client.get(reverse("eos_invoices:log"))

        self.assertContains(response, 'id="eos-invoices-log-table"')
        # the static manifest puts a hash before .js; no version number here,
        # Alliance Auth's own bundle picks the version
        self.assertContains(response, "datatables-filterdropdown.min")
        self.assertContains(response, "eos_invoices/js/log")
        self.assertContains(response, 'id="eos-invoices-log-labels"')
        self.assertContains(response, "All sources")


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

    def test_should_make_the_model_dropdown_searchable(self):
        self.client.force_login(make_ceo(perms=("manage_sources",)))

        form = self.client.get(reverse("eos_invoices:source_add")).context["form"]

        self.assertIn("data-eos-invoices-search", form.fields["model_label"].widget.attrs)


class TestMarkSelectedPaid(DueTestCase):
    def setUp(self):
        alliance = EveAllianceInfo.objects.create(
            alliance_id=3001, alliance_name="A", alliance_ticker="A", executor_corp_id=1
        )
        for corporation_id, name in ((2001, "Alpha"), (2002, "Beta")):
            EveCorporationInfo.objects.create(
                corporation_id=corporation_id, corporation_name=name,
                corporation_ticker=name[:3].upper(), member_count=1, alliance=alliance,
            )
        InvoiceConfiguration.objects.create(alliance=alliance)
        self.source = make_source()
        self.alpha = Due.objects.create(corp_id=2001, amount=100)
        self.beta = Due.objects.create(corp_id=2002, amount=200)
        self.admin = make_ceo(perms=("manage_sources",))
        self.url = reverse("eos_invoices:mark_selected_paid")

    def box(self, row, corporation_id=None):
        return f"{self.source.pk}:{corporation_id or row.corp_id}:{row.pk}"

    def post(self, *values):
        return self.client.post(self.url, {"selected": list(values)})

    def paid(self):
        return set(Due.objects.filter(paid=True).values_list("pk", flat=True))

    def test_should_mark_ticked_rows_across_corporations(self):
        self.client.force_login(self.admin)

        self.post(self.box(self.alpha), self.box(self.beta))

        self.assertEqual(self.paid(), {self.alpha.pk, self.beta.pk})
        self.assertEqual(
            sorted(PaymentLog.objects.values_list("corporation_id", flat=True)), [2001, 2002]
        )

    def test_should_leave_a_row_nobody_ticked(self):
        # arrived after the page was loaded, or simply not ticked
        self.client.force_login(self.admin)

        self.post(self.box(self.alpha))

        self.assertEqual(self.paid(), {self.alpha.pk})

    def test_should_skip_a_row_listed_under_the_wrong_corporation(self):
        self.client.force_login(self.admin)

        response = self.post(self.box(self.beta, corporation_id=2001), "garbage")

        self.assertEqual(self.paid(), set())
        notes = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn(
            "2 payments were skipped: already paid, gone or of another Corporation.", notes
        )

    def test_should_skip_rows_that_are_already_paid(self):
        self.alpha.paid = True
        self.alpha.save()
        self.client.force_login(self.admin)

        response = self.post(self.box(self.alpha), self.box(self.beta))

        self.assertEqual(PaymentLog.objects.count(), 1)
        notes = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Marked 1 payment as paid.", notes)

    def test_should_keep_ceos_out(self):
        self.client.force_login(make_ceo("other"))

        self.post(self.box(self.alpha))

        self.assertEqual(self.paid(), set())

    def test_should_offer_a_box_per_row_and_the_select_all_boxes(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("eos_invoices:admin"))

        self.assertContains(response, f'value="{self.box(self.alpha)}"')
        self.assertContains(response, f'value="{self.box(self.beta)}"')
        self.assertContains(response, 'data-eos-invoices-select-all="all"')
        self.assertContains(response, f'data-eos-invoices-select-all="2001-{self.source.pk}"')
        self.assertContains(response, "Mark selected as paid")

    def test_should_still_mark_a_single_row_from_the_same_form(self):
        # the per-row button posts the big form to mark_paid via formaction;
        # ticked boxes travel along and must not be marked by it
        self.client.force_login(self.admin)

        self.client.post(
            reverse("eos_invoices:mark_paid", args=[self.source.pk]),
            {"row": self.alpha.pk, "selected": [self.box(self.beta)]},
        )

        self.assertEqual(self.paid(), {self.alpha.pk})


class TestSortableTables(DueTestCase):
    def test_should_make_every_table_page_sortable(self):
        self.client.force_login(make_ceo(perms=("basic_access", "manage_sources")))

        for name in ("index", "admin", "log", "sources"):
            with self.subTest(name):
                response = self.client.get(reverse(f"eos_invoices:{name}"))
                # log sorts through its own log.js, which also wires up its
                # filterDropDown - the others through the shared tables.js
                self.assertContains(response, "eos_invoices/js/log" if name == "log" else "eos_invoices/js/tables")
                # the static manifest puts a hash before .js
                self.assertContains(response, "DataTables/2.3.8/js/dataTables.min")

    def test_should_sort_amounts_by_their_raw_value(self):
        # "1.500.000 ISK" would sort as text; the cell carries the number
        alliance = EveAllianceInfo.objects.create(
            alliance_id=3001, alliance_name="A", alliance_ticker="A", executor_corp_id=1
        )
        InvoiceConfiguration.objects.create(alliance=alliance)
        make_source()
        Due.objects.create(corp_id=2001, amount=1500000)
        self.client.force_login(make_ceo())

        self.assertContains(
            self.client.get(reverse("eos_invoices:index")), 'data-order="1500000.00"'
        )
