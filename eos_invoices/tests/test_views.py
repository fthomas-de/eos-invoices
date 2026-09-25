import importlib
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.apps import apps as django_apps
from django.contrib.auth.models import Permission
from django.test import RequestFactory
from django.urls import reverse

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo

import eos_invoices
from eos_invoices.auth_hooks import InvoicesDashboardHook, InvoicesMenuItem
from eos_invoices.models import InvoiceConfiguration, PaymentLog, PaymentSource
from eos_invoices.views import dashboard_overview

from .base import Due, DueTestCase, configure_alliance, make_ceo, make_corporation, make_source

# every page behind a permission, GET only
PAGES = ("index", "admin", "log", "sources", "source_add", "source_fields", "settings")
MAINTENANCE_PAGES = PAGES[1:]


class TestAccess(DueTestCase):
    """Who may open which page; the POST views check the same, next to their tests."""

    def status(self, name):
        return self.client.get(reverse(f"eos_invoices:{name}")).status_code

    def test_should_keep_users_without_permission_out(self):
        self.client.force_login(make_ceo(perms=()))

        for name in PAGES:
            with self.subTest(name):
                self.assertEqual(self.status(name), 302)

    def test_should_keep_a_ceo_out_of_the_maintenance_pages(self):
        self.client.force_login(make_ceo())

        self.assertEqual(self.status("index"), 200)
        for name in MAINTENANCE_PAGES:
            with self.subTest(name):
                self.assertEqual(self.status(name), 302)

    def test_should_show_the_menu_entry_only_with_a_permission(self):
        request = RequestFactory().get("/")

        request.user = make_ceo("nobody", perms=())
        self.assertEqual(InvoicesMenuItem().render(request), "")

        # an admin who is no CEO is sent to the admin overview
        request.user = make_ceo("keeper", perms=("manage_sources",))
        self.assertIn(f'href="{reverse("eos_invoices:admin")}"', InvoicesMenuItem().render(request))


class TestPageFrame(DueTestCase):
    """What every page of the app shares: header, navigation, footer."""

    def setUp(self):
        self.client.force_login(make_ceo(perms=("manage_sources",)))

    def page(self, name="sources", language="en"):
        return self.client.get(reverse(f"eos_invoices:{name}"), HTTP_ACCEPT_LANGUAGE=language)

    def test_should_note_generated_texts(self):
        self.assertContains(
            self.page(), "The texts of this app are machine-generated and may be inaccurate."
        )

    def test_should_use_alliance_auths_page_header(self):
        response = self.page()

        self.assertContains(response, 'class="aa-page-header')
        self.assertContains(response, eos_invoices.__version__)

    def test_should_write_the_navigation_like_alliance_auth(self):
        # the theme colours the active link, as in groupmanagement
        sources = reverse("eos_invoices:sources")

        for name in ("sources", "source_add"):
            with self.subTest(name):
                response = self.page(name)
                self.assertContains(response, f'class="nav-link active" href="{sources}"')
                self.assertNotContains(response, "text-warning")

    def test_should_hand_datatables_its_translation(self):
        # the static manifest puts a hash before .json
        self.assertContains(
            self.page(language="de"),
            'data-eos-invoices-datatables-language="/static/allianceauth/libs/DataTables/Plugins/2.3.6/i18n/de-DE.',
        )
        # English needs none
        self.assertContains(
            self.page(language="en"), 'data-eos-invoices-datatables-language=""'
        )


