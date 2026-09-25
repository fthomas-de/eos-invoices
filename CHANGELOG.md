# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- A row for the current month stays out of the outstanding total through
  the 1st of the following month too, not just up to the last day of its
  own month - a full day's grace before the total picks it up, instead of
  the instant the calendar flips.
- The overview's totals - the Outstanding line and each source's total -
  count only rows whose Reason is shown. A row still in progress (Reason
  hidden for the current month) still appears with its amount, but stays
  out of every total, like on the dashboard: its amount can still change,
  and the source total is what gets copied out to pay.
- The dashboard widget no longer hides itself when there is nothing
  outstanding (or only a row still in progress) - it now shows a "Nothing
  outstanding." state with a check icon instead, so a CEO sees that at a
  glance rather than wondering whether the widget failed to load. Still
  hidden without the permission or when the full overview would only
  explain itself (no main character, no Alliance configured, Corporation
  outside it).
- The catalogue tests are selected by the tag `translations` instead of the
  environment variable `EOS_INVOICES_CHECK_TRANSLATIONS`: the suite runs with
  `--exclude-tag translations`, `tools/translate.py` with `--tag
  translations`. It is the same switch as in the sister apps, so one command
  works for all of them. A plain `eos-test eos_invoices` without the flag now
  runs the catalogue tests too.

## [0.0.13] - 2026-09-25

### Fixed

- Undo refuses an entry once its source reads another model than the one
  the row was marked in: the same row key there is a different payment, and
  its paid flag may well hold the very value that was written. The log now
  stores the model (migration 0007); entries made before keep working as
  they did.
- A row whose amount is empty (NULL) is dropped like a 0 ISK row; it used to
  show as "0 ISK", because excluding 0 on a nullable column keeps NULL rows.
- The overview says when a source had more rows than one page shows. With
  "Including paid" the oldest rows fell off silently, open ones included, and
  the Outstanding total dropped with them.
- "All Corporations" no longer counts Corporations as having nothing
  outstanding while a source failed or was cut short - they may owe exactly
  there.
- The Description column sorts in time order: by the row's year and month
  when the source names both fields, else by its date. As text,
  "01/2027" sorted before "12/2026".
- The copy confirmation shows a check mark again: Font Awesome Free has no
  regular "check", so the icon vanished for a moment instead. A failed copy
  is reported in the browser console, as on Alliance Auth's SRP page.
- The ISK display no longer fails on a NaN amount (possible in a float field
  on PostgreSQL); copied amounts round half a cent up, like the display,
  instead of to the nearest even cent.
- The source form ignores a field list that arrives after the model was
  changed again, and empties the dropdowns when the list cannot be loaded
  instead of keeping the previous model's fields.

### Changed

- The log's Source and Corporation filter runs on the server, across every
  page of 100 entries, and the page links keep it; the choices list every
  source and Corporation of the whole log. The browser-side
  datatables-filterdropdown only ever saw the page it ran on.
- A row whose Reason is hidden for the month still in progress has no copy
  button for its amount any more; the row and its amount still show, and the
  source total keeps its copy button.
- DataTables on every page get Alliance Auth's translation for the viewer's
  language, the way Auth's own pages load it.
- The navigation is written the way Alliance Auth's own apps do it; the
  theme styles the active tab instead of fixed colours of our own. The page
  heading uses Auth's page header, with the version below the title.
- The edit and delete buttons on the sources page are named for screen
  readers.
- Help texts: the Reason example is `{corp_id}/{month}/{year}` - the
  zero-padded month of the old example is exactly what eos-tax does not
  match. The Date field's help and the README no longer claim it decides the
  displayed order. The permission names say what they allow, including
  marking, the log and undo; migration 0007 renames them on installed sites,
  which Django would not do by itself.
- The message for skipped rows also names sources that cannot be read or
  marked.
- Russian: "Pay to" reads "Получатель", an open payment "Не оплачено".
  German: the paid field is "Feld Bezahlt" in every message.
- `tools/translate.py` ran for this release: "Outstanding only", "Including
  paid" and "Nothing outstanding." now carry the `eos-invoices` context -
  Alliance Auth's own catalogue translated them differently and won the
  clash before. All three catalogues (`de`, `ru`, `zh_Hans`) are complete,
  `msgfmt --check` clean, `.mo` newer than `.po`, and the catalogue tests
  pass.
