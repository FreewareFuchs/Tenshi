"""Destination metadata, FAT limits and no-write review boundaries."""
import ctypes
import os
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock

from recoverydesk.export_target import (assess_target, _mount_filesystem,
    _windows_filesystem, FAT_MAX_FILE, TargetReviewDeclined)
from recoverydesk.batch_export import export_batch
from recoverydesk.device_identity import DeviceSourceChanged
from recoverydesk.i18n import LANGUAGES
import test_batch_export


def task(path, size, *, directory=False, recoverable=True):
    return NS(path=path,is_directory=directory,entry=NS(size=size,recoverable=recoverable))


class TargetAssessmentTests(unittest.TestCase):
    def assess(self, plan, *, fs='NTFS', free=100, existing=frozenset()):
        with patch('recoverydesk.export_target.destination_filesystem',return_value=fs), \
             patch('recoverydesk.export_target.shutil.disk_usage',return_value=NS(free=free)):
            return assess_target('target',plan,existing)

    def test_content_estimate_excludes_directories_and_nonexportable_files(self):
        r=self.assess([task('folder',999,directory=True),task('old',60),task('new',80),
                       task('unavailable',1000,recoverable=False)],existing={'old'})
        self.assertEqual((r.total_bytes,r.required_bytes,r.existing_files),(140,80,1))
        self.assertFalse(r.insufficient)
        self.assertTrue(self.assess([task('x',101)]).insufficient)

    def test_fat_limit_exact_boundary_and_exfat_large_file(self):
        for fs in ('FAT32','fat','vfat','msdos'):
            r=self.assess([task('fits',FAT_MAX_FILE),task('too large',FAT_MAX_FILE+1)],fs=fs,free=2**50)
            self.assertEqual(r.oversized_count,1);self.assertEqual(r.oversized_paths,('too large',))
        self.assertEqual(self.assess([task('large',2**40)],fs='exFAT').oversized_count,0)

    def test_many_large_files_have_bounded_examples(self):
        r=self.assess([task(str(n),2**32) for n in range(50)],fs='FAT32')
        self.assertEqual(r.oversized_count,50);self.assertEqual(len(r.oversized_paths),3)

    def test_failed_queries_are_unknown_not_zero_or_guessed_fat(self):
        with patch('recoverydesk.export_target.destination_filesystem',side_effect=OSError), \
             patch('recoverydesk.export_target.shutil.disk_usage',side_effect=OSError):
            r=assess_target('share',[task('big',2**40)])
        self.assertIsNone(r.free_bytes);self.assertIsNone(r.filesystem)
        self.assertFalse(r.insufficient);self.assertEqual(r.oversized_count,0)

    def test_all_six_languages_and_paths_are_preserved(self):
        r=self.assess([task('Fremde Datei/Window NTFS.img',2**32)],fs='FAT32',free=1)
        for language in LANGUAGES:
            text=r.text(language)
            self.assertIn('Fremde Datei/Window NTFS.img',text)
            self.assertNotIn('{size}',text)
            self.assertNotIn('{count}',text)
            if language!='de':self.assertNotIn('Der verfügbare Platz',text)
        shared=self.assess([],fs='vboxsf').text('en')
        self.assertIn('unknown',shared)

    def test_linux_mount_namespace_escapes_boundaries_and_device(self):
        text=('1 0 8:1 / / rw - ext4 /dev/a rw\n'
              '2 1 8:2 / /media/FAT\\040USB rw - vfat /dev/b rw\n'
              '3 1 0:9 / /media/share rw - vboxsf output rw\n')
        self.assertEqual(_mount_filesystem('/media/FAT USB/exports',(8,2),text),'vfat')
        self.assertEqual(_mount_filesystem('/media/share/exports',(0,9),text),'vboxsf')
        self.assertIsNone(_mount_filesystem('/media/FAT USB-other',(8,2),text))
        self.assertEqual(_mount_filesystem('/media/FAT USB/exports',(8,1),text),'ext4')
        self.assertIsNone(_mount_filesystem('/media/FAT USB',(8,2),text+'4 1 8:2 / /media/FAT\\040USB rw - ext4 /dev/b rw\n'))

    def test_windows_folder_mount_is_queried_instead_of_drive_letter(self):
        kernel=MagicMock()
        def root(path,buffer,length):
            self.assertEqual(path,r'C:\mounted\exports');buffer.value='C:\\mounted\\';return 1
        def info(root,*args):
            self.assertEqual(root,'C:\\mounted\\');args[-2].value='FAT32';return 1
        kernel.GetVolumePathNameW.side_effect=root
        kernel.GetVolumeInformationW.side_effect=info
        with patch.object(ctypes,'WinDLL',return_value=kernel,create=True):
            self.assertEqual(_windows_filesystem(r'C:\mounted\exports'),'FAT32')


