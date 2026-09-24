import gettext
import os
from pathlib import Path
from unittest import skipUnless

from django.utils import translation

import eos_invoices

from .base import EosInvoicesTestCase

LOCALE = Path(eos_invoices.__file__).parent / "locale"
LANGUAGES = {"de": "de", "ru": "ru", "zh_Hans": "zh-hans"}

# set by tools/translate.py
RELEASE_CHECK = "EOS_INVOICES_CHECK_TRANSLATIONS"


# The catalogues are only brought up to date at a release, so between releases
# these checks describe the last release, not the code - red for a known
# reason, which only teaches everybody to ignore a red suite. tools/translate.py
# runs them after it has filled and compiled the catalogues.
@skipUnless(os.environ.get(RELEASE_CHECK) == "1", "catalogue check, run by tools/translate.py")
class TestTranslations(EosInvoicesTestCase):
    def test_should_load_every_compiled_catalogue(self):
        # a catalogue that was not compiled falls back to English silently
        expected = {"de": "Übersicht", "ru": "Обзор", "zh-hans": "概览"}

        for language, text in expected.items():
            with self.subTest(language), translation.override(language):
                self.assertEqual(translation.gettext("Overview"), text)

    def test_should_keep_eve_jargon_english(self):
        for language in ("de", "ru", "zh-hans"):
            with self.subTest(language), translation.override(language):
                self.assertEqual(translation.pgettext("EVE jargon", "Alliance"), "Alliance")
                self.assertEqual(translation.pgettext("EVE jargon", "Reason"), "Reason")

    def test_should_show_our_translation_for_every_message(self):
        """Nothing another app translates differently may hide ours.

        Django merges every installed app's catalogue, and for the same msgid
        an app earlier in INSTALLED_APPS wins. Alliance Auth translates many
        short words itself - "Open" as the verb, "Amount" as a quantity - and
        without a context of our own the page silently shows its version.
        This asks Django what it actually shows for each of our entries.
        """
        for folder, language in LANGUAGES.items():
            with open(LOCALE / folder / "LC_MESSAGES" / "django.mo", "rb") as mo:
                catalogue = gettext.GNUTranslations(mo)._catalog

            with translation.override(language):
                for key, ours in catalogue.items():
                    if key == "":
                        continue
                    if isinstance(key, tuple):
                        msgid, form = key
                        if form != 0:
                            continue
                        context, _sep, msgid = msgid.rpartition("\x04")
                        shown = (
                            translation.npgettext(context, msgid, msgid, 1)
                            if context
                            else translation.ngettext(msgid, msgid, 1)
                        )
                    else:
                        context, _sep, msgid = key.rpartition("\x04")
                        shown = (
                            translation.pgettext(context, msgid)
                            if context
                            else translation.gettext(msgid)
                        )
                    with self.subTest(language=folder, msgid=msgid):
                        self.assertEqual(shown, ours)

