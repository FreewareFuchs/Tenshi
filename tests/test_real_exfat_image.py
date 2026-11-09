"""Mount-free exFAT reference: exfatprogs format/check, FATtools population."""
import base64
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from recoverydesk.filesystems import scan_tree, export_selection
from recoverydesk.batch_export import export_batch


@unittest.skipUnless(all(shutil.which(t) for t in ('mkfs.exfat', 'fsck.exfat'))
                     and importlib.util.find_spec('FATtools') is not None,
                     'exfatprogs and FATtools required')
class RealExfatImageTests(unittest.TestCase):
    def test_external_delete_recovers_long_name_and_bytes_via_directory_entries(self):
        from FATtools.Volume import vopen, vclose

        with tempfile.TemporaryDirectory(prefix='tenshi-exfat-deleted-ci-') as temporary:
            root = Path(temporary)
            image = root / 'new-test-image.img'
            with image.open('xb') as stream:
                stream.truncate(64 * 1024**2)
            subprocess.run(['mkfs.exfat', '-c', '4096', str(image)],
                           check=True, capture_output=True, timeout=45)

            deleted_name = 'Grüne gelöschte Referenz.bin'
            originals = {
                'active.bin': hashlib.shake_256(b'exFAT active').digest(9001),
                deleted_name: hashlib.shake_256(b'exFAT deleted').digest(9001),
            }
            volume = vopen(str(image), 'r+b')
            try:
                for name, data in originals.items():
                    handle = volume.create(name)
                    try:
                        handle.write(data)
                        self.assertTrue(handle.File.nofat, 'Reference must be contiguous')
                    finally:
                        handle.close()
                volume.erase(deleted_name)
            finally:
                vclose(volume)
            subprocess.run(['fsck.exfat', '-n', str(image)],
                           check=True, capture_output=True, timeout=45)

            before = hashlib.sha256(image.read_bytes()).digest()
            index = scan_tree(str(image))
            active, = index.list_dir(index.root, show_deleted=False)
            deleted, = [entry for entry in index.list_dir(index.root) if entry.is_deleted]
            self.assertEqual(active.name, 'active.bin')
            self.assertEqual(deleted.name, deleted_name)
            self.assertTrue(deleted.recoverable, deleted.unsupported_reason)

            target = root / 'export'
            target.mkdir()
            report = export_batch(str(image), index, [deleted], str(target))
            self.assertEqual(report.errors, [])
            self.assertEqual(report.exported, 1)
            exported = Path(report.root) / 'files' / deleted_name
            self.assertEqual(exported.read_bytes(), originals[deleted_name])
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(), before)

    def test_external_delete_free_signature_export_and_resume(self):
        from FATtools.Volume import vopen, vclose
        from recoverydesk.signature_search import scan_signatures
        from recoverydesk.export_resume import read_saved_export, prepare_saved_export
        with tempfile.TemporaryDirectory(prefix='tenshi-exfat-free-ci-') as temporary:
            root=Path(temporary);image=root/'new-test-image.img'
            with image.open('xb') as stream:stream.truncate(64*1024**2)
            subprocess.run(['mkfs.exfat','-c','4096',str(image)],check=True,capture_output=True,timeout=45)
            # Fixed PNG seed keeps the isolated FATtools environment stdlib-only.
            payload=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAABgAAAAQCAIAAACDRijCAAAAI0lEQVR4nGNkYPjPQA3ARBVTGEYNIgaMBjZhMBpGhMHgCyMA1j8BH9wczesAAAAASUVORK5CYII=')
            volume=vopen(str(image),'r+b')
            try:
                for name in ('active.png','deleted.png'):
                    handle=volume.create(name);handle.write(payload);handle.close()
                volume.erase('deleted.png')
            finally:
                vclose(volume)
            subprocess.run(['fsck.exfat','-n',str(image)],check=True,capture_output=True,timeout=45)
            before=hashlib.sha256(image.read_bytes()).digest()
            self.assertEqual(len(scan_signatures(str(image)).entries),2)
            index=scan_signatures(str(image),search_area='exfat-free')
            self.assertEqual(len(index.entries),1)
            target=root/'export';target.mkdir();report=export_batch(str(image),index,index.entries,str(target))
            self.assertEqual(next((Path(report.root)/'files').glob('*.png')).read_bytes(),payload)
            saved=read_saved_export(report.manifest)
            self.assertEqual(saved.signature_search_area,'exfat-free')
            self.assertEqual(len(prepare_saved_export(saved)['index'].entries),1)
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(),before)

    def test_contiguous_fragmented_nested_export_and_resume(self):
        from FATtools.Volume import vopen, vclose
        with tempfile.TemporaryDirectory(prefix='tenshi-exfat-ci-') as temporary:
            root = Path(temporary)
            image = root / 'new-test-image.img'
            with image.open('xb') as stream:
                stream.truncate(64 * 1024 * 1024)

            def run(*args):
                result = subprocess.run(args, capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            # Format only an exclusively created disposable regular file.
            run('mkfs.exfat', '-c', '4096', str(image))
            original = bytes(range(256)) * 8192 + b'partial final cluster'
            originals = {'contiguous.bin': original,
                         'fragmented.bin': original[::-1],
                         'blocker.bin': b'B' * 4096,
                         'nested/Grüne long reference.txt': 'exFAT Referenz\r\n'.encode('utf-8')}
            volume = vopen(str(image), 'r+b')
            try:
                self.assertEqual(volume.boot.cluster, 4096)
                handle = volume.create('contiguous.bin')
                handle.write(originals['contiguous.bin'])
                handle.close()
                # Occupy the next cluster before extending the still-open file.
                fragmented = volume.create('fragmented.bin')
                fragmented.write(originals['fragmented.bin'][:4096])
                blocker = volume.create('blocker.bin')
                blocker.write(originals['blocker.bin'])
                blocker.close()
                fragmented.write(originals['fragmented.bin'][4096:])
                self.assertFalse(fragmented.File.nofat, 'Reference must actually be fragmented')
                self.assertGreaterEqual(len(fragmented.File.runs), 2)
                fragmented.close()
                nested = volume.mkdir('nested')
                handle = nested.create('Grüne long reference.txt')
                handle.write(originals['nested/Grüne long reference.txt'])
                handle.close()
                nested.close()
            finally:
                vclose(volume)
            # A second independent implementation must accept the complete image.
            run('fsck.exfat', '-n', str(image))
            before = hashlib.sha256(image.read_bytes()).digest()
            index = scan_tree(str(image))
            self.assertEqual(index.filesystem, 'exFAT')
            roots = {entry.name: entry for entry in index.list_dir(index.root)}
            self.assertEqual(set(roots), {'contiguous.bin', 'fragmented.bin', 'blocker.bin', 'nested'})
            children = {entry.name: entry for entry in index.list_dir(roots['nested'].record_number)}
            self.assertEqual(set(children), {'Grüne long reference.txt'})
            self.assertTrue(roots['contiguous.bin'].locator[1])
            self.assertFalse(roots['fragmented.bin'].locator[1])
            with image.open('rb') as stream:
                clusters = list(index.volumes.clusters(stream, roots['fragmented.bin'].locator[0]))
            self.assertTrue(any(b != a + 1 for a, b in zip(clusters, clusters[1:])))
            for entry in (roots['contiguous.bin'], roots['fragmented.bin']):
                self.assertEqual(entry.size, len(originals[entry.name]))
                self.assertEqual(index.preview(str(image), entry), originals[entry.name][:65536])
            selected = list(roots.values())
            output = root / 'export'
            output.mkdir()
            result = export_selection(str(image), index, selected, str(output))
            self.assertEqual(result.exported, len(originals), result.errors)
            self.assertEqual(result.errors, [])
            for relative, data in originals.items():
                actual = (output / relative).read_bytes()
                self.assertEqual(len(actual), len(data))
                self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(data).digest())
            target = root / 'batch'
            target.mkdir()
            first = export_batch(str(image), index, selected, str(target))
            self.assertEqual(first.exported, len(originals), first.errors)
            self.assertEqual(first.errors, [])
            for relative, data in originals.items():
                actual = (Path(first.root) / 'files' / relative).read_bytes()
                self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(data).digest())
            resumed = export_batch(str(image), index, selected, str(target))
            self.assertEqual(resumed.verified_existing, len(originals), resumed.errors)
            self.assertEqual(resumed.exported, 0)
            self.assertEqual(resumed.errors, [])
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(), before)
