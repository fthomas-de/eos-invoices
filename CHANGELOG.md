# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
