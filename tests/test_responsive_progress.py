"""Live progress stays visible; resize bursts do bounded UI work."""
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.filesystems import scan_tree
from test_filesystems import fat_img


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Display required')
class ResponsiveProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env = patch.dict(os.environ, {'TENSHI_SETTINGS_FILE':str(self.root/'settings.json'),
                                     'TENSHI_LOG_DIR':str(self.root/'logs')})
        env.start()
        self.addCleanup(env.stop)
        self.app = RecoveryDeskApp()
        self.addCleanup(self.app.destroy)
        self.app.change_theme('light')
        self.pump()

    def pump(self, duration=.12):
        end = time.monotonic()+duration
        while time.monotonic()<end:
            self.app.update()
            time.sleep(.005)

    def assert_visible(self, widget):
        self.assertTrue(widget.winfo_ismapped())
        self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight())
        self.assertGreaterEqual(widget.winfo_rooty(), self.app.winfo_rooty())
        self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),
                             self.app.winfo_rooty()+self.app.winfo_height())

    def test_live_scan_counter_survives_resize_and_separate_export_view(self):
        source = self.root/'source.img'
        source.write_bytes(fat_img())
        index = scan_tree(str(source))
        self.app.source_path.set(str(source))
        self.app._select_main_tab('files')
        callbacks = []
        def scan(*args, progress, **kwargs):
            with patch('recoverydesk.gui.time.monotonic', return_value=10.):
                for done in range(10001):
                    progress(done,10000)
            return index
        def thread(*, target, **kwargs):
            return SimpleNamespace(start=target)
        with patch('recoverydesk.gui.threading.Thread', side_effect=thread), \
             patch('recoverydesk.gui.scan_other_tree', side_effect=scan), \
             patch.object(self.app,'_post_scan_callback',side_effect=callbacks.append):
            self.app.start_ntfs_scan()
        self.assertLessEqual(len(callbacks),6,'Progress burst flooded the GUI callback queue')
        self.assertTrue(self.app.ntfs_scanning)
        callbacks.pop(0)()
        self.assertIn('MFT:',self.app.status.get())
        for size in ('1024x650+0+0','1280x720+0+0','1024x750+0+0','1340x830+0+0','1024x650+0+0'):
            self.app.geometry(size)
            self.pump()
            self.assert_visible(self.app.status_label)
            self.app.export_progress_button.invoke()
            self.pump()
            self.assert_visible(self.app.status_label)
            self.assertGreaterEqual(self.app.file_tree.winfo_height(),70,
                                     f'geometry={self.app.geometry()} scaling={self.app.tk.call("tk","scaling")}')
            self.app._export_progress_window.destroy()
        for callback in callbacks:
            callback()
        self.assertFalse(self.app.ntfs_scanning)
        self.assertIs(self.app.browser_index,index)
        self.assertNotIn('MFT: 10,000 / 10,000',self.app.status.get(),
                         'A stale progress message replaced the completed scan status')

    def test_resize_bursts_coalesce_header_and_chart_work(self):
        with patch.object(self.app._header_title,'configure',wraps=self.app._header_title.configure) as header, \
             patch.object(self.app,'_draw_usage_bar',wraps=self.app._draw_usage_bar) as chart:
            for width in range(700,800):
                self.app._schedule_header_wrap(SimpleNamespace(width=width))
                self.app._schedule_usage_redraw()
            self.pump()
        wraps = [call for call in header.call_args_list if 'wraplength' in call.kwargs]
        self.assertGreater(len(wraps),0)
        self.assertLessEqual(len(wraps),3)
        self.assertEqual(wraps[-1].kwargs['wraplength'],799)
        self.assertGreater(chart.call_count,0)
        self.assertLessEqual(chart.call_count,3)

    def test_unchanged_usage_does_not_rewrite_caption_or_canvas(self):
        changes = []
        self.app.usage_caption.trace_add('write',lambda *_: changes.append(self.app.usage_caption.get()))
        with patch.object(self.app.usage_canvas,'delete',wraps=self.app.usage_canvas.delete) as redraw:
            for _ in range(100):
                self.app._draw_usage_bar()
        self.assertEqual(changes,[])
        redraw.assert_not_called()
        self.app._draw_usage_bar(SimpleNamespace(used_percent=25.))
        self.assertIn('25.0',self.app.usage_caption.get())
