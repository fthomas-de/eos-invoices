from itertools import groupby

from django import forms
from django.apps import apps
from django.db.models import Q
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo

from eos_invoices.models import InvoiceConfiguration, PaymentSource
from eos_invoices.sources import (
    SourceError,
    accepted_kinds,
    check_source,
    field_options,
    resolve_model,
)

# settings that name a single field of the chosen model
PATH_FIELDS = (
    "corporation_field", "amount_field", "paid_field", "date_field", "month_field", "year_field",
)


def model_choices():
    """Every installed model, grouped by app, for the model dropdown."""
    labels = sorted(
        model._meta.label
        for model in apps.get_models()
        # our own tables never hold payments of another app
        if model.__module__ != "eos_invoices.models"
    )
    grouped = [
        (app, [(label, label) for label in group])
        for app, group in groupby(labels, key=lambda label: label.split(".")[0])
    ]
    return [("", "---------")] + grouped


class PathChoiceField(forms.ChoiceField):
    """A dropdown of field paths that leaves validation to check_source.

    The offered paths are only a search aid: the list is one relation deep and
    filtered by type, while check_source knows the real rules and gives the
    better message - "must be a number field" rather than "not one of the
    available choices".
    """

    def valid_value(self, value):
        return True


class PaymentSourceForm(forms.ModelForm):
    class Meta:
        model = PaymentSource
        fields = [
            "name",
            "enabled",
            "model_label",
            "corporation_field",
            "amount_field",
            "paid_field",
            "paid_mode",
            "paid_value",
            "reason_template",
            "label_template",
            "date_field",
            "month_field",
            "year_field",
            "pay_to",
            "url",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = model_choices()
        current = self.instance.model_label
        # a source whose app was uninstalled must stay editable, or it could
        # only be deleted from the admin
        if current and not any(
            current == value for _app, group in choices[1:] for value, _label in group
        ):
            choices.append((_("Not installed"), [(current, current)]))
        self.fields["model_label"] = forms.ChoiceField(
            label=PaymentSource._meta.get_field("model_label").verbose_name,
            help_text=PaymentSource._meta.get_field("model_label").help_text,
            choices=choices,
            widget=forms.Select(attrs={"data-eos-invoices-search": ""}),
        )

        self.fields["pay_to"].queryset = self._pay_to_corporations()
        self.fields["pay_to"].widget.attrs["data-eos-invoices-search"] = ""

        self.field_options = self._field_options()
        paid_mode = self._value("paid_mode") or PaymentSource.PaidMode.TRUE
        for name in PATH_FIELDS:
            self._make_path_field(name, paid_mode)

    def _pay_to_corporations(self):
        """Corporations of the configured Alliance, plus the one already saved.

        The saved one stays even after it left the Alliance: otherwise the
        next save of an unrelated field would silently clear it.
        """
        alliance = InvoiceConfiguration.get_solo().alliance
        wanted = Q(pk=self.instance.pay_to_id) if self.instance.pay_to_id else Q(pk__in=[])
        if alliance is not None:
            wanted |= Q(alliance__alliance_id=alliance.alliance_id)
        return EveCorporationInfo.objects.filter(wanted).order_by("corporation_name")

    def _value(self, name):
        """What the form shows for a field: posted data, else the instance."""
        if self.is_bound:
            return self.data.get(self.add_prefix(name), "")
        return getattr(self.instance, name)

    def _field_options(self):
        label = self._value("model_label")
        if not label:
            return []
        try:
            return field_options(resolve_model(label))
        except SourceError:
            return []

    def _make_path_field(self, name, paid_mode):
        model_field = PaymentSource._meta.get_field(name)
        kinds = accepted_kinds(name, paid_mode)
        choices = [
            (option["path"], option["label"])
            for option in self.field_options
            if not kinds or option["kind"] in kinds
        ]
        # a saved path the list does not offer - deeper than one relation, or
        # of the wrong type - stays selectable so the source can be edited
        current = self._value(name)
        if current and current not in {path for path, _label in choices}:
            choices.append((current, current))

        self.fields[name] = PathChoiceField(
            label=model_field.verbose_name,
            help_text=model_field.help_text,
            required=not model_field.blank,
            choices=[("", "---------")] + choices,
        )
        self.fields[name].widget.attrs["data-eos-invoices-path"] = name

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned

        # the instance already carries the cleaned values at this point only
        # after _post_clean, so check a throwaway copy instead
        candidate = PaymentSource(
            **{name: cleaned.get(name) for name in self.Meta.fields}
        )
        for name, message in check_source(candidate).items():
            self.add_error(name, message)

        return cleaned


class InvoiceConfigurationForm(forms.ModelForm):
    alliance = forms.ModelChoiceField(
        label=pgettext_lazy("EVE jargon", "Alliance"),
        queryset=EveAllianceInfo.objects.order_by("alliance_name"),
        required=False,
        help_text=InvoiceConfiguration._meta.get_field("alliance").help_text,
        widget=forms.Select(attrs={"data-eos-invoices-search": ""}),
    )

    class Meta:
        model = InvoiceConfiguration
        fields = ["alliance"]
