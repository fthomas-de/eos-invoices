# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
