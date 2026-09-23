from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from eos_invoices import VERSION
from eos_invoices.forms import InvoiceConfigurationForm, PaymentSourceForm
from eos_invoices.models import InvoiceConfiguration, PaymentSource
from eos_invoices.overview import build_overview
from eos_invoices.sources import probe


def _render(request, template, context):
    return render(request, template, {"version": VERSION, **context})


@login_required
@permission_required("eos_invoices.basic_access")
def index(request):
    include_paid = request.GET.get("paid") == "1"
    return _render(
        request,
        "eos_invoices/index.html",
        {
            "overview": build_overview(request.user, include_paid=include_paid),
            "include_paid": include_paid,
        },
    )


@login_required
@permission_required("eos_invoices.manage_sources")
def sources(request):
    rows = []
    for source in PaymentSource.objects.all():
        count, error = probe(source)
        rows.append({"source": source, "count": count, "error": error})

    return _render(request, "eos_invoices/sources.html", {"rows": rows})


@login_required
@permission_required("eos_invoices.manage_sources")
def source_edit(request, pk=None):
    source = get_object_or_404(PaymentSource, pk=pk) if pk else PaymentSource()
    form = PaymentSourceForm(request.POST or None, instance=source)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Saved %(name)s.") % {"name": source.name})
        return redirect("eos_invoices:sources")

    return _render(
        request, "eos_invoices/source_form.html", {"form": form, "source": source}
    )


@login_required
@permission_required("eos_invoices.manage_sources")
@require_POST
def source_delete(request, pk):
    source = get_object_or_404(PaymentSource, pk=pk)
    source.delete()
    messages.success(request, _("Deleted %(name)s.") % {"name": source.name})
    return redirect("eos_invoices:sources")


@login_required
@permission_required("eos_invoices.manage_sources")
def settings(request):
    form = InvoiceConfigurationForm(
        request.POST or None, instance=InvoiceConfiguration.get_solo()
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Settings saved."))
        return redirect("eos_invoices:settings")

    return _render(request, "eos_invoices/settings.html", {"form": form})
