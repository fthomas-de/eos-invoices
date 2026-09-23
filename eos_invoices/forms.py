from itertools import groupby

from django import forms
from django.apps import apps
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from allianceauth.eveonline.models import EveAllianceInfo

from eos_invoices.models import InvoiceConfiguration, PaymentSource
from eos_invoices.sources import check_source


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
            "pay_to",
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
        )

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
    )

    class Meta:
        model = InvoiceConfiguration
        fields = ["alliance"]