- `tools/translate.py` checks the glossary's shape first (one translation per
  language, the right number of plural forms, the same placeholders), leaves
  `tests/` out of makemessages, and names the failing test rather than always
  blaming a context clash. The normal test suite runs the same glossary
  check.
- `runtests.py` and tox run the suite standalone on testauth, which has its
  own sqlite database now instead of naming the dev instance's `aa_dev`;
  `.coveragerc` added. `pyproject.toml`: `django-solo` declared (imported
  directly), a `dev` extra with polib, coverage and tox.
- Tests: one access test per permission over every page, admin overview
  tests next to the overview's, UI tests in `test_views.py`, a shared
  `configure_alliance`; a vacuous assertion in the undo tests and a
  language-independent "every language" test replaced by real checks.

## [0.0.12] - 2026-09-24

### Changed

- The dashboard widget's total now leaves out rows for the current month
  (the ones whose Reason is hidden as still in progress): the amount owed for
  them can still change, so the compact widget only sums what is actually
  settled. The full overview still shows those rows, and their amount still
  counts toward its own total - only the dashboard widget's number changes.
- The log now defaults to chronological order (newest first), not the
  Corporation/Description convention the other tables use - a log reads as a
  log. A header click still re-sorts the current page by anything else.

## [0.0.11] - 2026-09-24

### Changed

- "All Corporations" groups by source instead of by Corporation: one table
  per source, with every Corporation's open rows in it and a Corporation
  column, rather than one card per Corporation with a table per source inside
  it. An admin working one app's payments now sees them together, across
  every Corporation, instead of split into as many tables as there are
  Corporations that owe it something. "Select all" is scoped to a source's
  table now, spanning every Corporation in it, rather than to one
  Corporation's table within a source.
- Every table with a Description column now sorts by Corporation first, then
  Description, on load - on a table that spans several Corporations
  ("All Corporations", the log); the overview has no Corporation column, so
  Description alone. A header click still re-sorts by anything else, and the
  log keeps its filterDropDown besides.
- README: replaced the stale mention of a standalone "Mark all as paid"
  button (removed when ticking rows and "Select all" took its place) with the
  current wording, and documented the "All Corporations" grouping.

### Added

- Payment sources may name a *Month field* and a *Year field* (both optional
  integer fields; migrations 0005-0006). While a row's values in both equal
  today's month and year, its Reason is hidden on the overview and "All
  Corporations" - the amount owed for a month still in progress can still
  change, so the payment code is withheld until it is settled. The row
  itself, its amount and its Description still show; only the Reason is
  replaced by a note. The real Reason is kept internally and still reaches
  the log if the row is marked paid regardless - only the two live overviews
  hide it, and only while the condition holds. Both fields are required
  together: a month number alone cannot tell this year's row from the same
  month a year ago, so setting only one of the two never hides anything.

## [0.0.10] - 2026-09-24

### Changed

- Rows worth exactly 0 ISK are dropped from every listing and total,
  whether paid or not - a corp exempted that month says nothing either
  way, and only added a row to skip past.

## [0.0.9] - 2026-09-24

### Added

- Filter dropdowns on the log, over Source and Corporation - Alliance Auth's
  own `datatables-filterdropdown` (`bundles/filterdropdown-js.html`), the
  same plugin groupmanagement uses. The other tables stay sort-only: they
  either group by Corporation already (a card, not a column) or list too few
  sources for a filter to earn its place.
- A widget on Alliance Auth's own dashboard: the CEO's overview, compact,
  with the open total per source and a link to the full page. Registered
  through `dashboard_hook`, the same mechanism as Auth's own widgets. Hidden
  without the `basic_access` permission, with nothing outstanding, or
  whenever the full overview itself would only show an explanation (no main
  character, no Alliance configured, Corporation outside it) - the full page
  explains those, a dashboard widget only would not.
- `docs/HANDOVER.md`: where the work stands, the decisions the user made and
  what is open, for the next session to start from.
- `tools/translate.py` lists glossary entries the code no longer uses; two
  such leftovers were removed.

## [0.0.8] - 2026-09-24

### Added

- A line at the foot of every page of the app, in every language, says its
  texts are machine-generated and may be inaccurate.

## [0.0.7] - 2026-09-24

### Added

