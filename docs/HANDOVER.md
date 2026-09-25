# Handover

Where the work stands and what is still open. `CLAUDE.md` holds the durable
rules for working on this app; this file holds the moment, and goes stale on
purpose - if a statement here contradicts the code, the code is right.

Last updated 2026-09-24.

## Release

- Version **0.0.13** in `eos_invoices/__init__.py`, **not committed** - the
  review of 2026-09-25 sits in the working tree, under `[0.0.13]` in
  `CHANGELOG.md`. `e73411a` (0.0.12) is still the last commit; 0.0.11 is the
  last version pushed to `fthomas-de/eos-invoices` (private)
- Migrations **0001-0007** applied in `aa_dev`, including **0007**
  (`0007_log_model_label_and_texts`: `PaymentLog.model_label`, new help
  texts, new permission names plus a RunPython that renames the two existing
  `auth.Permission` rows - Django never renames one by itself).
- Catalogues (`de`, `ru`, `zh_Hans`) are caught up: `tools/translate.py` ran
  for 0.0.13 and reported "Catalogues complete, checked, compiled and
  tested". "Outstanding only", "Including paid" and "Nothing outstanding."
  needed the `eos-invoices` context - Alliance Auth's own catalogue had
  already claimed those words and was winning the clash.
- 148 tests green (3 catalogue tests skipped in the normal run - they run
  inside `tools/translate.py`, where they also passed), `makemigrations
  --check` clean, `collectstatic` run
- A personal, cross-project skill for this ritual exists now:
  `C:\Users\flt\.claude\skills\push\SKILL.md` - bumps the version, runs the
  project's translation tool, splits the changelog, runs the checks, commits
  via a message file (never a heredoc), but never pushes. Invoke it by saying
  "push"; it stops at a ready commit and shows the `git push` command.

## What the app is

A Corporation's outstanding payments across other Alliance Auth apps, read
generically: a `PaymentSource` names a model and its fields (Corporation ID,
amount, paid flag, optional reason/description templates, date, month/year,
pay-to Corporation). Nothing is written for one app in particular; all reads
and writes go through the ORM and the owning model's `save()`.

| Page | Permission | What |
|---|---|---|
| Overview | `basic_access` (CEOs) | Payments of the main's Corporation, read only; copy buttons for recipient, amount, reason |
| Dashboard widget | `basic_access` | Compact version of Overview on Alliance Auth's own dashboard, hidden unless something is settled and outstanding - a current-month row still in progress does not count towards its total |
| All Corporations | `manage_sources` | Open payments of every Corporation in the configured Alliance, **grouped by source** (not by Corporation) with a Corporation column; mark one row or the ticked rows as paid |
| Log | `manage_sources` | Every marking, with undo for a misclick; filterable by Source and Corporation on the server, across all pages |
| Sources | `manage_sources` | Payment sources; field dropdowns read from the chosen model |
| Alliance | `manage_sources` | The Alliance the app works for; outside it nobody sees anything |

Every table with a Description column sorts by Corporation then Description
on load (tables that have no Corporation column - the CEO overview - sort by
Description alone); a header click still re-sorts by anything else. The log
is the one exception: it defaults to chronological order (newest first) -
a log reads as a log, not grouped by Corporation. A Description cell sorts
by `Invoice.label_order` (year-month, else date, then the text), so
"01/2027" comes after "12/2026".

Where the logic lives:

