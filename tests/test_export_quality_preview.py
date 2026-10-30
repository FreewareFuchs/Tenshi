"""Synthetic-file checks for 0.9: bounded preview, risk labels and cancellation."""
import io
import tempfile
import unittest
from pathlib import Path

from recoverydesk.preview import describe
from recoverydesk.recovery_quality import assess
from recoverydesk.export_io import write_chunks, ExportCancelled
from recoverydesk.ntfs_browser import export_file as ntfs_export_file, export_selection as ntfs_export_selection, FileEntry
from recoverydesk.filesystems import export_file as generic_export_file, export_selection as generic_export_selection, scan_tree
from test_browser import image_with_folders
from test_filesystems import fat_img
from recoverydesk.ntfs_browser import scan_ntfs_tree


class PreviewQualityTests(unittest.TestCase):
    def test_classifies_text_utf16_and_binary_without_hex(self):
        self.assertEqual(describe(b'Hallo\nWelt', 10).kind, 'text')
        self.assertEqual(describe(b'\xff\xfeH\x00i\x00', 6).text, 'Hi')
        self.assertEqual(describe(b'\x00\x02\x7f', 3).kind, 'binary')
        self.assertEqual(describe(b'%PDF-1.7', 10).kind, 'binary')
        self.assertEqual(describe(b'\x89PNG\r\n\x1a\n', 8).kind, 'image')
        self.assertEqual(describe(b'GIF89a', 6).kind, 'image')
        self.assertIn('begrenzt', describe(b'Text', 200).text)

    def test_never_claims_deleted_contents_verified(self):
        present = FileEntry(8, 1, 'file.bin', 5, 1, False, False, size=4, data_kind='resident', resident_data=b'data')
        deleted = FileEntry(8, 1, 'file.bin', 5, 1, False, True, size=4, data_kind='resident', resident_data=b'data')
        metadata = FileEntry(9, 1, 'x.bin', 5, 1, False, False, metadata_only=True)
        invalid = FileEntry(10, 1, 'enc.bin', 5, 1, False, False, unsupported_reason='Verschlüsselt')
        self.assertEqual(assess(present).grade, 'possible')
        self.assertEqual(assess(deleted).grade, 'uncertain')
        self.assertIn('überschrieben', assess(deleted).detail)
        self.assertEqual(assess(metadata).grade, 'unknown')
        self.assertEqual(assess(invalid).grade, 'blocked')


