"""Safe session persistence regression tests using only synthetic test images."""
import json
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import tkinter as tk

from recoverydesk.filesystems import scan_tree, export_file
from recoverydesk.ntfs_browser import scan_ntfs_tree, export_file as export_ntfs_file
from recoverydesk.partition_scan import analyze_image
from recoverydesk.session_store import (SessionError, save_session, load_session,
                                         fingerprint_image)
from test_filesystems import fat_img, ext4_img, exfat_img
from test_ntfs import make_image


class SessionLogicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'image.raw'
        self.session = self.root / 'scan.tenshi-session'

    def test_fat32_index_and_export_after_restore(self):
        original = fat_img()
        self.source.write_bytes(original)
        report = analyze_image(str(self.source))
        idx = scan_tree(str(self.source))
        save_session(str(self.session), str(self.source), report, idx, 'FAT32')
        restored = load_session(str(self.session))
        self.assertEqual(restored.filesystem, 'FAT32')
        self.assertEqual(len(restored.report.partitions), len(report.partitions))
        self.assertEqual({x.name for x in restored.index.entries}, {x.name for x in idx.entries})
        file = next(e for e in restored.index.entries if e.name == 'README.TXT')
        dst = self.root / 'recovered.txt'
        export_file(str(self.source), restored.index, file, str(dst))
        self.assertEqual(dst.read_bytes(), b'HELLO')
        self.assertEqual(self.source.read_bytes(), original)

    def test_ntfs_resident_metadata_export_after_restore(self):
        original = make_image()
        self.source.write_bytes(original)
        index = scan_ntfs_tree(str(self.source))
        save_session(str(self.session), str(self.source), index=index, filesystem='NTFS')
        restored = load_session(str(self.session))
        self.assertEqual(restored.filesystem, 'NTFS')
        self.assertEqual(len(restored.index.entries), len(index.entries))
        file = next(e for e in restored.index.entries if e.name == 'aktiv.txt')
        dst = self.root / 'active.out'
        export_ntfs_file(str(self.source), restored.index.info, file, str(dst))
        self.assertEqual(dst.read_bytes(), b'ACTIVE')
        self.assertEqual(self.source.read_bytes(), original)

    def test_ext4_hierarchy_restored(self):
        self.source.write_bytes(ext4_img())
        index = scan_tree(str(self.source))
        save_session(str(self.session), str(self.source), index=index, filesystem=index.filesystem)
        restored = load_session(str(self.session))
        self.assertEqual({e.name for e in restored.index.entries}, {e.name for e in index.entries})
        self.assertEqual({p: [e.key for e in rows] for p, rows in restored.index.children.items()},
                         {p: [e.key for e in rows] for p, rows in index.children.items()})

    def test_modified_source_is_rejected_even_if_size_same(self):
        data = fat_img()
        self.source.write_bytes(data)
        save_session(str(self.session), str(self.source), index=scan_tree(str(self.source)))
        with open(self.source, 'r+b') as f:
            f.seek(0)
            f.write(b'CHANGED')
        with self.assertRaises(SessionError):
            load_session(str(self.session))

    def test_changed_timestamp_is_rejected_even_if_samples_match(self):
        self.source.write_bytes(fat_img())
        save_session(str(self.session), str(self.source), index=scan_tree(str(self.source)))
        st = self.source.stat()
        os.utime(self.source, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
        with self.assertRaisesRegex(SessionError, 'geändert'):
            load_session(str(self.session))

    def test_relocated_image_is_verified_and_accepted(self):
        self.source.write_bytes(fat_img())
        save_session(str(self.session), str(self.source), index=scan_tree(str(self.source)))
        moved = self.root / 'moved.raw'
        self.source.rename(moved)
        result = load_session(str(self.session), source_override=str(moved))
        self.assertEqual(result.source, str(moved))
        self.assertTrue(result.index.entries)

    def test_relocated_image_with_different_bytes_is_rejected(self):
        self.source.write_bytes(fat_img())
        save_session(str(self.session), str(self.source), index=scan_tree(str(self.source)))
        other = self.root / 'other.raw'
        other.write_bytes(b'B' * len(fat_img()))
        with self.assertRaises(SessionError):
            load_session(str(self.session), source_override=str(other))

    def test_session_not_overwritten_and_existing_stays_intact(self):
        self.source.write_bytes(fat_img())
        index = scan_tree(str(self.source))
        save_session(str(self.session), str(self.source), index=index)
        previous = self.session.read_bytes()
        with self.assertRaises(FileExistsError):
            save_session(str(self.session), str(self.source), index=index)
        self.assertEqual(self.session.read_bytes(), previous)

    def test_session_fails_closed_for_raw_devices(self):
        self.source.write_bytes(fat_img())
        with self.assertRaises(SessionError):
            save_session(str(self.session), r'\\.\PhysicalDrive0', index=scan_tree(str(self.source)))

    def test_corrupt_archive_rejected_without_filesystem_changes(self):
        self.source.write_bytes(fat_img())
        self.session.write_bytes(b'not a zip')
        with self.assertRaises(SessionError):
            load_session(str(self.session))
        self.assertTrue(self.source.exists())

    def test_manifest_payload_checksum_rejects_changed_rows(self):
        self.source.write_bytes(fat_img())
        save_session(str(self.session), str(self.source), index=scan_tree(str(self.source)))
        with zipfile.ZipFile(self.session) as z:
            manifest = z.read('manifest.json')
            payload = json.loads(z.read('analysis.json'))
        payload['index']['entries'][0]['name'] = 'TAMPERED'
        altered = self.root / 'tampered.tenshi-session'
        with zipfile.ZipFile(altered, 'w') as z:
            z.writestr('manifest.json', manifest)
            z.writestr('analysis.json', json.dumps(payload))
        with self.assertRaisesRegex(SessionError, 'verändert'):
            load_session(str(altered))

    def test_unsupported_format_rejected(self):
        self.source.write_bytes(fat_img())
        save_session(str(self.session), str(self.source), index=scan_tree(str(self.source)))
        with zipfile.ZipFile(self.session) as z:
            manifest = json.loads(z.read('manifest.json'))
            payload = z.read('analysis.json')
        manifest['version'] = 999
        altered = self.root / 'version.tenshi-session'
        with zipfile.ZipFile(altered, 'w') as z:
            z.writestr('manifest.json', json.dumps(manifest))
            z.writestr('analysis.json', payload)
        with self.assertRaisesRegex(SessionError, 'Sitzungsversion'):
            load_session(str(altered))

    def test_zero_analyses_refused(self):
        self.source.write_bytes(fat_img())
        with self.assertRaisesRegex(SessionError, 'analysieren'):
            save_session(str(self.session), str(self.source))

    def test_declared_oversized_payload_rejected_without_decompression(self):
        self.source.write_bytes(fat_img())
        self.session.write_bytes(b'ZIP')
        with patch('recoverydesk.session_store.MAX_ARCHIVE_BYTES', 2):
            with self.assertRaisesRegex(SessionError, 'groß'):
                load_session(str(self.session))

    def test_exfat_index_survives_roundtrip(self):
        self.source.write_bytes(exfat_img())
        index = scan_tree(str(self.source))
        save_session(str(self.session), str(self.source), index=index)
        restored = load_session(str(self.session))
        self.assertEqual(restored.filesystem, 'exFAT')
        self.assertEqual([e.name for e in restored.index.entries], [e.name for e in index.entries])
        self.assertEqual(restored.index.children.keys(), index.children.keys())

    def test_partition_only_session_without_files(self):
        self.source.write_bytes(fat_img())
        report = analyze_image(str(self.source))
        save_session(str(self.session), str(self.source), report=report)
        restored = load_session(str(self.session))
        self.assertIsNone(restored.index)
        self.assertIsNotNone(restored.report)

    def test_source_image_never_overwritten_as_session(self):
        original = fat_img()
        self.source.write_bytes(original)
        with self.assertRaises(SessionError):
            save_session(str(self.source), str(self.source), index=scan_tree(str(self.source)))
        self.assertEqual(self.source.read_bytes(), original)

    def test_fingerprint_from_scan_rejects_image_changed_before_save(self):
        self.source.write_bytes(fat_img())
        indexed = scan_tree(str(self.source))
        captured = fingerprint_image(str(self.source))
        st = self.source.stat()
        os.utime(self.source, ns=(st.st_atime_ns, st.st_mtime_ns+1000000000))
        with self.assertRaises(SessionError):
            save_session(str(self.session), str(self.source), index=indexed,
                         expected_fingerprint=captured)
        self.assertFalse(self.session.exists())

    def test_valid_checksum_does_not_override_bounds_validation(self):
        self.source.write_bytes(make_image())
        index = scan_ntfs_tree(str(self.source))
        save_session(str(self.session), str(self.source), index=index)
        with zipfile.ZipFile(self.session) as z:
            manifest = json.loads(z.read('manifest.json'))
            payload = json.loads(z.read('analysis.json'))
        entry = next(e for e in payload['index']['entries'] if e['data_runs'])
        entry['data_runs'][0]['lcn'] = 999999999999
        raw = json.dumps(payload).encode('utf-8')
        manifest['sha256'] = hashlib.sha256(raw).hexdigest()
        invalid = self.root / 'invalid.tenshi-session'
        with zipfile.ZipFile(invalid, 'w') as z:
            z.writestr('manifest.json', json.dumps(manifest))
            z.writestr('analysis.json', raw)
        with self.assertRaisesRegex(SessionError, 'Datenlauf'):
            load_session(str(invalid))

    def test_unsafe_children_pointer_rejected_even_with_valid_checksum(self):
        self.source.write_bytes(fat_img())
        save_session(str(self.session), str(self.source), index=scan_tree(str(self.source)))
        with zipfile.ZipFile(self.session) as z:
            manifest = json.loads(z.read('manifest.json'))
            payload = json.loads(z.read('analysis.json'))
        payload['index']['children']['5'] = [999999]
        raw = json.dumps(payload).encode('utf-8')
        manifest['sha256'] = hashlib.sha256(raw).hexdigest()
        invalid = self.root / 'bad-pointer.tenshi-session'
        with zipfile.ZipFile(invalid, 'w') as z:
            z.writestr('manifest.json', json.dumps(manifest))
            z.writestr('analysis.json', raw)
        with self.assertRaisesRegex(SessionError, 'Eintragsverweis'):
            load_session(str(invalid))


class SessionGuiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        settings = patch.dict(os.environ, {
            'TENSHI_SETTINGS_FILE': str(Path(temporary.name) / 'settings.json')})
        settings.start()
        self.addCleanup(settings.stop)
        from recoverydesk.gui import RecoveryDeskApp
        try:
            self.app = RecoveryDeskApp()
        except tk.TclError:
            self.skipTest('GUI benötigt eine grafische Anzeige')
        self.app.withdraw()
        self.addCleanup(self.app.destroy)

    def test_buttons_keep_existing_main_tabs(self):
        self.assertTrue(self.app.session_menu_button.winfo_exists())
        self.assertTrue(self.app.session_menu_button.winfo_exists())
        self.assertEqual(len(self.app.tabs.tabs()), 3)
        self.assertEqual(self.app.export_button.cget('bg'), self.app._palette()['accent'])

    def test_restored_index_moves_to_files_tab(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / 'disk.raw'
            source.write_bytes(fat_img())
            index = scan_tree(str(source))
            save = Path(d) / 'scan.tenshi-session'
            save_session(str(save), str(source), index=index, filesystem='FAT32')
            result = load_session(str(save))
            self.app._finish_session_load(result, self.app._source_generation)
            self.assertIsNotNone(self.app.browser_index)
            self.assertEqual(self.app.tabs.select(), str(self.app.ntfs_tab))
            self.assertEqual(self.app.ntfs_byte_offset.get(), '0')
            self.assertEqual(self.app.browser_fs, 'FAT32')
            self.assertEqual(len(self.app.browser_index.entries), len(index.entries))

    def test_session_menu_translated_to_all_six_languages(self):
        from recoverydesk.i18n import LANGUAGES, translate
        for lang in LANGUAGES:
            self.app.change_language(lang)
            self.assertEqual(self.app.session_menu_button.cget('text'),
                             translate('Analysesitzung', lang))
            self.assertEqual(self.app.session_menu.entrycget(0, 'label'),
                             translate('Sitzung speichern', lang))
            self.assertEqual(self.app.session_menu.entrycget(1, 'label'),
                             translate('Sitzung laden', lang))

    def test_loading_a_new_image_discard_old_tree(self):
        with tempfile.TemporaryDirectory() as d:
            img = Path(d) / 'disk.raw'
            img.write_bytes(fat_img())
            index = scan_tree(str(img))
            self.app.source_path.set(str(img))
            self.app._set_browser_fs('FAT32')
            self.app._show_browser_index(str(img), index)
            self.app._reset_analysis_for_source()
            self.assertIsNone(self.app.browser_index)
            self.assertFalse(self.app.folder_tree.get_children())
