# EOS Invoices

An [Alliance Auth](https://gitlab.com/allianceauth/allianceauth) app that shows
the CEO of a Corporation every payment their Corporation still owes, collected
from other apps in one list: mining tax, PvE tax, rent, whatever an app records
per Corporation.

The app does not know those apps. Each one is registered as a **payment source**
on a settings page by naming its model and the fields that hold the Corporation
ID, the amount and whether it has been paid. Nothing has to change in the other
app.

## Features

- One overview of outstanding payments across all configured apps, per source
  and in total
- Recipient, amount and reason per payment, each ready to copy into the
  in-game transfer
- "Pay to" Corporation per source, chosen from the Alliance
- Toggle between outstanding only and including paid
- Admin overview of all Corporations of the Alliance, where payments can be
  marked as paid, and a log of who marked what
- Sources are checked when they are saved; the source list shows whether each
  one can currently be read
- Restricted to the Corporations of one Alliance

## Installation

1. Install the package into the virtual environment of your Alliance Auth:

   ```bash
   pip install git+https://github.com/fthomas-de/eos-invoices.git
   ```

2. Add `"eos_invoices",` to `INSTALLED_APPS` in `local.py`.

3. Run migrations and collect static files:

   ```bash
   python manage.py migrate
   ```

   ```bash
   python manage.py collectstatic --noinput
   ```

4. Restart supervisor.

## Permissions

| Permission | Who | What |
|---|---|---|
| `eos_invoices.basic_access` | CEOs | See outstanding payments of the Corporation of their main character |
| `eos_invoices.manage_sources` | Admins | See the open payments of all Corporations of the Alliance, mark them as paid, read the log; maintain payment sources and the Alliance |

A Corporation can have several CEOs in Auth terms (directors, alt CEOs): give
the permission to each of them, via a group or state.

Only the **main character** counts. Its Corporation has to be in the Alliance
chosen on the *Alliance* tab; without an Alliance nobody sees anything.

## Configuring a source

*Invoices → Sources → Add source*

| Field | Meaning |
|---|---|
| Model | The model with one row per payment, e.g. `eos_tax.MonthlyTax` |
| Corporation ID field | Field with the EVE Corporation ID. Relations are followed with `__`, e.g. `corporation__corporation_id` |
| Amount field | Amount owed in ISK |
| Paid field / Paid when | When a row counts as paid: the field is true, is not empty (e.g. a paid-at date), or equals a given value |
| Reason | Template for the in-game reason. Field names in braces are replaced: `{corp_id}/{month:02d}/{year}` |
| Description | Template shown next to the amount, e.g. `{month:02d}/{year}` |
| Date field | Optional, rows are sorted by it |
| Pay to | The Corporation that collects the ISK, chosen from the Corporations of the configured Alliance |

The field settings are dropdowns with the fields of the chosen model, one
relation deep and filtered to the types that fit. Placeholders for the
reason and description can be inserted with a click.

Only forward relations to one row can be followed. A path across a reverse or
many-to-many relation would repeat a payment once per related row and is
refused.

### Examples

**eos-tax**

| | |
|---|---|
| Model | `eos_tax.MonthlyTax` |
| Corporation ID field | `corp_id` |
| Amount field | `tax_value` |
| Paid field | `payed`, *Field is true* |
| Reason | `{corp_id}/{month}/{year}` |
| Description | `{month:02d}/{year}` |

**aa-miningtax**

| | |
|---|---|
| Model | `miningtax.AllianceBillingRecord` |
| Corporation ID field | `corporation__corporation_id` |
| Amount field | `total_due` |
| Paid field | `paid`, *Field is true* |
| Reason | `{corporation__corporation_id}/{month:02d}/{year}` |
| Description | `{month:02d}/{year}` |

## Marking payments as paid

*Invoices → All Corporations* lists the open payments of every Corporation in
the Alliance. Its *Mark as paid* button writes to the table of the other app,
through that model's own `save()`, and adds an entry to *Invoices → Log*. The value follows the source's *Paid when* setting:

| Paid when | Written |
|---|---|
| Field is true | `True` |
| Field equals value | the configured value |
| Field is not empty, date or datetime field | today, or now |

There is no button for a text field under *Field is not empty*, nor for a paid
field behind a relation (`something__paid`). Only the paid field itself is
written; a separate "paid at" column of the other app, as aa-miningtax has,
stays as it is.

## Possible extensions

Apps that keep a running balance instead of one row per payment cannot be
described by field names. A small provider interface, a function the other app
exposes, would cover them; it will be added once an app needs it.
