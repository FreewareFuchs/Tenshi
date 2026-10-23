"""Mount-free read/export checks of independently formatted Btrfs and XFS.

Only new regular files inside TemporaryDirectory are formatted. No /dev,
loop devices, mounting, sudo or original user files are involved.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from recoverydesk.filesystems import scan_tree, export_selection
from recoverydesk.partition_scan import analyze_image


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').digest()


class RealAdvancedImageTests(unittest.TestCase):
    def exercise(self, filesystem):
        with tempfile.TemporaryDirectory(prefix='tenshi-real-fs-') as temp:
            root = Path(temp)
            seed = root / 'seed'
            (seed / 'nested').mkdir(parents=True)
            text = 'Tenshi: echte Dateisystemprüfung – Grüße\n'.encode()
            binary = bytes(range(256)) * 4096 + b'last bytes'
            (seed / 'hello.txt').write_bytes(text)
            (seed / 'nested' / 'binary.dat').write_bytes(binary)
            image = root / 'new.img'
            with image.open('xb') as out:
                out.truncate(384 * 1024 * 1024)
            if filesystem == 'Btrfs':
                command = ['mkfs.btrfs', '-q', '-r', str(seed), str(image)]
            else:
                proto = root / 'prototype'
                proto.write_text(
                    f'dummy\n0 0\nd--755 0 0\n'
                    f'hello.txt ---644 0 0 {seed / "hello.txt"}\n'
                    f'nested d--755 0 0\n'
                    f'binary.dat ---644 0 0 {seed / "nested" / "binary.dat"}\n'
                    '$\n$\n', encoding='utf-8')
                command = ['mkfs.xfs', '-q', '-p', str(proto), str(image)]
            subprocess.run(command, check=True, capture_output=True,
                           text=True, timeout=60)
            before = digest(image)
            report = analyze_image(str(image))
            self.assertIn(filesystem, [p.filesystem for p in report.partitions])
            index = scan_tree(str(image))
            self.assertEqual(index.filesystem, filesystem)
            entries = {e.name: e for e in index.list_dir(index.root)}
            self.assertIn('hello.txt', entries)
            self.assertIn('nested', entries)
            self.assertEqual(index.preview(str(image), entries['hello.txt']), text)
            children = {e.name: e for e in index.list_dir(entries['nested'].record_number)}
            self.assertEqual(children['binary.dat'].size, len(binary))
            target = root / 'recovered'
            target.mkdir()
            result = export_selection(str(image), index,
                                      [entries['hello.txt'], entries['nested']], str(target))
            self.assertEqual((result.exported, result.directories, result.skipped),
                             (2, 1, 0), result.errors)
            self.assertEqual((target / 'hello.txt').read_bytes(), text)
            self.assertEqual((target / 'nested' / 'binary.dat').read_bytes(), binary)
            self.assertEqual(digest(image), before, 'Source image changed')

    @unittest.skipUnless(shutil.which('mkfs.btrfs'), 'btrfs-progs unavailable')
    def test_real_btrfs_default_format(self):
        self.exercise('Btrfs')

    @unittest.skipUnless(shutil.which('mkfs.xfs'), 'xfsprogs unavailable')
    def test_real_xfs_default_format(self):
        self.exercise('XFS')
