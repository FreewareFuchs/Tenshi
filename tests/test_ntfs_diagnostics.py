"""Bounded reason collection distinguishes parse failures and scan limits."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk import ntfs_browser as browser
from recoverydesk.ntfs import NTFSError
from recoverydesk.scan_report import format_scan_report
from recoverydesk.session_store import _encode_index, _decode_index, SessionError
from recoverydesk.i18n import translate
from test_ntfs import make_image, file_record, filename_attr, nonresident_attr
from test_explorer import e


class NtfsDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'test.raw'
        self.source.write_bytes(make_image())

    def synthetic_scan(self, count, reader):
        with patch.object(browser, '_mft_stream', return_value=([], count * 1024)), \
             patch.object(browser, '_read_mft_piece', side_effect=lambda f, info, runs, start, n: (b'FILE' + bytes(1020)) * n), \
             patch.object(browser, '_read_entry_records', side_effect=reader):
            return browser.scan_ntfs_tree(str(self.source))

    def test_reasons_and_samples_are_bounded_and_count_every_failure(self):
        def fail(raw, number, info):
            raise NTFSError(f'failure-{number}')
        index = self.synthetic_scan(40, fail)
        self.assertEqual(index.damaged_records, 40)
        self.assertEqual(index.unreadable_records, 0)
        self.assertEqual(sum(index.record_error_reasons.values()), 40)
        self.assertEqual(len(index.record_error_reasons), 21)
        self.assertEqual(len(index.record_error_samples), 20)
        self.assertEqual(index.record_error_samples[0]['record'], 0)
        text = format_scan_report(str(self.source), index)
        self.assertIn('NTFSError: failure-0', text)
        self.assertIn('Nicht auswertbare MFT-Datensätze: 40', text)
        self.assertNotIn('Beschädigte MFT-Datensätze:', text)

    def test_out_of_volume_runs_distinguish_deleted_live_and_untrusted_headers(self):
        attr = nonresident_attr(0x80, b'\x21\x01\x58\x02\x00', 512, 0)
        deleted = file_record([filename_attr('old.bin'), attr], in_use=False)
        live = file_record([filename_attr('live.bin'), attr], in_use=True)
        torn = bytearray(live)
        torn[510:512] = b'XX'
        records = deleted + live + bytes(torn)
        with patch.object(browser, '_mft_stream', return_value=([], len(records))), \
             patch.object(browser, '_read_mft_piece', return_value=records):
            index = browser.scan_ntfs_tree(str(self.source))
        self.assertEqual(index.damaged_records, 3)
        self.assertEqual(index.record_error_states, {'deleted': 1, 'in_use': 1, 'unknown': 1})
        self.assertEqual([x['state'] for x in index.record_error_samples], ['deleted', 'in_use', 'unknown'])
        self.assertFalse(index.entries)
        text = format_scan_report(str(self.source), index)
        self.assertIn('Als belegt markiert: 1', text)
        self.assertIn('Als gelöscht markiert: 1', text)
        self.assertIn('Status nicht sicher auswertbar: 1', text)

    def test_attribute_limit_count_is_separate_and_warning_not_repeated(self):
        def entry(raw, number, info):
            item = e(number + 10, str(number))
            item.unsupported_reason = 'Attributliste nicht unterstützt'
            return [item]
        with patch.object(browser, 'MAX_ATTRIBUTE_BASES', 2), \
             patch.object(browser, 'recover_attribute_stream', side_effect=NTFSError('unresolved')):
            index = self.synthetic_scan(5, entry)
        self.assertEqual(index.damaged_records, 0)
        self.assertEqual(index.attribute_list_limit_skipped, 3)
        self.assertEqual(index.unresolved_attribute_lists, 2)
        self.assertEqual(index.scan_warnings.count('Sicherheitslimit für NTFS-Attributlisten erreicht.'), 1)
        self.assertIn('nicht untersuchte Basisrecords: 3', format_scan_report(str(self.source), index))

    def test_diagnostics_roundtrip_and_older_session_defaults(self):
        def fail(*args):
            raise NTFSError('test reason')
        index = self.synthetic_scan(2, fail)
        raw = _encode_index(index)
        restored = _decode_index(raw, str(self.source))
        self.assertEqual(restored.record_error_reasons, index.record_error_reasons)
        old = copy.deepcopy(raw)
        for key in ('record_error_reasons', 'record_error_states', 'record_error_samples', 'attribute_list_limit_skipped', 'index_parse_failures'):
            old['properties'].pop(key)
        restored = _decode_index(old, str(self.source))
        self.assertEqual(restored.record_error_reasons, {})
        self.assertEqual(restored.damaged_records, 2)
        self.assertEqual(restored.record_error_states, {})
        raw['properties']['record_error_samples'] = [{'record': 'invalid', 'reason': 'test'}]
        with self.assertRaises(SessionError):
            _decode_index(raw, str(self.source))

    def test_new_warning_labels_translated(self):
        for language in ('en', 'es', 'zh', 'ru', 'ja'):
            for text in ('MFT-Auswertungsfehler', 'MFT-Lesefehler',
                         'Attributlisten-Limit: nicht untersuchte Basisrecords',
                         'Verzeichnisindex-Auswertungsmeldungen'):
                self.assertNotEqual(translate(text, language), text)
