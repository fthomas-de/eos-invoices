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
from django.db.models import BooleanField, Case, F, Q, Value, When
from django.utils import timezone
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
    pk: object
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
    can_mark_paid: bool = False

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


# the corporation value is fetched under this alias, so it cannot collide
# with a template placeholder of the same path
CORPORATION_ALIAS = "eos_invoices_corporation"


def _invoice_rows(source, **filters):
    """Annotated values() of a source, filtered, newest first.

    The one place that turns rows of a foreign model into invoice data, shared
    by the lists and by the snapshot taken before a row is marked as paid.
    """
    errors = check_source(source)
    if errors:
        raise SourceError(" ".join(errors.values()))

    model = resolve_model(source.model_label)
    paid_q = _paid_q(source, model)

    queryset = model._default_manager.filter(**filters).annotate(
        **{
            PAID_ALIAS: Case(
                When(paid_q, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
            CORPORATION_ALIAS: F(source.corporation_field),
        }
    )

    wanted = {"pk", source.amount_field, PAID_ALIAS, CORPORATION_ALIAS}
    wanted.update(template_fields(source.reason_template))
    wanted.update(template_fields(source.label_template))
    if source.date_field:
        wanted.add(source.date_field)
        queryset = queryset.order_by(f"-{source.date_field}", "-pk")
    else:
        queryset = queryset.order_by("-pk")

    return queryset.values(*wanted), paid_q


def _to_invoice(source, row):
    when = row.get(source.date_field) if source.date_field else None
    if isinstance(when, datetime):
        when = when.date()

    return Invoice(
        pk=row["pk"],
        amount=Decimal(str(row[source.amount_field] or 0)),
        paid=row[PAID_ALIAS],
        reason=render_template(source.reason_template, row),
        label=render_template(source.label_template, row),
        date=when,
    )


def get_invoices_by_corporation(source, corporation_ids, *, include_paid=False, limit=MAX_ROWS):
    """Payments of several Corporations in one source, in one query.

    Returns ``({corporation_id: [Invoice, ...]}, truncated)``, newest first
    within each Corporation. ``truncated`` says the source had more rows than
    ``limit``; the caller has to say so rather than show a short list as if it
    were complete.
    """
    rows, paid_q = _invoice_rows(
        source, **{f"{source.corporation_field}__in": list(corporation_ids)}
    )
    if not include_paid:
        rows = rows.exclude(paid_q)

    rows = list(rows[: limit + 1])
    truncated = len(rows) > limit

    by_corporation = {}
    for row in rows[:limit]:
        by_corporation.setdefault(row[CORPORATION_ALIAS], []).append(_to_invoice(source, row))

    return by_corporation, truncated


def get_invoice(source, pk):
    """One row as ``(corporation_id, Invoice)``, or SourceError if it is gone."""
    try:
        rows, _paid_q = _invoice_rows(source, pk=pk)
        row = rows.first()
    except (ValueError, ValidationError) as exc:
        raise SourceError(_("The payment no longer exists.")) from exc
    if row is None:
        raise SourceError(_("The payment no longer exists."))
    return row[CORPORATION_ALIAS], _to_invoice(source, row)


def get_invoices(source, corporation_id, *, include_paid=False):
    """Payments of one Corporation in one source, newest first."""
    by_corporation, _truncated = get_invoices_by_corporation(
        source, [corporation_id], include_paid=include_paid
    )
    return by_corporation.get(corporation_id, [])


def paid_marker(source):
    """The value that marks a row of this source as paid, or None.

    Only a field of the row itself can be written: a path across a relation
    would change a row of another model that other payments may share. For
    "Field is not empty" only dates have an obvious value - now.
    """
    if check_source(source) or "__" in source.paid_field:
        return None

    model_field = resolve_field(resolve_model(source.model_label), source.paid_field)

    if source.paid_mode == "true":
        return lambda: True
    if source.paid_mode == "equals":
        value = model_field.to_python(source.paid_value)
        return lambda: value
    if isinstance(model_field, models.DateTimeField):
        return timezone.now
    if isinstance(model_field, models.DateField):
        return lambda: timezone.localdate()
    return None


def to_json(value):
    """A field value as JSON, without losing precision on the way.

    Not DjangoJSONEncoder: it cuts datetimes to milliseconds, while the
    database keeps microseconds - the stored stamp would then never equal the
    field again, and undoing a date would always be refused as "changed".
    """
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


@dataclass(frozen=True)
class Marking:
    """What mark_paid changed, as the log needs it to show and to undo it."""

    corporation_id: int
    invoice: Invoice
    paid_field: str
    previous: object
    written: object

    @property
    def previous_json(self):
        return to_json(self.previous)

    @property
    def written_json(self):
        return to_json(self.written)


def mark_paid(source, pk, *, corporation_id=None):
    """Mark one row of a source as paid, through the model's own save().

    save() rather than a queryset update, so the owning app's save logic and
    signals still run - its own idea of what paying means stays in charge.

    Returns a ``Marking``: the row as it was, and the paid field's value
    before and after, so the change can be undone exactly. A row that is
    already paid is refused, so the log never records a change that did not
    happen. With ``corporation_id`` a row of any other Corporation is refused
    as well - a batch posted for one Corporation must not reach into another.
    """
    marker = paid_marker(source)
    if marker is None:
        raise SourceError(_("Rows of this source cannot be marked as paid here."))

    row_corporation_id, invoice = get_invoice(source, pk)
    if corporation_id is not None and row_corporation_id != corporation_id:
        raise SourceError(_("This payment belongs to another Corporation."))
    if invoice.paid:
        raise SourceError(_("This payment is already marked as paid."))

    model = resolve_model(source.model_label)
    row = model._default_manager.get(pk=invoice.pk)
    previous = getattr(row, source.paid_field)
    written = marker()
    setattr(row, source.paid_field, written)
    row.save(update_fields=[source.paid_field])
    return Marking(row_corporation_id, invoice, source.paid_field, previous, written)


def undo_mark_paid(source, pk, paid_field, previous, written):
    """Put back the value mark_paid replaced, through the model's own save().

    Refused when the field no longer holds what was written: then the owning
    app, or somebody else, has changed it since, and putting the old value
    back would overwrite that - an automatic payment check, for instance.
    ``previous`` and ``written`` may come back from JSON as strings; the
    field turns them into its own type before anything is compared.
    """
    model = resolve_model(source.model_label)
    try:
        model_field = resolve_field(model, paid_field)
    except SourceError as exc:
        raise SourceError(_("The paid field of this source has changed since.")) from exc
    if "__" in paid_field:
        raise SourceError(_("The paid field of this source has changed since."))

    try:
        row = model._default_manager.get(pk=pk)
    except (model.DoesNotExist, ValueError, ValidationError) as exc:
        raise SourceError(_("The payment no longer exists.")) from exc

    if getattr(row, paid_field) != model_field.to_python(written):
        raise SourceError(
            _("The payment has been changed since it was marked; it was left as it is.")
        )

    setattr(row, paid_field, model_field.to_python(previous))
    row.save(update_fields=[paid_field])


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
