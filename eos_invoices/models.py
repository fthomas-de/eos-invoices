from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo

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

    name = models.CharField(pgettext_lazy("eos-invoices", "Name"), max_length=100, unique=True)
    enabled = models.BooleanField(pgettext_lazy("eos-invoices", "Enabled"), default=True)
    model_label = models.CharField(
        pgettext_lazy("eos-invoices", "Model"),
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
    month_field = models.CharField(
        _("Month field"),
        max_length=255,
        blank=True,
        help_text=_(
            "Optional integer field (1-12) holding the row's month. Together "
            "with the Year field below, hides the Reason while the row is for "
            "the month still in progress - the amount owed for it can still "
            "change. Both fields are required for this; set alone, this one "
            "does nothing."
        ),
    )
    year_field = models.CharField(
        _("Year field"),
        max_length=255,
        blank=True,
        help_text=_(
            "Optional integer field holding the row's year, e.g. 2026. Used "
            "together with the Month field above - a month number alone "
            "cannot tell this year's row from the same month a year ago."
        ),
    )
    pay_to = models.ForeignKey(
        EveCorporationInfo,
        verbose_name=_("Pay to"),
        null=True,
        blank=True,
        # a closed Corporation must not delete the source that named it
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_(
            "The Corporation that receives the ISK. Lists the Corporations of the "
            "Alliance chosen on the Alliance tab."
        ),
    )

    class Meta:
        default_permissions = ()
        ordering = ["name"]
        verbose_name = _("Payment source")
        verbose_name_plural = _("Payment sources")

    def __str__(self):
        return self.name


class PaymentLog(models.Model):
    """Who marked which payment as paid, and what it was at that moment.

    The owning apps keep no record of who flipped their paid flag. Names are
    stored as text next to the foreign keys, so an entry still reads correctly
    after the source, the Corporation or the user is gone.
    """

    created = models.DateTimeField(_("Date"), auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    user_name = models.CharField(_("Marked by"), max_length=254)
    source = models.ForeignKey(
        PaymentSource, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    source_name = models.CharField(_("Source"), max_length=100)
    row_pk = models.CharField(_("Row"), max_length=64)
    corporation_id = models.BigIntegerField(_("Corporation ID"))
    corporation_name = models.CharField(
        pgettext_lazy("EVE jargon", "Corporation"), max_length=254, blank=True
    )
    amount = models.DecimalField(pgettext_lazy("eos-invoices", "Amount"), max_digits=24, decimal_places=2)
    reason = models.CharField(pgettext_lazy("EVE jargon", "Reason"), max_length=255, blank=True)
    label = models.CharField(_("Description"), max_length=255, blank=True)

    # what was written, to undo it exactly; empty on entries made before 0.0.7,
    # which therefore cannot be undone from here
    paid_field = models.CharField(max_length=255, blank=True, default="")
    # plain JSON, filled through sources.to_json: DjangoJSONEncoder would cut
    # datetimes to milliseconds
    previous_value = models.JSONField(null=True)
    written_value = models.JSONField(null=True)

    # an undone entry stays: a log that loses lines proves nothing
    reverted_at = models.DateTimeField(_("Undone"), null=True)
    reverted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    reverted_by_name = models.CharField(_("Undone by"), max_length=254, blank=True, default="")

    class Meta:
        default_permissions = ()
        ordering = ["-created", "-pk"]
        verbose_name = _("Payment log entry")
        verbose_name_plural = _("Payment log")

    def __str__(self):
        return f"{self.created:%Y-%m-%d %H:%M} {self.user_name}: {self.source_name} {self.row_pk}"

    @property
    def can_undo(self):
        return self.reverted_at is None and bool(self.paid_field) and self.source_id is not None
