"""Real Linux/ntfs-3g deletion; only a newly created regular image is mounted.

Opt-in privileged integration test. Never accepts an external source path.
"""
import errno
import hashlib
import json
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

    def test_os_deleted_fragmented_file_preserves_original_bytes(self):
        self._check_deletion(remove_directories=False, fragmented=True)

    def test_os_reused_deleted_clusters_are_blocked_by_batch_export(self):
        self._check_deletion(remove_directories=False, overwrite=True)

    def _check_deletion(self, *, remove_directories, fragmented=False, overwrite=False):
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
            if overwrite:
                # Reserve a live MFT record before deletion; growing this file
                # later reuses clusters without creating/reusing file records.
                replacement = mount / 'replacement.bin'
                replacement.write_bytes(b'R')
            if fragmented:
                # Exhaust this newly created image, then free alternating
                # 1-MiB files. Retained guards separate the reusable holes.
                # Allocation is performed entirely by the filesystem driver.
                guards = mount / 'allocation-guards'
                guards.mkdir()
                allocated = []
                for number in range(80):
                    guard = guards / f'guard-{number:03d}.bin'
                    try:
                        with guard.open('xb', buffering=0) as stream:
                            stream.write(b'G' * 1024**2)
                            os.fsync(stream.fileno())
                    except OSError as exc:
                        if exc.errno != errno.ENOSPC:
                            raise
                        guard.unlink(missing_ok=True)
                        break
                    allocated.append(guard)
                else:
                    self.fail('Fresh 64-MiB image was not exhausted')
                self.assertGreater(len(allocated), 20)
                for guard in allocated[::2]:
                    guard.unlink()
                # Guard files remain allocated until the image is discarded.
                large = next(relative for relative in originals if len(relative.parts) > 1)
                originals[large] = hashlib.shake_256(b'Tenshi fragmented original').digest(8 * 1024**2 + 137)
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
            if fragmented:
                runs = active[large].data_runs
                self.assertTrue(all(run.lcn is not None for run in runs))
                self.assertTrue(any(left.lcn + left.clusters != right.lcn
                                    for left, right in zip(runs, runs[1:])),
                                f'Driver did not create physical fragmentation: {runs}')
            # Delete through Linux filesystem calls, then unmount before Tenshi.
            # No manual MFT flags, bitmap edits, or subsequent volume writes.
            run('ntfs-3g', '-o', 'no_def_opts,norecover', str(image), str(mount))
            self.assertTrue(os.path.ismount(mount))
            for relative in originals:
                (folder / relative).unlink()
                self.assertFalse((folder / relative).exists())
            if overwrite:
                with replacement.open('ab', buffering=0) as stream:
                    for _ in range(80):
                        try:
                            stream.write(b'R' * 1024**2)
                            os.fsync(stream.fileno())
                        except OSError as exc:
                            if exc.errno != errno.ENOSPC:
                                raise
                            break
                    else:
                        self.fail('Replacement did not exhaust the fresh image')
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
                self.assertEqual(entry.data_runs, previous.data_runs)
                self.assertNotIn(entry, index.list_dir(entry.parent_record, show_deleted=False))
            if overwrite:
                replacement_entry = next(e for e in index.list_dir(5)
                                         if e.name == replacement.name and not e.is_deleted)
                replaced = next(e for relative, e in active.items() if len(relative.parts) > 1)
                # Prove every original physical cluster now belongs to the live
                # replacement file, rather than assuming allocator behaviour.
                for old in replaced.data_runs:
                    self.assertIsNotNone(old.lcn)
                    coverage = sum(max(0, min(old.lcn + old.clusters, new.lcn + new.clusters)
                                          - max(old.lcn, new.lcn))
                                   for new in replacement_entry.data_runs if new.lcn is not None)
                    self.assertEqual(coverage, old.clusters)
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
            if overwrite:
                from recoverydesk.recovery_preflight import inspect_metadata
                from recoverydesk.verification_labels import EXPORT_SCOPE
                large = next(relative for relative in originals if len(relative.parts) > 1)
                entry = index.by_record[active[large].record_number]
                self.assertEqual(inspect_metadata(index, str(large), entry).state, 'Gesperrt')
                # Low-level copying proves the bytes have actually changed;
                # the application batch path must reject this metadata conflict.
                raw_copy = (output / folder.name / large).read_bytes()
                self.assertEqual(raw_copy, b'R' * len(originals[large]))
                self.assertNotEqual(hashlib.sha256(raw_copy).digest(),
                                    hashlib.sha256(originals[large]).digest())
                for attempt in (first, export_batch(str(image), index, selected, str(batch))):
                    self.assertEqual(attempt.skipped, 1)
                    self.assertEqual(attempt.failed, 0)
                    self.assertEqual(len(attempt.errors), 1)
                    self.assertIn('bereits von einer vorhandenen Datei genutzt', attempt.errors[0])
                    self.assertEqual(attempt.exported + attempt.verified_existing, 1)
                    self.assertFalse((Path(attempt.root) / 'files' / folder.name / large).exists())
                    state = json.loads(Path(attempt.manifest).read_text(encoding='utf-8'))
                    item = state['results'][(Path(folder.name) / large).as_posix()]
                    self.assertEqual(item['status'], 'Übersprungen')
                    self.assertNotIn('sha256', item)
                    report = Path(attempt.log).read_text(encoding='utf-8')
                    self.assertIn(EXPORT_SCOPE, report)
                    self.assertNotIn(hashlib.sha256(originals[large]).hexdigest(), report)
                    self.assertNotIn(hashlib.sha256(raw_copy).hexdigest(), report)
                self.assertEqual(hashlib.sha256(image.read_bytes()).digest(), before)
                return
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
