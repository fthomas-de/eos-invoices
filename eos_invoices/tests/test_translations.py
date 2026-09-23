from django.utils import translation

from .base import EosInvoicesTestCase


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
