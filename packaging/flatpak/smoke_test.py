"""Run inside the installed Flatpak; only disposable regular-file fixtures."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch

# Test the installed package, never a copy from the host checkout.
sys.path.insert(0, '/app/share/tenshi')
import recoverydesk
from recoverydesk.filesystems import scan_tree, export_selection
from recoverydesk.imaging import create_image
from recoverydesk.version_info import build_info


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_installed_gui() -> None:
    from recoverydesk import gui
    from recoverydesk.i18n import LANGUAGES

    assert Path(gui.__file__).is_relative_to('/app/share/tenshi')

    class ProbeApp(gui.RecoveryDeskApp):
        def __init__(self):
            self.callback_errors = []
            super().__init__()

        def report_callback_exception(self, exc_type, exc, tb):
            # Fail the probe instead of blocking CI on a modal error dialog.
            self.callback_errors.append((exc_type.__name__, str(exc)))

    with tempfile.TemporaryDirectory(prefix='tenshi-flatpak-gui-') as temporary:
        root = Path(temporary)
        with patch.dict(os.environ, {
                'TENSHI_SETTINGS_FILE': str(root / 'settings.json'),
                'TENSHI_LOG_DIR': str(root / 'logs')}), \
                patch.object(gui, 'list_physical_sources',
                             side_effect=AssertionError('Unexpected device enumeration')), \
                patch.object(gui, 'list_volumes',
                             side_effect=AssertionError('Unexpected volume enumeration')):
            app = ProbeApp()
            try:
                app.geometry('1280x900+0+0')
                app.update()
                assert app.brand_logo.width() > 0
                assert app.source_path.get() == '', 'Probe must not select a source'
                from tkinter import ttk
                for theme in ('dark', 'light', 'system'):
                    app.change_theme(theme)
                    app.update()
                    style = ttk.Style(app)
                    assert style.theme_use() == 'sun-valley-' + app.theme
                    from recoverydesk.appearance import palette
                    colors = palette(app.theme)
                    for name in ('TEntry', 'TCombobox'):
                        assert style.lookup(name, 'fieldbackground', ('readonly',)) == colors['input']
                        assert style.lookup(name, 'bordercolor', ('focus',)) == colors['accent']
                    assert style.lookup('Treeview', 'background', ('selected',)) == colors['inactive']
                for language in LANGUAGES:
                    app.change_language(language)
                    app.update()
                    assert app.language == language
                    # Installed destination review uses the UI thread, keeps
                    # paths intact and never needs physical-device enumeration.
                    from recoverydesk.export_target import TargetAssessment
                    import threading
                    assessment = TargetAssessment(str(root/'日本語'),100,100,0,200,'ext4',0,())
                    decision = dict(ready=threading.Event(),accepted=False)
                    with patch.object(gui._messagebox,'askyesno',return_value=False) as ask:
                        app._handle_export_event(dict(type='target_review',assessment=assessment,
                                                      decision=decision,resume=False))
                    assert decision['ready'].is_set() and not decision['accepted']
                    assert str(root/'日本語') in ask.call_args.args[1]
                    # Installed Tk 9: a view-only event projection, no source I/O.
                    app.export_running = True
                    app._handle_export_event(dict(type='plan',total=1,total_bytes=100,items=[]))
                    app._handle_export_event(dict(type='start',path='fixture.bin',size=100))
                    app._handle_export_event(dict(type='bytes',path='fixture.bin',delta=100))
                    app._handle_export_event(dict(type='verify',path='fixture.bin',read=100,size=100))
                    progress = app._show_export_progress()
                    progress.geometry('620x550+0+0')
                    app.update(); progress.refresh_display(); app.update_idletasks()
                    assert len(progress.grid_view.find_all()) == 200
                    assert progress.grid_view.winfo_height() > 60
                    assert app.export_blocks.confirmed_fraction == 0
                    from recoverydesk.i18n import translate
                    assert progress.labels['verification'].cget('text') == translate('SHA256-Prüfung der Zieldatei läuft …',language)
                    assert '%' not in progress.labels['verification'].cget('text')
                    assert app.grab_current() is None
                    progress.pause_button.invoke()
                    app._handle_export_event(dict(type='paused'));progress.refresh_display()
                    assert progress.pause_button.cget('text')==translate('Fortsetzen',language)
                    assert progress.labels['phase'].cget('text')==translate('Export pausiert.',language)
                    assert app.export_progress.written_bytes==100
                    progress.pause_button.invoke();app._handle_export_event(dict(type='resumed'))
                    assert not app.export_progress.paused and not app.export_cancel.is_set()
                    progress.destroy()
                    assert app.export_running and not app.export_cancel.is_set()
                    progress = app._show_export_progress()
                    app._handle_export_event(dict(type='done',path='fixture.bin',size=100,status='Erfolgreich'))
                    assert app.export_blocks.confirmed_fraction == 1
                    progress.destroy()
                    app.export_running = False
                    from recoverydesk.imaging_window import ImagingProgressWindow
                    from recoverydesk.imaging_blocks import ImagingBlocks
                    from recoverydesk.imaging import ImagingProgress
                    import threading,time
                    blocks=ImagingBlocks()
                    blocks.handle(ImagingProgress(50,100,1,1,'running',((23,1),)))
                    session=dict(blocks=blocks,running=True,state='running',stop=threading.Event(),
                        started=time.monotonic(),ended=None,baseline=0,report=None,saving=False,error='',destination='')
                    image_view=ImagingProgressWindow(app,session,pause=session['stop'].set,
                        report=lambda:None,save=lambda:None,folder=lambda:None,settings=lambda:None)
                    image_view.geometry('660x590+0+0')
                    app.update();image_view.refresh_display();app.update_idletasks()
                    assert len(image_view.grid_view.find_all())==200
                    assert blocks.cell_states().count('error')==1
                    for button in image_view.buttons.values():
                        assert button.winfo_ismapped(),language
                        assert button.winfo_width()>=button.winfo_reqwidth(),language
                        assert button.winfo_rooty()+button.winfo_height()<=image_view.winfo_rooty()+image_view.winfo_height(),language
                    image_view.destroy()
                    assert session['running'] and not session['stop'].is_set()
                    from recoverydesk.source_catalog import SourceChoice
                    with patch.object(gui, 'open_source', side_effect=AssertionError('Unconfirmed device read')):
                        picker = app._show_source_dialog([
                            SourceChoice('/dev/testdisk', '/dev/testdisk', 'disk', 16384),
                            SourceChoice('/dev/testdisk1', '/dev/testdisk1', 'volume', 8192,
                                         filesystem='FAT32', parent='/dev/testdisk')])
                        app.update()
                        assert not picker.source_tree.selection()
                        assert str(picker.confirm_button.cget('state')) == 'disabled'
                        assert picker.source_tree.parent('/dev/testdisk1') == '/dev/testdisk'
                        picker.source_tree.selection_set('/dev/testdisk1')
                        app.update()
                        assert str(picker.confirm_button.cget('state')) == 'normal'
                        picker.destroy()
                    for tab in ('partition', 'files'):
                        app._select_main_tab(tab)
                        app.update()
                        assert app.tabs.winfo_height() >= 100, (language, tab)
                    assert app.file_tree.winfo_ismapped(), language
                    assert app.file_tree.winfo_height() >= 70, language
                    assert app.export_button.winfo_ismapped(), language
                    app.geometry('1024x650+0+0')
                    app.status.set('MFT: 123,456 / 987,654 Datensätze geprüft …')
                    app.update()
                    assert app.status_label.winfo_ismapped(), language
                    assert app.status_label.winfo_height() >= app.status_label.winfo_reqheight(), language
                    assert app.status_label.winfo_rooty()+app.status_label.winfo_height() <= app.winfo_rooty()+app.winfo_height(), language
                    assert 'export_queue_tree' not in app.__dict__
                    assert 'export_queue_bar' not in app.__dict__
                    assert app.export_progress_button.winfo_ismapped(),language
                    assert app.export_preflight_button.winfo_ismapped(),language
                    app.export_progress_button.invoke()
                    app.update()
                    app._export_progress_window.destroy()
                    assert app.status_label.winfo_ismapped(),language
                    assert app.file_tree.winfo_height()>=70,language
                    app.geometry('1280x900+0+0')
                assert app.callback_errors == [], app.callback_errors
                assert app.source_path.get() == ''
            finally:
                app.destroy()
    print('Installed Flatpak GUI: six languages, main tabs, export and imaging progress passed.')


def main() -> None:
    assert Path(recoverydesk.__file__).is_relative_to('/app/share/tenshi')
    assert not build_info().released
    assert build_info().commit
    check_installed_gui()
    # Validate the lsblk interface without reading any raw device contents.
    subprocess.run(['lsblk', '--version'], check=True)
    image = Path(sys.argv[1])
    expected = json.loads(Path(sys.argv[2]).read_text())
    assert image.is_file() and not image.is_symlink()
    before = digest(image)
    index = scan_tree(str(image))
    assert index.filesystem == 'FAT32'
    entries = index.list_dir(index.root)
    with tempfile.TemporaryDirectory(prefix='tenshi-flatpak-check-') as temporary:
        output = Path(temporary) / 'export'
        output.mkdir()
        result = export_selection(str(image), index, entries, str(output))
        assert not result.errors, result.errors
        assert result.exported == len(expected)
        for name, checksum in expected.items():
            assert digest(output / name) == checksum
        from recoverydesk.batch_export import export_batch
        from recoverydesk.export_target import TargetReviewDeclined
        declined=Path(temporary)/'declined';declined.mkdir()
        def decline_target(assessment):
            assert assessment.required_bytes==sum(e.size for e in entries if not e.is_directory and e.recoverable)
            assert not list(declined.iterdir())
            return False
        try:
            export_batch(str(image),index,entries,str(declined),target_review=decline_target)
        except TargetReviewDeclined:
            pass
        else:
            raise AssertionError('Declined destination review started an export')
        assert not list(declined.iterdir())
        batch_output=Path(temporary)/'batch';batch_output.mkdir()
        stop=False
        def interrupt_after_file(event):
            nonlocal stop
            if event['type']=='done' and event['status']=='Erfolgreich':stop=True
        interrupted=export_batch(str(image),index,entries,str(batch_output),
                                 event=interrupt_after_file,cancel=lambda:stop)
        assert interrupted.cancelled and not interrupted.checksum_errors,interrupted
        singles=Path(interrupted.root)/'Pruefsummen_Einzeln'
        assert len(list(singles.glob('*.sha256')))==1
        resumed=export_batch(str(image),index,entries,str(batch_output),expected_root=interrupted.root)
        assert not resumed.failed and not resumed.checksum_errors,resumed
        assert resumed.verified_existing==1 and resumed.exported==len(expected)-1
        assert not list(singles.glob('*.sha256'))
        assert not singles.exists()
        summary=Path(resumed.checksums)
        lines=summary.read_text(encoding='utf-8').splitlines()
        assert len(lines)==len(expected)
        for line in lines:
            checksum,relative=line.split('  ',1)
            assert digest(summary.parent/relative)==checksum
        # A real in-session pause must retain a partially written large file.
        from recoverydesk.export_pause import ExportPause
        import threading
        pause_output=Path(temporary)/'pause-batch';pause_output.mkdir()
        large=next(entry for entry in entries if entry.name=='binary.bin')
        cancelled=threading.Event();paused=threading.Event();finished=threading.Event()
        results=[];failures=[];requested=False
        def pause_event(event):
            if event['type']=='paused':paused.set()
        control=ExportPause(cancelled,pause_event)
        def copied(count):
            nonlocal requested
            if not requested:requested=True;control.request(True)
        def paused_worker():
            try:
                results.append(export_batch(str(image),index,[large],str(pause_output),
                    byte_progress=copied,cancel=control.check_cancel,event=pause_event))
            except Exception as exc:failures.append(exc)
            finally:finished.set()
        worker=threading.Thread(target=paused_worker);worker.start()
        try:
            assert paused.wait(10) and not finished.is_set(),failures
            paused_root=next(pause_output.glob('Tenshi_Export_*'))
            partial=paused_root/'files/binary.bin';meta=partial.stat()
            assert 0<meta.st_size<large.size
            assert not list(paused_root.rglob('*.sha256'))
            control.request(False);assert finished.wait(20),failures
        finally:
            cancelled.set();control.request(False);worker.join(5)
        assert not failures,failures
        resumed_pause=results[0]
        assert not resumed_pause.cancelled and not resumed_pause.checksum_errors,resumed_pause
        assert resumed_pause.exported==1 and digest(partial)==expected['binary.bin']
        assert not (Path(resumed_pause.root)/'Pruefsummen_Einzeln').exists()
        assert partial.stat().st_ino==meta.st_ino
        copy = Path(temporary) / 'copy.img'
        create_image(str(image), str(copy))
        assert digest(copy) == before
    assert digest(image) == before, 'Source image changed'
    print('Installed Flatpak: Tenshi GUI, FAT32 export hashes and imaging hashes passed.')


if __name__ == '__main__':
    main()
