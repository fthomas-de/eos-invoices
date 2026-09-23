from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
    user_passes_test,
)
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from allianceauth.services.hooks import get_extension_logger

from eos_invoices import VERSION
from eos_invoices.forms import InvoiceConfigurationForm, PaymentSourceForm
from eos_invoices.models import InvoiceConfiguration, PaymentSource
from eos_invoices.overview import build_overview
from eos_invoices.sources import (
    ACCEPTED_KINDS,
    SourceError,
    field_options,
    mark_paid as mark_row_paid,
    probe,
    resolve_model,
)

logger = get_extension_logger(__name__)


def _may_view_overview(user):
    # admins open it too: that is where they mark payments as paid
    return user.has_perm("eos_invoices.basic_access") or user.has_perm(
        "eos_invoices.manage_sources"
    )


def _render(request, template, context):
    return render(request, template, {"version": VERSION, **context})


@login_required
@user_passes_test(_may_view_overview)
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
@require_POST
def mark_paid(request, pk):
    source = get_object_or_404(PaymentSource, pk=pk)
    row = request.POST.get("row", "")

    try:
        mark_row_paid(source, row)
    except SourceError as exc:
        messages.error(request, str(exc))
    else:
        # the owning app keeps no record of who flipped its flag - we do
        logger.info("eos_invoices: %s marked row %s of %s as paid", request.user, row, source)
        messages.success(request, _("Marked as paid."))

    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = reverse("eos_invoices:index")
    return redirect(target)


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
        request,
        "eos_invoices/source_form.html",
        {
            "form": form,
            "source": source,
            "field_options": form.field_options,
            # the same type rules the server applies, for filtering in the browser
            "accepted_kinds": {
                **{name: sorted(kinds) for name, kinds in ACCEPTED_KINDS.items()},
                "paid_field_true": ["boolean"],
            },
        },
    )


@login_required
@permission_required("eos_invoices.manage_sources")
def source_fields(request):
    """Field paths of a model, to refill the dropdowns when the model changes."""
    try:
        model = resolve_model(request.GET.get("model", ""))
    except SourceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"fields": field_options(model)})


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
