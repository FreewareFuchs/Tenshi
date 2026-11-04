"""Binary Office content checks remain partial, isolated and read-only."""
from io import BytesIO
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.content_check import analyze, check_file, check_path
from recoverydesk.content_worker import inspect, content_kind
from recoverydesk.content_smoke import binary_office_fixture, office_fixture
from recoverydesk.signature_cfb import _Compound, MAGIC
from recoverydesk.signature_formats import Limit
from recoverydesk.filesystems import scan_tree
from test_content_check import file_image

FIXTURES = Path(__file__).parent / 'fixtures' / 'office_cfb'


class BinaryOfficeContentTests(unittest.TestCase):
    def test_independent_doc_xls_ppt_are_partial_and_have_no_rendered_content(self):
        for name, kind in [('simple.doc', 'DOC'), ('Simple.xls', 'XLS'), ('basic_test_ppt_file.ppt', 'PPT')]:
            for preview in (False, True):
                with self.subTest(name=name, preview=preview):
                    data = (FIXTURES / name).read_bytes()
                    answer = analyze(data, name, preview=preview)
                    self.assertEqual((answer['status'], answer['format'], answer['code']),
                                     ('partial', kind, 'office_binary_structure'))
                    self.assertEqual((answer['image'], answer['text']), ('', ''))

    def test_magic_identifies_actual_type_without_trusting_filename(self):
        data = (FIXTURES / 'simple.doc').read_bytes()
        for name in ('no-extension', 'renamed.bin', 'wrong.xls', 'wrong.docx'):
            with self.subTest(name=name):
                self.assertEqual(content_kind(data, Path(name).suffix), 'office')
                self.assertEqual(analyze(data, name)['format'], 'DOC')

    def test_arbitrary_bytes_with_legacy_extension_never_pass(self):
        for extension in ('.doc', '.xls', '.ppt'):
            self.assertEqual(inspect(b'not an office file', extension)['status'], 'unsupported')

    def test_modern_office_with_legacy_extension_uses_actual_package_type(self):
        answer=analyze(office_fixture('docx'),'renamed.xls')
        self.assertEqual((answer['status'],answer['format'],answer['code']),
                         ('checked','DOCX','office_container'))

    def test_broken_sector_chains_and_truncation_do_not_pass(self):
        data = bytearray(binary_office_fixture())
        struct.pack_into('<I', data, 512+2*4, 2)  # self-loop in workbook chain
        for payload in (bytes(data), binary_office_fixture()[:-1], MAGIC+bytes(100)):
            answer = inspect(payload, '.xls')
            self.assertEqual((answer['status'], answer['code']), ('unreadable', 'office_cfb_unreadable'))

    def test_unknown_valid_cfb_and_invalid_format_header_are_not_called_corrupt(self):
        data = bytearray(binary_office_fixture())
        # Structurally valid container with an unrelated stream name.
        encoded = ('OtherData\0').encode('utf-16le')
        data[1152:1152+64] = bytes(64)
        data[1152:1152+len(encoded)] = encoded
        struct.pack_into('<H', data, 1152+64, len(encoded))
        answer = inspect(bytes(data), '.xls')
        self.assertEqual((answer['status'], answer['code']), ('unsupported', 'office_ole'))
        data = bytearray(binary_office_fixture());data[1536:1556] = bytes(20)
        self.assertEqual(inspect(bytes(data), '.xls')['status'], 'unsupported')

    def test_protected_modern_office_fallback_remains_not_checked(self):
        answer = analyze(MAGIC+bytes(100), 'protected.docx')
        self.assertEqual((answer['status'], answer['code']), ('unsupported', 'office_ole'))

    def test_structure_budget_limit_is_distinct_from_unreadable(self):
        with patch('recoverydesk.signature_cfb._Compound', side_effect=Limit):
            self.assertEqual(inspect(binary_office_fixture(), '.xls')['status'], 'limited')
        with patch.object(_Compound, 'classify', side_effect=Limit):
            self.assertEqual(inspect(binary_office_fixture(), '.xls')['status'], 'limited')

    def test_source_file_and_exported_file_checks_do_not_modify_inputs(self):
        data = (FIXTURES / 'Simple.xls').read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.img';original = file_image(data, 'LEGACY  XLS')
            source.write_bytes(original);index = scan_tree(str(source))
            entry = next(e for e in index.entries if e.name == 'LEGACY.XLS')
            self.assertEqual(check_file(str(source), index, entry, 'FAT32')['status'], 'partial')
            self.assertEqual(source.read_bytes(), original)
            output = Path(folder) / 'export.xls';output.write_bytes(data);before = output.stat()
            self.assertEqual(check_path(output)['status'], 'partial')
            self.assertEqual(output.read_bytes(), data)
            self.assertEqual(output.stat().st_mtime_ns, before.st_mtime_ns)
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ['export.xls', 'source.img'])

    def test_packaging_probe_is_only_a_partial_structure_check(self):
        answer = analyze(binary_office_fixture(), 'sample.xls', preview=True)
        self.assertEqual((answer['status'], answer['format']), ('partial', 'XLS'))
        self.assertFalse(answer['image']);self.assertFalse(answer['text'])


if __name__ == '__main__':
    unittest.main()