- Undo in the log, for the misclick: puts back the exact value the paid
  field held before, through the owning model's `save()`. The log now stores
  the paid field with its value before and after (migration 0004). Undo is
  refused when the field no longer holds what was written - the owning app or
  somebody else changed it since, and putting the old value back would
  overwrite an automatic payment check, for instance. The entry stays in the
  log, marked with who undid it and when; each entry can be undone once, and
  the row is locked while it is, so two admins cannot both write. Entries
  made before this version hold no previous value and offer no undo.
- The values are stored as plain JSON through our own conversion rather
  than `DjangoJSONEncoder`, which cuts datetimes to milliseconds while the
  database keeps microseconds: the stored stamp would never have matched the
  field again, and undoing a date would always have been refused.
- The model dropdown on the source form filters while typing, like the
  Alliance and "Pay to" dropdowns; the field dropdowns still refill when the
  model changes.
- A test that asks Django, for every entry of our catalogues, what it
  actually shows in each language, and fails when that is not our
  translation. Like the other catalogue tests it is skipped in the normal
  suite - between releases the catalogues describe the last release, not the
  code - and runs at the end of `tools/translate.py` instead.

### Fixed

- Fourteen translations never showed, because Alliance Auth translates the
  same short words itself and an app earlier in `INSTALLED_APPS` wins a msgid
  clash: German showed "Öffnen" for an open payment and "Menge" for an
  amount, Chinese "公开" (public) for open and "角色名" (character name) for
  the source name, Russian "Открыть" (to open). Amount, Display, Enabled,
  Model, Open, Save, Disabled and Name now carry the message context
  `eos-invoices`, which no other catalogue has. The new test found them and
  keeps new ones from slipping in.

### Changed

- The "All Corporations" tab has a box per row, one per source table and
  "Select all" at the top, and a single "Mark selected as paid" button that
  marks the ticked rows of every Corporation at once. It replaces the "Mark
  all as paid" button per source, which a table's own box now does. The same
  guards as before: only the ticked rows are marked, each only if it still
  belongs to the Corporation it was listed under, one log entry per row, all
  in one transaction. The per-row button stays.
