# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
