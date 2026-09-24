# Working on eos-invoices

Alliance Auth app that lists the payments a Corporation still owes, read
generically out of other apps' models (`PaymentSource`). `README.md` says what
it does; this file says how to work on it; `docs/HANDOVER.md` says where the
work currently stands, which decisions the user made and what is open.
Read both before changing anything.

## Where things are

| | |
|---|---|
| This app | `~/aa-dev/working/eos-invoices/eos_invoices` |
| Alliance Auth instance | `~/aa-dev/working/myauth` (has `manage.py`) |
| Virtualenv | `~/aa-dev/venv` |
| Sister project with the long form of these rules | `~/aa-dev/working/eos-tax/CLAUDE.md` |

## Commands

Run from `~/aa-dev/working/myauth`:

```bash
eos-test eos_invoices --parallel 2
```

The catalogue tests (`tests/test_translations.py`) are skipped in this run;
`tools/translate.py` runs them at a release, on fresh catalogues. A failing
subtest hangs `--parallel` - the runner cannot pickle it - so drop the flag
to see which one.

```bash
~/aa-dev/venv/bin/python manage.py makemigrations eos_invoices
```

```bash
~/aa-dev/venv/bin/python manage.py collectstatic --noinput
```

## Rules

- The `aa_dev` database holds corptools data that cannot be fetched again.
  Read foreign models, never change their rows or schema.
- Everything goes through the ORM. No SQL is built from what an admin typed
  on the sources page; field paths are validated by `sources.check_source`.
- Comments say why, not what. English everywhere in the code.
- AA standard templates and bundles, JavaScript only in
  `static/eos_invoices/js/`, loaded with `sri_static`.
- Tests use the `Due` stand-in model from `tests/base.py`. Its table is
  created outside the class transaction because MySQL commits DDL implicitly.
- Every new test gets checked against the broken code.

## Translations and releases

Alliance Auth translates many plain words itself and wins a msgid clash -
"Open" becomes the verb, "Amount" a quantity. Two contexts keep ours:
`EVE jargon` for terms that must stay English, `eos-invoices` for ordinary
words AA translates differently (`pgettext_lazy`, `{% translate ... context %}`).
`test_should_show_our_translation_for_every_message` asks Django what it shows
for each entry and names every clash; give a clashing word the `eos-invoices`
context. It runs only inside `tools/translate.py`, like the other catalogue
tests: between releases the catalogues describe the last release, not the code.

English only between releases. On the user's release call:

1. Raise the version in `eos_invoices/__init__.py`.
2. Add every new message to `tools/glossary.py` (de, ru, zh_Hans; EVE jargon
   stays English), then run from the repo root:

   ```bash
   ~/aa-dev/venv/bin/python tools/translate.py
   ```

   It runs makemessages, fills the catalogues from the glossary, drops
   obsolete entries, checks every entry against the glossary, runs
   `msgfmt --check` and compilemessages, confirms each `.mo` is newer than
   its `.po`, and finally runs the catalogue tests. It also lists glossary
   entries the code no longer uses - remove them. A message missing from the glossary stops it with a list; that
   entry is left empty, never with gettext's fuzzy guess.
3. Split `[Unreleased]` in `CHANGELOG.md` into the new version.
4. Commit and push - asking before the commit.

The glossary is the source of truth: never edit a `.po` file by hand, the next
run overwrites it. The tool needs `polib` in the venv (`pip install polib`).
