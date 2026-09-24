from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _, ngettext
from django.views.decorators.http import require_POST

from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger

from eos_invoices import VERSION
from eos_invoices.forms import InvoiceConfigurationForm, PaymentSourceForm
from eos_invoices.models import InvoiceConfiguration, PaymentLog, PaymentSource
from eos_invoices.overview import build_admin_overview, build_overview
from eos_invoices.sources import (
    ACCEPTED_KINDS,
    SourceError,
    field_options,
    mark_paid as mark_row_paid,
    probe,
    resolve_model,
)

logger = get_extension_logger(__name__)


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
def admin_overview(request):
    return _render(
        request, "eos_invoices/admin.html", {"overview": build_admin_overview()}
    )


@login_required
@permission_required("eos_invoices.manage_sources")
def payment_log(request):
    page = Paginator(PaymentLog.objects.all(), 100).get_page(request.GET.get("page"))
    return _render(request, "eos_invoices/log.html", {"page": page})


@login_required
@permission_required("eos_invoices.manage_sources")
@require_POST
def mark_paid(request, pk):
    source = get_object_or_404(PaymentSource, pk=pk)
    row = request.POST.get("row", "")

    try:
        with transaction.atomic():
            corporation_id, invoice = mark_row_paid(source, row)
            _log_marking(request, source, corporation_id, invoice)
    except SourceError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, _("Marked as paid."))

    return _back(request)


@login_required
@permission_required("eos_invoices.manage_sources")
@require_POST
def mark_all_paid(request, pk):
    """Mark the rows of one Corporation in one source that the page showed.

    The page posts the keys it listed rather than asking for "everything open
    now": a payment that arrived after the page was loaded was never seen by
    the admin and stays open.
    """
    source = get_object_or_404(PaymentSource, pk=pk)
    try:
        corporation_id = int(request.POST.get("corporation", ""))
    except ValueError:
        messages.error(request, _("No Corporation given."))
        return _back(request)

    marked = skipped = 0
    # all or nothing if the database fails half way; a row that is merely
    # paid already, gone or of another Corporation is skipped, not fatal
    with transaction.atomic():
        for row in request.POST.getlist("rows"):
            try:
                _corporation_id, invoice = mark_row_paid(
                    source, row, corporation_id=corporation_id
                )
            except SourceError:
                skipped += 1
                continue
            _log_marking(request, source, corporation_id, invoice)
            marked += 1

    if marked:
        messages.success(
            request,
            ngettext(
                "Marked %(count)s payment as paid.",
                "Marked %(count)s payments as paid.",
                marked,
            )
            % {"count": marked},
        )
    if skipped:
        messages.warning(
            request,
            ngettext(
                "%(count)s payment was skipped: already paid, gone or of another Corporation.",
                "%(count)s payments were skipped: already paid, gone or of another Corporation.",
                skipped,
            )
            % {"count": skipped},
        )
    return _back(request)


def _log_marking(request, source, corporation_id, invoice):
    main = request.user.profile.main_character
    corporation = EveCorporationInfo.objects.filter(corporation_id=corporation_id).first()
    # the owning app keeps no record of who flipped its flag - we do
    PaymentLog.objects.create(
        user=request.user,
        user_name=main.character_name if main else request.user.username,
        source=source,
        source_name=source.name,
        row_pk=str(invoice.pk),
        corporation_id=corporation_id,
        corporation_name=corporation.corporation_name if corporation else "",
        amount=invoice.amount,
        reason=invoice.reason[:255],
        label=invoice.label[:255],
    )
    logger.info(
        "eos_invoices: %s marked row %s of %s as paid", request.user, invoice.pk, source
    )


def _back(request):
    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = reverse("eos_invoices:admin")
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
