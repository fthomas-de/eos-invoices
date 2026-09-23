from django.apps import AppConfig

from eos_invoices import __version__


class EosInvoicesConfig(AppConfig):
    name = "eos_invoices"
    label = "eos_invoices"
    verbose_name = f"EOS Invoices v{__version__}"
    default_auto_field = "django.db.models.BigAutoField"
