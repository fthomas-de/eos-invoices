"""Reading payments out of the models of other apps.

A ``PaymentSource`` only names fields; nothing here is written for one app in
particular. Everything goes through the ORM - no SQL is assembled from what an
admin typed into the settings page, so a field name can at worst fail the
lookup, never change the query.
"""

import re
import string
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.db.models import BooleanField, Case, Q, Value, When
from django.utils.translation import gettext as _

from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)

# One field name, or a path of them joined by "__". Deliberately no dots or
# brackets: str.format would follow those into attributes and items of the
# value, which turns a reason template into a way to read arbitrary objects.
NAME = re.compile(r"^[A-Za-z_]\w*$")

# Paid history can be long; nobody reads more than this per source on one page.
MAX_ROWS = 500

# alias for the computed paid flag, chosen so it cannot collide with a field
PAID_ALIAS = "eos_invoices_paid"

_FORMATTER = string.Formatter()


class SourceError(Exception):
    """A payment source cannot be read as configured."""


def plain_isk(value):
    """An amount as the in-game transfer field takes it: digits, no grouping.

    Whole amounts lose the ".00" - ISK transfers are nearly always whole, and
    a trailing fraction is one more thing to delete by hand after pasting.
    """
    value = Decimal(value).quantize(Decimal("0.01"))
    if value == value.to_integral_value():
        return str(int(value))
    return f"{value:f}"


@dataclass(frozen=True)
class Invoice:
    amount: Decimal
    paid: bool
    reason: str
    label: str
    date: date | None

    @property
    def amount_plain(self):
        return plain_isk(self.amount)


@dataclass
class SourceResult:
    source: object
    invoices: list = field(default_factory=list)
    error: str = ""

    @property
    def open_total(self):
        return sum((i.amount for i in self.invoices if not i.paid), Decimal(0))

    @property
    def open_total_plain(self):
        return plain_isk(self.open_total)


def resolve_model(label):
    try:
        return apps.get_model(label)
    except (LookupError, ValueError) as exc:
        raise SourceError(_("Unknown model %(label)s.") % {"label": label}) from exc


def field_names(model):
    """Plain fields of a model, offered when a name does not match."""
    return sorted(
        f.name
        for f in model._meta.get_fields()
        if f.concrete or f.many_to_one or f.one_to_one
    )


def resolve_field(model, path):
    """The model field at the end of a ``__`` path.

    Only forward relations to a single row may be crossed. Following a reverse
    or many-to-many relation would repeat a payment once per related row and
    quietly multiply the amount owed.
    """
    current = model
    parts = path.split("__")

    for index, part in enumerate(parts):
        if not NAME.match(part):
            raise SourceError(_("Invalid field name %(name)s.") % {"name": path})

        try:
            model_field = current._meta.get_field(part)
        except FieldDoesNotExist as exc:
            raise SourceError(
                _("%(model)s has no field %(field)s. Available: %(fields)s")
                % {
                    "model": current._meta.label,
                    "field": part,
                    "fields": ", ".join(field_names(current)),
                }
            ) from exc

        if not model_field.is_relation:
            if index != len(parts) - 1:
                raise SourceError(
                    _("%(field)s is not a relation and cannot be followed.")
                    % {"field": part}
                )
            return model_field

        if model_field.many_to_many or model_field.one_to_many:
            raise SourceError(
                _("%(field)s points at many rows; only single relations can be followed.")
                % {"field": part}
            )

        current = model_field.related_model

    raise SourceError(
        _("%(path)s ends at a relation. Name a field on it, e.g. %(path)s__%(example)s.")
        % {"path": path, "example": current._meta.pk.name}
    )


def kind_of(model_field):
    """Coarse type of a field, used to match it to what a setting needs."""
    # BooleanField before IntegerField: the check order matters for any
    # backend field that subclasses both
    if isinstance(model_field, models.BooleanField):
        return "boolean"
    if isinstance(model_field, models.IntegerField):
        return "integer"
    if isinstance(model_field, (models.DecimalField, models.FloatField)):
        return "number"
    if isinstance(model_field, models.DateField):
        return "date"
    if isinstance(model_field, (models.CharField, models.TextField)):
        return "text"
    return "other"


# which kinds each setting accepts; a missing entry accepts every kind
ACCEPTED_KINDS = {
    "corporation_field": {"integer"},
    "amount_field": {"integer", "number"},
    "date_field": {"date"},
}


def accepted_kinds(name, paid_mode=None):
    if name == "paid_field" and paid_mode == "true":
        return {"boolean"}
    return ACCEPTED_KINDS.get(name)


def field_options(model):
    """Every field path a setting can name, one relation deep.

    Deeper paths still work when typed into the admin, they are only not
    offered: fanning out every relation of every related model would bury the
    handful of useful entries.
    """
    options = []

    def add(path, model_field):
        options.append(
            {
                "path": path,
                "label": f"{path} · {model_field.verbose_name}",
                "kind": kind_of(model_field),
            }
        )

    for model_field in model._meta.get_fields():
        if not model_field.is_relation:
            if model_field.concrete:
                add(model_field.name, model_field)
            continue

        # the same rule resolve_field enforces: never across many rows
        if model_field.many_to_many or model_field.one_to_many:
            continue

        for related in model_field.related_model._meta.get_fields():
            if related.concrete and not related.is_relation:
                add(f"{model_field.name}__{related.name}", related)

    return sorted(options, key=lambda option: option["path"])


