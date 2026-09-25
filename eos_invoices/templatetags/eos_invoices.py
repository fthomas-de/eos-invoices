from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def isk(value):
    """An ISK amount for display: whole ISK, thousands split by dots.

    Fixed rather than localised on purpose - with USE_THOUSAND_SEPARATOR the
    separator followed the viewer's language, so the same sum read 1,500,000
    for one CEO and 1.500.000 for the next.

    What is no finite number comes back unchanged. int() stays inside the
    try: a NaN quantizes without complaint and only fails there.
    """
    try:
        amount = int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        return value
    return f"{amount:,}".replace(",", ".")
