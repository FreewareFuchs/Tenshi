"""Real Linux FAT32/exFAT fragmentation/deletion on new regular images only."""
import errno
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

from recoverydesk.filesystems import scan_tree
from recoverydesk.batch_export import export_batch


@unittest.skipUnless(sys.platform == 'linux' and
                     os.environ.get('TENSHI_TEST_MOUNTED_FAT') == '1',
                     'explicit Linux mounted FAT image integration test only')
class MountedFatDeletionTests(unittest.TestCase):
    def test_real_fragmented_fat32_deletion(self):
        self._check_reference('FAT32')

    def test_real_fragmented_exfat_deletion(self):
        self._check_reference('exFAT')

    def _check_reference(self, filesystem):
        self.assertEqual(os.geteuid(), 0)
        formatter = 'mkfs.fat' if filesystem == 'FAT32' else 'mkfs.exfat'
        for tool in (formatter, 'mount', 'umount'):
            self.assertIsNotNone(shutil.which(tool), tool)
        root = Path(tempfile.mkdtemp(prefix='tenshi-fat-fragmented-'))
        image = root / 'new-test-image.img'
        mount = root / 'mount'
        mount.mkdir()

        def run(*args):
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0,
                             f'{args}: {result.stdout}\n{result.stderr}')

        def attach():
            # mount's loop device is backed exclusively by our new regular file.
            run('mount', '-t', 'vfat' if filesystem == 'FAT32' else 'exfat',
                '-o', 'loop', str(image), str(mount))
            self.assertTrue(os.path.ismount(mount))

        def detach():
            run('umount', str(mount))
            self.assertFalse(os.path.ismount(mount))

        try:
            with image.open('xb') as stream:
                stream.truncate(64 * 1024**2)
            self.assertTrue(image.is_file())
            self.assertFalse(image.is_symlink())
            if filesystem == 'FAT32':
                run(formatter, '-F', '32', '-s', '1', str(image))
            else:
                run(formatter, '-c', '4096', str(image))
            attach()
            folder = mount / 'FOLDER'
            folder.mkdir()
            guards = mount / 'GUARDS'
            guards.mkdir()
            allocated = []
            for number in range(80):
                guard = guards / f'G{number:03d}.BIN'
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
                self.fail('Fresh image was not exhausted')
            self.assertGreater(len(allocated), 20)
            for guard in allocated[::2]:
                guard.unlink()
            original = hashlib.shake_256((filesystem + ' fragmented original').encode()).digest(8 * 1024**2 + 137)
            target = folder / 'TARGET.BIN'
            target.write_bytes(original)
            self.assertEqual(target.read_bytes(), original)
            detach()
            initial = scan_tree(str(image))
            self.assertEqual(initial.filesystem, filesystem)
            parent = next(e for e in initial.list_dir(initial.root) if e.name.upper() == 'FOLDER')
            entry, = initial.list_dir(parent.record_number)
            self.assertFalse(entry.is_deleted)
            self.assertTrue(entry.recoverable, entry.unsupported_reason)
            volume = initial.volumes
            with image.open('rb') as stream:
                if filesystem == 'FAT32':
                    chain = list(volume.clusters(stream, entry.locator[0]))
                else:
                    self.assertFalse(entry.locator[1], 'Reference must use a FAT chain')
                    chain = list(volume.clusters(stream, entry.locator[0]))
            self.assertTrue(any(right != left + 1 for left, right in zip(chain, chain[1:])),
                            'Driver did not create physical fragmentation')

            def read_original_clusters():
                data = bytearray()
                with image.open('rb') as stream:
                    for cluster in chain:
                        stream.seek(volume.cluster_offset(cluster))
                        data.extend(stream.read(volume.cluster_size))
                return bytes(data[:len(original)])

            self.assertEqual(read_original_clusters(), original)
            before_active = hashlib.sha256(image.read_bytes()).digest()
            active_out = root / 'active-export'
            active_out.mkdir()
            active = export_batch(str(image), initial, [entry], str(active_out))
            self.assertEqual(active.errors, [])
            self.assertEqual(active.exported, 1)
            self.assertEqual((Path(active.root) / 'files' / entry.name).read_bytes(), original)
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(), before_active)
            attach()
            target.unlink()
            self.assertFalse(target.exists())
            detach()
            # No writes after deletion: distinguish missing links from lost bytes.
            self.assertEqual(read_original_clusters(), original)
            before = hashlib.sha256(image.read_bytes()).digest()
            index = scan_tree(str(image))
            parent = next(e for e in index.list_dir(index.root) if e.name.upper() == 'FOLDER')
            deleted, = index.list_dir(parent.record_number)
            self.assertTrue(deleted.is_deleted)
            self.assertEqual(deleted.name.upper(), '?ARGET.BIN' if filesystem == 'FAT32' else 'TARGET.BIN')
            self.assertEqual(deleted.size, len(original))
            self.assertEqual(index.list_dir(parent.record_number, show_deleted=False), [])
            if filesystem == 'exFAT':
                # The tested Linux driver retains the fragmented FAT links.
                self.assertTrue(deleted.recoverable, deleted.unsupported_reason)
                self.assertFalse(deleted.locator[1])
                self.assertEqual(deleted.locator[3], tuple(chain))
            else:
                # The tested Linux driver clears every original FAT link in
                # both copies. The old physical bytes alone cannot prove order.
                self.assertFalse(deleted.recoverable)
                self.assertIn('FAT32', deleted.unsupported_reason)
                with image.open('rb') as stream:
                    for number in range(volume.fats):
                        stream.seek(volume.fat_offset + number * volume.fat_bytes)
                        table = stream.read(volume.fat_bytes)
                        self.assertEqual(len(table), volume.fat_bytes)
                        self.assertTrue(all(struct.unpack_from('<I', table, c * 4)[0] & 0x0FFFFFFF == 0
                                            for c in chain))
            out = root / 'deleted-export'
            out.mkdir()
            result = export_batch(str(image), index, [deleted], str(out))
            if deleted.recoverable:
                self.assertEqual(result.errors, [])
                self.assertEqual(result.exported, 1)
                recovered = Path(result.root) / 'files' / deleted.name
                self.assertEqual(recovered.read_bytes(), original)
                self.assertEqual(hashlib.sha256(recovered.read_bytes()).digest(), hashlib.sha256(original).digest())
                resumed = export_batch(str(image), index, [deleted], str(out))
                self.assertEqual(resumed.errors, [])
                self.assertEqual(resumed.verified_existing, 1)
                self.assertEqual(resumed.exported, 0)
            else:
                self.assertTrue(deleted.unsupported_reason)
                self.assertEqual(result.exported, 0)
                self.assertEqual(result.skipped, 1)
                self.assertEqual(len(result.errors), 1)
                self.assertFalse((Path(result.root) / 'files' / deleted.name).exists())
            print(f'{filesystem}: {len(chain)} original clusters; '
                  f'deleted recoverable={deleted.recoverable}; reason={deleted.unsupported_reason}', flush=True)
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(), before)
        finally:
            if os.path.ismount(mount):
                detach()
            if not os.path.ismount(mount):
                shutil.rmtree(root)
