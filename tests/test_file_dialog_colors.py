import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import MagicMock,patch
from recoverydesk.file_dialog_colors import FileDialogColors
from recoverydesk.gui import RecoveryDeskApp,filedialog


class NativeDialogGuardTests(unittest.TestCase):
    def test_windows_and_macos_install_no_dialog_hooks(self):
        for platform in ('win32','darwin'):
            app=MagicMock()
            with patch('recoverydesk.file_dialog_colors.sys.platform',platform):
                colors=FileDialogColors(app)
                colors.prepare();colors.on_map('.__tk_filedialog');colors.refresh();colors.close()
            app.tk.call.assert_not_called()
            app.register.assert_not_called()
            app.bind_class.assert_not_called()


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Display required')
class CanvasColorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        env=patch.dict(os.environ,{'TENSHI_SETTINGS_FILE':str(self.root/'settings.json'),
                                   'TENSHI_LOG_DIR':str(self.root/'logs')})
        env.start();self.addCleanup(env.stop)
        self.app=RecoveryDeskApp();self.addCleanup(self.app.destroy)

    def test_tcl_owned_text_selection_and_geometry_survive_color_changes(self):
        app=self.app;tcl=app.tk
        tcl.call('toplevel','.palette_test','-class','TkFDialog')
        tcl.call('canvas','.palette_test.canvas','-background','white')
        canvas='.palette_test.canvas'
        normal=tcl.call(canvas,'create','text',10,10,'-text','Image ü.raw','-fill','black')
        selected=tcl.call(canvas,'create','text',10,30,'-text','selected.raw','-fill','black','-tags','selectionText')
        rect=tcl.call(canvas,'create','rectangle',1,20,90,40,'-tags','selection')
        for mode in ('dark','light','dark'):
            app.change_theme(mode);app._file_dialog_colors._paint('.palette_test')
            colors=app._palette()
            self.assertEqual(tcl.call(canvas,'cget','-background'),colors['input'])
            self.assertEqual(tcl.call(canvas,'itemcget',normal,'-fill'),colors['text'])
            self.assertEqual(tcl.call(canvas,'itemcget',selected,'-fill'),colors['selection_text'])
            self.assertEqual(tcl.call(canvas,'itemcget',rect,'-fill'),colors['select'])
            self.assertEqual(tcl.call(canvas,'itemcget',normal,'-text'),'Image ü.raw')
            self.assertEqual(tuple(tcl.call(canvas,'coords',normal)),(10.,10.))

    @unittest.skipUnless(sys.platform.startswith('linux') and os.environ.get('DISPLAY'),'Linux/X11 required')
    def test_real_open_save_and_directory_dialogs_follow_theme_and_keep_paths(self):
        app=self.app;tcl=app.tk;app.change_theme('dark')
        self.assertTrue(app._file_dialog_colors.enabled)
        folder=self.root/'folder';folder.mkdir()
        image=folder/'Image ü 文件.raw';image.write_bytes(b'fixture')
        (self.root/'other.raw').write_bytes(b'other')
        failures=[]
        dialog='.__tk_filedialog'
        var='::tk::dialog::file::__tk_filedialog'
        def data(key):return str(tcl.call('set',var+'('+key+')'))
        def canvas():
            stack=[dialog]
            while stack:
                widget=stack.pop()
                if str(tcl.call('winfo','class',widget))=='Canvas':return widget
                stack.extend(tcl.splitlist(tcl.call('winfo','children',widget)))
            self.fail('No canvas in the standard Tk file dialog')
        def cancel():
            if tcl.call('winfo','exists',dialog):tcl.call('::tk::dialog::file::CancelCmd',dialog)
        def later(callback):
            def guarded():
                try:callback()
                except BaseException as exc:failures.append(exc);cancel()
            app.after(100,guarded)
        def assert_colors():
            c=canvas();palette=app._palette()
            self.assertEqual(tcl.call(c,'cget','-background'),palette['input'],
                (str(tcl.call('bindtags',dialog)),str(tcl.call('winfo','class',dialog)),
                 tuple(app._file_dialog_colors.dialogs),app._file_dialog_colors.traced))
            selected=set(tcl.splitlist(tcl.call(c,'find','withtag','selectionText')))
            texts=[]
            for item in tcl.splitlist(tcl.call(c,'find','all')):
                if tcl.call(c,'type',item)=='text':
                    texts.append(item)
                    expected=palette['selection_text'] if item in selected else palette['text']
                    self.assertEqual(tcl.call(c,'itemcget',item,'-fill'),expected)
            self.assertTrue(texts)
        def open_stage1():
            assert_colors();tcl.call(data('icons'),'selection','set',0);later(open_stage2)
        def open_stage2():
            assert_colors();self.assertTrue(tcl.call(canvas(),'find','withtag','selectionText'))
            tcl.call(data('icons'),'selection','clear',0,'end');later(open_stage3)
        def open_stage3():
            assert_colors();tcl.call('set',var+'(selectPath)',str(folder));later(open_stage4)
        def open_stage4():
            assert_colors();app.change_theme('light');later(open_stage5)
        def choose(name):
            entry=data('ent');tcl.call(entry,'delete',0,'end');tcl.call(entry,'insert',0,name)
            tcl.call(data('okBtn'),'invoke')
        def open_stage5():assert_colors();choose(image.name)
        later(open_stage1)
        result=filedialog.askopenfilename(parent=app,initialdir=str(self.root),filetypes=[('Image','*.raw')])
        if failures:raise failures[0]
        self.assertEqual(result,str(image))
        destination=folder/'Report ü.txt'
        def save_stage1():assert_colors();app.change_theme('dark');later(save_stage2)
        def save_stage2():assert_colors();choose(destination.name)
        later(save_stage1)
        result=filedialog.asksaveasfilename(parent=app,initialdir=str(folder),defaultextension='.txt')
        if failures:raise failures[0]
        self.assertEqual(result,str(destination));self.assertFalse(destination.exists())
        dialog='.__tk_choosedir'
        var='::tk::dialog::file::__tk_choosedir'
        def directory_stage():assert_colors();cancel()
        later(directory_stage)
        result=filedialog.askdirectory(parent=app,initialdir=str(self.root))
        if failures:raise failures[0]
        self.assertFalse(result)
