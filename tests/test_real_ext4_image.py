"""Mount-free integration test against an ext4 image built by e2fsprogs.

Only a freshly created regular file inside TemporaryDirectory is formatted.
Never invokes mkfs on /dev nodes or an existing user-supplied path.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from recoverydesk.filesystems import scan_tree, export_selection
from recoverydesk.partition_scan import analyze_image


@unittest.skipUnless(shutil.which('mke2fs'), 'mke2fs (e2fsprogs) unavailable')
class RealExt4ImageTests(unittest.TestCase):
    def test_mke2fs_populated_ext4_image_read_and_export(self):
        with tempfile.TemporaryDirectory(prefix='tenshi-ext4-ci-') as temp:
            root = Path(temp)
            payload = root / 'seed'
            subdir = payload / 'nested'
            subdir.mkdir(parents=True)
            text = b'Tenshi ext4 independent integration test\n'
            binary = bytes(range(256)) * 4096 + b'last bytes'
            (payload / 'hello.txt').write_bytes(text)
            (subdir / 'binary.dat').write_bytes(binary)

            image = root / 'new-test-image.img'
            with image.open('xb') as out:
                out.truncate(64 * 1024 * 1024)

            # -d populates the filesystem directly: no mount, loop, sudo or
            # operations on physical block devices are required.
            subprocess.run(
                ['mke2fs', '-q', '-t', 'ext4', '-F', '-b', '4096',
                 '-d', str(payload), str(image)],
                check=True, capture_output=True, text=True, timeout=45,
            )
            before = hashlib.sha256(image.read_bytes()).digest()

            index = scan_tree(str(image))
            self.assertEqual(index.filesystem, 'ext4')
            roots = {e.name: e for e in index.list_dir(index.root)}
            self.assertIn('hello.txt', roots)
            self.assertIn('nested', roots)
            self.assertEqual(index.preview(str(image), roots['hello.txt']), text)

            contents = {e.name: e for e in index.list_dir(roots['nested'].record_number)}
            self.assertIn('binary.dat', contents)
            self.assertEqual(contents['binary.dat'].size, len(binary))

            target = root / 'recovered'
            target.mkdir()
            result = export_selection(
                str(image), index, [roots['hello.txt'], roots['nested']], str(target)
            )
            self.assertEqual((result.exported, result.directories, result.skipped),
                             (2, 1, 0), result.errors)
            self.assertEqual((target / 'hello.txt').read_bytes(), text)
            self.assertEqual((target / 'nested' / 'binary.dat').read_bytes(), binary)
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(), before,
                             'Source image was modified during analysis/export')


if __name__ == '__main__':
    unittest.main()