class StreamingTests(unittest.TestCase):
    def test_partial_writes_and_chunk_bounding(self):
        class Partial:
            def __init__(self): self.data = bytearray()
            def write(self, block):
                n = min(7, len(block))
                self.data.extend(block[:n])
                return n
        writer = Partial()
        result = write_chunks(writer, [b'A' * (2 * 1024 * 1024 + 7)])
        self.assertEqual(result, 2 * 1024 * 1024 + 7)
        self.assertEqual(writer.data[:3], b'AAA')
        self.assertEqual(len(writer.data), result)

    def test_cancelled_removes_partial_ntfs_and_generic_files(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / 'ntfs.raw'
            src.write_bytes(image_with_folders())
            idx = scan_ntfs_tree(str(src))
            entry = next(x for x in idx.list_dir(6) if x.name == 'bericht.txt')
            target = Path(td) / 'partial.txt'
            flag = {'stop': False}
            def progress(amount): flag['stop'] = True
            with self.assertRaises(ExportCancelled):
                ntfs_export_file(str(src), idx.info, entry, str(target),
                                 cancel=lambda: flag['stop'], byte_progress=progress)
            self.assertFalse(target.exists())
            self.assertEqual(src.read_bytes(), image_with_folders())

            fat_source = Path(td) / 'fat.raw'
            fat_source.write_bytes(fat_img())
            other_idx = scan_tree(str(fat_source))
            other_entry = next(x for x in other_idx.list_dir(5) if x.name == 'README.TXT')
            flag['stop'] = False
            with self.assertRaises(ExportCancelled):
                generic_export_file(str(fat_source), other_idx, other_entry, str(target),
                                    cancel=lambda: flag['stop'], byte_progress=progress)
            self.assertFalse(target.exists())

    def test_export_reports_bytes_and_cancelled_state(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / 'ntfs.raw'; src.write_bytes(image_with_folders())
            idx = scan_ntfs_tree(str(src))
            folder = next(x for x in idx.list_dir(5) if x.name == 'Dokumente')
            out = Path(td) / 'out'; out.mkdir()
            chunks = []
            report = ntfs_export_selection(str(src), idx, [folder], str(out), byte_progress=chunks.append)
            self.assertEqual(report.exported, 3)
            self.assertEqual(report.bytes_written, 5 + 7 + len(b'NOT-A-JPEG'))
            self.assertEqual(sum(chunks), report.bytes_written)
            self.assertFalse(report.cancelled)

            fat_source = Path(td) / 'fat.raw'; fat_source.write_bytes(fat_img())
            other_idx = scan_tree(str(fat_source))
            item = next(e for e in other_idx.list_dir(5) if e.name == 'README.TXT')
            out2 = Path(td)/'out2'; out2.mkdir()
            g_report = generic_export_selection(str(fat_source), other_idx, [item], str(out2))
            self.assertEqual(g_report.bytes_written, 5)
            self.assertEqual((out2/'README.TXT').read_bytes(), b'HELLO')

    def test_cancel_during_file_marks_report_and_deletes_target(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td)/'fat.raw'; src.write_bytes(fat_img())
            idx = scan_tree(str(src))
            entry = next(e for e in idx.list_dir(5) if e.name == 'README.TXT')
            out = Path(td)/'out'; out.mkdir()
            flag = {'value':False}
            report = generic_export_selection(str(src), idx, [entry], str(out),
                cancel=lambda:flag['value'], byte_progress=lambda amount:flag.__setitem__('value',True))
            self.assertTrue(report.cancelled)
            self.assertEqual(report.exported,0)
            self.assertFalse((out/'README.TXT').exists())

if __name__ == '__main__': unittest.main()

class LargeImageTests(unittest.TestCase):
    def test_large_nonresident_ntfs_export_is_streamed(self):
        from recoverydesk.ntfs import DataRun, parse_boot_sector
        import math, struct, hashlib
        with tempfile.TemporaryDirectory() as td:
            src = Path(td)/'large.raw'
            dst = Path(td)/'rescued.bin'
            size = 3*1024*1024 + 123
            payload = (b'0123456789abcdef' * ((size + 15)//16))[:size]
            sectors = math.ceil((24*512+size)/512)+100
            boot = bytearray(512)
            boot[3:11] = b'NTFS    '
            struct.pack_into('<H', boot, 11, 512)
            boot[13] = 1
            struct.pack_into('<Q', boot, 40, sectors)
            struct.pack_into('<Q', boot, 48, 4)
            struct.pack_into('<b', boot, 64, -10)
            boot[510:512] = b'\x55\xaa'
            with open(src, 'wb') as f:
                f.truncate(sectors*512)
                f.seek(0); f.write(boot)
                f.seek(24*512); f.write(payload)
            with open(src, 'rb') as f:
                info = parse_boot_sector(f)
            entry = FileEntry(23,1,'large.bin',5,1,False,False, size=size,
                              data_kind='nonresident', initialized_size=size,
                              data_runs=[DataRun(24, math.ceil(size/512))])
            progress = []
            count = ntfs_export_file(str(src),info,entry,str(dst),byte_progress=progress.append)
            self.assertEqual(count,size)
            self.assertEqual(sum(progress),size)
            self.assertGreater(len(progress),1)
            self.assertEqual(hashlib.sha256(dst.read_bytes()).digest(),hashlib.sha256(payload).digest())
            with self.assertRaises(FileExistsError):
                ntfs_export_file(str(src),info,entry,str(dst))
            self.assertEqual(dst.read_bytes(),payload)

    def test_gui_quality_column_and_two_tab_layout(self):
        from recoverydesk.gui import RecoveryDeskApp
        app = RecoveryDeskApp()
        app.withdraw()
        try:
            self.assertEqual(app.tabs.tabs().__len__(), 3)
            self.assertIn('quality', app.file_tree['columns'])
            self.assertEqual(app.file_tree.heading('quality')['text'], 'Rettbarkeit')
        finally:
            app.destroy()

class ErrorCleanupTests(unittest.TestCase):
    def test_generic_midstream_failure_removes_partial_file(self):
        from recoverydesk.filesystems import FileSystemError
        with tempfile.TemporaryDirectory() as td:
            src = Path(td)/'fat.raw'; src.write_bytes(fat_img())
            idx = scan_tree(str(src))
            file_entry = next(e for e in idx.list_dir(5) if e.name=='README.TXT')
            original_iter = idx.volumes.iter_file
            def broken(f, entry, max_bytes=None):
                yield b'AB'
                raise FileSystemError('Simulierter Lesefehler')
            idx.volumes.iter_file = broken
            dest = Path(td)/'broken.txt'
            try:
                with self.assertRaises(FileSystemError):
                    generic_export_file(str(src),idx,file_entry,str(dest))
                self.assertFalse(dest.exists())
            finally:
                idx.volumes.iter_file = original_iter
