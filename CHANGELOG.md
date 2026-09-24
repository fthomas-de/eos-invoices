# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
