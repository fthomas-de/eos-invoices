# Handover

Where the work stands and what is still open. `CLAUDE.md` holds the durable
rules for working on this app; this file holds the moment, and goes stale on
purpose - if a statement here contradicts the code, the code is right.

Last updated 2026-09-24.

## Release

- Version **0.0.8** in `eos_invoices/__init__.py`, committed and pushed to
  `fthomas-de/eos-invoices` (private), branch `master`
- Migrations **0001-0004** written and applied in `aa_dev`
- Catalogues complete: `de`, `ru`, `zh_Hans`, filled from `tools/glossary.py`
- 101 tests green (3 catalogue tests skipped - they run inside
  `tools/translate.py`), `makemigrations --check` clean, `collectstatic` run

## What the app is

A Corporation's outstanding payments across other Alliance Auth apps, read
generically: a `PaymentSource` names a model and its fields (Corporation ID,
amount, paid flag, optional reason/description templates, date, pay-to
Corporation). Nothing is written for one app in particular; all reads and
writes go through the ORM and the owning model's `save()`.

| Page | Permission | What |
|---|---|---|
| Overview | `basic_access` (CEOs) | Payments of the main's Corporation, read only; copy buttons for recipient, amount, reason |
| All Corporations | `manage_sources` | Open payments of every Corporation in the configured Alliance; mark one or the ticked rows as paid |
| Log | `manage_sources` | Every marking, with undo for a misclick |
| Sources | `manage_sources` | Payment sources; field dropdowns read from the chosen model |
| Alliance | `manage_sources` | The Alliance the app works for; outside it nobody sees anything |

Where the logic lives:

| File | Role |
|---|---|
| `sources.py` | the engine: field validation (`check_source`), reading (`get_invoices_by_corporation`), marking and undo |
| `overview.py` | what a CEO and an admin get to see |
| `views.py` | pages, marking, undo, log, the `dashboard_overview` widget |
| `templatetags/eos_invoices.py` | `isk` filter: whole ISK, dots between thousands |
| `static/eos_invoices/js/` | copy, confirm, searchable dropdowns (Tom Select), sortable tables (DataTables), row selection |
| `tools/translate.py`, `tools/glossary.py` | the release translation run and its source of truth |

## Decisions the user made

These are not derivable from the code alone - keep them unless the user says
otherwise:

- Sources are Django models only, no raw tables.
- The Alliance is a filter: a CEO sees their own Corporation only if it is in
  the configured Alliance.
- CEOs see only their main's Corporation. There is no Corporation choice on
  the overview - the user removed it as superfluous.
- Marking as paid happens on "All Corporations" only, never on the normal
  overview, not even for admins.
- The ISK rounding is display only; copy buttons copy the exact amount.
- Translations only at a release, via `tools/translate.py`; the catalogue
  tests run only there.
- The month filter was dropped ("filter ist egal").
- A provider hook for apps that keep balances instead of rows is postponed
  until an app needs it (see README, "Possible extensions").

## Open

1. **"PvE Tax" source in `aa_dev` uses the wrong month format.** Its reason
   template is `{corp_id}/{month:02d}/{year}`, but eos-tax matches payments
   against `{corp_id}/{month}/{year}` - no leading zero (`eos_tax/util.py`).
   With eos-tax's `use_reason` on, a payment made with the copied reason for
   January to September would not be recognised. Not changed: it is the
   user's configuration - ask. The README example is correct.
2. The log sorts within its page of 100 entries only; server-side sorting
   would be needed once it grows long.
3. aa-miningtax is not installed in the dev instance; its README example was
   taken from its source (`miningtax.AllianceBillingRecord`), not tried live.

## Dev instance

- `eos_invoices` is in `INSTALLED_APPS` of `~/aa-dev/working/myauth/myauth/settings/local.py`,
  installed editable into `~/aa-dev/venv`; `polib` is in the venv for the
  translation tool.
- Configured: Alliance "Invidia Gloriae Comes"; one source "PvE Tax" on
  `eos_tax.MonthlyTax`, pay to "Invidia Administrative"; 14 log entries from
  the user's own testing.
- The dev server needs a login, so pages were never checked in the browser by
  the assistant. Visual checks were done on local test pages with the real
  theme CSS (Darkly, Flatly, Bootstrap light and dark) instead.

## Traps met on the way

- Alliance Auth's catalogues translate many short words and win a msgid
  clash ("Open" became the verb, "Amount" a quantity). Use the contexts
  `EVE jargon` / `eos-invoices`; the clash test names every case.
- `DjangoJSONEncoder` cuts datetimes to milliseconds - undo compares stored
  values, so `sources.to_json` keeps full precision.
- Tom Select's Bootstrap 5 theme hard-codes light colours; `searchable.js`
  copies the theme's own `form-select` colours instead. Darkly has white
  inputs on a dark page, so the page variables are the wrong source.
- A failing subtest hangs `--parallel`; run without it to see the failure.
- A patch that inserts a test method at the wrong indentation makes the whole
  module fail to import - the suite then silently runs fewer tests. Compare
  the test count after every test change.
- `manage.py shell` connects to the real `aa_dev` database, with no
  transaction to roll back - unlike `manage.py test`. Calling `make_ceo()` or
  `make_source()` from `tests/base.py` there (done once, by mistake, while
  poking at rendered HTML) left a fake user "ceo" and a `PaymentSource`
  pointing at the test-only `eos_invoices.Due` sitting in the real database
  until they were found and removed on 2026-09-24. Those two helpers, and any
  other `tests/` code, belong inside a `TestCase` (`manage.py test`) only.
- `~/aa-dev/working/allianceauth` (the git checkout, used to read AA's own
  source) is not what actually runs - that is the `allianceauth` package
  installed in `~/aa-dev/venv`, and the two can differ. `bundles/
  filterdropdown-js.html` renders a different plugin with a different,
  camelCase option API (`labelFilter`, `labelDropdownAll`) in the installed
  version than the snake_case one the checkout's own `filterDropDown.js`
  suggests. When a bundle's behaviour matters, check the file the venv
  actually serves (`~/aa-dev/venv/lib/python3.12/site-packages/allianceauth/
  static/...` and `.../templates/...`), not the checkout.
