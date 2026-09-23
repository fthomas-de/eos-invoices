from django.contrib import admin

from solo.admin import SingletonModelAdmin

from eos_invoices.models import InvoiceConfiguration, PaymentLog, PaymentSource


@admin.register(PaymentSource)
class PaymentSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "model_label", "corporation_field", "amount_field")
    list_filter = ("enabled",)


admin.site.register(InvoiceConfiguration, SingletonModelAdmin)


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ("created", "user_name", "source_name", "corporation_name", "amount", "reason")
    list_filter = ("source_name",)
    search_fields = ("user_name", "corporation_name", "reason")

    # a log that can be edited proves nothing
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
