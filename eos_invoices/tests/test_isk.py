from decimal import Decimal

from django.urls import reverse

from eos_invoices.templatetags.eos_invoices import isk

from .base import (
    Due,
    DueTestCase,
    EosInvoicesTestCase,
    configure_alliance,
    make_ceo,
    make_corporation,
    make_source,
)


class TestIskFilter(EosInvoicesTestCase):
    def test_should_split_thousands_with_dots(self):
        self.assertEqual(isk(Decimal("1234567")), "1.234.567")

    def test_should_drop_the_fraction_rounding_half_up(self):
        self.assertEqual(isk(Decimal("1500000.49")), "1.500.000")
        self.assertEqual(isk(Decimal("1500000.50")), "1.500.001")

    def test_should_take_integers_and_floats(self):
        # amounts come from BigIntegerField, DecimalField or FloatField sources
        self.assertEqual(isk(250000000), "250.000.000")
        self.assertEqual(isk(999.6), "1.000")

    def test_should_keep_small_and_negative_amounts_readable(self):
        self.assertEqual(isk(0), "0")
        self.assertEqual(isk(Decimal("-1234")), "-1.234")
        self.assertEqual(isk(Decimal("-0.4")), "0")

    def test_should_leave_what_is_no_number(self):
        self.assertEqual(isk(""), "")
        self.assertIsNone(isk(None))

    def test_should_leave_what_is_no_finite_number(self):
        # a NaN float - PostgreSQL can store one - used to raise from int()
        # and take the whole page down
        for value in (float("nan"), Decimal("NaN"), float("inf")):
            with self.subTest(value):
                self.assertIs(isk(value), value)


class TestIskOnPages(DueTestCase):
    @classmethod
    def setUpTestData(cls):
        make_corporation(2001, "Alpha", configure_alliance())
        Due.objects.create(corp_id=2001, amount=Decimal("1500000.40"))

    def test_should_format_amounts_on_both_overviews(self):
        make_source()
        self.client.force_login(make_ceo(perms=("basic_access", "manage_sources")))

        for name in ("index", "admin"):
            with self.subTest(name):
                response = self.client.get(reverse(f"eos_invoices:{name}"))
                self.assertContains(response, "1.500.000 ISK")
                self.assertNotContains(response, "1,500,000")
