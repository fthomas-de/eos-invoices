from decimal import Decimal
from unittest.mock import patch

from allianceauth.eveonline.models import EveAllianceInfo
from allianceauth.tests.auth_utils import AuthUtils

from eos_invoices.models import InvoiceConfiguration
from eos_invoices.overview import build_admin_overview, build_overview

from .base import Due, DueTestCase, configure_alliance, make_ceo, make_corporation, make_source


class TestBuildOverview(DueTestCase):
    @classmethod
    def setUpTestData(cls):
        Due.objects.create(corp_id=2001, amount=100)
        Due.objects.create(corp_id=2001, amount=20)
        Due.objects.create(corp_id=2002, amount=999)

    def test_should_explain_a_missing_main(self):
        overview = build_overview(AuthUtils.create_user("nomain"))

        self.assertTrue(overview.notice)
        self.assertEqual(overview.results, [])

    def test_should_show_nothing_without_an_alliance(self):
        make_source()

        overview = build_overview(make_ceo())

        self.assertIn("No Alliance", overview.notice)
        self.assertEqual(overview.results, [])

    def test_should_show_nothing_to_a_corporation_outside_the_alliance(self):
        configure_alliance(3001)
        make_source()

        overview = build_overview(make_ceo(alliance_id=3999))

        self.assertIn("not a member", overview.notice)
        self.assertEqual(overview.results, [])

    def test_should_sum_the_corporation_of_the_main(self):
        configure_alliance()
        make_source()

        overview = build_overview(make_ceo(corp_id=2001))

        self.assertEqual(overview.notice, "")
        self.assertEqual(overview.open_total, Decimal("120"))

    def test_should_keep_the_other_sources_when_one_is_broken(self):
        configure_alliance()
        make_source(name="Broken", amount_field="gone")
        make_source(name="Working")

        results = {r.source.name: r for r in build_overview(make_ceo()).results}

        self.assertTrue(results["Broken"].error)
        self.assertEqual(results["Working"].open_total, Decimal("120"))

    def test_should_skip_disabled_sources(self):
        configure_alliance()
        make_source(enabled=False)

        self.assertEqual(build_overview(make_ceo()).results, [])

    def test_should_say_when_a_source_was_cut_short(self):
        # "Including paid" keeps the newest rows; an older open one falls off
        # the list and out of the total, so the page has to say so
        configure_alliance()
        make_source()

        with patch("eos_invoices.overview.MAX_ROWS", 1):
            cut = build_overview(make_ceo(), include_paid=True)
        whole = build_overview(make_ceo("other"), include_paid=True)

        self.assertTrue(cut.results[0].truncated)
        self.assertEqual(len(cut.results[0].invoices), 1)
        self.assertFalse(whole.results[0].truncated)
        self.assertEqual(len(whole.results[0].invoices), 2)


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
            make_corporation(corporation_id, name, member_of)
        InvoiceConfiguration.objects.create(alliance=alliance)
        Due.objects.create(corp_id=2001, amount=111)
        Due.objects.create(corp_id=2002, amount=222)
        Due.objects.create(corp_id=2002, amount=5, paid=True)
        Due.objects.create(corp_id=2009, amount=999)

    def test_should_group_open_payments_by_source_across_corporations(self):
        # two sources: one table each, every Corporation's open rows in it -
        # not one table per Corporation
        make_source(name="First")
        make_source(name="Second")

        overview = build_admin_overview()

        self.assertEqual([s.source.name for s in overview.sources], ["First", "Second"])
        for result in overview.sources:
            self.assertEqual(
                sorted((r.corporation.corporation_name, r.invoice.amount) for r in result.rows),
                [("Alpha", 111), ("Beta", 222)],
            )
        # Gamma has nothing open; Stranger is outside the Alliance
        self.assertEqual(overview.settled_count, 1)
        self.assertEqual(overview.open_total, 666)

    def test_should_read_each_source_once_for_all_corporations(self):
        # one query per Corporation would be 30+ queries in a real Alliance
        make_source()

        # configuration, Corporations, sources, then one query for the source
        with self.assertNumQueries(4):
            build_admin_overview()

    def test_should_say_when_a_source_was_cut_short(self):
        make_source()

        with patch("eos_invoices.overview.ADMIN_MAX_ROWS", 1):
            overview = build_admin_overview()

        self.assertEqual(len(overview.problems), 1)
        # Beta's row fell off the list; it must not count as settled
        self.assertEqual(overview.settled_count, 0)

    def test_should_not_count_settled_corporations_while_a_source_has_problems(self):
        # Gamma may owe something in the source that could not be read
        make_source(name="Working")
        make_source(name="Broken", amount_field="gone")

        overview = build_admin_overview()

        self.assertEqual(len(overview.problems), 1)
        self.assertEqual(overview.settled_count, 0)