| File | Role |
|---|---|
| `sources.py` | the engine: field validation (`check_source`), reading (`get_invoices_by_corporation`), marking and undo, the month/year reason-hiding check |
| `overview.py` | what a CEO and an admin get to see; `build_admin_overview` groups by source |
| `views.py` | pages, marking, undo, log, the `dashboard_overview` widget |
| `templatetags/eos_invoices.py` | `isk` filter: whole ISK, dots between thousands |
| `static/eos_invoices/js/` | copy, confirm, searchable dropdowns (Tom Select), sortable tables (DataTables, `tables.js`, with AA's DataTables translation from `base.html`), row selection, the log (`log.js`: its table, and sending the server-side filter form on change) |
| `tools/translate.py`, `tools/glossary.py` | the release translation run and its source of truth; also reports glossary entries the code no longer uses; `glossary.problems()` checks the glossary's shape, run by translate.py and by `TestGlossary` in the normal suite |
| `runtests.py`, `tox.ini`, `testauth/` | the suite without an Auth instance: `python runtests.py eos_invoices` on testauth's own sqlite (needs Redis on localhost, like Auth) |

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
- 0 ISK rows are dropped everywhere, paid or not - a corp exempted that
  month says nothing either way.
- Translations only at a release, via `tools/translate.py`; the catalogue
  tests run only there.
- The month filter (a date-range filter on the overview) was dropped
  ("filter ist egal") - not to be confused with the Month/Year field feature
  below, which the user asked for afterwards for a different reason.
- **Month field + Year field** on a source hide the Reason while a row's
  month and year both equal today's - *both fields are required together*;
  the user explicitly asked for this after the month-only version shipped,
  because a month number alone cannot tell this year's row from the same
  month a year ago. Comparison is plain integer equality both sides, so
  leading zeros never enter into it.
- "All Corporations" groups by source (one table per source, Corporation as
  a column) rather than by Corporation (one card per Corporation) - the user
  asked for this explicitly; an admin working one app's payments wants them
  together across every Corporation.
- A provider hook for apps that keep balances instead of rows is postponed
  until an app needs it (see README, "Possible extensions").
- The **dashboard widget's total** excludes rows still in progress
  (`reason_hidden`, the current-month Month/Year rows): the amount owed for
  them can still change, so a compact number shown outside the full overview
  should not include it. The full overview still shows those rows and their
  amount still counts toward its own total - the row itself explains why the
  Reason is hidden, a bare number on the dashboard would not.
- The **log's default sort is chronological**, not the Corporation/
  Description convention the other tables use - the user wants a log to read
  as a log. A header click still re-sorts the current page by anything else;
  since the default already matches the query's own order, no separate
  server-side sorting is needed even once the log spans several pages.
- A row whose Reason is hidden for the month still in progress gets **no
  copy button for its amount**; the row and its amount still show. The
  **source total and its copy button stay as they are** (they still count
  that row) - asked and decided explicitly.
- The **log filter runs on the server** (query parameters `source`,
  `corporation`; paging stays at 100 and keeps the filter), replacing
  datatables-filterdropdown, which only saw one page.
- Undo is **refused once a source reads another model** than the row was
  marked in (`PaymentLog.model_label`); entries older than migration 0007
  have no model and stay undoable as before.
- "N Corporations with nothing outstanding" is **left out while a source
  failed or was cut short** on "All Corporations".
- The Description column sorts **by period** (year/month, else date).
- Russian glossary: "Pay to" = "Получатель", status "Open" = "Не оплачено".
- The navigation uses **Alliance Auth's standard** `nav-link {% navactive %}`,
  no colours of our own.
- testauth has its **own database, never `aa_dev`**.
- Permission names were reworded; `manage_sources` names marking, the log
  and undo.

## Since 0.0.12 (in 0.0.13, not committed)

Everything under `[0.0.13]` in `CHANGELOG.md`, working tree only. The
glossary entries below are already in the compiled catalogues now - written
by the assistant, like the rest, not checked by a native speaker; worth a
look before this ships:

- the Reason and Date field help texts, the skip message (plural), the undo
  refusal "This source reads another model since this was marked; nothing
  was changed.", "Only the newest %(limit)s payments are shown; the total
  counts only those.", "No entries match this filter.", "Edit" and "Delete"
  (context `eos-invoices` in the code)
- ru "Pay to", ru "Open", de "The paid field of this source has changed
  since."
- "Outstanding only", "Including paid" and "Nothing outstanding." now carry
  the `eos-invoices` context too (added while running `tools/translate.py`
  for this release, after the catalogue test named the clash).

`pyproject.toml` keeps `allianceauth>=5.1.4`: raising it to 5.3.0 was only
needed for datatables-filterdropdown's camelCase options, and the log no
longer uses that plugin. Everything the templates use now exists in 5.1.4
(checked in the AA git tags).

## Open

1. **"PvE Tax" source in `aa_dev` uses the wrong month format.** Its reason
   template is `{corp_id}/{month:02d}/{year}`, but eos-tax matches payments
   against `{corp_id}/{month}/{year}` - no leading zero (`eos_tax/util.py`).
   With eos-tax's `use_reason` on, a payment made with the copied reason for
   January to September would not be recognised. Not changed: it is the
   user's configuration - ask. The README example is correct, and the form's
   help text no longer suggests `{month:02d}` as its example. The same
   source has no Month/Year field configured, so the new hide-Reason feature
   does nothing for it yet.
2. aa-miningtax is not installed in the dev instance; its README example was
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
  A failure can also show up only as a cascade of
  `TransactionManagementError` in the setUpClass of later classes - same
  cure. With other sessions testing at the same time, give each run its own
  database: `EOS_TEST_DB=test_eos_invoices eos-test eos_invoices`.
- Static URLs in rendered pages carry the manifest hash before the
  extension (`de-DE.5ab6….json`); a test matches up to the dot.
- `values_list(...).distinct()` on `PaymentLog` needs `.order_by()` first:
  the model's ordering would otherwise join the DISTINCT columns.
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
- A Bash heredoc for a commit message can silently mangle apostrophes and
  cut the message off mid-sentence, dropping even the attribution line
  (happened once, release 0.0.9). Always write the message to a file first
  and commit with `git commit -F <file>` - see the `push` skill above.
- A long session resends its whole transcript on every request, so cost per
  turn grows with the conversation, not with what that turn actually does.
  One session carried the entire 0.0.1-0.0.11 history; see the user's own
  memory note "Eine Sitzung je Thema". Start a fresh session per topic.