def template_fields(template):
    """The field paths a reason or description template refers to."""
    try:
        parsed = list(_FORMATTER.parse(template))
    except ValueError as exc:
        raise SourceError(_("Malformed template: %(error)s") % {"error": exc}) from exc

    names = []
    for _literal, name, spec, conversion in parsed:
        if name is None:
            continue
        if not NAME.match(name) or conversion or "{" in (spec or ""):
            raise SourceError(
                _("Invalid placeholder {%(name)s}. Use a field name with an optional format.")
                % {"name": name}
            )
        names.append(name)

    return names


def render_template(template, row):
    if not template:
        return ""
    try:
        return template.format_map(row)
    except (ValueError, TypeError, KeyError) as exc:
        # a format that does not suit the value, e.g. 02d on a text field;
        # showing the raw template beats hiding the whole payment
        logger.warning("eos_invoices: cannot render %r: %s", template, exc)
        return template


def check_source(source):
    """Every configuration problem of a source, keyed by form field name."""
    errors = {}

    try:
        model = resolve_model(source.model_label)
    except SourceError as exc:
        return {"model_label": str(exc)}

    messages = {
        "corporation_field": _("The Corporation ID field must be an integer field."),
        "amount_field": _("The amount field must be a number field."),
        "paid_field": _("\"Field is true\" needs a boolean field."),
        "date_field": _("The date field must be a date or datetime field."),
    }

    def check(name):
        try:
            model_field = resolve_field(model, getattr(source, name))
        except SourceError as exc:
            errors[name] = str(exc)
            return None
        kinds = accepted_kinds(name, source.paid_mode)
        if kinds and kind_of(model_field) not in kinds:
            errors[name] = messages[name]
        return model_field

    check("corporation_field")
    check("amount_field")
    paid_field = check("paid_field")
    if paid_field is not None and source.paid_mode == "equals":
        if source.paid_value == "":
            errors["paid_value"] = _("Enter the value that means paid.")
        else:
            try:
                paid_field.to_python(source.paid_value)
            except ValidationError as exc:
                errors["paid_value"] = " ".join(exc.messages)

    if source.date_field:
        check("date_field")

    for name in ("reason_template", "label_template"):
        try:
            for path in template_fields(getattr(source, name)):
                resolve_field(model, path)
        except SourceError as exc:
            errors[name] = str(exc)

    return errors


def _paid_q(source, model):
    path = source.paid_field
    if source.paid_mode == "true":
        return Q(**{path: True})
    if source.paid_mode == "equals":
        value = resolve_field(model, path).to_python(source.paid_value)
        return Q(**{path: value})

    # not empty: NULL, and for text also the empty string, count as unpaid
    query = Q(**{f"{path}__isnull": False})
    if isinstance(resolve_field(model, path), (models.CharField, models.TextField)):
        query &= ~Q(**{path: ""})
    return query


def get_invoices(source, corporation_id, *, include_paid=False):
    """Payments of one Corporation in one source, newest first."""
    errors = check_source(source)
    if errors:
        raise SourceError(" ".join(errors.values()))

    model = resolve_model(source.model_label)
    paid_q = _paid_q(source, model)

    queryset = model._default_manager.filter(**{source.corporation_field: corporation_id})
    if not include_paid:
        queryset = queryset.exclude(paid_q)

    queryset = queryset.annotate(
        **{
            PAID_ALIAS: Case(
                When(paid_q, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        }
    )

    wanted = {source.amount_field, PAID_ALIAS}
    wanted.update(template_fields(source.reason_template))
    wanted.update(template_fields(source.label_template))
    if source.date_field:
        wanted.add(source.date_field)
        queryset = queryset.order_by(f"-{source.date_field}", "-pk")
    else:
        queryset = queryset.order_by("-pk")

    invoices = []
    for row in queryset.values(*wanted)[:MAX_ROWS]:
        when = row.get(source.date_field) if source.date_field else None
        if isinstance(when, datetime):
            when = when.date()

        invoices.append(
            Invoice(
                amount=Decimal(str(row[source.amount_field] or 0)),
                paid=row[PAID_ALIAS],
                reason=render_template(source.reason_template, row),
                label=render_template(source.label_template, row),
                date=when,
            )
        )

    return invoices


def probe(source):
    """How many rows a source sees in total, or why it cannot be read."""
    errors = check_source(source)
    if errors:
        return None, " ".join(errors.values())

    try:
        return resolve_model(source.model_label)._default_manager.count(), ""
    except Exception as exc:  # noqa: BLE001 - a broken foreign table must not break the page
        logger.exception("eos_invoices: probing %s failed", source)
        return None, str(exc)
