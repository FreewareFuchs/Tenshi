import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from recoverydesk.export_blocks import ExportBlocks, copy_export_report


class BlockProjectionTests(unittest.TestCase):
    def plan(self, size, total=1):
        blocks=ExportBlocks()
        blocks.handle(dict(type='plan',total=total,total_bytes=size,items=[]))
        return blocks

    def assert_conserved(self, blocks):
        self.assertEqual(len(blocks.cells),100)
        for cell in blocks.cells:
            self.assertEqual(sum(cell.values()),blocks.total)
            self.assertTrue(all(value>=0 for value in cell.values()),cell)

    def test_full_copy_and_full_verification_read_are_not_confirmation(self):
        blocks=self.plan(1000)
        blocks.handle(dict(type='start',path='big',size=1000))
        blocks.handle(dict(type='bytes',path='big',delta=250))
        self.assertEqual(blocks.cell_states().count('copied'),25)
        blocks.handle(dict(type='bytes',path='big',delta=750))
        blocks.handle(dict(type='verify',path='big',read=1000,size=1000))
        self.assertEqual(blocks.confirmed_fraction,0)
        self.assertEqual(set(blocks.cell_states()),{'copied'})
        blocks.handle(dict(type='done',path='big',size=1000,status='Erfolgreich'))
        self.assertEqual(blocks.confirmed_fraction,1)
        self.assertEqual(set(blocks.cell_states()),{'confirmed'})
        self.assert_conserved(blocks)

    def test_tiny_error_is_visible_in_mixed_cell_without_hiding_good_bytes(self):
        blocks=self.plan(1000,3)
        for path,size,status in [('ok',9,'Erfolgreich'),('bad',1,'Fehler'),('rest',990,'Übersprungen')]:
            blocks.handle(dict(type='start',path=path,size=size))
            blocks.handle(dict(type='done',path=path,size=size,status=status))
            self.assert_conserved(blocks)
        self.assertEqual(blocks.cell_states()[0],'error')
        self.assertEqual(blocks.cell_states().count('unconfirmed'),99)
        self.assertAlmostEqual(blocks.confirmed_fraction,.009)
        self.assertEqual((blocks.errors,blocks.skipped),(1,1))

    def test_resumed_file_has_confirmation_without_new_copy_bytes(self):
        blocks=self.plan(101)
        blocks.handle(dict(type='start',path='old',size=101))
        blocks.handle(dict(type='verify',path='old',read=101,size=101))
        self.assertEqual(blocks.confirmed_fraction,0)
        blocks.handle(dict(type='done',path='old',size=101,status='Bereits verifiziert'))
        self.assertEqual(blocks.confirmed_fraction,1)
        self.assert_conserved(blocks)

    def test_cancel_and_new_plan_do_not_claim_success_or_keep_old_errors(self):
        blocks=self.plan(100,2)
        blocks.handle(dict(type='start',path='partial',size=50))
        blocks.handle(dict(type='bytes',path='partial',delta=20))
        blocks.handle(dict(type='done',path='partial',size=50,status='Abgebrochen'))
        self.assertEqual(blocks.cell_states().count('unconfirmed'),50)
        self.assertEqual(blocks.cell_states().count('pending'),50)
        self.assertEqual(blocks.confirmed_fraction,0)
        self.assertEqual(blocks.cancelled,1)
        blocks.handle(dict(type='plan',total=1,total_bytes=1))
        self.assertEqual(blocks.cancelled,0)
        self.assertEqual(set(blocks.cell_states()),{'pending'})

    def test_zero_byte_plan_uses_entries_and_empty_plan_stays_empty(self):
        blocks=self.plan(0,3)
        self.assertTrue(blocks.entries)
        for i in range(3):
            blocks.handle(dict(type='start',path=str(i),size=0))
            blocks.handle(dict(type='done',path=str(i),size=0,status='Ordner erstellt'))
        self.assertEqual(blocks.confirmed_fraction,1)
        self.assert_conserved(blocks)
        empty=self.plan(0,0)
        self.assertEqual(empty.confirmed_fraction,0)
        self.assertEqual(set(empty.cell_states()),{'pending'})

    def test_large_sizes_are_exact_and_preview_is_not_required(self):
        total=2**60+3
        blocks=self.plan(total,3)
        for i,size in enumerate((1,total-2,1)):
            blocks.handle(dict(type='start',path=str(i),size=size))
            blocks.handle(dict(type='bytes',path=str(i),delta=size))
            self.assert_conserved(blocks)
            if i == 2:
                self.assertLess(blocks.confirmed_fraction,1)
            blocks.handle(dict(type='done',path=str(i),size=size,status='Erfolgreich'))
            self.assert_conserved(blocks)
        self.assertEqual(blocks.confirmed_fraction,1)


class ReportCopyTests(unittest.TestCase):
    def test_exact_copy_is_exclusive_and_source_guard_runs_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'image';source.write_bytes(b'original image')
            report=root/'report';data=b'Report\r\n'+bytes(range(256))*8193;report.write_bytes(data)
            target=root/'saved'
            copy_export_report(str(source),str(report),str(target))
            self.assertEqual(target.read_bytes(),data)
            with self.assertRaises(FileExistsError):
                copy_export_report(str(source),str(report),str(target))
            with self.assertRaises(ValueError):
                copy_export_report(str(source),str(report),str(source))
            self.assertEqual(source.read_bytes(),b'original image')
            blocked=root/'blocked'
            with patch('recoverydesk.sources.ensure_safe_destination',side_effect=ValueError('same disk')):
                with self.assertRaises(ValueError):
                    copy_export_report(str(source),str(report),str(blocked))
            self.assertFalse(blocked.exists())
            with self.assertRaises(ValueError):
                copy_export_report('',str(report),str(blocked))