class TargetBoundaryTests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        source,index,parent,target=test_batch_export.BatchExportTests().fixture(Path(temp.name))
        entry=next(e for e in index.list_dir(parent.record_number) if e.name=='bericht.txt')
        return source,index,entry,target

    def test_declining_review_changes_no_files_and_calls_no_exporter(self):
        src,index,entry,target=self.fixture();original=src.read_bytes()
        def decline(report):
            self.assertEqual(list(target.iterdir()),[])
            self.assertEqual(report.required_bytes,entry.size)
            return False
        with patch('recoverydesk.batch_export.export_ntfs_file') as writer:
            with self.assertRaises(TargetReviewDeclined):
                export_batch(str(src),index,[entry],str(target),target_review=decline)
        writer.assert_not_called();self.assertEqual(list(target.iterdir()),[])
        self.assertEqual(src.read_bytes(),original)

    def test_known_fat_overflow_and_insufficient_space_stop_before_target_changes(self):
        for fat in (True,False):
            src,index,entry,target=self.fixture()
            if fat:entry.size=FAT_MAX_FILE+1
            with patch('recoverydesk.export_target.destination_filesystem',return_value='FAT32' if fat else 'NTFS'), \
                 patch('recoverydesk.export_target.shutil.disk_usage',return_value=NS(free=2**50 if fat else 0)):
                with self.assertRaises(ValueError):export_batch(str(src),index,[entry],str(target))
            self.assertEqual(list(target.iterdir()),[])

    def test_explicit_space_override_keeps_existing_copy_and_hash_checks(self):
        src,index,entry,target=self.fixture();reports=[]
        def accept(r):reports.append(r);return True
        with patch('recoverydesk.export_target.shutil.disk_usage',return_value=NS(free=0)):
            result=export_batch(str(src),index,[entry],str(target),target_review=accept)
        self.assertTrue(reports[0].insufficient);self.assertEqual(result.exported,1)
        self.assertEqual(result.failed,0)

    def test_full_resume_requires_no_new_content_bytes_but_hashes_again(self):
        src,index,entry,target=self.fixture()
        first=export_batch(str(src),index,[entry],str(target))
        output=Path(first.root)/'files/bericht.txt'
        output.write_bytes(b'WRONG')  # Same size, so capacity credit must not trust contents.
        reports=[]
        with patch('recoverydesk.export_target.shutil.disk_usage',return_value=NS(free=0)):
            result=export_batch(str(src),index,[entry],str(target),target_review=lambda r:reports.append(r) or True)
        self.assertEqual(reports[0].required_bytes,0);self.assertEqual(reports[0].existing_files,1)
        self.assertEqual(result.verified_existing,0);self.assertEqual(result.failed,1)
        self.assertEqual(output.read_bytes(),b'WRONG')

    def test_source_change_during_review_is_rejected_before_writing(self):
        src,index,entry,target=self.fixture()
        def changed(r):
            stamp=src.stat();os.utime(src,ns=(stamp.st_atime_ns,stamp.st_mtime_ns+1000000000))
            return True
        with self.assertRaises(DeviceSourceChanged):
            export_batch(str(src),index,[entry],str(target),target_review=changed)
        self.assertEqual(list(target.iterdir()),[])

    def test_resume_decline_preserves_checkpoint_and_completed_files(self):
        src,index,entry,target=self.fixture()
        first=export_batch(str(src),index,[entry],str(target))
        before={p.relative_to(first.root):p.read_bytes() for p in Path(first.root).rglob('*') if p.is_file()}
        with self.assertRaises(TargetReviewDeclined):
            export_batch(str(src),index,[entry],str(target),expected_root=first.root,target_review=lambda r:False)
        self.assertEqual(before,{p.relative_to(first.root):p.read_bytes() for p in Path(first.root).rglob('*') if p.is_file()})


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Display required')
class TargetGuiTests(unittest.TestCase):
    import test_export_pause as pause_tests
    setUp=pause_tests.ExportPauseGuiTests.setUp
    stop_worker=pause_tests.ExportPauseGuiTests.stop_worker
    pump=pause_tests.ExportPauseGuiTests.pump
    start_paused=pause_tests.ExportPauseGuiTests.start_paused

    def prepare(self):
        src,index,entry,target=TargetBoundaryTests.fixture(self)
        self.app.browser_source=str(src);self.app.browser_index=index
        real_thread=threading.Thread
        def thread(*args,**kwargs):
            worker=real_thread(*args,**kwargs);self.threads.append(worker);return worker
        for context in (patch.object(self.app,'_selected_browser_entries',return_value=[entry]),
                        patch('recoverydesk.gui.filedialog.askdirectory',return_value=str(target)),
                        patch('recoverydesk.gui.threading.Thread',side_effect=thread)):
            self.stack.enter_context(context)
        return src,entry,target

    def test_decline_is_on_ui_thread_and_never_creates_an_export(self):
        src,entry,target=self.prepare();ui_thread=threading.get_ident();before=src.read_bytes()
        def decline(title,text,**kwargs):
            self.assertEqual(threading.get_ident(),ui_thread)
            self.assertIn('Aktuell verfügbar:',text)
            self.assertEqual(list(target.iterdir()),[])
            return False
        with patch('recoverydesk.gui.messagebox.askyesno',side_effect=decline) as confirm, \
             patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.export_browser_selection();self.pump(lambda:not self.app.export_running)
        confirm.assert_called_once();error.assert_not_called()
        self.assertEqual(list(target.iterdir()),[]);self.assertIsNone(self.app.export_result)
        self.assertFalse(self.app._export_target_reviewing)
        self.assertEqual(src.read_bytes(),before)

    def test_fat_limit_has_one_translated_error_and_no_copy_confirmation(self):
        src,entry,target=self.prepare();entry.size=2**32
        self.app.change_language('en')
        with patch('recoverydesk.export_target.destination_filesystem',return_value='FAT32'), \
             patch('recoverydesk.gui.messagebox.askyesno') as confirm, \
             patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.export_browser_selection();self.pump(lambda:not self.app.export_running)
        confirm.assert_not_called();error.assert_called_once()
        self.assertIn('files exceed',error.call_args.args[1])
        self.assertEqual(list(target.iterdir()),[])

    def test_cancel_and_close_during_metadata_query_release_worker_without_writes(self):
        for closing in (False,True):
            src,entry,target=self.prepare();entered=threading.Event()
            self.release.clear()
            def metadata(path):entered.set();self.release.wait(5);return 'NTFS'
            with patch('recoverydesk.export_target.destination_filesystem',side_effect=metadata), \
                 patch('recoverydesk.gui.messagebox.askyesno',return_value=True) as confirm, \
                 patch('recoverydesk.gui.messagebox.showerror') as error:
                self.app.export_browser_selection();self.pump(entered.is_set)
                self.app._export_progress_window.refresh_display()
                self.assertEqual(str(self.app._export_progress_window.pause_button.cget('state')),'disabled')
                if closing:self.app._request_close()
                else:self.app._cancel_export()
                self.release.set()
                self.pump(lambda:self.app._closing if closing else not self.app.export_running)
            self.assertEqual(confirm.call_count,1 if closing else 0)
            error.assert_not_called();self.assertEqual(list(target.iterdir()),[])

    def test_declining_space_warning_keeps_cancelled_job_resumable(self):
        output,expected=self.start_paused();app=self.app
        app._export_progress_window.cancel_button.invoke();self.pump(lambda:not app.export_running)
        previous=app.export_result
        checkpoint=Path(previous.manifest).read_bytes()
        with patch('recoverydesk.export_target.shutil.disk_usage',return_value=NS(free=0)), \
             patch('recoverydesk.gui.messagebox.askyesno',return_value=False) as confirm:
            app._export_progress_window.pause_button.invoke();self.pump(lambda:not app.export_running)
        confirm.assert_called_once()
        self.assertEqual(confirm.call_args.kwargs['default'],'no')
        self.assertIs(app.export_result,previous);self.assertTrue(app._can_resume_export())
        self.assertEqual(Path(previous.manifest).read_bytes(),checkpoint)
        app._export_progress_window.pause_button.invoke();self.pump(lambda:not app.export_running)
        self.assertEqual(output.read_bytes(),expected);self.assertEqual(app.export_result.failed,0)
