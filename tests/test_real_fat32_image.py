"""Independent FAT32 reference: dosfstools/mtools, no mount or physical device."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from recoverydesk.filesystems import scan_tree, export_selection
from recoverydesk.batch_export import export_batch


@unittest.skipUnless(all(shutil.which(tool) for tool in ('mkfs.fat', 'mcopy', 'mmd', 'mdel')),
                     'dosfstools and mtools required')
class RealFat32ImageTests(unittest.TestCase):
    def test_external_delete_leaves_long_names_with_ambiguous_short_name_checksum(self):
        with tempfile.TemporaryDirectory(prefix='tenshi-fat32-long-name-ci-') as temporary:
            root = Path(temporary)
            image = root / 'new-test-image.img'
            with image.open('xb') as stream:
                stream.truncate(64 * 1024**2)

            def run(*args):
                subprocess.run(args, check=True, capture_output=True, timeout=45)

            names = {'FIRST': 'Reference name Alpha.bin',
                     'SECOND': 'Reference name Bravo.bin'}
            originals = {folder: hashlib.shake_256(name.encode('ascii')).digest(9001)
                         for folder, name in names.items()}
            run('mkfs.fat', '-F', '32', '-s', '1', str(image))
            for folder, name in names.items():
                seed = root / name
                seed.write_bytes(originals[folder])
                run('mmd', '-i', str(image), '::/' + folder)
                run('mcopy', '-i', str(image), str(seed), f'::/{folder}/{name}')

            initial = scan_tree(str(image))
            folders = {entry.name.upper(): entry for entry in initial.list_dir(initial.root)}
            self.assertEqual(set(folders), set(names))

            def read_name_records(folder):
                # The only file follows the two dot entries in this fresh directory.
                offset = initial.volumes.cluster_offset(folders[folder].locator[0]) + 64
                with image.open('rb') as stream:
                    stream.seek(offset)
                    return tuple(stream.read(32) for _ in range(3))

            short_names = set()
            checksums = set()
            for folder, name in names.items():
                active, = initial.list_dir(folders[folder].record_number)
                self.assertEqual(active.name, name)
                outer, inner, short = read_name_records(folder)
                self.assertEqual((outer[0], inner[0]), (0x42, 0x01))
                self.assertEqual((outer[11], inner[11]), (0x0F, 0x0F))
                self.assertEqual(outer[13], inner[13])
                short_names.add(short[:11])
                checksums.add(inner[13])

                run('mdel', '-i', str(image), f'::/{folder}/{name}')
                deleted = read_name_records(folder)
                self.assertEqual([record[0] for record in deleted], [0xE5] * 3)
                self.assertEqual(tuple(record[1:] for record in deleted[:2]),
                                 (outer[1:], inner[1:]))
                name_bytes = b''.join(record[1:11] + record[14:26] + record[28:32]
                                      for record in reversed(deleted[:2]))
                self.assertEqual(name_bytes.decode('utf-16le').split('\0', 1)[0], name)

            # Distinct long names can have identical short names and checksums.
            self.assertEqual(len(short_names), 1)
            self.assertEqual(len(checksums), 1)
            before = hashlib.sha256(image.read_bytes()).digest()
            index = scan_tree(str(image))
            selected = index.list_dir(index.root)
            for folder in selected:
                entry, = index.list_dir(folder.record_number)
                self.assertTrue(entry.is_deleted)
                self.assertTrue(entry.name.startswith('?'))
                self.assertTrue(entry.recoverable, entry.unsupported_reason)

            target = root / 'export'
            target.mkdir()
            report = export_batch(str(image), index, selected, str(target))
            self.assertEqual(report.errors, [])
            self.assertEqual(report.exported, 2)
            for folder in selected:
                recovered, = (Path(report.root) / 'files' / folder.name).iterdir()
                self.assertEqual(recovered.read_bytes(), originals[folder.name.upper()])
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(), before)

    def test_external_delete_recovers_bytes_and_parent_via_directory_entries(self):
        with tempfile.TemporaryDirectory(prefix='tenshi-fat32-deleted-ci-') as temporary:
            root = Path(temporary)
            image = root / 'new-test-image.img'
            with image.open('xb') as stream:
                stream.truncate(64 * 1024**2)

            def run(*args):
                subprocess.run(args, check=True, capture_output=True, timeout=45)

            originals = {
                'ACTIVE.BIN': hashlib.shake_256(b'FAT32 active').digest(9001),
                'RESTORE.BIN': hashlib.shake_256(b'FAT32 deleted').digest(9001),
            }
            run('mkfs.fat', '-F', '32', '-s', '1', str(image))
            run('mmd', '-i', str(image), '::/FOLDER')
            for name, data in originals.items():
                seed = root / name
                seed.write_bytes(data)
                run('mcopy', '-i', str(image), str(seed), '::/FOLDER/' + name)
            run('mdel', '-i', str(image), '::/FOLDER/RESTORE.BIN')

            before = hashlib.sha256(image.read_bytes()).digest()
            index = scan_tree(str(image))
            folder, = index.list_dir(index.root)
            self.assertEqual(folder.name.upper(), 'FOLDER')
            entries = index.list_dir(folder.record_number)
            active, = index.list_dir(folder.record_number, show_deleted=False)
            deleted, = [entry for entry in entries if entry.is_deleted]
            self.assertEqual(active.name.upper(), 'ACTIVE.BIN')
            self.assertEqual(deleted.name.upper(), '?ESTORE.BIN')
            self.assertTrue(deleted.recoverable, deleted.unsupported_reason)

            target = root / 'export'
            target.mkdir()
            report = export_batch(str(image), index, [deleted], str(target))
            self.assertEqual(report.errors, [])
            self.assertEqual(report.exported, 1)
            exported, = [path for path in (Path(report.root) / 'files').rglob('*') if path.is_file()]
            self.assertEqual(exported.read_bytes(), originals['RESTORE.BIN'])
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(), before)

    def test_external_delete_then_free_signature_search_exports_only_deleted_payload(self):
        from test_signature_search import picture
        from recoverydesk.signature_search import scan_signatures
        from recoverydesk.export_resume import read_saved_export, prepare_saved_export
        with tempfile.TemporaryDirectory(prefix='tenshi-fat32-free-ci-') as temporary:
            root=Path(temporary);image=root/'new-test-image.img'
            with image.open('xb') as stream:stream.truncate(64*1024**2)
            def run(*args):
                subprocess.run(args,check=True,capture_output=True,text=True,timeout=45)
            run('mkfs.fat','-F','32','-s','1',str(image))
            payload=picture('PNG');seed=root/'seed.png';seed.write_bytes(payload)
            run('mcopy','-i',str(image),str(seed),'::/active.png')
            run('mcopy','-i',str(image),str(seed),'::/deleted.png')
            run('mdel','-i',str(image),'::/deleted.png')
            before=hashlib.sha256(image.read_bytes()).digest()
            self.assertEqual(len(scan_signatures(str(image)).entries),2)
            index=scan_signatures(str(image),search_area='fat32-free')
            self.assertEqual(len(index.entries),1)
            target=root/'export';target.mkdir()
            report=export_batch(str(image),index,index.entries,str(target))
            self.assertEqual(next((Path(report.root)/'files').glob('*.png')).read_bytes(),payload)
            saved=read_saved_export(report.manifest)
            self.assertEqual(saved.signature_search_area,'fat32-free')
            self.assertEqual(len(prepare_saved_export(saved)['index'].entries),1)
            self.assertEqual(hashlib.sha256(image.read_bytes()).digest(),before)

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
