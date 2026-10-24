"""Independent FAT32 reference: dosfstools/mtools, no mount or physical device."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from recoverydesk.filesystems import scan_tree, export_selection
from recoverydesk.batch_export import export_batch


@unittest.skipUnless(all(shutil.which(tool) for tool in ('mkfs.fat', 'mcopy', 'mmd')),
                     'dosfstools and mtools required')
class RealFat32ImageTests(unittest.TestCase):
    def test_external_format_populate_export_and_resume(self):
        with tempfile.TemporaryDirectory(prefix='tenshi-fat32-ci-') as temporary:
            root = Path(temporary)
            image = root / 'new-test-image.img'
            with image.open('xb') as stream:
                stream.truncate(64 * 1024 * 1024)
            text = b'Tenshi independent FAT32 reference\r\n'
            binary = bytes(range(256)) * 8192 + b'last partial cluster'
            originals = {'hello.txt': text, 'nested/long reference filename.bin': binary}
            for relative, data in originals.items():
                path = root / 'seed' / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)

            def run(*args):
                subprocess.run(args, check=True, capture_output=True, text=True, timeout=45)

            # Only the exclusively created disposable regular file is formatted.
            # Explicit cluster size gives a valid FAT32 cluster count at 64 MiB.
            run('mkfs.fat', '-F', '32', '-s', '1', str(image))
            run('mmd', '-i', str(image), '::/nested')
            for relative in originals:
                run('mcopy', '-i', str(image), str(root / 'seed' / relative), '::/' + relative)
            before = hashlib.sha256(image.read_bytes()).digest()
            index = scan_tree(str(image))
            self.assertEqual(index.filesystem, 'FAT32')
            roots = {entry.name: entry for entry in index.list_dir(index.root)}
            self.assertEqual(set(roots), {'hello.txt', 'nested'})
            children = {entry.name: entry for entry in index.list_dir(roots['nested'].record_number)}
            self.assertIn('long reference filename.bin', children)
            self.assertEqual(index.preview(str(image), roots['hello.txt']), text)
            self.assertEqual(index.preview(str(image), children['long reference filename.bin']), binary[:65536])
            selected = [roots['hello.txt'], roots['nested']]
            output = root / 'export'
            output.mkdir()
            result = export_selection(str(image), index, selected, str(output))
            self.assertEqual(result.exported, 2, result.errors)
            self.assertEqual(result.errors, [])
            for relative, original in originals.items():
                actual = (output / relative).read_bytes()
                self.assertEqual(len(actual), len(original))
                self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(original).digest())
            batch_target = root / 'batch'
            batch_target.mkdir()
            first = export_batch(str(image), index, selected, str(batch_target))
            self.assertEqual(first.exported, 2, first.errors)
            for relative, original in originals.items():
                actual = (Path(first.root) / 'files' / relative).read_bytes()
                self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(original).digest())
            resumed = export_batch(str(image), index, selected, str(batch_target))
            self.assertEqual(resumed.verified_existing, 2, resumed.errors)
            self.assertEqual(resumed.exported, 0)
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(), before)
