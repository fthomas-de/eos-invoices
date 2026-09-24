from datetime import date
from decimal import Decimal

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo

from eos_invoices.models import PaymentSource
from eos_invoices.sources import (
    SourceError,
    check_source,
    field_options,
    get_invoices,
    plain_isk,
    render_template,
    resolve_field,
    template_fields,
)

from .base import Due, DueTestCase, EosInvoicesTestCase, make_source


class TestResolveField(DueTestCase):
    def test_should_follow_a_forward_relation(self):
        field = resolve_field(Due, "corporation__corporation_id")

        self.assertEqual(field.name, "corporation_id")
        self.assertIs(field.model, EveCorporationInfo)

    def test_should_list_the_available_fields_for_an_unknown_one(self):
        with self.assertRaisesMessage(SourceError, "Available: amount, corp_id"):
            resolve_field(Due, "amount_due")

    def test_should_refuse_a_path_ending_at_a_relation(self):
        # the FK alone would compare against the primary key, not the EVE ID
        with self.assertRaisesMessage(SourceError, "ends at a relation"):
            resolve_field(Due, "corporation")

    def test_should_refuse_a_relation_to_many_rows(self):
        # alliance -> its Corporations would repeat a payment once per member corp
        with self.assertRaisesMessage(SourceError, "many rows"):
            resolve_field(EveAllianceInfo, "evecorporationinfo__corporation_id")

    def test_should_refuse_a_lookup_in_the_path(self):
        with self.assertRaises(SourceError):
            resolve_field(Due, "paid_at__isnull")


class TestFieldOptions(DueTestCase):
    def kinds(self, model):
        return {option["path"]: option["kind"] for option in field_options(model)}

    def test_should_offer_own_fields_with_their_kind(self):
        kinds = self.kinds(Due)

        self.assertEqual(kinds["corp_id"], "integer")
        self.assertEqual(kinds["amount"], "number")
        self.assertEqual(kinds["paid"], "boolean")
        self.assertEqual(kinds["created"], "date")
        self.assertEqual(kinds["state"], "text")

    def test_should_resolve_a_relation_one_level_deep(self):
        kinds = self.kinds(Due)

        self.assertEqual(kinds["corporation__corporation_id"], "integer")
        # the relation itself would compare against the primary key
        self.assertNotIn("corporation", kinds)
        # two levels are left out to keep the list short
        self.assertNotIn("corporation__alliance__alliance_id", kinds)

    def test_should_not_offer_relations_to_many_rows(self):
        paths = self.kinds(EveAllianceInfo)

        self.assertFalse(any(p.startswith("evecorporationinfo__") for p in paths))


class TestPlainIsk(EosInvoicesTestCase):
    def test_should_drop_grouping_and_a_zero_fraction(self):
        self.assertEqual(plain_isk(Decimal("1234567.00")), "1234567")

    def test_should_keep_a_real_fraction(self):
        self.assertEqual(plain_isk(Decimal("1234567.5")), "1234567.50")

    def test_should_accept_integers_and_floats(self):
        # sources may hold BigIntegerField or FloatField amounts
        self.assertEqual(plain_isk(250000000), "250000000")
        self.assertEqual(plain_isk(Decimal(str(0.1 + 0.2))), "0.30")


class TestTemplates(EosInvoicesTestCase):
    def test_should_return_the_field_paths(self):
        self.assertEqual(
            template_fields("{corporation__corporation_id}/{month:02d}/{year}"),
            ["corporation__corporation_id", "month", "year"],
        )

    def test_should_refuse_attribute_access(self):
        # {x.__class__} would let a template walk into arbitrary objects
        for template in ("{amount.__class__}", "{amount[0]}", "{amount!r}", "{}"):
            with self.subTest(template), self.assertRaises(SourceError):
                template_fields(template)

    def test_should_apply_the_format(self):
        self.assertEqual(
            render_template("{corp_id}/{month:02d}/{year}", {"corp_id": 9, "month": 7, "year": 2026}),
            "9/07/2026",
        )

    def test_should_fall_back_to_the_template_when_the_format_does_not_fit(self):
        self.assertEqual(render_template("{state:02d}", {"state": "x"}), "{state:02d}")


