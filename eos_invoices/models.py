from django.db import models
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from allianceauth.eveonline.models import EveAllianceInfo

from solo.models import SingletonModel


class General(models.Model):
    """Meta model for app permissions"""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "Can view outstanding payments of the own corporation"),
            ("manage_sources", "Can manage payment sources and app settings"),
        )


class InvoiceConfiguration(SingletonModel):
    """App wide settings, maintained on the settings page."""

    alliance = models.ForeignKey(
        EveAllianceInfo,
        verbose_name=pgettext_lazy("EVE jargon", "Alliance"),
        null=True,
        blank=True,
        # losing the alliance must not take the configuration row with it;
        # the overview then simply shows nothing until one is chosen again
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_(
            "Only Corporations in this Alliance see their outstanding payments. "
            "Without an Alliance nobody sees anything."
        ),
    )

    class Meta:
        default_permissions = ()
        verbose_name = _("Configuration")

    def __str__(self):
        return str(_("Configuration"))


class PaymentSource(models.Model):
    """One model of another app that holds payments owed by Corporations.

    Every field below names a field of that model, not a value. The model is
    read through the ORM, so a path may cross forward relations the way a
    queryset filter does, e.g. ``corporation__corporation_id``.
    """

    class PaidMode(models.TextChoices):
        TRUE = "true", _("Field is true")
        NOT_EMPTY = "not_empty", _("Field is not empty")
        EQUALS = "equals", _("Field equals value")

    name = models.CharField(_("Name"), max_length=100, unique=True)
    enabled = models.BooleanField(_("Enabled"), default=True)
    model_label = models.CharField(
        _("Model"),
        max_length=255,
        help_text=_("The model holding one row per payment, as app_label.ModelName."),
    )
    corporation_field = models.CharField(
        _("Corporation ID field"),
        max_length=255,
        help_text=_(
            "Field holding the EVE Corporation ID, e.g. corp_id or "
            "corporation__corporation_id."
        ),
    )
    amount_field = models.CharField(
        _("Amount field"),
        max_length=255,
        help_text=_("Field holding the amount owed in ISK."),
    )
    paid_field = models.CharField(
        _("Paid field"),
        max_length=255,
        help_text=_("Field that tells whether a payment has been made."),
    )
    paid_mode = models.CharField(
        _("Paid when"),
        max_length=16,
        choices=PaidMode.choices,
        default=PaidMode.TRUE,
    )
    paid_value = models.CharField(
        _("Paid value"),
        max_length=255,
        blank=True,
        help_text=_("Only for \"Field equals value\": the value that means paid."),
    )
    reason_template = models.CharField(
        pgettext_lazy("EVE jargon", "Reason"),
        max_length=255,
        blank=True,
        help_text=_(
            "Reason to enter with the payment in game. Field names in braces are "
            "replaced by their values, with an optional format: "
            "{corp_id}/{month:02d}/{year}"
        ),
    )
    label_template = models.CharField(
        _("Description"),
        max_length=255,
        blank=True,
        help_text=_(
            "What a row is for, shown next to the amount. Same placeholders as "
            "the reason, e.g. {month:02d}/{year}"
        ),
    )
    date_field = models.CharField(
        _("Date field"),
        max_length=255,
        blank=True,
        help_text=_("Optional date or datetime field; rows are sorted by it, newest first."),
    )
    pay_to = models.CharField(
        _("Pay to"),
        max_length=255,
        blank=True,
        help_text=_("Whom to send the ISK to, e.g. the holding Corporation."),
    )

    class Meta:
        default_permissions = ()
        ordering = ["name"]
        verbose_name = _("Payment source")
        verbose_name_plural = _("Payment sources")

    def __str__(self):
        return self.name
