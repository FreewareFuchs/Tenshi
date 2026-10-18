"""Deterministic tests for conservative, read-only partition reconstruction."""
from __future__ import annotations
import os
import struct
import tempfile
import unittest
from pathlib import Path
from recoverydesk.partition_scan import analyze_image


def ntfs_boot(sectors: int, mft_lcn: int = 4):
    boot = bytearray(512)
    boot[0:3] = b'\xeb\x52\x90'
    boot[3:11] = b'NTFS    '
    struct.pack_into('<H', boot, 11, 512)
    boot[13] = 8
    struct.pack_into('<Q', boot, 40, sectors)
    struct.pack_into('<Q', boot, 48, mft_lcn)
    boot[64] = 0xf6
    boot[510:512] = b'\x55\xaa'
    return boot


class PartitionRecoveryTests(unittest.TestCase):
    def _scan(self, image, deep=False):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'disk.raw'
            file.write_bytes(image)
            original = file.read_bytes()
            report = analyze_image(str(file), deep_scan=deep, max_scan_mb=0)
            self.assertEqual(original, file.read_bytes(), 'disk source must remain unchanged')
            return report

    def test_ntfs_backup_vbr_recovers_offset_when_mft_matches(self):
        image = bytearray(4*1024*1024)
        start = 1024*512
        nsec = 2048
        image[start+4*4096:start+4*4096+4] = b'FILE'
        backup = start+(nsec-1)*512
        image[backup:backup+512] = ntfs_boot(nsec)
        report = self._scan(image, deep=True)
        self.assertEqual(len(report.partitions), 1)
        p = report.partitions[0]
        self.assertEqual(p.offset_bytes, start)
        self.assertEqual(p.scheme, 'Fund (NTFS-Kopie)')
        self.assertEqual(p.confidence, 'Niedrig')
        self.assertIn('Primärer NTFS-Bootsektor fehlt', p.warning)
        self.assertTrue(any('$MFT' in x for x in p.evidence))

    def test_fake_backup_without_mft_cannot_be_inferred(self):
        image = bytearray(4*1024*1024)
        start = 1024*512
        nsec = 2048
        backup = start+(nsec-1)*512
        image[backup:backup+512] = ntfs_boot(nsec)
        report = self._scan(image, deep=True)
        self.assertFalse(any(p.scheme == 'Fund (NTFS-Kopie)' for p in report.partitions))

    def test_primary_vbr_and_backup_are_not_double_counted(self):
        image = bytearray(4*1024*1024)
        start = 1024*512
        nsec = 2048
        image[start:start+512] = ntfs_boot(nsec)
        image[start+(nsec-1)*512:start+nsec*512] = ntfs_boot(nsec)
        image[start+4*4096:start+4*4096+4] = b'FILE'
        report = self._scan(image, deep=True)
        self.assertEqual(len(report.partitions), 1)
        self.assertEqual(report.partitions[0].scheme, 'Fund (VBR)')
        self.assertEqual(report.partitions[0].confidence, 'Mittel')

    def test_overlapping_mbr_partitions_warn_and_reduce_confidence(self):
        image = bytearray(4*1024*1024)
        image[510:512] = b'\x55\xaa'
        for i, (start, count) in enumerate(((1024,2048),(2048,2048))):
            image[446+i*16+4] = 7
            struct.pack_into('<II', image, 446+i*16+8, start, count)
            image[start*512:start*512+512] = ntfs_boot(count)
        report = self._scan(image)
        self.assertEqual(len(report.partitions), 2)
        self.assertTrue(all('Überlappende' in p.warning for p in report.partitions))
        self.assertTrue(all(p.confidence == 'Niedrig' for p in report.partitions))
        self.assertTrue(any('Überlappung' in w for w in report.warnings))

    def test_mbr_and_filesystem_size_conflict_warn(self):
        image = bytearray(4*1024*1024)
        image[510:512] = b'\x55\xaa'
        image[446+4] = 7
        struct.pack_into('<II', image, 446+8, 2048, 600)
        image[2048*512:2049*512] = ntfs_boot(2500)
        report = self._scan(image)
        self.assertEqual(len(report.partitions), 1)
        p = report.partitions[0]
        self.assertIn('Dateisystem meldet mehr Sektoren', p.warning)
        self.assertEqual(p.confidence, 'Niedrig')

    def test_recovered_copy_matches_known_partition_from_table(self):
        image = bytearray(4*1024*1024)
        start_lba, sectors = 1024, 2048
        image[510:512] = b'\x55\xaa'
        image[446+4] = 7
        struct.pack_into('<II', image, 446+8, start_lba, sectors)
        start = start_lba*512
        image[start+4*4096:start+4*4096+4] = b'FILE'
        at = start+(sectors-1)*512
        image[at:at+512] = ntfs_boot(sectors)
        report = self._scan(image, deep=True)
        self.assertEqual(len(report.partitions), 1)
        self.assertEqual(report.partitions[0].filesystem, 'NTFS')
        self.assertIn('Primärer NTFS-Bootsektor fehlt', report.partitions[0].warning)
        self.assertEqual(report.partitions[0].confidence, 'Niedrig')

if __name__ == '__main__':
    unittest.main()

class ReportsAndGuiTests(unittest.TestCase):
    def test_report_contains_evidence_and_is_deterministic(self):
        from recoverydesk.partition_scan import format_partition_findings
        report = PartitionRecoveryTests()._scan(bytearray(512))
        text = format_partition_findings('sample.raw', report)
        self.assertIn('Plausibilität beschreibt Metadaten', text)
        self.assertIn('sample.raw', text)
        self.assertEqual(text, format_partition_findings('sample.raw', report))

    def test_gui_confidence_column_and_source_reset(self):
        from recoverydesk.gui import RecoveryDeskApp
        from recoverydesk.partition_scan import AnalysisReport, Partition
        app = RecoveryDeskApp()
        try:
            self.assertIn('confidence', app.part_tree['columns'])
            report = AnalysisReport(4096, partitions=[Partition(1,'Fund (VBR)',0,8,'NTFS',
                                           filesystem='NTFS', confidence='Mittel', evidence=['Plausibler Bootsektor'])])
            app._show_partitions(report)
            self.assertEqual(app.part_tree.set('0','confidence'),'Mittel')
            app._reset_analysis_for_source()
            self.assertIsNone(app.last_partition_report)
            # A late scan belonging to an old source cannot repopulate the table.
            app._show_partitions(report, app._source_generation - 1, 'other.raw')
            self.assertEqual(len(app.part_tree.get_children()),0)
        finally:
            app.destroy()

class GPTConfidenceTests(unittest.TestCase):
    def test_verified_backup_gpt_graded_high_with_fs(self):
        # Reuse synthetic 512-byte-sector GPT fixture from existing suite.
        from test_partitions import write_gpt
        disk = bytearray(4 * 1024 * 1024)
        write_gpt(disk, bad_primary=True)
        report = PartitionRecoveryTests()._scan(disk)
        self.assertEqual(report.table_type, 'GPT')
        self.assertEqual(report.partitions[0].scheme, 'GPT Backup')
        self.assertEqual(report.partitions[0].confidence, 'Hoch')
        self.assertTrue(any('Prüfsummen bestätigt' in text for text in report.partitions[0].evidence))
