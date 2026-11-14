"""Independent NTFS reference created by ntfs-3g tools without mounting."""
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

from recoverydesk.ntfs_browser import scan_ntfs_tree, export_selection
from recoverydesk.batch_export import export_batch


@unittest.skipUnless(all(shutil.which(tool) for tool in ('mkntfs', 'ntfscp')),
                     'ntfs-3g tools required')
class RealNtfsImageTests(unittest.TestCase):
    def test_external_resident_and_nonresident_export_and_resume(self):
        self._check_export(synthetic_deleted=False)

    def test_external_contents_with_synthetic_deleted_flags(self):
        # This is NOT an OS deletion: directory indexes and allocation bitmaps
        # remain intact. Only MFT in-use flags in a disposable image are cleared.
        self._check_export(synthetic_deleted=True)

    def _check_export(self, *, synthetic_deleted):
        with tempfile.TemporaryDirectory(prefix='tenshi-ntfs-ci-') as temporary:
            root = Path(temporary)
            image = root / 'new-test-image.img'
            with image.open('xb') as stream:
                stream.truncate(64 * 1024 * 1024)
            originals = {
                'hello.txt': b'Tenshi independent NTFS reference\r\n',
                'long reference filename.bin': bytes(range(256)) * 8192 + b'partial final cluster',
                'Grüße aus NTFS.txt': 'Referenz mit Umlauten\n'.encode('utf-8'),
            }

            def run(*args):
                subprocess.run(args, check=True, capture_output=True, text=True, timeout=45)

            # Format only this exclusively created disposable regular file.
            run('mkntfs', '-F', '-Q', '-s', '512', '-c', '4096', str(image))
            for name, data in originals.items():
                seed = root / name
                seed.write_bytes(data)
                run('ntfscp', str(image), str(seed), '/' + name)
            if synthetic_deleted:
                active = scan_ntfs_tree(str(image))
                mft = next(entry for entry in active.entries if entry.name == '$MFT')
                targets = {entry.name: entry for entry in active.list_dir(5)}
                # Translate each record through the actual MFT runlist; never
                # assume the MFT is contiguous or overwrite fixup bytes.
                with image.open('r+b') as stream:
                    for name in originals:
                        logical = targets[name].record_number * active.info.record_size + 22
                        for run in mft.data_runs:
                            length = run.clusters * active.info.cluster_size
                            if logical < length:
                                self.assertIsNotNone(run.lcn)
                                stream.seek(run.lcn * active.info.cluster_size + logical)
                                flags = struct.unpack('<H', stream.read(2))[0]
                                self.assertTrue(flags & 1)
                                stream.seek(-2, 1)
                                stream.write(struct.pack('<H', flags & ~1))
                                break
                            logical -= length
                        else:
                            self.fail('Reference record outside MFT runlist')
            before = hashlib.sha256(image.read_bytes()).digest()
            index = scan_ntfs_tree(str(image))
            roots = {entry.name: entry for entry in index.list_dir(5)}
            self.assertTrue(set(originals).issubset(roots))
            self.assertEqual(roots['hello.txt'].data_kind, 'resident')
            self.assertEqual(roots['long reference filename.bin'].data_kind, 'nonresident')
            selected = [roots[name] for name in originals]
            for entry in selected:
                self.assertEqual(entry.size, len(originals[entry.name]))
                self.assertEqual(entry.is_deleted, synthetic_deleted)
                self.assertFalse(entry.unsupported_reason)
            visible = {entry.name for entry in index.list_dir(5, show_deleted=False)}
            self.assertEqual(set(originals) & visible,
                             set() if synthetic_deleted else set(originals))
            output = root / 'export'
            output.mkdir()
            result = export_selection(str(image), index, selected, str(output))
            self.assertEqual(result.exported, len(originals), result.errors)
            self.assertEqual(result.errors, [])
            for name, original in originals.items():
                actual = (output / name).read_bytes()
                self.assertEqual(len(actual), len(original))
                self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(original).digest())
            batch_target = root / 'batch'
            batch_target.mkdir()
            first = export_batch(str(image), index, selected, str(batch_target))
            self.assertEqual(first.exported, len(originals), first.errors)
            self.assertEqual(first.errors, [])
            for name, original in originals.items():
                actual = (Path(first.root) / 'files' / name).read_bytes()
                self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(original).digest())
            resumed = export_batch(str(image), index, selected, str(batch_target))
            self.assertEqual(resumed.verified_existing, len(originals), resumed.errors)
            self.assertEqual(resumed.exported, 0)
            self.assertEqual(resumed.errors, [])
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(), before)
