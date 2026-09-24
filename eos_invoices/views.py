from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
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
    undo_mark_paid,
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


def dashboard_overview(request):
    """Compact widget for Alliance Auth's own dashboard: the viewer's Corporation.

    Not a URL - Alliance Auth's dashboard_hook calls this directly and drops
    an empty string, the same way timerboard hides its widget without
    upcoming timers. Hidden without the permission, without anything
    outstanding, and in every case build_overview itself has nothing to show
    (no main character, no Alliance configured, Corporation outside it) - the
    full overview explains those, a dashboard widget only would not.
    """
    if not request.user.has_perm("eos_invoices.basic_access"):
        return ""

    overview = build_overview(request.user)
    if overview.notice or not overview.open_total:
        return ""

    return render_to_string(
        "eos_invoices/dashboard.overview.html", {"overview": overview}, request=request
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
    # a static file cannot read the catalogue; log.js reads this instead
    filter_labels = {
        "filterLabel": _("Filter by"),
        "allSources": _("All sources"),
        # same msgid as the "All Corporations" nav tab - one glossary entry for both
        "allCorporations": _("All Corporations"),
    }
    return _render(
        request, "eos_invoices/log.html", {"page": page, "filter_labels": filter_labels}
    )


@login_required
@permission_required("eos_invoices.manage_sources")
@require_POST
def mark_paid(request, pk):
    source = get_object_or_404(PaymentSource, pk=pk)
    row = request.POST.get("row", "")

    try:
        with transaction.atomic():
            _log_marking(request, source, mark_row_paid(source, row))
    except SourceError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, _("Marked as paid."))

    return _back(request)


@login_required
@permission_required("eos_invoices.manage_sources")
@require_POST
def mark_selected_paid(request):
    """Mark every row ticked on the admin overview, across Corporations.

    Each box carries "source:corporation:row" as the page showed it. Only
    those rows are marked - a payment that arrived after the page was loaded
    was never seen and stays open - and each one only if it still belongs to
    the Corporation it was listed under.
    """
    sources = {}
    wanted = []
    skipped = 0
    for value in request.POST.getlist("selected"):
        try:
            source_pk, corporation_id, row = value.split(":", 2)
            wanted.append((int(source_pk), int(corporation_id), row))
        except ValueError:
            skipped += 1

    for source in PaymentSource.objects.filter(pk__in={w[0] for w in wanted}):
        sources[source.pk] = source

    marked = 0
    # all or nothing if the database fails half way; a row that is merely
    # paid already, gone or of another Corporation is skipped, not fatal
    with transaction.atomic():
        for source_pk, corporation_id, row in wanted:
            source = sources.get(source_pk)
            if source is None:
                skipped += 1
                continue
            try:
                marking = mark_row_paid(source, row, corporation_id=corporation_id)
            except SourceError:
                skipped += 1
                continue
            _log_marking(request, source, marking)
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
    if not marked and not skipped:
        messages.info(request, _("Nothing was selected."))
    return _back(request)


def _user_name(user):
    main = user.profile.main_character
    return main.character_name if main else user.username


def _log_marking(request, source, marking):
    invoice = marking.invoice
    corporation = EveCorporationInfo.objects.filter(
        corporation_id=marking.corporation_id
    ).first()
    # the owning app keeps no record of who flipped its flag - we do
    PaymentLog.objects.create(
        user=request.user,
        user_name=_user_name(request.user),
        source=source,
        source_name=source.name,
        row_pk=str(invoice.pk),
        corporation_id=marking.corporation_id,
        corporation_name=corporation.corporation_name if corporation else "",
        amount=invoice.amount,
        reason=invoice.reason[:255],
        label=invoice.label[:255],
        paid_field=marking.paid_field,
        previous_value=marking.previous_json,
        written_value=marking.written_json,
    )
    logger.info(
        "eos_invoices: %s marked row %s of %s as paid", request.user, invoice.pk, source
    )


@login_required
@permission_required("eos_invoices.manage_sources")
@require_POST
def undo_marking(request, pk):
    """Take back a mark as paid, for the misclick."""
    with transaction.atomic():
        # locked, so two admins undoing the same entry cannot both write
        entry = get_object_or_404(PaymentLog.objects.select_for_update(), pk=pk)
        if not entry.can_undo:
            messages.error(request, _("This entry cannot be undone."))
            return _back_to_log(request)
        try:
            undo_mark_paid(
                entry.source,
                entry.row_pk,
                entry.paid_field,
                entry.previous_value,
                entry.written_value,
            )
        except SourceError as exc:
            messages.error(request, str(exc))
            return _back_to_log(request)

        entry.reverted_at = timezone.now()
        entry.reverted_by = request.user
        entry.reverted_by_name = _user_name(request.user)
        entry.save(update_fields=["reverted_at", "reverted_by", "reverted_by_name"])

    logger.info(
        "eos_invoices: %s undid marking row %s of %s as paid",
        request.user,
        entry.row_pk,
        entry.source_name,
    )
    messages.success(request, _("Undone: the payment is open again."))
    return _back_to_log(request)


def _back_to_log(request):
    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = reverse("eos_invoices:log")
    return redirect(target)


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
