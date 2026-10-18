"""Tenshi 2.8.0: read-only, conservative checks for NTFS deleted-cluster conflicts."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

from recoverydesk.ntfs import DataRun
from recoverydesk.ntfs_browser import FileEntry, scan_ntfs_tree
from recoverydesk.recovery_evidence import (build_live_cluster_evidence,
    deleted_stream_claim_issue, self_overlap_issue, LiveClusterEvidence)
from recoverydesk.recovery_preflight import inspect_metadata, inspect_selection
from recoverydesk.batch_export import export_batch
from test_browser import image_with_folders


class DeletedClusterEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.image = Path(self.tmp.name) / 'disk.raw'
        self.image.write_bytes(image_with_folders())
        self.index = scan_ntfs_tree(str(self.image))
        self.deleted = next(e for e in self.index.entries if e.name == 'fragmentiert.bin')
        self.original = self.image.read_bytes()

    def live(self, runs, *, key=870, reason=''):
        entry = FileEntry(key, 1, f'live{key}.bin', 5, 1, False, False,
            size=512, initialized_size=512, data_kind='nonresident',
            data_runs=runs, unsupported_reason=reason)
        self.index.entries.append(entry)
        return entry

    def test_positive_overlap_blocks_deleted_candidate(self):
        self.live([DataRun(40, 1)])
        row = inspect_metadata(self.index, self.deleted.name, self.deleted)
        self.assertEqual(row.state, 'Gesperrt')
        self.assertIn('bereits von einer vorhandenen Datei', ' '.join(row.details))
        self.assertEqual(self.image.read_bytes(), self.original)

    def test_unrelated_live_run_keeps_uncertain_deleted_warning(self):
        self.live([DataRun(100, 5)])
        report = inspect_selection(self.index, [self.deleted], filesystem='NTFS')
        self.assertEqual(report.warnings, 1)
        self.assertEqual(report.blocked, 0)
        self.assertIn('Gelöscht', ' '.join(report.items[0].details))
        self.assertNotIn('unversehrt sind', report.items[0].details)
        self.assertIn('NICHT', report.as_text())

    def test_adjacent_intervals_are_not_overlap(self):
        self.live([DataRun(39, 1), DataRun(41, 1)])
        evidence = build_live_cluster_evidence(self.index)
        self.assertFalse(evidence.overlaps(40, 41))
        self.assertTrue(evidence.overlaps(39, 40))
        self.assertTrue(evidence.overlaps(41, 42))

    def test_fragmented_deleted_second_extent_conflicts(self):
        self.live([DataRun(60, 2)])
        self.assertEqual(inspect_metadata(self.index, 'x', self.deleted).state, 'Gesperrt')

    def test_sparse_runs_are_not_claimed_as_live_disk_space(self):
        self.live([DataRun(None, 80), DataRun(100, 1)])
        self.assertEqual(inspect_metadata(self.index, 'x', self.deleted).state, 'Warnung')

    def test_unsupported_live_entry_does_not_claim_reliable_ownership(self):
        self.live([DataRun(40, 1)], reason='Verschlüsselter Datenstrom')
        self.assertEqual(inspect_metadata(self.index, 'x', self.deleted).state, 'Warnung')

    def test_duplicate_live_hardlinks_merge_correctly(self):
        self.live([DataRun(40, 1)])
        self.live([DataRun(40, 1)], key=871)
        self.live([DataRun(41, 1)], key=872)
        evidence = build_live_cluster_evidence(self.index)
        self.assertIn((40, 42), evidence.spans)
        self.assertEqual(len(evidence.spans), len(set(evidence.spans)))

    def test_bad_self_overlap_blocks_even_current_file(self):
        entry = self.live([DataRun(50, 2), DataRun(51, 1)])
        entry.size = entry.initialized_size = 1536
        self.assertIsNotNone(self_overlap_issue(entry))
        row = inspect_metadata(self.index, entry.name, entry)
        self.assertEqual(row.state, 'Gesperrt')
        self.assertIn('überlappende', ' '.join(row.details))

    def test_different_non_overlapping_runs_are_accepted(self):
        entry = self.live([DataRun(70, 1), DataRun(90, 1)])
        entry.size = entry.initialized_size = 1024
        self.assertIsNone(self_overlap_issue(entry))
        self.assertEqual(inspect_metadata(self.index, entry.name, entry).state, 'Bereit')

    def test_export_does_not_create_output_for_known_conflict(self):
        self.live([DataRun(60, 1)])
        target = Path(self.tmp.name) / 'target'
        target.mkdir()
        result = export_batch(str(self.image), self.index, [self.deleted], str(target))
        self.assertEqual(result.exported, 0)
        self.assertEqual(result.skipped, 1)
        self.assertIn('NTFS-Cluster', result.errors[0])
        self.assertFalse(list(target.rglob('fragmentiert.bin')))
        self.assertEqual(self.image.read_bytes(), self.original)

    def test_unselected_live_file_still_blocks_conflict(self):
        self.live([DataRun(40, 1)])
        report = inspect_selection(self.index, [self.deleted], filesystem='NTFS')
        self.assertEqual(report.files, 1)
        self.assertEqual(report.blocked, 1)
        self.assertEqual(report.expected_bytes, 0)

    def test_regular_non_deleted_file_not_mislabelled(self):
        self.live([DataRun(40, 1)])
        existing = next(e for e in self.index.entries if e.name == 'bericht.txt')
        self.assertEqual(inspect_metadata(self.index, existing.name, existing).state, 'Bereit')

    def test_empty_claims_do_not_imply_safe_recovery(self):
        evidence = build_live_cluster_evidence(self.index)
        self.assertFalse(evidence.overlaps(40, 41))
        row = inspect_metadata(self.index, self.deleted.name, self.deleted,
                               allocation_evidence=evidence)
        self.assertEqual(row.state, 'Warnung')
        self.assertTrue(any('überschrieben' in note for note in row.details))

    def test_large_union_merges_ranges_and_binary_queries(self):
        # 1000 input extents, 1 merged span; no quadratic per-file scan.
        for x in range(1000):
            self.live([DataRun(100 + x, 1)], key=1000 + x)
        evidence = build_live_cluster_evidence(self.index)
        self.assertEqual(evidence.spans, ((100, 1100),))
        self.assertTrue(evidence.overlaps(1099, 1100))
        self.assertFalse(evidence.overlaps(1100, 1101))
        self.assertFalse(evidence.overlaps(99, 100))

    def test_new_recovery_messages_translated_into_six_languages(self):
        from recoverydesk.i18n import LANGUAGES, translate
        messages = (
            'NTFS-Datenstrom enthält überlappende physische Clusterbereiche.',
            'NTFS-Cluster der gelöschten Datei werden laut aktuellen MFT-Metadaten bereits von einer vorhandenen Datei genutzt. Der ursprüngliche Dateiinhalt ist an diesen Stellen nicht zuverlässig zuordenbar.',
            'Gesperrt', 'Warnung', 'Bereit', 'Ordner',
        )
        for phrase in messages:
            for language in LANGUAGES:
                result = translate(phrase, language)
                self.assertTrue(result)
                if language != 'de':
                    self.assertNotEqual(result, phrase)

    def test_report_does_not_overpromise_content_integrity(self):
        self.live([DataRun(40, 1)])
        report = inspect_selection(self.index, [self.deleted])
        self.assertIn('Dateiinhalte wurden nicht gelesen', report.as_text())
        self.assertNotIn('Erfolgreich wiederhergestellt', report.as_text())


if __name__ == '__main__':
    unittest.main()
