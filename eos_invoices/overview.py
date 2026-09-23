"""What one user gets to see on the overview."""

from dataclasses import dataclass, field
from decimal import Decimal

from django.utils.translation import gettext as _

from allianceauth.services.hooks import get_extension_logger

from eos_invoices.models import InvoiceConfiguration, PaymentSource
from eos_invoices.sources import SourceError, SourceResult, get_invoices

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


def build_overview(user, *, include_paid=False):
    """Payments of the Corporation of the user's main, across all sources.

    Only the main counts, not alts: a CEO permission is given to a person, and
    the Corporation that person leads is the one their main sits in.
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
                source, main.corporation_id, include_paid=include_paid
            )
        except SourceError as exc:
            result.error = str(exc)
        except Exception as exc:  # noqa: BLE001 - one broken app must not hide the others
            logger.exception("eos_invoices: reading %s failed", source)
            result.error = str(exc)
        overview.results.append(result)

    return overview
