"""Signature scan publication, cancellation and original-source ownership."""
import os
import threading
import time
from tkinter import ttk
import unittest
from unittest.mock import patch

import test_preview_worker_gui as preview_tests
from test_signature_search import picture
from recoverydesk.signature_search import scan_signatures,FILESYSTEM
from recoverydesk.filesystems import ScanCancelled
from recoverydesk.i18n import LANGUAGES,translate


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'GUI required')
class SignatureGuiTests(unittest.TestCase):
    setUp=preview_tests.PreviewWorkerGuiTests.setUp
    widgets=preview_tests.PreviewWorkerGuiTests.widgets
    wait_for=preview_tests.PreviewWorkerGuiTests.wait_for

    def prepare(self):
        self.source.write_bytes(b'X'*512+picture('JPEG')+b'X'*512+picture('PNG'))
        self.app.source_path.set(str(self.source))

    def test_real_scan_publishes_candidates_without_changing_source(self):
        self.prepare();before=self.source.read_bytes()
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_signature_scan();self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertEqual(self.app.browser_fs,FILESYSTEM);self.assertEqual(len(self.app.browser_index.entries),2)
        self.assertIn('Signatursuche beendet',self.app.status.get());self.assertEqual(self.source.read_bytes(),before)
        self.assertEqual(str(self.app.ntfs_cancel_btn.cget('state')),'disabled')

    def test_combined_scan_uses_selected_categories_and_restores_button(self):
        self.prepare()
        with patch('recoverydesk.gui.messagebox.askyesno', return_value=True), patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_signature_scan(('images', 'audio'))
            self.wait_for(lambda: not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertEqual(len(self.app.browser_index.entries), 2)
        self.assertEqual(self.app.browser_index.signature_categories, ('images', 'audio'))
        self.assertEqual(str(self.app.signature_combined_button.cget('state')), 'normal')

    def scan_for_list(self):
        self.prepare()
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_signature_scan();self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        return self.app.signature_results

    def test_signature_inspection_explains_evidence_without_reading_and_fits_languages(self):
        import tkinter as tk
        from recoverydesk.recovery_quality import SIGNATURE_CHECK_GUIDE, SIGNATURE_DETAIL
        from recoverydesk.help_center import topic_text
        self.scan_for_list()
        item=self.app.signature_result_index.entries[0]
        original=self.source.read_bytes()
        for language in LANGUAGES:
            self.app.change_language(language)
            with patch('recoverydesk.gui.verify_file') as read, patch('recoverydesk.gui.check_content_file') as content:
                self.app.inspect_file(context=(str(self.source),self.app.signature_result_index,(item,)))
                window=next(w for w in self.app.winfo_children() if isinstance(w,tk.Toplevel))
                window.geometry('650x520');self.app.update()
                widgets=list(self.widgets(window))
                text=next(w for w in widgets if isinstance(w,tk.Text))
                self.assertIn(translate(SIGNATURE_CHECK_GUIDE,language),text.get('1.0','end'))
                labels='\n'.join(str(w.cget('text')) for w in widgets if isinstance(w,ttk.Label))
                self.assertIn(translate(SIGNATURE_DETAIL,language),labels)
                self.assertNotIn('Rettbarkeit:',labels)
                self.assertNotIn('Dateisystem:',labels)
                self.assertIn(translate(SIGNATURE_CHECK_GUIDE,language),topic_text('browser',language)[1])
                for button in (w for w in widgets if isinstance(w,ttk.Button)):
                    self.assertTrue(button.winfo_ismapped(),language)
                    self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),window.winfo_rooty()+window.winfo_height(),language)
                read.assert_not_called();content.assert_not_called()
                window.destroy()
        self.assertEqual(self.source.read_bytes(),original)

    def test_summary_is_unchanged_by_filters_or_next_scan_options(self):
        view=self.scan_for_list();summary=self.app.signature_summary
        text=self.app.signature_scope_label.cget('text')
        self.app.signature_free_only.set(True)
        self.app.signature_free_filesystem.set('exFAT')
        self.app.signature_partition_offset.set('8192')
        self.app.signature_file_limit_mib.set('256')
        self.app._update_signature_scope()
        view.query.set('no matches')
        self.assertIs(self.app.signature_summary,summary)
        self.assertEqual(self.app.signature_scope_label.cget('text'),text)
        self.assertEqual(summary.area,'all');self.assertEqual(summary.offset,0)
        self.assertEqual(summary.file_limit,32*1024**2)
        self.assertIn('Kein Fund passt',view.caption.cget('text'))
        self.assertEqual(summary.count,2)
        self.app._reset_analysis_for_source()
        self.assertIsNone(self.app.signature_summary)

    def test_no_matches_and_limit_reached_are_distinct_real_scan_outcomes(self):
        self.source.write_bytes(b'X'*4096)
        self.app.source_path.set(str(self.source))
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_signature_scan();self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertEqual(self.app.signature_summary.state,'finished')
        self.assertIn('Keine passenden Signaturen',self.app.signature_scope_label.cget('text'))
        self.prepare()
        with patch('recoverydesk.signature_search.MAX_HITS',1), \
             patch('recoverydesk.gui.messagebox.askyesno',return_value=True), \
             patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_signature_scan();self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertEqual(self.app.signature_summary.state,'limited')
        self.assertIn('Prüfgrenze erreicht',self.app.signature_scope_label.cget('text'))
        self.assertNotIn('Keine passenden Signaturen',self.app.signature_scope_label.cget('text'))

    def test_failed_read_or_checkpoint_write_is_not_a_successful_empty_search(self):
        self.prepare()
        for problem in (OSError('Image lieferte unvollständige Daten.'),PermissionError('Suchstand nicht beschreibbar')):
            with patch('recoverydesk.signature_search.scan_signatures',side_effect=problem), \
                 patch('recoverydesk.gui.messagebox.askyesno',return_value=True), \
                 patch('recoverydesk.gui.messagebox.showerror') as error:
                self.app.start_signature_scan();self.wait_for(lambda:not self.app.ntfs_scanning)
            error.assert_called_once()
            self.assertEqual(self.app.signature_summary.state,'failed')
            self.assertIsNone(self.app.signature_result_index)
            text=self.app.signature_scope_label.cget('text')
            self.assertIn('Suche fehlgeschlagen',text)
            self.assertNotIn('Keine passenden Signaturen',text)

    def test_summary_and_actions_fit_small_window_in_all_languages_and_outcomes(self):
        from recoverydesk.signature_summary import SignatureSummary
        self.app.deiconify();self.app.geometry('1024x650')
        self.app._select_main_tab('signatures')
        run=SignatureSummary('/images/'+'long-name-'*12+'.img','exfat-free',1099511627776,
            ('images','office','archives','audio','video'),256*1024**2,count=0)
        for language in LANGUAGES:
            self.app.change_language(language)
            for state in ('finished','limited','failed','cancelled'):
                self.app._set_signature_summary(run.outcome(state));self.app.update()
                self.assertGreaterEqual(self.app.signature_results.tree.winfo_height(),60,(language,state))
                label=self.app.signature_scope_label
                self.assertTrue(label.winfo_ismapped())
                bottom=self.app.signature_tab.winfo_rooty()+self.app.signature_tab.winfo_height()
                self.assertLessEqual(self.app.signature_results.export.winfo_rooty()+self.app.signature_results.export.winfo_height(),bottom)

    def test_results_sort_numerically_and_keep_selection(self):
        view=self.scan_for_list()
        self.assertEqual(len(view.tree.get_children()),2)
        first=self.app.browser_index.entries[0]
        view.tree.selection_set(str(first.key));view._selection_changed()
        view.sort('offset')
        self.assertEqual(view.selected_entries(),(first,))
        offsets=[view.entries[key].locator[1] for key in view.tree.get_children()]
        self.assertEqual(offsets,sorted(offsets,reverse=True))
        self.assertEqual(view.tree.item(str(first.key),'text'),first.name)
        self.assertEqual(str(view.inspect.cget('state')),'normal')
        view.select_all()
        self.assertEqual(len(view.selected_entries()),2)
        self.assertEqual(str(view.inspect.cget('state')),'disabled')

    def test_find_shortcut_focuses_the_active_tabs_filter(self):
        view=self.app.signature_results
        view.query.set('PNG')
        self.app._select_main_tab('signatures')
        with patch.object(view.query_entry,'focus_set') as signature_focus, \
             patch.object(self.app.browser_search_entry,'focus_set') as browser_focus:
            self.assertEqual(self.app._focus_browser_search(),'break')
            signature_focus.assert_called_once();browser_focus.assert_not_called()
            self.assertEqual(view.query_entry.selection_get(),'PNG')
            self.app._select_main_tab('files')
            self.app._focus_browser_search()
            browser_focus.assert_called_once()
        self.assertEqual(view.query.get(),'PNG')

    def context_event(self,view,key):
        from types import SimpleNamespace
        self.app.deiconify();self.app._select_main_tab('signatures');self.app.update()
        view.tree.see(key);self.app.update_idletasks()
        _,y,_,height=view.tree.bbox(key)
        return SimpleNamespace(y=y+height//2,x_root=100,y_root=100)

    def test_context_menu_keeps_multiselection_and_single_file_inspection_is_disabled(self):
        view=self.scan_for_list();view.select_all()
        keys=view.tree.get_children()
        event=self.context_event(view,keys[0])
        for language in LANGUAGES:
            self.app.change_language(language)
            with patch('recoverydesk.signature_results.tk.Menu') as menu:
                view._context_popup(event)
                rows=[c.kwargs for c in menu.return_value.add_command.call_args_list]
                self.assertEqual(rows[0]['label'],translate('Vorschau',language))
                self.assertEqual(rows[1]['state'],'disabled')
                self.assertEqual(len(view.selected_entries()),2)
                menu.return_value.grab_release.assert_called_once()
                menu.return_value.destroy.assert_not_called()

    def test_context_menu_stays_alive_after_posting_and_replaces_previous_menu(self):
        from tkinter import Menu
        view=self.scan_for_list();event=self.context_event(view,view.tree.get_children()[0])
        # tk_popup posts without waiting for a command. Destroying in finally
        # would close the menu before a user could choose an action.
        with patch.object(Menu,'tk_popup'):
            view._context_popup(event)
            first=view._context_menu
            self.assertTrue(first.winfo_exists())
            view._context_popup(event)
            self.assertFalse(first.winfo_exists())
            self.assertTrue(view._context_menu.winfo_exists())

    def test_context_menu_selects_clicked_row_and_revalidates_source_when_used(self):
        view=self.scan_for_list();keys=view.tree.get_children()
        event=self.context_event(view,keys[1])
        view.tree.selection_set(keys[0])
        with patch('recoverydesk.signature_results.tk.Menu') as menu:
            view._context_popup(event)
            rows=[c.kwargs for c in menu.return_value.add_command.call_args_list]
        self.assertEqual(view.tree.selection(),(keys[1],))
        self.assertEqual(rows[1]['state'],'normal')
        self.app._source_generation+=1
        with patch.object(self.app,'preview_entry') as preview:
            rows[0]['command']()
        preview.assert_not_called()
        self.assertEqual(view.tree.get_children(),())

    def test_escape_preserves_filters_and_keyboard_menu_uses_visible_results(self):
        view=self.scan_for_list();view.kind.set('PNG');view.select_all()
        key=view.tree.get_children()[0]
        self.context_event(view,key)
        self.assertEqual(view.clear_selection(),'break')
        self.assertEqual(view.kind.get(),'PNG')
        self.assertEqual(view.selected_entries(),())
        self.assertEqual(str(view.preview.cget('state')),'disabled')
        self.assertEqual(str(view.report.cget('state')),'normal')
        view.tree.focus('')
        with patch('recoverydesk.signature_results.tk.Menu') as menu:
            self.assertEqual(view._keyboard_context_popup(),'break')
            menu.return_value.tk_popup.assert_called_once()
        self.assertEqual(view.tree.selection(),(key,))
        view.query.set('no result')
        with patch('recoverydesk.signature_results.tk.Menu') as menu:
            view._keyboard_context_popup()
        menu.assert_not_called()

    def test_signature_preview_reads_own_selection_without_switching_tabs(self):
        view=self.scan_for_list()
        self.app._select_main_tab('signatures')
        item=self.app.browser_index.entries[1]
        view.select_all();view.kind.set('PNG')
        self.assertEqual(view.selected_entries(),(item,))
        with patch('recoverydesk.gui.read_preview_file',return_value=b'signature preview') as read,patch('recoverydesk.gui.content_kind',return_value=''):
            self.app._signature_action('preview')
            self.wait_for(lambda:read.called)
        self.assertEqual(read.call_args.args[:4],(str(self.source),self.app.browser_index,item,FILESYSTEM))
        windows=[w for w in self.app.winfo_children() if hasattr(w,'_preview_thread')]
        self.assertEqual(len(windows),1)
        self.assertIn(item.name,windows[0].title())
        self.assertEqual(self.app.tabs.select(),str(self.app.signature_tab))
        windows[0].destroy()

    def test_export_from_signature_list_exports_only_selected_file(self):
        from pathlib import Path
        import hashlib
        view=self.scan_for_list()
        self.app._select_main_tab('signatures')
        item=self.app.browser_index.entries[1]
        view.select_all();view.kind.set('PNG')
        self.assertEqual(view.selected_entries(),(item,))
        target=self.source.parent/'export';target.mkdir()
        with patch('recoverydesk.gui.filedialog.askdirectory',return_value=str(target)),patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.gui.messagebox.showinfo'),patch('recoverydesk.gui.messagebox.showwarning'),patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app._signature_action('export')
            self.wait_for(lambda:not self.app.export_running and self.app.export_result is not None)
        error.assert_not_called()
        result=self.app.export_result
        self.assertEqual(result.exported,1)
        self.assertFalse(result.checksum_errors)
        self.assertEqual(self.app.tabs.select(),str(self.app.signature_tab))
        exported=list((Path(result.root)/'files').iterdir())
        self.assertEqual([p.name for p in exported],[item.name])
        self.assertEqual(exported[0].read_bytes(),picture('PNG'))
        self.assertIn(hashlib.sha256(exported[0].read_bytes()).hexdigest(),Path(result.checksums).read_text())

    def test_changed_source_discards_list_before_an_action_can_read_it(self):
        view=self.scan_for_list();view.select_all()
        self.app.source_path.set(str(self.source)+'.other')
        with patch.object(self.app,'preview_entry') as preview,patch.object(self.app,'export_browser_selection') as export:
            self.app._signature_action('preview');self.app._signature_action('export')
        preview.assert_not_called();export.assert_not_called()
        self.assertEqual(view.tree.get_children(),())
        self.assertIsNone(self.app.signature_result_index)

    def test_signature_inspection_uses_selected_metadata(self):
        view=self.scan_for_list();item=self.app.browser_index.entries[1]
        view.tree.selection_set(str(item.key))
        self.app._signature_action('inspect')
        windows=[w for w in self.app.winfo_children() if hasattr(w,'title') and w.title().startswith('Dateiprüfung')]
        self.assertEqual(len(windows),1)
        self.assertIn(item.name,windows[0].title())
        windows[0].destroy()

    def test_list_is_cleared_before_replacement_scan_and_after_source_reset(self):
        view=self.scan_for_list();self.app._clear_browser_results()
        self.assertEqual(view.tree.get_children(),())
        self.assertEqual(str(view.preview.cget('state')),'disabled')
        self.assertEqual(str(view.export.cget('state')),'disabled')

    def test_running_export_can_be_reopened_without_selection_or_new_job(self):
        view=self.scan_for_list()
        self.app.export_running=True
        try:
            view.tree.selection_remove(*view.tree.selection());view._selection_changed()
            self.assertEqual(str(view.export.cget('state')),'normal')
            with patch.object(self.app,'_show_export_progress') as progress,patch.object(self.app,'_start_export_job') as start:
                view.export.invoke()
            progress.assert_called_once();start.assert_not_called()
        finally:self.app.export_running=False

    def test_size_sort_is_numeric_and_full_bounded_list_can_be_selected(self):
        from recoverydesk.signature_search import _signature_entry
        view=self.app.signature_results
        entries=[_signature_entry(n*4096,size,'PNG') for n,size in enumerate((9,100,1024))]
        view.show_entries(entries);view.sort('size')
        self.assertEqual([e.size for e in view.entries.values()],[9,100,1024])
        self.assertEqual([view.entries[k].size for k in view.tree.get_children()],[9,100,1024])
        view.show_entries([_signature_entry(n*4096,10,'PNG') for n in range(1000)])
        view.select_all()
        self.assertEqual(len(view.selected_entries()),1000)

    def test_result_actions_and_list_are_visible_at_small_size_in_six_languages(self):
        self.app.deiconify();self.app.geometry('1024x650')
        self.app._select_main_tab('signatures')
        for language in LANGUAGES:
            self.app.change_language(language);self.app.update()
            view=self.app.signature_results
            self.assertGreaterEqual(view.tree.winfo_height(),60,language)
            bottom=self.app.signature_tab.winfo_rooty()+self.app.signature_tab.winfo_height()
            right=self.app.signature_tab.winfo_rootx()+self.app.signature_tab.winfo_width()
            for widget in (view.tree,view.preview,view.inspect,view.export,view.browser,view.report):
                self.assertTrue(widget.winfo_ismapped(),language)
                self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),bottom,language)
                self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),right,language)
            self.assertEqual(view.tree.heading('offset')['text'],translate('Fundposition (Bytes)',language))
            self.assertEqual(view.report.cget('text'),translate('Fundliste speichern…',language))

    def test_csv_report_uses_filtered_sorted_rows_without_selection_or_source_reads(self):
        import csv,io
        view=self.scan_for_list();index=self.app.signature_result_index
        view.kind.set('PNG')
        target=self.source.parent/'findings.csv'
        with patch('recoverydesk.gui.filedialog.asksaveasfilename',return_value=str(target)), \
             patch('recoverydesk.gui.messagebox.showinfo'), \
             patch('recoverydesk.gui.open_source',side_effect=AssertionError('No source read')), \
             patch('recoverydesk.gui.messagebox.showerror') as error:
            # Changing next-scan options must not relabel existing findings.
            self.app.signature_free_only.set(True)
            self.app.signature_free_filesystem.set('exFAT')
            self.app._signature_action('report')
        error.assert_not_called()
        rows=list(csv.DictReader(io.StringIO(target.read_text(encoding='utf-8-sig')),delimiter=';'))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['type'],'PNG')
        self.assertEqual(rows[0]['total_findings'],'2')
        self.assertEqual(rows[0]['search_area'],'all')
        self.assertEqual(rows[0]['absolute_offset_bytes'],str(view.visible_entries()[0].locator[1]))
        self.assertIs(index,self.app.signature_result_index)
        view.query.set('no matches')
        self.assertEqual(str(view.report.cget('state')),'disabled')

    def test_stale_source_cannot_save_a_report(self):
        self.scan_for_list();self.app._source_generation+=1
        with patch('recoverydesk.gui.filedialog.asksaveasfilename') as dialog:
            self.app._signature_action('report')
        dialog.assert_not_called()
        self.assertEqual(str(self.app.signature_results.report.cget('state')),'disabled')

    def test_filters_prune_hidden_selection_and_sort_does_not_restore_it(self):
        view=self.scan_for_list();view.select_all()
        before=self.source.read_bytes()
        with patch('recoverydesk.gui.open_source',side_effect=AssertionError('Filtering must not read source')):
            view.kind.set('PNG')
            self.assertEqual([e.name.split('_')[0] for e in view.selected_entries()],['PNG'])
            view.sort('size');view.sort('offset')
            self.assertEqual(len(view.tree.get_children()),1)
            view.reset_filters()
            self.assertEqual(len(view.tree.get_children()),2)
            self.assertEqual([e.name.split('_')[0] for e in view.selected_entries()],['PNG'])
        self.assertEqual(self.source.read_bytes(),before)

    def test_text_and_type_filters_combine_without_replacing_the_search_index(self):
        view=self.scan_for_list();index=self.app.browser_index
        view.query.set('pNg_')
        self.assertEqual(len(view.tree.get_children()),1)
        view.kind.set('JPEG')
        self.assertEqual(view.tree.get_children(),())
        self.assertEqual(len(view.entries),2)
        self.assertIs(self.app.browser_index,index)
        self.assertEqual(len(index.entries),2)
        self.assertIn('0 von 2',view.caption.cget('text'))
        view.reset_filters()
        self.assertEqual(len(view.tree.get_children()),2)

    def test_type_combobox_switches_between_format_and_all_types(self):
        view=self.scan_for_list()
        view.kind_combo.set('PNG');view.kind_combo.event_generate('<<ComboboxSelected>>')
        self.app.update()
        self.assertEqual(view.kind.get(),'PNG')
        self.assertEqual(len(view.tree.get_children()),1)
        view.kind_combo.current(0);view.kind_combo.event_generate('<<ComboboxSelected>>')
        self.app.update()
        self.assertEqual(view.kind.get(),'')
        self.assertEqual(len(view.tree.get_children()),2)

    def test_minimum_size_is_exact_and_invalid_input_cannot_export_old_selection(self):
        from recoverydesk.signature_search import _signature_entry
        view=self.app.signature_results
        view.show_entries([_signature_entry(n*4096,size,'PNG') for n,size in enumerate((1023,1024,1025))])
        view.minimum_kib.set('1');view.select_all()
        self.assertEqual([e.size for e in view.selected_entries()],[1024,1025])
        for value in ('-1','1.5','1,5','word','4294967297','9'*10000):
            with self.subTest(value=value[:30]):
                view.minimum_kib.set(value)
                self.assertEqual(view.tree.get_children(),())
                self.assertEqual(view.selected_entries(),())
                self.assertIn('Mindestgröße',view.caption.cget('text'))
                self.assertEqual(str(view.export.cget('state')),'disabled')
        view.minimum_kib.set('0')
        self.assertEqual(len(view.tree.get_children()),3)
        self.assertEqual(view.selected_entries(),())

    def test_new_scan_clears_detached_rows_and_resets_filters(self):
        from recoverydesk.signature_search import _signature_entry
        view=self.scan_for_list();keys=list(view.entries)
        view.query.set('no match');view.minimum_kib.set('10')
        self.assertEqual(view.tree.get_children(),())
        view.show_entries([_signature_entry(900000,20,'PDF')])
        self.assertEqual(len(view.tree.get_children()),1)
        self.assertEqual(view.query.get(),'')
        self.assertEqual(view.minimum_kib.get(),'0')
        for key in keys:self.assertFalse(view.tree.exists(key))
        view.query.set('no match');view.clear()
        self.assertEqual(view.entries,{})
        self.assertFalse(view.tree.exists(str(900100)))

    def test_language_change_preserves_canonical_filter_and_visible_selection(self):
        view=self.scan_for_list();view.query.set('pNg');view.kind.set('PNG');view.select_all()
        for language in LANGUAGES:
            self.app.change_language(language)
            self.assertEqual(view.kind.get(),'PNG')
            self.assertEqual(view.query.get(),'pNg')
            self.assertEqual(len(view.selected_entries()),1)
            expected=translate('{visible} von {total} Funden sichtbar · {selected} ausgewählt',language).format(visible=1,total=2,selected=1)
            self.assertEqual(view.caption.cget('text'),expected)
            self.assertEqual(view.kind_combo.cget('values')[0],translate('Alle Dateitypen',language))
        view.reset_filters()
        self.assertEqual(view.kind_display.get(),translate('Alle Dateitypen',self.app.language))

    def test_detached_row_cannot_be_previewed_even_if_tk_selection_is_stale(self):
        view=self.scan_for_list();jpeg=self.app.browser_index.entries[0]
        view.kind.set('PNG');view.tree.selection_set(str(jpeg.key))
        with patch.object(self.app,'preview_entry') as preview:
            self.app._signature_action('preview')
        preview.assert_not_called()

    def test_decline_keeps_previous_browser(self):
        self.prepare();index=self.app.browser_index
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=False),patch('recoverydesk.signature_search.scan_signatures') as scan:
            self.app.start_signature_scan()
        scan.assert_not_called();self.assertIs(self.app.browser_index,index)

    def test_free_ntfs_scope_and_offset_are_used_and_restored(self):
        from test_ntfs_bitmap_usage import make_volume, SECTOR
        data=bytearray(make_volume(used_clusters=120))
        payload=picture('PNG');data[140*SECTOR:140*SECTOR+len(payload)]=payload
        self.source.write_bytes(b'P'*4096+data)
        self.app.source_path.set(str(self.source))
        self.app.signature_free_only.set(True)
        self.app.signature_partition_offset.set('4096')
        self.app.signature_save_checkpoint.set(True)
        checkpoint=self.source.parent/'free.tenshi-search.json'
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True), patch('recoverydesk.gui.messagebox.showerror') as error, patch('recoverydesk.gui.filedialog.asksaveasfilename',return_value=str(checkpoint)):
            self.app.start_signature_scan()
            self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertEqual(self.app.browser_index.signature_search_area,'ntfs-free')
        self.assertEqual(self.app.browser_index.entries[0].locator[1],4096+140*SECTOR)
        self.app.signature_free_only.set(False)
        self.app.signature_partition_offset.set('0')
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True), patch('recoverydesk.gui.messagebox.showerror') as error, patch('recoverydesk.gui.filedialog.askopenfilename',return_value=str(checkpoint)):
            self.app._resume_signature_search()
            self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertTrue(self.app.signature_free_only.get())
        self.assertEqual(self.app.signature_partition_offset.get(),'4096')

    def test_checkpoint_save_and_reopen_from_gui(self):
        self.prepare()
        checkpoint = self.source.parent / 'saved.tenshi-search.json'
        self.app.signature_save_checkpoint.set(True)
        self.app.signature_file_limit_mib.set('64')
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True), patch('recoverydesk.gui.messagebox.showerror') as error, patch('recoverydesk.gui.filedialog.asksaveasfilename',return_value=str(checkpoint)):
            self.app.start_signature_scan(('images','archives'))
            self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertTrue(checkpoint.is_file())
        self.app.signature_file_limit_mib.set('32')
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True), patch('recoverydesk.gui.messagebox.showerror') as error, patch('recoverydesk.gui.filedialog.askopenfilename',return_value=str(checkpoint)):
            self.app._resume_signature_search()
            self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertEqual(self.app.signature_file_limit_mib.get(),'64')
        self.assertEqual(len(self.app.browser_index.entries),2)
        self.assertEqual(str(self.app.signature_pause_button.cget('state')),'disabled')

    def test_free_fat32_selection_and_checkpoint_scope_are_restored(self):
        from test_signature_free_fat32 import make_fat32
        from pathlib import Path
        self.source.unlink()
        volume=make_fat32(self.source,offset=4096)
        with self.source.open('r+b') as stream:
            stream.seek(volume.cluster_offset(140));stream.write(picture('PNG'))
        self.app.source_path.set(str(self.source))
        self.app.signature_free_only.set(True)
        self.app.signature_free_filesystem.set('FAT32')
        self.app.signature_partition_offset.set('4096')
        self.app.signature_save_checkpoint.set(True)
        checkpoint=self.source.parent/'fat32.tenshi-search.json'
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.gui.messagebox.showerror') as error,patch('recoverydesk.gui.filedialog.asksaveasfilename',return_value=str(checkpoint)):
            self.app.start_signature_scan();self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertEqual(self.app.browser_index.signature_search_area,'fat32-free')
        self.assertEqual(len(self.app.browser_index.entries),1)
        self.app.signature_free_only.set(False);self.app.signature_free_filesystem.set('NTFS')
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.gui.messagebox.showerror') as error,patch('recoverydesk.gui.filedialog.askopenfilename',return_value=str(checkpoint)):
            self.app._resume_signature_search();self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertTrue(self.app.signature_free_only.get())
        self.assertEqual(self.app.signature_free_filesystem.get(),'FAT32')
        self.assertEqual(self.app.signature_partition_offset.get(),'4096')
        self.assertIn('FAT32',self.app.signature_scope_label.cget('text'))

    def test_free_exfat_selection_and_checkpoint_restore(self):
        from test_signature_free_exfat import make_exfat
        self.source.unlink();volume=make_exfat(self.source,offset=4096)
        self.app.source_path.set(str(self.source))
        self.app.signature_free_only.set(True);self.app.signature_free_filesystem.set('exFAT')
        self.app.signature_partition_offset.set('4096');self.app.signature_save_checkpoint.set(True)
        checkpoint=self.source.parent/'exfat.tenshi-search.json'
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.gui.messagebox.showerror') as error,patch('recoverydesk.gui.filedialog.asksaveasfilename',return_value=str(checkpoint)):
            self.app.start_signature_scan();self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertEqual(self.app.browser_index.signature_search_area,'exfat-free')
        self.assertEqual(self.app.browser_index.entries[0].locator[1],volume.cluster_offset(140))
        self.app.signature_free_only.set(False);self.app.signature_free_filesystem.set('NTFS')
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.gui.messagebox.showerror') as error,patch('recoverydesk.gui.filedialog.askopenfilename',return_value=str(checkpoint)):
            self.app._resume_signature_search();self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertTrue(self.app.signature_free_only.get());self.assertEqual(self.app.signature_free_filesystem.get(),'exFAT')
        self.assertEqual(self.app.signature_partition_offset.get(),'4096')
        self.assertIn('exFAT',self.app.signature_scope_label.cget('text'))

    def test_cancelled_scan_does_not_publish_an_index(self):
        self.prepare();started=threading.Event()
        def scan(*args,cancel,**kwargs):
            started.set()
            end=time.monotonic()+2
            while not cancel() and time.monotonic()<end:time.sleep(.005)
            raise ScanCancelled()
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.signature_search.scan_signatures',side_effect=scan),patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_signature_scan();self.assertTrue(started.wait(1));self.app._cancel_scan()
            self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called();self.assertIsNone(self.app.browser_index)

    def test_results_from_previous_source_are_discarded(self):
        self.prepare();index=scan_signatures(str(self.source));release=threading.Event();started=threading.Event()
        self.addCleanup(release.set)
        def scan(*args,**kwargs):started.set();release.wait(2);return index
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.signature_search.scan_signatures',side_effect=scan):
            self.app.start_signature_scan();self.assertTrue(started.wait(1));self.app._source_generation+=1;release.set()
            self.wait_for(lambda:not self.app.ntfs_scanning)
        self.assertIsNone(self.app.browser_index)

    def test_scan_button_is_available_in_all_six_languages(self):
        self.app.deiconify();self.app.update()
        for language in LANGUAGES:
            self.app.change_language(language)
            self.app._select_main_tab('signatures')
            self.app.update()
            for category, key in self.app._signature_button_keys.items():
                button = self.app.signature_search_buttons[category]
                self.assertEqual(button.cget('text'), translate(key,language))
                self.assertTrue(button.winfo_ismapped())
