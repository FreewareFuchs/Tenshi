"""A cached NTFS analysis must not export from a changed regular image."""
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_ntfs import make_image, CLUSTER
from recoverydesk.ntfs_browser import scan_ntfs_tree, export_selection
from recoverydesk.batch_export import export_batch
from recoverydesk.session_store import save_session, load_session, SessionError


class NtfsStaleImageTests(unittest.TestCase):
    def test_changed_image_is_rejected_before_batch_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / 'source.img'
            image.write_bytes(make_image())
            index = scan_ntfs_tree(str(image))
            entry = next(e for e in index.entries if e.name == 'fragmentiert.bin')
            original_stamp = image.stat()
            with image.open('r+b') as stream:
                stream.seek(40 * CLUSTER)
                stream.write(b'Z' * CLUSTER)
            os.utime(image, ns=(original_stamp.st_atime_ns, original_stamp.st_mtime_ns + 1_000_000_000))
            output = root / 'export'
            output.mkdir()
            with self.assertRaisesRegex(ValueError, 'geändert|erneut'):
                export_batch(str(image), index, [entry], str(output))
            self.assertEqual(list(output.iterdir()), [])

    def test_restored_index_and_session_save_reject_changed_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / 'source.img'
            image.write_bytes(make_image())
            index = scan_ntfs_tree(str(image))
            saved = root / 'saved.json'
            save_session(str(saved), str(image), index=index, filesystem='NTFS')
            restored = load_session(str(saved)).index
            stamp = image.stat()
            with image.open('r+b') as stream:
                stream.seek(40 * CLUSTER)
                stream.write(b'Z' * CLUSTER)
            os.utime(image, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1_000_000_000))
            for cached in (index, restored):
                entry = next(e for e in cached.entries if e.name == 'fragmentiert.bin')
                output = root / ('restored-export' if cached is restored else 'original-export')
                output.mkdir()
                with self.assertRaisesRegex(ValueError, 'geändert|erneut'):
                    export_selection(str(image), cached, [entry], str(output))
                self.assertEqual(list(output.iterdir()), [])
                with self.assertRaises(SessionError):
                    save_session(str(root / 'stale.json'), str(image), index=cached, filesystem='NTFS')
                self.assertFalse((root / 'stale.json').exists())
            fresh = scan_ntfs_tree(str(image))
            entry = next(e for e in fresh.entries if e.name == 'fragmentiert.bin')
            output = root / 'fresh'
            output.mkdir()
            result = export_batch(str(image), fresh, [entry], str(output))
            self.assertEqual(result.errors, [])
            self.assertEqual((Path(result.root) / 'files' / entry.name).read_bytes(), b'Z' * CLUSTER + b'B' * 188)

    def test_replaced_image_with_preserved_size_and_mtime_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / 'source.img'
            image.write_bytes(make_image())
            index = scan_ntfs_tree(str(image))
            entry = next(e for e in index.entries if e.name == 'fragmentiert.bin')
            stamp = image.stat()
            replacement = root / 'replacement.img'
            replacement.write_bytes(image.read_bytes())
            os.utime(replacement, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            os.replace(replacement, image)
            output = root / 'export'
            output.mkdir()
            with self.assertRaisesRegex(ValueError, 'geändert|ausgetauscht'):
                export_batch(str(image), index, [entry], str(output))
            self.assertEqual(list(output.iterdir()), [])

    def test_change_during_scan_rejects_the_entire_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / 'source.img'
            image.write_bytes(make_image())
            stamp = image.stat()
            def progress(*_):
                os.utime(image, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1_000_000_000))
            with self.assertRaisesRegex(ValueError, 'geändert|erneut'):
                scan_ntfs_tree(str(image), progress=progress)

    def test_change_during_export_removes_partial_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / 'source.img'
            image.write_bytes(make_image())
            index = scan_ntfs_tree(str(image))
            entry = next(e for e in index.entries if e.name == 'fragmentiert.bin')
            stamp = image.stat()
            def on_bytes(_):
                os.utime(image, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1_000_000_000))
            output = root / 'export'
            output.mkdir()
            result = export_batch(str(image), index, [entry], str(output), byte_progress=on_bytes)
            self.assertEqual(result.exported, 0)
            self.assertEqual(result.failed, 1)
            self.assertIn('Image', result.errors[0])
            self.assertFalse((Path(result.root) / 'files' / entry.name).exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows CopyFile timestamp semantics')
    def test_windows_copy_with_unchanged_stat_times_rejects_old_analysis(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / 'source.img'
            replacement = root / 'changed.img'
            raw = make_image()
            changed = bytearray(raw)
            changed[40 * CLUSTER:41 * CLUSTER] = b'Z' * CLUSTER
            replacement.write_bytes(changed)
            image.write_bytes(raw)
            stamp = image.stat()
            # COPY preserves the source's last-write timestamp. Start with an
            # identical timestamp so all ordinary Windows stat fields survive.
            os.utime(image, ns=(stamp.st_atime_ns, replacement.stat().st_mtime_ns))
            before = image.stat()
            index = scan_ntfs_tree(str(image))
            entry = next(e for e in index.entries if e.name == 'fragmentiert.bin')
            subprocess.run(['cmd.exe', '/d', '/c', 'copy', '/b', '/y',
                            str(replacement), str(image)], check=True, capture_output=True)
            after = image.stat()
            def ordinary(meta):
                return meta.st_dev, meta.st_ino, meta.st_size, meta.st_mtime_ns, meta.st_ctime_ns
            self.assertEqual(ordinary(before), ordinary(after))
            self.assertNotEqual(image.read_bytes(), raw)
            target = root / 'export'
            target.mkdir()
            with self.assertRaisesRegex(ValueError, 'Image.*geändert'):
                export_batch(str(image), index, [entry], str(target))
            self.assertEqual(list(target.iterdir()), [])

    @unittest.skipUnless(os.name == 'nt', 'Windows native change-time query')
    def test_unavailable_native_change_time_does_not_allow_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / 'source.img'
            image.write_bytes(make_image())
            index = scan_ntfs_tree(str(image))
            entry = next(e for e in index.entries if e.name == 'fragmentiert.bin')
            target = root / 'export'
            target.mkdir()
            with patch('recoverydesk.ntfs_browser._windows_image_change_time',
                       side_effect=OSError('native metadata unavailable')):
                with self.assertRaisesRegex(ValueError, 'Image.*geändert'):
                    export_batch(str(image), index, [entry], str(target))
            self.assertEqual(list(target.iterdir()), [])

    def test_prefix_change_is_detected_even_when_metadata_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / 'source.img'
            image.write_bytes(make_image())
            original = image.stat()
            with patch('recoverydesk.ntfs_browser.os.fstat', return_value=original), \
                 patch('recoverydesk.ntfs_browser._windows_image_change_time', return_value=123):
                index = scan_ntfs_tree(str(image))
                entry = next(e for e in index.entries if e.name == 'fragmentiert.bin')
                with image.open('r+b') as stream:
                    stream.seek(40 * CLUSTER)
                    stream.write(b'Z' * CLUSTER)
                target = root / 'export'
                target.mkdir()
                with self.assertRaisesRegex(ValueError, 'Image.*geändert'):
                    export_batch(str(image), index, [entry], str(target))
                self.assertEqual(list(target.iterdir()), [])