class TestDashboardWidget(DueTestCase):
    """dashboard_overview: the CEO's overview as an Alliance Auth dashboard widget."""

    def alliance_ceo(self, **kwargs):
        configure_alliance()
        return make_ceo(**kwargs)

    def render(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return dashboard_overview(request)

    def test_should_hide_without_the_permission(self):
        # a real open payment, so a missing permission check is not
        # accidentally covered by the "nothing outstanding" one instead
        make_source()
        Due.objects.create(corp_id=2001, amount=10)

        self.assertEqual(self.render(self.alliance_ceo(perms=())), "")

    def test_should_hide_when_the_overview_only_explains_itself(self):
        # no Alliance configured: build_overview sets a notice, and the full
        # page explains it - a widget would only show an empty box
        self.assertEqual(self.render(make_ceo()), "")

    def test_should_show_a_nothing_outstanding_state_instead_of_hiding(self):
        # configured, permitted, but no source or nothing owed - the widget
        # still shows, so a CEO sees at a glance that nothing is missing
        # rather than wondering whether it failed to load
        html = self.render(self.alliance_ceo())

        self.assertIn("eos-invoices-dashboard-overview", html)
        self.assertIn("Nothing outstanding.", html)

    def test_should_show_the_total_and_link_to_the_full_overview(self):
        make_source(name="PvE Tax")
        Due.objects.create(corp_id=2001, amount=1500000)
        user = self.alliance_ceo(corp_id=2001)

        html = self.render(user)

        self.assertIn("eos-invoices-dashboard-overview", html)
        self.assertIn("PvE Tax", html)
        self.assertIn("1.500.000 ISK", html)
        self.assertIn(reverse("eos_invoices:index"), html)

    def test_should_show_nothing_outstanding_when_the_only_row_is_still_in_progress(self):
        # the amount owed for the current month can still change; the
        # compact widget only sums what is actually settled - with nothing
        # else settled, that leaves the "nothing outstanding" state rather
        # than the row's own (still changing) amount
        make_source(month_field="month", year_field="year")
        Due.objects.create(corp_id=2001, amount=1500000, month=7, year=2026)
        user = self.alliance_ceo(corp_id=2001)

        with patch("eos_invoices.sources.timezone.localdate", return_value=date(2026, 7, 15)):
            html = self.render(user)

        self.assertIn("Nothing outstanding.", html)
        self.assertNotIn("1.500.000", html)

    def test_should_sum_only_the_settled_rows(self):
        make_source(month_field="month", year_field="year")
        Due.objects.create(corp_id=2001, amount=500000, month=6, year=2026)
        Due.objects.create(corp_id=2001, amount=1500000, month=7, year=2026)
        user = self.alliance_ceo(corp_id=2001)

        with patch("eos_invoices.sources.timezone.localdate", return_value=date(2026, 7, 15)):
            html = self.render(user)

        self.assertIn("500.000 ISK", html)
        self.assertNotIn("2.000.000", html)

    def test_should_not_show_a_broken_source(self):
        # nothing to sum from it, and no error text leaked onto the dashboard
        make_source(name="Broken", amount_field="gone")
        make_source(name="Working")
        Due.objects.create(corp_id=2001, amount=50)
        user = self.alliance_ceo(corp_id=2001)

        html = self.render(user)

        self.assertNotIn("Broken", html)
        self.assertIn("Working", html)

    def test_should_render_through_the_registered_hook_without_raising(self):
        make_source()
        Due.objects.create(corp_id=2001, amount=10)
        request = RequestFactory().get("/")
        request.user = self.alliance_ceo(corp_id=2001)

        html = InvoicesDashboardHook().render(request)

        self.assertIn("eos-invoices-dashboard-overview", html)


class TestIndex(DueTestCase):
    def setUp(self):
        configure_alliance()
        self.client.force_login(make_ceo())

    def index(self, **params):
        return self.client.get(reverse("eos_invoices:index"), params)

    def test_should_list_open_payments_with_their_reason(self):
        make_source(name="Mining tax", reason_template="{corp_id}/{month:02d}/{year}")
        Due.objects.create(corp_id=2001, amount=1234567, month=3)

        response = self.index()

        self.assertContains(response, "Mining tax")
        self.assertContains(response, "2001/03/2026")

    def test_should_hide_the_reason_for_the_current_month(self):
        make_source(
            month_field="month", year_field="year", reason_template="{corp_id}/{month}/{year}"
        )
        Due.objects.create(corp_id=2001, amount=100, month=7)

        with patch("eos_invoices.sources.timezone.localdate", return_value=date(2026, 7, 15)):
            response = self.index()

        self.assertNotContains(response, "2001/7/2026")
        self.assertContains(response, "Not shown for the current month")

    def test_should_not_offer_the_amount_of_a_month_in_progress_for_copying(self):
        # its amount can still change; the row and its amount still show,
        # but nothing about it is offered for copying yet
        make_source(month_field="month", year_field="year")
        Due.objects.create(corp_id=2001, amount=100, month=7)
        Due.objects.create(corp_id=2001, amount=50, month=6)

        with patch("eos_invoices.sources.timezone.localdate", return_value=date(2026, 7, 15)):
            response = self.index()

        self.assertContains(response, "100 ISK")
        self.assertNotContains(response, 'data-clipboard-text="100"')
        self.assertContains(response, 'data-clipboard-text="50"')

    def test_should_leave_a_row_in_progress_out_of_every_total(self):
        # a total only counts rows whose Reason is shown - the rest can still
        # change, and the source total is what gets copied out to pay
        make_source(month_field="month", year_field="year")
        Due.objects.create(corp_id=2001, amount=100, month=7)
        Due.objects.create(corp_id=2001, amount=30, month=6)
        Due.objects.create(corp_id=2001, amount=20, month=5)

        with patch("eos_invoices.sources.timezone.localdate", return_value=date(2026, 7, 15)):
            response = self.index()

        self.assertContains(response, "<strong>50 ISK</strong>", html=True)
        self.assertContains(response, 'data-clipboard-text="50"')
        self.assertNotContains(response, "150 ISK")
        self.assertNotContains(response, 'data-clipboard-text="150"')

    def test_should_offer_the_source_total_for_copying_once_nothing_is_in_progress(self):
        make_source(month_field="month", year_field="year")
        Due.objects.create(corp_id=2001, amount=100, month=6)
        Due.objects.create(corp_id=2001, amount=50, month=6)

        with patch("eos_invoices.sources.timezone.localdate", return_value=date(2026, 7, 15)):
            response = self.index()

        self.assertContains(response, 'data-clipboard-text="150"')

    def test_should_say_when_a_source_was_cut_short(self):
        make_source()
        Due.objects.create(corp_id=2001, amount=10)
        Due.objects.create(corp_id=2001, amount=20)

        with patch("eos_invoices.overview.MAX_ROWS", 1):
            response = self.index(paid="1")

        self.assertContains(response, "Only the newest 1 payments are shown")

    def test_should_sort_descriptions_by_their_period(self):
        # as text "01/2027" would sort before "12/2026"
        make_source(month_field="month", year_field="year", label_template="{month:02d}/{year}")
        Due.objects.create(corp_id=2001, amount=10, month=12, year=2026)
        Due.objects.create(corp_id=2001, amount=10, month=1, year=2027)

        response = self.index()

        self.assertContains(response, 'data-order="2026-12 12/2026"')
        self.assertContains(response, 'data-order="2027-01 01/2027"')


class TestSortableTables(DueTestCase):
    def test_should_make_every_table_page_sortable(self):
        self.client.force_login(make_ceo(perms=("basic_access", "manage_sources")))

        for name in ("index", "admin", "log", "sources"):
            with self.subTest(name):
                response = self.client.get(reverse(f"eos_invoices:{name}"))
                # the log has its own log.js - chronological, plus the filter
                self.assertContains(response, "eos_invoices/js/log" if name == "log" else "eos_invoices/js/tables")
                # the static manifest puts a hash before .js
                self.assertContains(response, "DataTables/2.3.8/js/dataTables.min")

    def test_should_sort_amounts_by_their_raw_value(self):
        # "1.500.000 ISK" would sort as text; the cell carries the number
        configure_alliance()
        make_source()
        Due.objects.create(corp_id=2001, amount=1500000)
        self.client.force_login(make_ceo())

        self.assertContains(
            self.client.get(reverse("eos_invoices:index")), 'data-order="1500000.00"'
        )

    def test_should_default_sort_by_corporation_then_description(self):
        alliance = configure_alliance()
        # the admin overview reads Corporations of the Alliance, not the character
        make_corporation(2001, "Corp", alliance)
        make_source()
        Due.objects.create(corp_id=2001, amount=10)
        self.client.force_login(make_ceo(perms=("basic_access", "manage_sources")))

        index = self.client.get(reverse("eos_invoices:index"))
        admin = self.client.get(reverse("eos_invoices:admin"))

        # the CEO overview has no Corporation column - one Corporation only
        self.assertNotContains(index, 'class="eos-invoices-sort-1"')
        self.assertContains(index, 'class="eos-invoices-sort-2"')
        # "All Corporations" spans several - Corporation first, then Description
        self.assertContains(admin, 'class="eos-invoices-sort-1"')
        self.assertContains(admin, 'class="eos-invoices-sort-2"')


class TestSearchableDropdowns(DueTestCase):
    def setUp(self):
        self.client.force_login(make_ceo(perms=("manage_sources",)))

    def test_should_make_alliance_and_pay_to_searchable(self):
        for url in (reverse("eos_invoices:settings"), reverse("eos_invoices:source_add")):
            with self.subTest(url):
                response = self.client.get(url)
                self.assertContains(response, "data-eos-invoices-search")
                self.assertContains(response, "tom-select.complete.min.js")
                # the library alone is unreadable on a dark theme
                self.assertContains(response, "eos_invoices/css/tom-select-theme")

    def test_should_make_the_model_dropdown_searchable(self):
        form = self.client.get(reverse("eos_invoices:source_add")).context["form"]

        self.assertIn("data-eos-invoices-search", form.fields["model_label"].widget.attrs)


class TestLog(DueTestCase):
    """The log's filter runs in the query, over every page, not only the shown one."""

    def setUp(self):
        self.client.force_login(make_ceo(perms=("manage_sources",)))

    def entry(self, source_name="PvE Tax", corporation_id=2001, corporation_name="Alpha"):
        return PaymentLog(
            user_name="x", source_name=source_name, row_pk="1",
            corporation_id=corporation_id, corporation_name=corporation_name, amount=10,
        )

    def log(self, **params):
        return self.client.get(reverse("eos_invoices:log"), params)

    def shown(self, response):
        return [(e.source_name, e.corporation_id) for e in response.context["page"].object_list]

    def test_should_filter_by_source_across_pages(self):
        # the oldest entry lands on page 2; the filter still finds it
        PaymentLog.objects.bulk_create([self.entry("Rent")] + [self.entry() for _ in range(100)])

        self.assertNotIn(("Rent", 2001), self.shown(self.log()))
        self.assertEqual(self.shown(self.log(source="Rent")), [("Rent", 2001)])

    def test_should_filter_by_corporation(self):
        PaymentLog.objects.bulk_create(
            [self.entry(), self.entry(corporation_id=2002, corporation_name="Beta")]
        )

        self.assertEqual(self.shown(self.log(corporation="2002")), [("PvE Tax", 2002)])
        # not a Corporation ID: no filter rather than an error
        self.assertEqual(len(self.shown(self.log(corporation="x"))), 2)

    def test_should_offer_every_source_and_corporation_of_the_whole_log(self):
        PaymentLog.objects.bulk_create(
            [self.entry("Rent", 2002, "Beta")] + [self.entry() for _ in range(100)]
        )

        response = self.log()

        # both only on page 2, still in the choice, each once
        self.assertContains(response, '<option value="Rent">Rent</option>', count=1)
        self.assertContains(response, '<option value="2002">Beta</option>', count=1)
        self.assertContains(response, '<option value="2001">Alpha</option>', count=1)

    def test_should_keep_the_filter_in_the_page_links(self):
        PaymentLog.objects.bulk_create([self.entry() for _ in range(101)])

        self.assertContains(self.log(source="PvE Tax"), "?source=PvE+Tax&amp;page=2")

    def test_should_say_when_the_filter_matches_nothing(self):
        PaymentLog.objects.bulk_create([self.entry()])

        self.assertContains(self.log(source="Nope"), "No entries match this filter.")

    def test_should_not_filter_in_the_browser_any_more(self):
        # datatables-filterdropdown only ever saw the entries of one page
        PaymentLog.objects.bulk_create([self.entry()])

        response = self.log()

        self.assertContains(response, 'id="eos-invoices-log-filter"')
        self.assertNotContains(response, "datatables-filterdropdown")
        # chronological by default, not the Corporation/Description convention
        self.assertNotContains(response, 'class="eos-invoices-sort-1"')
        self.assertNotContains(response, 'class="eos-invoices-sort-2"')


class TestSourceMaintenance(DueTestCase):
    def setUp(self):
        self.client.force_login(make_ceo(perms=("manage_sources",)))

    def post(self, **overrides):
        data = {
            "name": "Tax",
            "enabled": "on",
            "model_label": "eos_invoices.Due",
            "corporation_field": "corp_id",
            "amount_field": "amount",
            "paid_field": "paid",
            "paid_mode": "true",
        }
        data.update(overrides)
        return self.client.post(reverse("eos_invoices:source_add"), data)

    def test_should_save_a_valid_source(self):
        response = self.post()

        self.assertRedirects(response, reverse("eos_invoices:sources"))
        self.assertTrue(PaymentSource.objects.filter(name="Tax").exists())

    def test_should_refuse_a_field_the_model_does_not_have(self):
        response = self.post(amount_field="total")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Available:")
        self.assertFalse(PaymentSource.objects.exists())

    def test_should_show_the_row_count_of_each_source(self):
        make_source()
        Due.objects.create(corp_id=1)

        self.assertContains(self.client.get(reverse("eos_invoices:sources")), "1 row")

    def test_should_name_the_icon_buttons(self):
        # an icon alone says nothing to a screen reader
        make_source()

        response = self.client.get(reverse("eos_invoices:sources"))

        self.assertContains(response, 'aria-label="Edit"')
        self.assertContains(response, 'aria-label="Delete"')

    def test_should_delete_only_by_post(self):
        source = make_source()
        url = reverse("eos_invoices:source_delete", args=[source.pk])

        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertFalse(PaymentSource.objects.exists())

    def test_should_save_the_alliance(self):
        alliance = EveAllianceInfo.objects.create(
            alliance_id=3001, alliance_name="A", alliance_ticker="A", executor_corp_id=1
        )

        self.client.post(reverse("eos_invoices:settings"), {"alliance": alliance.pk})

        self.assertEqual(InvoiceConfiguration.get_solo().alliance, alliance)

    def test_should_list_the_fields_of_a_model(self):
        url = reverse("eos_invoices:source_fields")

        fields = self.client.get(url, {"model": "eos_invoices.Due"}).json()["fields"]

        self.assertIn({"path": "corp_id", "kind": "integer"}, [
            {"path": f["path"], "kind": f["kind"]} for f in fields
        ])
        self.assertEqual(self.client.get(url, {"model": "nope.Nothing"}).status_code, 400)

    def test_should_offer_only_suitable_fields_in_each_dropdown(self):
        source = make_source()

        form = self.client.get(reverse("eos_invoices:source_edit", args=[source.pk])).context["form"]

        corporation = [value for value, _label in form.fields["corporation_field"].choices]
        paid = [value for value, _label in form.fields["paid_field"].choices]
        self.assertIn("corporation__corporation_id", corporation)
        self.assertNotIn("amount", corporation)
        # "Field is true" is the default mode: booleans only
        self.assertIn("paid", paid)
        self.assertNotIn("state", paid)

    def test_should_keep_a_saved_path_the_list_does_not_offer(self):
        # valid, but two relations deep and therefore not in the dropdown
        source = make_source(corporation_field="corporation__alliance__alliance_id")
        url = reverse("eos_invoices:source_edit", args=[source.pk])

        self.assertContains(self.client.get(url), 'value="corporation__alliance__alliance_id" selected')

    def test_should_report_a_wrong_type_rather_than_an_invalid_choice(self):
        response = self.post(amount_field="state")

        self.assertContains(response, "must be a number field")


class TestPayTo(DueTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alliance = EveAllianceInfo.objects.create(
            alliance_id=3001, alliance_name="A", alliance_ticker="A", executor_corp_id=1
        )
        other = EveAllianceInfo.objects.create(
            alliance_id=3002, alliance_name="B", alliance_ticker="B", executor_corp_id=2
        )
        cls.holding = EveCorporationInfo.objects.create(
            corporation_id=2100, corporation_name="Holding", corporation_ticker="HOLD",
            member_count=1, alliance=cls.alliance,
        )
        cls.outsider = EveCorporationInfo.objects.create(
            corporation_id=2200, corporation_name="Outsider", corporation_ticker="OUT",
            member_count=1, alliance=other,
        )
        InvoiceConfiguration.objects.create(alliance=cls.alliance)

    def offered(self, source):
        url = reverse("eos_invoices:source_edit", args=[source.pk])
        return set(self.client.get(url).context["form"].fields["pay_to"].queryset)

    def test_should_offer_only_corporations_of_the_alliance(self):
        self.client.force_login(make_ceo(perms=("manage_sources",)))

        self.assertEqual(self.offered(make_source()), {self.holding})

    def test_should_keep_a_saved_corporation_that_left_the_alliance(self):
        # otherwise saving any other field would clear it without a word
        self.client.force_login(make_ceo(perms=("manage_sources",)))

        offered = self.offered(make_source(pay_to=self.outsider))

        self.assertEqual(offered, {self.holding, self.outsider})

    def test_should_name_the_recipient_on_the_overview(self):
        make_source(pay_to=self.holding)
        Due.objects.create(corp_id=2001, amount=1)
        self.client.force_login(make_ceo())

        response = self.client.get(reverse("eos_invoices:index"))

        self.assertContains(response, "Holding")
        self.assertContains(response, "[HOLD]")

    def test_should_offer_recipient_amounts_and_total_for_copying(self):
        make_source(pay_to=self.holding)
        Due.objects.create(corp_id=2001, amount=1500000)
        Due.objects.create(corp_id=2001, amount=250000.5)
        Due.objects.create(corp_id=2001, amount=999, paid=True)
        self.client.force_login(make_ceo())

        response = self.client.get(reverse("eos_invoices:index"), {"paid": "1"})

        self.assertContains(response, 'data-clipboard-text="Holding"')
        self.assertContains(response, 'data-clipboard-text="1500000"')
        self.assertContains(response, 'data-clipboard-text="250000.50"')
        self.assertContains(response, 'data-clipboard-text="1750000.50"')
        # a paid row has nothing left to transfer
        self.assertNotContains(response, 'data-clipboard-text="999"')


class TestPermissionNames(DueTestCase):
    def ours(self, codename):
        # other apps have a basic_access too
        return Permission.objects.filter(content_type__app_label="eos_invoices", codename=codename)

    def test_should_say_what_manage_sources_allows(self):
        name = self.ours("manage_sources").get().name

        for part in ("mark them as paid", "undo the log", "payment sources"):
            with self.subTest(part):
                self.assertIn(part, name)

    def test_should_rename_the_permissions_of_an_installed_site(self):
        # Django never renames an existing permission; migration 0007 does
        migration = importlib.import_module(
            "eos_invoices.migrations.0007_log_model_label_and_texts"
        )
        self.ours("basic_access").update(
            name="Can view outstanding payments of the own corporation"
        )

        migration.rename_permissions(django_apps, None)

        self.assertEqual(
            self.ours("basic_access").get().name,
            "Can view the outstanding payments of their own Corporation",
        )


class TestCopyScript(DueTestCase):
    def test_should_confirm_with_an_icon_font_awesome_free_has(self):
        # Font Awesome Free has no regular "check": "far fa-check" draws nothing
        script = (
            Path(eos_invoices.__file__).parent / "static" / "eos_invoices" / "js" / "copy.js"
        ).read_text()

        self.assertIn('classList.replace("far", "fas")', script)
        self.assertIn('clipboard.on("error"', script)
