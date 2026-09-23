from decimal import Decimal

from allianceauth.eveonline.models import EveAllianceInfo
from allianceauth.tests.auth_utils import AuthUtils

from eos_invoices.models import InvoiceConfiguration
from eos_invoices.overview import build_overview

from .base import Due, DueTestCase, make_ceo, make_source


def configure_alliance(alliance_id=3001):
    alliance = EveAllianceInfo.objects.create(
        alliance_id=alliance_id,
        alliance_name=f"Alliance {alliance_id}",
        alliance_ticker="A",
        executor_corp_id=1,
    )
    config = InvoiceConfiguration.get_solo()
    config.alliance = alliance
    config.save()


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
