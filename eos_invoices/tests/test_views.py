from django.test import RequestFactory
from django.urls import reverse

from allianceauth.eveonline.models import EveAllianceInfo

from eos_invoices.auth_hooks import InvoicesMenuItem
from eos_invoices.models import InvoiceConfiguration, PaymentSource

from .base import Due, DueTestCase, make_ceo, make_source


class TestAccess(DueTestCase):
    def test_should_keep_users_without_permission_out(self):
        self.client.force_login(make_ceo(perms=()))

        for name in ("index", "sources", "settings"):
            with self.subTest(name):
                response = self.client.get(reverse(f"eos_invoices:{name}"))
                self.assertEqual(response.status_code, 302)

    def test_should_keep_a_ceo_out_of_the_maintenance_pages(self):
        self.client.force_login(make_ceo())

        self.assertEqual(self.client.get(reverse("eos_invoices:index")).status_code, 200)
        self.assertEqual(self.client.get(reverse("eos_invoices:sources")).status_code, 302)

    def test_should_show_the_menu_entry_only_with_a_permission(self):
        request = RequestFactory().get("/")

        request.user = make_ceo("nobody", perms=())
        self.assertEqual(InvoicesMenuItem().render(request), "")

        # a maintainer without the overview is sent to the sources instead
        request.user = make_ceo("keeper", perms=("manage_sources",))
        self.assertIn(reverse("eos_invoices:sources"), InvoicesMenuItem().render(request))


class TestIndex(DueTestCase):
    def test_should_list_open_payments_with_their_reason(self):
        alliance = EveAllianceInfo.objects.create(
            alliance_id=3001, alliance_name="A", alliance_ticker="A", executor_corp_id=1
        )
        InvoiceConfiguration.objects.create(alliance=alliance)
        make_source(name="Mining tax", reason_template="{corp_id}/{month:02d}/{year}")
        Due.objects.create(corp_id=2001, amount=1234567, month=3)
        self.client.force_login(make_ceo())

        response = self.client.get(reverse("eos_invoices:index"))

        self.assertContains(response, "Mining tax")
        self.assertContains(response, "2001/03/2026")


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