- Every table - overview, "All Corporations", log, sources - sorts by a click
  on its header (DataTables from Alliance Auth's bundle). No paging, so no
  ticked box drops out of the form; amounts and dates sort by their raw
  value, not by the formatted text. The log sorts within its page of 100.
- README, glossary and every catalogue say that the translations are
  machine-generated and may be inaccurate.

## [0.0.6] - 2026-09-24

### Added

- `tools/translate.py` and `tools/glossary.py`: the translation run of every
  release as one command, with the reviewed translations kept in the repo
  instead of in a session's scratch directory. A message missing from the
  glossary stops the run and stays empty in the catalogue - the earlier ad
  hoc script cleared gettext's fuzzy flag before it knew whether it had a
  translation of its own, which would have shipped gettext's guess as
  reviewed. After filling, every entry is checked against the glossary and
  each `.mo` against its `.po`. Not part of the installed package.

## [0.0.5] - 2026-09-24

### Added

- "Mark all as paid" per source within a Corporation on the "All
  Corporations" tab, shown when there is more than one open row. It marks
  exactly the rows the page listed, not whatever is open at the moment of the
  click, so a payment that arrived after the page was loaded stays open. Each
  row gets its own log entry. Rows that are already paid, gone or of another
  Corporation are skipped and counted in the message; the batch runs in one
  transaction, so a database failure half way leaves nothing marked and
  nothing logged.

### Changed

- ISK amounts are shown in whole ISK with dots between thousands
  (1.500.000 ISK), the same for every language. The separator used to follow
  the viewer's language, so one CEO read 1,500,000.00 and the next
  1.500.000,00 for the same sum. Copy buttons are unchanged and still copy the
  exact amount as plain digits.

## [0.0.4] - 2026-09-23

### Added

- "All Corporations" tab for admins: the open payments of every Corporation
  in the configured Alliance on one page, grouped by Corporation and source,
  with the total per Corporation and overall. Corporations with nothing open
  are only counted. Each source is read once for all Corporations together, so
  the page costs the same number of queries for 3 Corporations as for 30. A
  source with more than 2000 open rows says it was cut short instead of
  showing a short list as if it were complete.
- "Log" tab: every payment marked as paid, with who, when, source,
  Corporation, amount, reason and the row's key in the owning app. Names are
  stored as text beside the keys, so an entry stays readable after the source
  or the user is gone. The entries are read only in the Django admin as well -
  a log that can be edited proves nothing.

### Changed

- Payments are marked as paid on the "All Corporations" tab only. The normal
  overview is read only again, for admins too, and needs the CEO permission
  again; an admin who is no CEO is taken to "All Corporations" by the menu.
- Marking a row that is already paid is refused, so the log never records a
  change that did not happen.

## [0.0.3] - 2026-09-23

### Added

- Admins (`manage_sources`) can mark an open payment of their own
  Corporation as paid from the overview. The row is written through the owning model's own `save()`, not a
  queryset update, so that app's save logic and signals still run. What gets
  written follows the source: `True` for "Field is true", the configured value
  for "Field equals value", the current date or time for a date field under
  "Field is not empty". Text fields under "Field is not empty" and paid fields
  behind a relation get no button: there is no obvious value for the first,
  and the second would change a row other payments may share. Who marked
  which row is logged, because the owning app keeps no such record.
- The Alliance and "Pay to" dropdowns filter while typing (Tom Select 2.6.2,
  loaded from cdnjs with SRI like Alliance Auth's own bundles). Its Bootstrap 5
  theme paints field and dropdown with the page background and hard-coded dark
  text, which only fits themes whose inputs share the page colour - under
  Darkly, whose inputs are white on a dark page, it showed a dark list under a
  white field. The widget now takes background and text colour from the
  theme's own `form-select` when the page loads, so it looks like the theme's
  other fields; the highlighted option uses the primary colour like a Bootstrap
  dropdown item. Checked against Darkly, Flatly and Bootstrap light and dark.

### Changed

- The overview opens with either permission, and the menu entry always leads
  there; admins without the CEO permission were sent to the sources page
  before.

## [0.0.2] - 2026-09-23

### Added

- The source form offers the fields of the chosen model as dropdowns,
  one relation deep and filtered by type: integers for the Corporation ID,
  numbers for the amount, booleans for "Field is true", dates for the date.
  They refill when the model or the paid mode changes. Reason and
  description get clickable placeholder chips that insert `{field}` at the
  cursor. A saved path the list does not offer, e.g. two relations deep,
  stays selectable, and the check on save is unchanged - the dropdowns are
  a search aid, `check_source` still decides, and it now shares its type
  rules with the dropdowns so the two cannot drift apart.

- Copy buttons for the "Pay to" Corporation, the amount of each open
  payment and the open total of each source, next to the one the reason
  already had. Amounts are copied as plain digits without grouping or
  "ISK", and whole amounts without ".00", so they paste straight into the
  in-game transfer field.

### Changed

- "Pay to" is a dropdown of the Corporations in the configured Alliance
  instead of free text, so the overview names the recipient exactly as the
  game does, with its ticker. A Corporation saved earlier stays selectable
  after it left the Alliance - otherwise saving any other field of the
  source would silently clear it. Existing free text values are dropped by
  migration 0002; set the Corporation again on each source.

### Fixed

- Required Alliance Auth version raised from 5.0 to 5.1.4. The migrations
  depend on `eveonline` migration 0025, which first shipped with 5.1.4, so
  an older install would have failed at `migrate` rather than at `pip`.

## [0.0.1] - 2026-09-23

First prototype.

### Added

- Overview of the payments the Corporation of the viewer's main character still
  owes, across every configured source, with totals per source and overall.
- Payment sources: any installed model with one row per payment, described by
  the fields for Corporation ID, amount and paid state. Paths may follow
  forward relations (`corporation__corporation_id`); reverse and many-to-many
  relations are refused because they would repeat a payment per related row.
- Three ways to recognise a paid row: a true boolean, a filled field (an empty
  string counts as unpaid), or a given value.
- Reason and description templates with field placeholders and format specs,
  e.g. `{corp_id}/{month:02d}/{year}`. Placeholders are limited to field
  names, so a template cannot reach into attributes or items of a value.
- Reason copy button on the overview.
- Sources page that checks every source on load and shows its row count or
  what is wrong with it; the source form rejects unknown models, unknown
  fields and unsuitable field types, and lists the fields the model has.
- Alliance tab: only Corporations in the chosen Alliance see their payments.
- Permissions `basic_access` (CEO overview) and `manage_sources`
  (maintenance).
- Translations: German, Russian, Simplified Chinese. The EVE terms Alliance
  and Reason carry the message context `EVE jargon`: Alliance Auth's own
  catalogues translate the plain words (Allianz, Grund), and an app listed
  earlier in `INSTALLED_APPS` wins such a clash, so without a context they
  would never have stayed English.
