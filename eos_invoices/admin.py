from django.contrib import admin

from solo.admin import SingletonModelAdmin

from eos_invoices.models import InvoiceConfiguration, PaymentSource


@admin.register(PaymentSource)
class PaymentSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "model_label", "corporation_field", "amount_field")
    list_filter = ("enabled",)


admin.site.register(InvoiceConfiguration, SingletonModelAdmin)
