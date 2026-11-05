"""CSV evidence is scoped to visible results and cannot replace source files."""
import csv
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from recoverydesk.signature_report import report_csv,save_csv
from recoverydesk.signature_search import _signature_entry


class SignatureReportTests(unittest.TestCase):
    def test_partial_free_space_report_keeps_view_order_and_exact_integer_positions(self):
        entries=[_signature_entry(2**40+512,4096,'PNG'),_signature_entry(512,8192,'JPEG')]
        index=SimpleNamespace(entries=entries,signature_search_area='exfat-free',
            signature_partition_offset=4096,signature_categories=('images','office'),
            signature_parser_revision=3,signature_file_limit=64*1024**2,signature_complete=False)
        text=report_csv('=source;"ä"\nimage.img',index,list(reversed(entries)))
        rows=list(csv.DictReader(io.StringIO(text),delimiter=';'))
        self.assertEqual([r['type'] for r in rows],['JPEG','PNG'])
        self.assertEqual(rows[1]['absolute_offset_bytes'],str(2**40+512))
        self.assertEqual(rows[0]['source_image'],"'=source;\"ä\"\nimage.img")
        for row in rows:
            self.assertEqual(row['search_area'],'exfat-free')
            self.assertEqual(row['partition_offset_bytes'],'4096')
            self.assertEqual(row['scan_complete'],'false')
            self.assertEqual(row['categories'],'images,office')
            self.assertIn('not an export or integrity report',row['notice'])

    def test_save_is_utf8_with_bom_and_never_overwrites_existing_file_or_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source.img';source.write_bytes(b'original')
            output=Path(folder)/'report.csv'
            save_csv(str(output),'ä;文字\r\n',str(source))
            self.assertTrue(output.read_bytes().startswith(b'\xef\xbb\xbf'))
            self.assertEqual(output.read_text(encoding='utf-8-sig'),'ä;文字\n')
            with self.assertRaises(FileExistsError):save_csv(str(output),'replacement',str(source))
            with self.assertRaises(ValueError):save_csv(str(source),'replacement',str(source))
            self.assertEqual(source.read_bytes(),b'original')
            self.assertEqual(output.read_bytes(),b'\xef\xbb\xbf'+ 'ä;文字\r\n'.encode())
