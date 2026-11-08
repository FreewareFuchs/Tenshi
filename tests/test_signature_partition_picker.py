"""Partition choices use the current read-only report, never a stale offset."""
import os
import unittest
from unittest.mock import patch

import test_preview_worker_gui as preview_tests
from test_signature_free_fat32 import make_fat32
from test_signature_search import picture
from recoverydesk.partition_scan import analyze_image
from recoverydesk.session_store import fingerprint_image
from recoverydesk.i18n import LANGUAGES,translate


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'GUI required')
class SignaturePartitionPickerTests(unittest.TestCase):
    setUp=preview_tests.PreviewWorkerGuiTests.setUp
    wait_for=preview_tests.PreviewWorkerGuiTests.wait_for

    def publish_report(self):
        self.source.unlink()
        volume=make_fat32(self.source,offset=4096)
        with self.source.open('r+b') as stream:
            stream.seek(volume.cluster_offset(10));stream.write(picture('PNG'))
        source=str(self.source)
        self.app.source_path.set(source)
        self.app.partition_source=source
        report=analyze_image(source)
        self.app._show_partitions(report,generation=self.app._source_generation,
            source=source,fingerprint=fingerprint_image(source))
        return report

    def choose(self,position):
        self.app.signature_partition_combo.current(position)
        self.app._choose_signature_partition()

    def test_selected_fat32_candidate_scans_correct_partition_without_leaving_tab(self):
        self.publish_report();self.app._select_main_tab('signatures')
        self.assertEqual(len(self.app.signature_partition_combo.cget('values')),3)
        self.choose(2)
        self.assertTrue(self.app.signature_free_only.get())
        self.assertEqual(self.app.signature_free_filesystem.get(),'FAT32')
        self.assertEqual(self.app.signature_partition_offset.get(),'4096')
        self.assertEqual(self.app.tabs.select(),str(self.app.signature_tab))
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True) as confirm, \
             patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_signature_scan();self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertIn('4096',confirm.call_args.args[1])
        self.assertEqual(len(self.app.signature_result_index.entries),1)
        self.assertEqual(self.app.signature_summary.area,'fat32-free')
        self.assertEqual(self.app.signature_summary.offset,4096)

    def test_manual_edits_and_entire_image_are_explicit_modes(self):
        self.publish_report();self.choose(2)
        self.app.signature_partition_offset.set('8192')
        self.assertEqual(self.app.signature_partition_combo.current(),1)
        self.assertIsNone(self.app._signature_chosen_partition)
        self.choose(0)
        self.assertFalse(self.app.signature_free_only.get())
        self.assertEqual(self.app.signature_partition_offset.get(),'0')
        self.assertEqual(str(self.app.signature_offset_entry.cget('state')),'disabled')
        self.choose(1)
        self.assertTrue(self.app.signature_free_only.get())
        self.assertEqual(str(self.app.signature_offset_entry.cget('state')),'normal')

    def test_stale_generation_cannot_apply_a_partition(self):
        self.publish_report();self.app._source_generation+=1
        with patch('recoverydesk.gui.messagebox.showerror') as error:
            self.choose(2)
        error.assert_called_once()
        self.assertFalse(self.app.signature_free_only.get())
        self.assertEqual(len(self.app.signature_partition_combo.cget('values')),2)

    def test_changed_image_is_rejected_before_the_signature_parser_reads_it(self):
        self.publish_report();self.choose(2)
        with self.source.open('r+b') as stream:stream.write(b'changed')
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True), \
             patch('recoverydesk.signature_search.scan_signatures') as scan, \
             patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_signature_scan();self.wait_for(lambda:not self.app.ntfs_scanning)
        scan.assert_not_called();error.assert_called_once()
        self.assertEqual(self.app.signature_summary.state,'failed')

    def test_report_without_fingerprint_does_not_offer_automatic_offsets(self):
        report=self.publish_report()
        self.app._show_partitions(report,source=str(self.source),fingerprint=None)
        self.assertEqual(len(self.app.signature_partition_combo.cget('values')),2)
        self.assertIsNone(self.app._signature_chosen_partition)

    def test_unsupported_filesystem_is_not_offered_as_free_space(self):
        report=self.publish_report()
        report.partitions[0].filesystem='ext4'
        self.app._refresh_signature_partitions()
        self.assertEqual(len(self.app.signature_partition_combo.cget('values')),2)
        self.assertFalse(self.app.signature_free_only.get())

    def test_changed_partition_metadata_does_not_silently_reuse_old_offset(self):
        self.publish_report();self.choose(2)
        self.app._signature_chosen_partition.start_lba+=8
        with patch('recoverydesk.gui.messagebox.askyesno') as confirm, \
             patch('recoverydesk.signature_search.scan_signatures') as scan, \
             patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_signature_scan()
        scan.assert_not_called();confirm.assert_not_called();error.assert_called_once()

    def test_language_and_source_reset_do_not_reuse_an_old_partition(self):
        self.publish_report();self.choose(2)
        chosen=self.app._signature_chosen_partition
        self.app.deiconify();self.app.geometry('1024x650')
        self.app._select_main_tab('signatures')
        for language in LANGUAGES:
            self.app.change_language(language);self.app.update()
            self.assertIs(self.app._signature_chosen_partition,chosen)
            self.assertEqual(self.app.signature_partition_combo.current(),2)
            values=self.app.signature_partition_combo.cget('values')
            self.assertEqual(values[0],translate('Gesamtes Image',language))
            self.assertEqual(values[1],translate('Manuell: freie Bereiche',language))
            right=self.app.signature_tab.winfo_rootx()+self.app.signature_tab.winfo_width()
            entry=self.app.signature_offset_entry
            self.assertLessEqual(entry.winfo_rootx()+entry.winfo_width(),right)
        self.app._reset_analysis_for_source()
        self.assertEqual(len(self.app.signature_partition_combo.cget('values')),2)
        self.assertFalse(self.app.signature_free_only.get())
        self.assertEqual(self.app.signature_partition_offset.get(),'0')
