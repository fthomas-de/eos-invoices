"""Shared test case and a stand-in for another app's payment model.

``Due`` plays the part of a foreign model such as MonthlyTax of eos-tax or
AllianceBillingRecord of aa-miningtax. It only exists while tests run: it has no
migration, so its table is created around each test class.

The table is created *before* the class transaction opens and dropped after it
closes. On MySQL a CREATE TABLE commits implicitly, and inside the transaction
it would commit every fixture of the class along with it.
"""

from django.db import connection, models
from django.test import TestCase, override_settings

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from eos_invoices.models import InvoiceConfiguration, PaymentSource


class Due(models.Model):
    corporation = models.ForeignKey(
        EveCorporationInfo, null=True, on_delete=models.CASCADE, related_name="+"
    )
    corp_id = models.IntegerField(default=0)
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    # an amount another app may leave empty
    maybe_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True)
    state = models.CharField(max_length=10, blank=True)
    month = models.PositiveSmallIntegerField(default=1)
    year = models.PositiveSmallIntegerField(default=2026)
    created = models.DateField(null=True)

    class Meta:
        app_label = "eos_invoices"


# django-solo caches the configuration singleton, and the cache outlives the
# rolled back transaction of a TestCase; see eos-tax for the full story
@override_settings(SOLO_CACHE=None)
class EosInvoicesTestCase(TestCase):
    """Base class for every test in this app."""


class DueTestCase(EosInvoicesTestCase):
    @classmethod
    def setUpClass(cls):
        with connection.schema_editor() as editor:
            editor.create_model(Due)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        with connection.schema_editor() as editor:
            editor.delete_model(Due)


def make_source(**kwargs):
    """A saved source on ``Due``; keyword arguments override the defaults."""
    values = {
        "name": "Due",
        "model_label": "eos_invoices.Due",
        "corporation_field": "corp_id",
        "amount_field": "amount",
        "paid_field": "paid",
        "paid_mode": PaymentSource.PaidMode.TRUE,
    }
    values.update(kwargs)
    return PaymentSource.objects.create(**values)


def configure_alliance(alliance_id=3001):
    """The Alliance the app works for, saved in its configuration."""
    alliance = EveAllianceInfo.objects.create(
        alliance_id=alliance_id,
        alliance_name=f"Alliance {alliance_id}",
        alliance_ticker="A",
        executor_corp_id=1,
    )
    config = InvoiceConfiguration.get_solo()
    config.alliance = alliance
    config.save()
    return alliance


def make_corporation(corporation_id, name, alliance=None):
    return EveCorporationInfo.objects.create(
        corporation_id=corporation_id,
        corporation_name=name,
        corporation_ticker=name[:4].upper(),
        member_count=1,
        alliance=alliance,
    )


def make_ceo(username="ceo", corp_id=2001, alliance_id=3001, perms=("basic_access",)):
    user = AuthUtils.create_user(username)
    AuthUtils.add_main_character_2(
        user,
        f"{username} main",
        character_id=user.pk + 1000,
        corp_id=corp_id,
        corp_name=f"Corp {corp_id}",
        corp_ticker="C",
        alliance_id=alliance_id,
        alliance_name=f"Alliance {alliance_id}",
    )
    for perm in perms:
        AuthUtils.add_permission_to_user_by_name(f"eos_invoices.{perm}", user)
    # has_perm caches on the instance; tests want the stored permissions
    return type(user).objects.get(pk=user.pk)
