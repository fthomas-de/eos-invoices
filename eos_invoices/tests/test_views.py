from django.test import RequestFactory
from django.urls import reverse

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo

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


class TestFieldsEndpointAccess(DueTestCase):
    def test_should_need_the_maintenance_permission(self):
        self.client.force_login(make_ceo())

        response = self.client.get(reverse("eos_invoices:source_fields"), {"model": "eos_invoices.Due"})

        self.assertEqual(response.status_code, 302)
