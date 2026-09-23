# Working on eos-invoices

Alliance Auth app that lists the payments a Corporation still owes, read
generically out of other apps' models (`PaymentSource`). `README.md` says what
it does; this file says how to work on it.

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

Alliance Auth translates many plain words itself and wins a msgid clash.
EVE jargon that has to stay English therefore gets the context
`EVE jargon` (`pgettext_lazy`, `{% translate ... context %}`);
`tests/test_translations.py` checks it.

English only between releases. On the user's release call: raise the version
in `eos_invoices/__init__.py`, translate into `de`, `ru`, `zh_Hans` (EVE jargon
stays English), split `[Unreleased]` in `CHANGELOG.md`, then commit and push -
asking before the commit.