class TestCheckSource(DueTestCase):
    def check(self, **kwargs):
        values = {
            "model_label": "eos_invoices.Due",
            "corporation_field": "corp_id",
            "amount_field": "amount",
            "paid_field": "paid",
            "paid_mode": "true",
        }
        values.update(kwargs)
        return check_source(PaymentSource(**values))

    def test_should_accept_a_valid_source(self):
        self.assertEqual(self.check(), {})

    def test_should_report_an_unknown_model(self):
        self.assertIn("model_label", self.check(model_label="nope.Nothing"))

    def test_should_report_wrong_field_types(self):
        errors = self.check(corporation_field="state", amount_field="state", paid_field="state")

        self.assertEqual(
            set(errors), {"corporation_field", "amount_field", "paid_field"}
        )

    def test_should_require_a_value_for_equals(self):
        self.assertIn("paid_value", self.check(paid_mode="equals", paid_field="state"))

    def test_should_report_a_value_the_field_cannot_hold(self):
        errors = self.check(paid_mode="equals", paid_field="month", paid_value="many")

        self.assertIn("paid_value", errors)

    def test_should_report_a_bad_placeholder(self):
        self.assertIn("reason_template", self.check(reason_template="{nothing}"))


class TestGetInvoices(DueTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.corp = EveCorporationInfo.objects.create(
            corporation_id=2001, corporation_name="Corp", corporation_ticker="C", member_count=1
        )
        other = EveCorporationInfo.objects.create(
            corporation_id=2002, corporation_name="Other", corporation_ticker="O", member_count=1
        )
        Due.objects.create(corporation=cls.corp, corp_id=2001, amount=100, month=7, created=date(2026, 7, 31))
        Due.objects.create(
            corporation=cls.corp, corp_id=2001, amount=50, month=6, paid=True,
            state="done", created=date(2026, 6, 30),
        )
        Due.objects.create(corporation=other, corp_id=2002, amount=999, month=7)
        Due.objects.create(corporation=cls.corp, corp_id=2001, amount=0, month=8)

    def test_should_drop_a_zero_amount_row(self):
        # a corp exempted that month tells nobody anything, paid or not
        invoices = get_invoices(make_source(), 2001, include_paid=True)

        self.assertNotIn(Decimal("0"), [i.amount for i in invoices])

    def test_should_only_return_open_payments_of_the_corporation(self):
        invoices = get_invoices(make_source(), 2001)

        self.assertEqual([i.amount for i in invoices], [Decimal("100")])
        self.assertFalse(invoices[0].paid)

    def test_should_include_paid_payments_on_request(self):
        invoices = get_invoices(make_source(date_field="created"), 2001, include_paid=True)

        self.assertEqual([(i.amount, i.paid) for i in invoices], [(100, False), (50, True)])
        self.assertEqual(invoices[0].date, date(2026, 7, 31))

    def test_should_filter_through_a_relation(self):
        source = make_source(corporation_field="corporation__corporation_id")

        self.assertEqual([i.amount for i in get_invoices(source, 2002)], [Decimal("999")])

    def test_should_treat_a_filled_field_as_paid(self):
        # "state" is empty on the open row - an empty string must not count
        source = make_source(paid_field="state", paid_mode=PaymentSource.PaidMode.NOT_EMPTY)

        self.assertEqual([i.amount for i in get_invoices(source, 2001)], [Decimal("100")])

    def test_should_treat_a_matching_value_as_paid(self):
        source = make_source(paid_field="month", paid_mode="equals", paid_value="7")

        self.assertEqual([i.amount for i in get_invoices(source, 2001)], [Decimal("50")])

    def test_should_render_reason_and_description(self):
        source = make_source(
            reason_template="{corporation__corporation_id}/{month:02d}/{year}",
            label_template="{month:02d}/{year}",
        )

        invoice = get_invoices(source, 2001)[0]

        self.assertEqual(invoice.reason, "2001/07/2026")
        self.assertEqual(invoice.label, "07/2026")

    def test_should_raise_for_a_broken_source(self):
        with self.assertRaises(SourceError):
            get_invoices(make_source(amount_field="gone"), 2001)
