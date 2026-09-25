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
- A widget on Alliance Auth's own dashboard, for a CEO with something
  outstanding, linking to the full overview
- Recipient, amount and reason per payment, each ready to copy into the
  in-game transfer
- "Pay to" Corporation per source, chosen from the Alliance
- Toggle between outstanding only and including paid
- A row worth exactly 0 ISK - a corp exempted that month, say - is dropped
  everywhere rather than shown as noise
- Admin overview of all Corporations of the Alliance, grouped by source with
  Corporation as a column, where payments can be marked as paid, and a log of
  who marked what, filterable by Source and Corporation across all its pages
- Optional: hide the Reason of a row for the month still in progress
- The overview sorts by Description on load, "All Corporations" by
  Corporation then Description, the log newest first; a header click
  re-sorts by anything else. Descriptions sort in time order when the source
  names a Month and Year field or a Date field
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
| `eos_invoices.manage_sources` | Admins | See the open payments of all Corporations of the Alliance, mark them as paid, read and undo the log; maintain payment sources and the Alliance |

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
| Reason | Template for the in-game reason. Field names in braces are replaced, e.g. `{corp_id}/{month}/{year}`; a format may follow a colon, as in `{month:02d}`. Use exactly the form the receiving app matches payments against - eos-tax, for one, expects no leading zero |
| Description | Template shown next to the amount, e.g. `{month:02d}/{year}` |
| Date field | Optional, shown in the Date column. Without Month and Year fields the Description column sorts by it; a source with more rows than one page shows keeps the newest |
| Month field | Optional integer field (1-12). Together with Year field, hides the Reason while the row is for the current month - see below |
| Year field | Optional integer field, e.g. `2026`. Required together with Month field for hiding to take effect |
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

## Hiding the reason for the current month

Setting *both* *Month field* and *Year field* hides the Reason of a row while
that row's month and year are the current ones - the amount owed for a month
still in progress can still change, so the code to pay it is withheld until it
is settled. The row still shows, with its amount; the Reason is replaced by a
note, and the row's amount has no copy button. The source total above keeps
its own, and still counts the row. Left unset (the default), or with only one of the two fields set,
the Reason always shows - a month number alone cannot tell this year's row
from the same month a year ago, so both are required together.

## Marking payments as paid

*Invoices → All Corporations* lists the open payments of every Corporation in
the Alliance, grouped by source: one table per source, every Corporation's
rows in it. *Mark as paid* on a row writes to the table of the other app,
through that model's own `save()`, and adds an entry to *Invoices → Log*.
Ticking rows and *Mark selected as paid* does the same for all of them at
once, across sources and Corporations; *Select all* above a source's table
ticks every row in it.

A misclick is taken back with *Undo* in the log. It restores the exact value
the paid field held before - unless the field has changed since, in which case
it is left alone. The entry stays in the log, marked as undone. The value follows the source's *Paid when* setting:

| Paid when | Written |
|---|---|
| Field is true | `True` |
| Field equals value | the configured value |
| Field is not empty, date or datetime field | today, or now |

There is no button for a text field under *Field is not empty*, nor for a paid
field behind a relation (`something__paid`). Only the paid field itself is
written; a separate "paid at" column of the other app, as aa-miningtax has,
stays as it is.

## Translations

The German, Russian and Simplified Chinese translations are machine-generated and may be inaccurate. Corrections are welcome: every translation lives in
`tools/glossary.py`; `tools/translate.py` writes it into the catalogues.
EVE terms (Corporation, Alliance, Main, Reason, ISK) stay English on purpose.

## Possible extensions

Apps that keep a running balance instead of one row per payment cannot be
described by field names. A small provider interface, a function the other app
exposes, would cover them; it will be added once an app needs it.
