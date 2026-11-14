"""Real Linux/ntfs-3g deletion; only a newly created regular image is mounted.

Opt-in privileged integration test. Never accepts an external source path.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from recoverydesk.ntfs_browser import scan_ntfs_tree, export_selection, ORPHANS
from recoverydesk.batch_export import export_batch


@unittest.skipUnless(sys.platform == 'linux' and
                     os.environ.get('TENSHI_TEST_MOUNTED_NTFS') == '1',
                     'explicit Linux mounted-image integration test only')
class MountedNtfsDeletionTests(unittest.TestCase):
    def test_os_deleted_files_with_retained_parent_folders(self):
        self._check_deletion(remove_directories=False)

    def test_os_deleted_parent_folders_leave_conservative_orphans(self):
        self._check_deletion(remove_directories=True)

    def _check_deletion(self, *, remove_directories):
        # In the opt-in CI step, missing privileges/tools are failures, not skips.
        self.assertEqual(os.geteuid(), 0, 'mounted image test requires root')
        for tool in ('mkntfs', 'ntfs-3g', 'umount'):
            self.assertIsNotNone(shutil.which(tool), tool)
        root = Path(tempfile.mkdtemp(prefix='tenshi-os-delete-ntfs-'))
        image = root / 'new-test-image.img'
        mount = root / 'mount'
        mount.mkdir()

        def run(*args):
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0,
                             f'{args}: {result.stdout}\n{result.stderr}')

        try:
            with image.open('xb') as stream:
                stream.truncate(64 * 1024**2)
            self.assertTrue(image.is_file())
            self.assertFalse(image.is_symlink())
            run('mkntfs', '-F', '-Q', '-s', '512', '-c', '4096', str(image))
            # ntfs-3g supports regular image files directly (no physical disk).
            run('ntfs-3g', '-o', 'no_def_opts,norecover', str(image), str(mount))
            self.assertTrue(os.path.ismount(mount))
            folder = mount / 'Gelöschte Dokumente'
            folder.mkdir()
            nested = folder / 'Unterordner'
            nested.mkdir()
            originals = {
                Path('Grüße und bekannte Originalinhalte.txt'):
                    'Bekannte residente Referenz\n'.encode('utf-8'),
                Path('Unterordner') / 'Große Datei mit langem Originalnamen.bin':
                    hashlib.shake_256(b'Tenshi OS deleted NTFS reference').digest(2 * 1024**2 + 137),
            }
            for relative, data in originals.items():
                (folder / relative).write_bytes(data)
                self.assertEqual((folder / relative).read_bytes(), data)
            run('umount', str(mount))
            self.assertFalse(os.path.ismount(mount))
            initial = scan_ntfs_tree(str(image))
            active_folder = next(e for e in initial.list_dir(5)
                                 if e.name == folder.name)
            active = {}
            for relative in originals:
                parent = active_folder.record_number
                if len(relative.parts) > 1:
                    parent = next(e.record_number for e in initial.list_dir(parent)
                                  if e.name == 'Unterordner')
                entry = next(e for e in initial.list_dir(parent) if e.name == relative.name)
                self.assertFalse(entry.is_deleted)
                self.assertTrue(entry.recoverable, entry.unsupported_reason)
                active[relative] = entry
            self.assertEqual({e.data_kind for e in active.values()}, {'resident', 'nonresident'})
            # Delete through Linux filesystem calls, then unmount before Tenshi.
            # No manual MFT flags, bitmap edits, or subsequent volume writes.
            run('ntfs-3g', '-o', 'no_def_opts,norecover', str(image), str(mount))
            self.assertTrue(os.path.ismount(mount))
            for relative in originals:
                (folder / relative).unlink()
                self.assertFalse((folder / relative).exists())
            if remove_directories:
                nested.rmdir()
                folder.rmdir()
            run('umount', str(mount))
            self.assertFalse(os.path.ismount(mount))
            before = hashlib.sha256(image.read_bytes()).digest()
            index = scan_ntfs_tree(str(image))
            deleted_folder = index.by_record[active_folder.record_number]
            self.assertEqual(deleted_folder.is_deleted, remove_directories)
            self.assertEqual(deleted_folder.name, folder.name)
            for relative, previous in active.items():
                entry = index.by_record[previous.record_number]
                self.assertEqual(entry.name, relative.name)
                self.assertEqual(entry.parent_record, previous.parent_record)
                self.assertTrue(entry.is_deleted)
                self.assertTrue(entry.recoverable, entry.unsupported_reason)
                self.assertEqual(entry.size, len(originals[relative]))
                self.assertNotIn(entry, index.list_dir(entry.parent_record, show_deleted=False))
            selected = [deleted_folder]
            if remove_directories:
                # ntfs-3g increments the freed directory record sequence.
                # Stale references must remain orphaned: a matching record
                # number alone cannot prove that a parent was not reused.
                selected = [index.by_record[e.record_number] for e in active.values()]
                for entry in selected:
                    parent = index.by_record[entry.parent_record]
                    self.assertTrue(parent.is_deleted)
                    self.assertEqual(parent.sequence, entry.parent_sequence + 1)
                    self.assertIn(entry, index.list_dir(ORPHANS))
                    self.assertNotIn(entry, index.list_dir(parent.record_number))
            output = root / 'export'
            output.mkdir()
            result = export_selection(str(image), index, selected, str(output))
            self.assertEqual(result.errors, [])
            self.assertEqual(result.exported, len(originals))
            batch = root / 'batch'
            batch.mkdir()
            first = export_batch(str(image), index, selected, str(batch))
            self.assertEqual(first.errors, [])
            self.assertEqual(first.exported, len(originals))
            for relative, original in originals.items():
                for base in (output, Path(first.root) / 'files'):
                    actual_path = (base / relative.name if remove_directories
                                   else base / folder.name / relative)
                    actual = actual_path.read_bytes()
                    self.assertEqual(actual, original)
                    self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(original).digest())
            resumed = export_batch(str(image), index, selected, str(batch))
            self.assertEqual(resumed.errors, [])
            self.assertEqual(resumed.exported, 0)
            self.assertEqual(resumed.verified_existing, len(originals))
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(), before)
        finally:
            # Never recursively clean a mounted tree. Preserve it on unmount failure.
            if os.path.ismount(mount):
                run('umount', str(mount))
            if not os.path.ismount(mount):
                shutil.rmtree(root)
