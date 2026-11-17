"""Synthetic deleted NTFS references, not evidence of an operating-system deletion."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from test_browser import filename, image_with_folders, record
from test_ntfs import CLUSTER, MFT_LCN, SIZE, nonresident_attr, resident_attr
from recoverydesk.ntfs_browser import scan_ntfs_tree, export_selection
from recoverydesk.batch_export import export_batch


class DeletedNtfsReferenceTests(unittest.TestCase):
    def test_deleted_sparse_stream_is_refused_without_successful_output(self):
        # Synthetic metadata: data, a logical hole, then another data cluster.
        # Also cover a missing sparse flag: the runlist alone must block export.
        for flags in (0x8000, 0):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as temporary:
                raw = bytearray(image_with_folders())
                name = 'Gelöschte Sparse-Datei.bin'
                start = MFT_LCN * CLUSTER + 7 * SIZE
                raw[start:start + SIZE] = record([
                    filename(name, 6, parent_sequence=1),
                    nonresident_attr(0x80, b'\x11\x01\x28\x01\x01\x11\x01\x14\x00',
                                     3 * CLUSTER, 2, flags=flags)], flags=0)
                root = Path(temporary)
                source = root / 'synthetic.img'
                source.write_bytes(raw)
                before = hashlib.sha256(source.read_bytes()).digest()
                index = scan_ntfs_tree(str(source))
                entry = index.by_record[7]
                self.assertTrue(entry.is_deleted)
                self.assertEqual(entry.name, name)
                self.assertEqual(entry.size, 3 * CLUSTER)
                self.assertEqual([run.lcn for run in entry.data_runs], [40, None, 60])
                self.assertFalse(entry.recoverable)
                self.assertIn('Sparse', entry.unsupported_reason)
                target = root / 'selection'
                target.mkdir()
                result = export_selection(str(source), index, [entry], str(target))
                self.assertEqual(result.exported, 0)
                self.assertEqual(result.skipped, 1)
                self.assertEqual(list(target.iterdir()), [])
                batch = root / 'batch'
                batch.mkdir()
                for _ in range(2):
                    result = export_batch(str(source), index, [entry], str(batch))
                    self.assertEqual(result.exported, 0)
                    self.assertEqual(result.verified_existing, 0)
                    self.assertEqual(result.skipped, 1)
                    self.assertFalse((Path(result.root) / 'files' / name).exists())
                    manifest = json.loads(Path(result.manifest).read_text(encoding='utf-8'))
                    item = manifest['results'][name]
                    self.assertEqual(item['status'], 'Übersprungen')
                    self.assertNotIn('sha256', item)
                self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)

    def test_deleted_empty_file_is_created_and_verified_on_resume(self):
        raw = bytearray(image_with_folders())
        name = 'Leere gelöschte Datei ohne Endung'
        start = MFT_LCN * CLUSTER + 7 * SIZE
        raw[start:start + SIZE] = record(
            [filename(name, 6, parent_sequence=1), resident_attr(0x80, b'')], flags=0)
        with tempfile.TemporaryDirectory(prefix='tenshi-empty-deleted-ntfs-') as temporary:
            root = Path(temporary)
            source = root / 'synthetic.img'
            source.write_bytes(raw)
            before = hashlib.sha256(source.read_bytes()).digest()
            index = scan_ntfs_tree(str(source))
            entry = index.by_record[7]
            self.assertTrue(entry.is_deleted)
            self.assertTrue(entry.recoverable, entry.unsupported_reason)
            self.assertEqual(entry.size, 0)
            self.assertEqual(entry.name, name)
            target = root / 'export'
            target.mkdir()
            first = export_batch(str(source), index, [entry], str(target))
            self.assertEqual(first.errors, [])
            self.assertEqual(first.exported, 1)
            exported = Path(first.root) / 'files' / name
            self.assertTrue(exported.is_file())
            self.assertEqual(exported.read_bytes(), b'')
            resumed = export_batch(str(source), index, [entry], str(target))
            self.assertEqual(resumed.errors, [])
            self.assertEqual(resumed.exported, 0)
            self.assertEqual(resumed.verified_existing, 1)
            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)

    def test_deleted_folder_long_names_fragmented_bytes_and_resume(self):
        resident_name = 'Grüße und bekannte Originalinhalte.txt'
        fragmented_name = 'Langer Dateiname mit verteilten Bereichen.bin'
        originals = {
            resident_name: 'Bekannte Referenz mit Umlauten\n'.encode('utf-8'),
            fragmented_name: bytes(range(256)) * 2 + b'zweiter Bereich' * 13,
        }
        raw = bytearray(image_with_folders())

        def install(number, attrs, flags):
            start = MFT_LCN * CLUSTER + number * SIZE
            raw[start:start + SIZE] = record(attrs, flags=flags)

        install(6, [filename('Gelöschte Dokumente', 5)], 2)
        install(7, [filename(resident_name, 6, parent_sequence=1),
                    resident_attr(0x80, originals[resident_name])], 0)
        install(9, [filename('Unterordner', 6, parent_sequence=1)], 2)
        payload = originals[fragmented_name]
        install(10, [filename(fragmented_name, 9, parent_sequence=1),
                     nonresident_attr(0x80, b'\x11\x01\x28\x11\x01\x14\x00',
                                      len(payload), 1)], 0)
        raw[40 * CLUSTER:41 * CLUSTER] = payload[:CLUSTER]
        raw[60 * CLUSTER:60 * CLUSTER + len(payload) - CLUSTER] = payload[CLUSTER:]
        with tempfile.TemporaryDirectory(prefix='tenshi-deleted-ntfs-') as temporary:
            root = Path(temporary)
            source = root / 'synthetic.img'
            source.write_bytes(raw)
            before = hashlib.sha256(source.read_bytes()).digest()
            index = scan_ntfs_tree(str(source))
            folder = next(e for e in index.list_dir(5) if e.record_number == 6)
            self.assertTrue(folder.is_deleted)
            self.assertNotIn(folder, index.list_dir(5, show_deleted=False))
            for number, name, parent, kind in (
                    (7, resident_name, 6, 'resident'),
                    (10, fragmented_name, 9, 'nonresident')):
                entry = next(e for e in index.list_dir(parent) if e.record_number == number)
                self.assertEqual(entry.name, name)
                self.assertTrue(entry.is_deleted)
                self.assertTrue(entry.recoverable, entry.unsupported_reason)
                self.assertEqual(entry.data_kind, kind)
                self.assertEqual(entry.size, len(originals[name]))
            fragmented = index.by_record[10]
            self.assertEqual([run.lcn for run in fragmented.data_runs], [40, 60])
            paths = {
                resident_name: Path('Gelöschte Dokumente') / resident_name,
                fragmented_name: Path('Gelöschte Dokumente') / 'Unterordner' / fragmented_name,
            }
            target = root / 'selection'
            target.mkdir()
            result = export_selection(str(source), index, [folder], str(target))
            self.assertEqual(result.errors, [])
            # Existing unrelated fixture files are also exported recursively.
            self.assertEqual(result.exported, 3)
            batch = root / 'batch'
            batch.mkdir()
            first = export_batch(str(source), index, [folder], str(batch))
            self.assertEqual(first.errors, [])
            self.assertEqual(first.exported, 3)
            for name, relative in paths.items():
                for exported in (target / relative, Path(first.root) / 'files' / relative):
                    actual = exported.read_bytes()
                    self.assertEqual(actual, originals[name])
                    self.assertEqual(hashlib.sha256(actual).digest(),
                                     hashlib.sha256(originals[name]).digest())
            resumed = export_batch(str(source), index, [folder], str(batch))
            self.assertEqual(resumed.errors, [])
            self.assertEqual(resumed.exported, 0)
            self.assertEqual(resumed.verified_existing, 3)
            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)
