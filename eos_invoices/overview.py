"""What one user gets to see on the overview."""

from dataclasses import dataclass, field
from decimal import Decimal

from django.utils.translation import gettext as _

from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger

from eos_invoices.models import InvoiceConfiguration, PaymentSource
from eos_invoices.sources import (
    SourceError,
    SourceResult,
    get_invoices,
    get_invoices_by_corporation,
    paid_marker,
)

logger = get_extension_logger(__name__)


@dataclass
class Overview:
    corporation_id: int | None = None
    corporation_name: str = ""
    # why nothing is shown; empty when the user may see their Corporation
    notice: str = ""
    results: list = field(default_factory=list)

    @property
    def open_total(self):
        return sum((r.open_total for r in self.results), Decimal(0))

    @property
    def open_total_settled(self):
        return sum((r.open_total_settled for r in self.results), Decimal(0))


def build_overview(user, *, include_paid=False):
    """Payments of the Corporation of the user's main, across all sources.

    Only the main counts, not alts: a CEO permission is given to a person, and
    the Corporation that person leads is the one their main sits in. Read only
    for everybody: payments are marked as paid on the admin overview.
    """
    main = user.profile.main_character
    if main is None:
        return Overview(notice=_("You have no main character."))

    overview = Overview(
        corporation_id=main.corporation_id,
        corporation_name=main.corporation_name,
    )

    alliance = InvoiceConfiguration.get_solo().alliance
    if alliance is None:
        overview.notice = _("No Alliance has been configured for this app yet.")
        return overview

    if main.alliance_id != alliance.alliance_id:
        overview.notice = _(
            "%(corporation)s is not a member of %(alliance)s."
        ) % {"corporation": main.corporation_name, "alliance": alliance.alliance_name}
        return overview

    for source in PaymentSource.objects.filter(enabled=True).select_related("pay_to"):
        result = SourceResult(source=source)
        try:
            result.invoices = get_invoices(
                source, overview.corporation_id, include_paid=include_paid
            )
        except SourceError as exc:
            result.error = str(exc)
        except Exception as exc:  # noqa: BLE001 - one broken app must not hide the others
            logger.exception("eos_invoices: reading %s failed", source)
            result.error = str(exc)
        overview.results.append(result)

    return overview


# open payments of a whole Alliance per source; far above a real month's
# count, low enough that a source whose paid flag never matches cannot flood
# the page
ADMIN_MAX_ROWS = 2000


@dataclass(frozen=True)
class CorporationInvoice:
    """One invoice next to whose Corporation it is - a row of a table grouped
    by source, where the Corporation is a column rather than the grouping."""

    corporation: object
    invoice: object


@dataclass
class SourceInvoices:
    source: object
    can_mark_paid: bool = False
    rows: list = field(default_factory=list)  # list[CorporationInvoice]

    @property
    def open_total(self):
        return sum((r.invoice.amount for r in self.rows if not r.invoice.paid), Decimal(0))


@dataclass
class AdminOverview:
    notice: str = ""
    sources: list = field(default_factory=list)  # list[SourceInvoices]
    # (source, message) for sources that failed or were cut short
    problems: list = field(default_factory=list)
    settled_count: int = 0

    @property
    def open_total(self):
        return sum((s.open_total for s in self.sources), Decimal(0))


def build_admin_overview():
    """Open payments of every Corporation in the Alliance, grouped by source.

    One table per source rather than one per Corporation: an admin working a
    given app's payments (mining tax, say) wants that app's rows together,
    across every Corporation, not split into as many tables as there are
    Corporations that owe it something.
    """
    # the key is enough; loading the Alliance itself would cost a query for nothing
    alliance_pk = InvoiceConfiguration.get_solo().alliance_id
    if alliance_pk is None:
        return AdminOverview(notice=_("No Alliance has been configured for this app yet."))

    corporations = {
        c.corporation_id: c
        for c in EveCorporationInfo.objects.filter(alliance_id=alliance_pk).order_by(
            "corporation_name"
        )
    }
    corporation_ids = list(corporations)
    has_open = set()
    overview = AdminOverview()

    for source in PaymentSource.objects.filter(enabled=True).select_related("pay_to"):
        try:
            by_corporation, truncated = get_invoices_by_corporation(
                source, corporation_ids, limit=ADMIN_MAX_ROWS
            )
        except SourceError as exc:
            overview.problems.append((source, str(exc)))
            continue
        except Exception as exc:  # noqa: BLE001 - one broken app must not hide the others
            logger.exception("eos_invoices: reading %s failed", source)
            overview.problems.append((source, str(exc)))
            continue

        if truncated:
            overview.problems.append(
                (
                    source,
                    _("More than %(limit)s open payments; only the newest are shown.")
                    % {"limit": ADMIN_MAX_ROWS},
                )
            )

        rows = []
        for corporation_id, invoices in by_corporation.items():
            has_open.add(corporation_id)
            corporation = corporations[corporation_id]
            rows.extend(CorporationInvoice(corporation, invoice) for invoice in invoices)

        if rows:
            overview.sources.append(
                SourceInvoices(
                    source=source, rows=rows, can_mark_paid=paid_marker(source) is not None
                )
            )

    overview.settled_count = len(corporation_ids) - len(has_open)
    return overview
