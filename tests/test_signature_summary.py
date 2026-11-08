"""Run outcomes are snapshots, never guesses from a filtered list."""
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
import unittest

from recoverydesk.signature_summary import SignatureSummary,summary_text
from recoverydesk.i18n import LANGUAGES


class SignatureSummaryTests(unittest.TestCase):
    def test_snapshot_keeps_original_settings_and_has_distinct_outcomes_in_six_languages(self):
        index=SimpleNamespace(signature_search_area='exfat-free',signature_partition_offset=4096,
            signature_categories=['images','archives'],signature_file_limit=64*1024**2,
            signature_complete=True,entries=[])
        run=SignatureSummary.from_index('/images/source.img',index)
        index.signature_categories.append('video');index.signature_partition_offset=8192
        self.assertEqual(run.categories,('images','archives'))
        self.assertEqual(run.offset,4096)
        with self.assertRaises(FrozenInstanceError):run.offset=0
        for language in LANGUAGES:
            outcomes=[summary_text(run.outcome(state),language) for state in
                      ('finished','limited','failed','cancelled','running')]
            self.assertEqual(len(set(outcomes)),5,language)
            for text in outcomes:
                self.assertIn('source.img',text)
                self.assertIn('exFAT',text)
                self.assertIn('4096',text)
                self.assertIn('64 MiB',text)
                self.assertEqual(len(text.splitlines()),3)
        self.assertIn('Keine passenden Signaturen innerhalb der Prüfgrenzen',summary_text(run,'de'))
        self.assertIn('unvollständig',summary_text(run.outcome('limited'),'de'))

    def test_source_name_is_bounded_without_control_lines(self):
        run=SignatureSummary('/images/'+'x'*200+'\nsource.img','all',0,('images',),32*1024**2)
        text=summary_text(run,'de')
        self.assertEqual(len(text.splitlines()),3)
        self.assertIn('…',text)
        self.assertTrue(text.splitlines()[0].endswith('source.img'))
