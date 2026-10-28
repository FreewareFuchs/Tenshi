from __future__ import annotations
import os
import sys
import threading
import time
import queue
import base64
import gc
import uuid
import tkinter as tk
from tkinter import ttk, filedialog as _filedialog, messagebox as _messagebox
from .i18n import (LANGUAGES, UITranslator, DialogProxy, load_language,
                   save_language, translate, canonical_choice, display_kind_text)

_CURRENT_LOCALE = 'de'
messagebox = DialogProxy(_messagebox, lambda: _CURRENT_LOCALE)
filedialog = DialogProxy(_filedialog, lambda: _CURRENT_LOCALE, is_file_dialog=True)
from pathlib import Path
from .export_errors import export_error_message
from .source_catalog import collect_choices, device_choices, volume_choices
from .branding import asset_path
from .appearance import apply_theme, detect_system_theme, palette
from .version_info import display_version
from .verification_labels import (METADATA_SCOPE, READ_SCOPE, EXPORT_SCOPE, RESUME_SCOPE,
                                  RESUME_LABEL, METADATA_LABEL)
from .help_center import HelpWindow
from .ui_preferences import load_ui_preferences, save_ui_preferences, valid_geometry
from .diagnostics import log_issue, diagnostic_log_path
from .session_store import (save_session, load_session, fingerprint_image,
                            check_fingerprint, SessionError)
from .core import list_volumes
from .partition_scan import analyze_image, format_partition_findings
from .device_identity import capture_device_identity, check_device_identity
from .partition_health import inspect_partition, format_partition_details, format_partition_confidence
from .ntfs import iter_stream
from .recovery_quality import assess
from .recovery_preflight import inspect_selection, MAX_DETAIL_ROWS
from .browser_filter import (STATUS_FILTERS, FILTER_ALL, filter_entries, matches_status,
                             folder_warning_records, visual_status)
from .explorer import (SearchCriteria, search_entries, construct_paths, sorted_entries,
                       display_size, display_kind, display_modified, file_extension,
                       EXTENSION_CATEGORIES, append_category_extensions, visible_entries,
                       compile_search, is_temporary_file)
from .batch_export import export_batch
from .export_queue import QueueProgress, readable_bytes
from .export_blocks import ExportBlocks, copy_export_report
from .progress_window import ExportProgressWindow
from .imaging_window import ImagingProgressWindow
from .imaging_blocks import ImagingBlocks
from .zip_verification import verify_zip, ZIP_CHECK_SCOPE, ZipCheckResult
from .preview import describe, PREVIEW_LIMIT, IMAGE_LIMIT
from .file_verification import verify_file, MAX_VERIFY_BYTES, VerificationCancelled
from .imaging import create_image, sidecar_path, describe_bad_ranges, ImagingProgress
from .ntfs_browser import scan_ntfs_tree, ScanCancelled
from .scan_report import format_scan_report
from .filesystems import (scan_tree as scan_other_tree,
                          ScanCancelled as OtherScanCancelled, FileSystemError)
from .sources import (validate_source, open_source, source_size, is_physical,
                      list_physical_sources, ensure_safe_destination, raw_volume_path, is_volume,
                      is_device_source)

APP_NAME = "Tenshi"

class RecoveryDeskApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Tenshi — Datenrettung | {display_version()}")
        self._view_settings = load_ui_preferences()
        self.theme_mode = self._view_settings['theme']
        self._system_theme = detect_system_theme() if os.name == 'nt' else None
        self.theme = (self._system_theme or 'light') if self.theme_mode == 'system' else self.theme_mode
        geometry = self._view_settings['geometry']
        # A detached or resized monitor must not strand the saved window offscreen.
        if geometry:
            import re
            match = re.fullmatch(r'(\d+)x(\d+)([+-]\d+)([+-]\d+)', geometry)
            if match:
                width, height, x, y = map(int, match.groups())
                screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
                if x > screen_w - 160 or y > screen_h - 100 or x < -screen_w or y < -screen_h:
                    geometry = f'{width}x{height}+25+25'
        self.geometry(geometry or "1340x900")
        self.minsize(1024, 650)
        self.configure(bg="#f3f5f8")
        global _CURRENT_LOCALE
        self.language = load_language()
        _CURRENT_LOCALE = self.language
        self._i18n = UITranslator(self, self.language)
        self.source_path = tk.StringVar()
        self.status = tk.StringVar(value="Bereit. Quelldatenträger werden nur lesend geöffnet.")
        # All application-owned Tcl timers are canceled before Tk is destroyed.
        self._pending_after = set()
        self._closing = False
        self._scan_callbacks = queue.Queue()
        self.after(20, self._drain_scan_callbacks)
        self._setup_style()
        self._build()
        self._apply_theme()
        self._compact_layout = None
        self.bind("<Configure>", self._update_compact_layout, add="+")
        self.after_idle(self._update_compact_layout)
        if self._view_settings['maximized'] and os.name == 'nt':
            try:
                self.state('zoomed')
            except tk.TclError:
                pass
        self.bind_class('Toplevel', '<Map>', self._on_popup_map, add='+')
        self._i18n.start()
        self.bind('<F1>', self._help_shortcut)
        self._appearance_stop = threading.Event()
        threading.Thread(target=self._watch_system_appearance, daemon=True,
                         name='Tenshi appearance').start()

    def report_callback_exception(self, exc_type, exc, tb):
        """Avoid a silent Tcl callback failure; do not leak file contents to logs."""
        log_issue('ui_callback', exc)
        messagebox.showerror('Tenshi',
            f'Ein Bedienfehler wurde festgestellt: {type(exc).__name__}.\n'
            f'Technisches Protokoll: {diagnostic_log_path()}', parent=self)

    def _help_shortcut(self, event=None):
        """F1 explains the currently selected main tab, without starting I/O."""
        topic = 'browser' if self.tabs.select() == str(self.ntfs_tab) else 'partitions'
        self.show_help(topic)
        return 'break'

    def show_help(self, topic='start'):
        """Open local help once; a repeated request selects the requested topic."""
        window = getattr(self, '_help_window', None)
        if window is not None and window.winfo_exists():
            window.topic = topic
            window.search_var.set('')
            window.refresh_language(self.language)
            window.lift()
            return window
        window = HelpWindow(self, topic=topic)
        self._help_window = window
        return window

    def show_error_log(self):
        """Display bounded, metadata-only diagnostic records inside Tenshi."""
        win = tk.Toplevel(self)
        win.title(translate('Fehlerprotokoll', self.language))
        win.geometry('840x430')
        win.minsize(550, 290)
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=str(diagnostic_log_path()), wraplength=780).pack(anchor='w')
        output = tk.Text(frame, wrap='none', font=('Consolas', 10))
        output.pack(fill='both', expand=True, pady=10)
        try:
            file = diagnostic_log_path()
            with file.open('rb') as fh:
                fh.seek(0, 2)
                fh.seek(max(0, fh.tell() - 128 * 1024))
                data = fh.read().decode('utf-8', 'replace')
            # In case a bounded seek begins in the middle of a record.
            if data and not data[0].isdigit():
                data = data.partition('\n')[2]
        except FileNotFoundError:
            data = translate('Noch keine Fehler protokolliert.', self.language)
        except OSError as exc:
            log_issue('log_view', exc)
            data = translate('Fehlerprotokoll kann nicht geöffnet werden.', self.language)
        output.insert('1.0', data)
        output.configure(state='disabled')
        ttk.Button(frame, text=translate('Support-Bericht', self.language),
                   command=self.show_support_report).pack(anchor='e')

    def show_support_report(self):
        from .support_report import collect_report, report_text, save_report
        text = report_text(collect_report(
            language=self.language, tk_version=str(self.tk.call('package', 'provide', 'Tk')),
            window_system=str(self.tk.call('tk', 'windowingsystem'))))
        win = tk.Toplevel(self)
        win.title(translate('Support-Bericht', self.language))
        win.geometry('840x520')
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=translate(
            'Vorschau: technische Metadaten und Fehlercodes. Keine Pfade, Dateinamen oder Dateiinhalte. Der Bericht wird nur lokal gespeichert.',
            self.language), wraplength=760).pack(anchor='w')
        output = tk.Text(frame, wrap='word', font=('Consolas', 10))
        output.pack(fill='both', expand=True, pady=10)
        output.insert('1.0', text)
        output.configure(state='disabled')

        def save():
            destination = filedialog.asksaveasfilename(
                parent=win, title='Support-Bericht speichern', defaultextension='.json',
                initialfile='Tenshi_Support.json', filetypes=[('JSON', '*.json')])
            if not destination:
                return
            try:
                save_report(destination, text, (self.source_path.get().strip(),
                    getattr(self, 'browser_source', ''), getattr(self, 'partition_source', '')))
            except (OSError, ValueError) as exc:
                messagebox.showerror('Support-Bericht', str(exc), parent=win)
                return
            messagebox.showinfo('Support-Bericht', 'Bericht gespeichert.', parent=win)

        ttk.Button(frame, text=translate('Support-Bericht speichern', self.language),
                   command=save).pack(anchor='e')
        return win

    def change_language(self, language: str):
        """Apply the language immediately; persist the choice for future launches."""
        global _CURRENT_LOCALE
        if language not in LANGUAGES:
            raise ValueError('Unbekannte Sprache')
        self.language = language
        _CURRENT_LOCALE = language
        self._language_var.set(language)
        self._i18n.set_language(language)
        help_window = getattr(self, '_help_window', None)
        if help_window is not None and help_window.winfo_exists():
            help_window.refresh_language(language)
        self._language_button.configure(text='🌐  ' + LANGUAGES[language])
        self._sync_localized_combos()
        self._translate_display_rows()
        if self.last_partition_report is not None and hasattr(self, 'partition_quality_summary'):
            p = self.last_partition_report.partitions
            self.partition_quality_summary.set(
                f"{translate('Hohe Plausibilität', self.language)}: {sum(x.confidence == 'Hoch' for x in p)}   ·   "
                f"{translate('Mittlere Plausibilität', self.language)}: {sum(x.confidence == 'Mittel' for x in p)}   ·   "
                f"{translate('Geringe Plausibilität', self.language)}: {sum(x.confidence == 'Niedrig' for x in p)}   ·   "
                f"{translate('Auffällige Partitionen', self.language)}: {sum(bool(x.warning) for x in p)}")
        if hasattr(self, 'browser_page_caption'):
            self._update_browser_page_caption()
        try:
            save_language(language)
        except OSError as exc:
            messagebox.showwarning('Sprache auswählen', str(exc), parent=self)

    def _sync_localized_combos(self):
        """Localized dropdown captions never enter the internal search engine."""
        if hasattr(self, 'browser_filter_combo'):
            self.browser_filter_combo.configure(
                values=[translate(key, self.language) for key in STATUS_FILTERS])
            self.browser_status_display.set(translate(self.browser_status_filter.get(), self.language))
        if hasattr(self, 'browser_kind_display'):
            self.browser_kind_display.set(translate(self.browser_kind.get(), self.language))
        if hasattr(self, 'browser_kind_combo') and self.browser_kind_combo.winfo_exists():
            self.browser_kind_combo.configure(
                values=[translate(key, self.language) for key in ('Alle', 'Nur Dateien', 'Nur Ordner')])

    def _translate_display_rows(self):
        """Change display labels without modifying underlying partition/file data."""
        if hasattr(self, 'part_tree'):
            for idx, part in enumerate(getattr(self, 'partitions', [])):
                if self.part_tree.exists(str(idx)):
                    self.part_tree.set(str(idx), 'confidence',
                                       translate(part.confidence, self.language))
        if hasattr(self, 'file_tree'):
            for iid in self.file_tree.get_children(''):
                if not self.file_tree.exists(iid):
                    continue
                entry = getattr(self, 'browser_entries_visible', {}).get(iid)
                if entry is None:
                    continue
                values = list(self.file_tree.item(iid, 'values'))
                if len(values) >= 4:
                    values[0] = display_kind_text(display_kind(entry), self.language)
                    values[2] = translate(entry.status, self.language)
                    values[3] = translate(assess(entry).label, self.language)
                    self.file_tree.item(iid, values=values)
    def _on_localized_status_selected(self, event=None):
        self.browser_status_filter.set(canonical_choice(
            self.browser_status_display.get(), STATUS_FILTERS, self.language))
        return self._on_browser_filter_change(event)

    def _post_scan_callback(self, callback):
        """Workers only enqueue Python objects; all Tcl calls stay on the UI thread."""
        self._scan_callbacks.put(callback)

    def _drain_scan_callbacks(self):
        if self._closing:
            return
        try:
            # Bound each poll so progress traffic cannot starve GUI events.
            for _ in range(100):
                try:
                    callback = self._scan_callbacks.get_nowait()
                except queue.Empty:
                    break
                if self._closing:
                    break
                callback()
        finally:
            if not self._closing:
                self.after(20, self._drain_scan_callbacks)

    def after(self, ms, func=None, *args):
        """Own root timers so closing Tenshi never leaves dead Tcl commands.

        Tk registers every Python callback under a Tcl command name. Destroying
        that widget unregisters the command, *not* a pending Tcl `after` job;
        when the job later fires Tk prints `invalid command name ...<lambda>`.
        Track those jobs, including idle callbacks, and cancel at shutdown.
        """
        if func is None:
            return super().after(ms)
        if getattr(self, '_closing', False):
            return None
        pending = getattr(self, '_pending_after', None)
        # Tk's own initialization may schedule callbacks before our widgets exist.
        if pending is None:
            return super().after(ms, func, *args)
        holder = []

        def run():
            if holder:
                pending.discard(holder[0])
            if not self._closing:
                return func(*args)

        try:
            job = super().after(ms, run)
        except (tk.TclError, RuntimeError):
            # Workers can finish during shutdown. Do not resurrect the GUI.
            if self._closing:
                return None
            raise
        holder.append(job)
        pending.add(job)
        return job

    def after_cancel(self, job):
        if hasattr(self, '_pending_after'):
            self._pending_after.discard(job)
        return super().after_cancel(job)

    def _after_window(self, window, ms, func):
        """Schedule a dialog poll and cancel it when that dialog is destroyed."""
        if self._closing or not window.winfo_exists():
            return None
        jobs = getattr(window, '_tenshi_pending_after', None)
        if jobs is None:
            jobs = set()
            window._tenshi_pending_after = jobs

            def on_destroy(event):
                if event.widget is not window:
                    return  # Child widget destruction must not cancel dialog work.
                for job in tuple(jobs):
                    try:
                        window.after_cancel(job)
                    except tk.TclError:
                        pass
                jobs.clear()

            window.bind('<Destroy>', on_destroy, add='+')
        holder = []

        def run():
            if holder:
                jobs.discard(holder[0])
            if not self._closing and window.winfo_exists():
                func()

        job = window.after(ms, run)
        holder.append(job)
        jobs.add(job)
        return job

    def destroy(self):
        if getattr(self, '_closing', False):
            return
        self._closing = True
        if hasattr(self, '_appearance_stop'):
            self._appearance_stop.set()
        if hasattr(self, '_i18n'):
            self._i18n.stop()
        for job in tuple(getattr(self, '_pending_after', ())):
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        if hasattr(self, 'part_tree') and hasattr(self, 'file_tree'):
            try:
                self._save_display_preferences()
            except (OSError, ValueError, tk.TclError) as exc:
                # Display settings must never prevent closing or affect disk operations.
                log_issue('display_preferences', exc)
        super().destroy()

    def _save_display_preferences(self):
        """Save only layout metadata; never a filename, source or export state."""
        geometry = self.geometry() if self.state() == 'normal' else self._view_settings.get('geometry')
        if not valid_geometry(geometry):
            geometry = self._view_settings.get('geometry')
        ratio = self._view_settings.get('folder_ratio') or .38
        if getattr(self, '_browser_sash_initialized', False):
            width = self.browser_paned.winfo_width()
            if width >= 620:
                measured = self.browser_paned.sashpos(0) / width
                if .22 <= measured <= .66:
                    ratio = measured
        payload = {
            'geometry': geometry,
            'maximized': self.state() == 'zoomed' if os.name == 'nt' else False,
            'theme': self.theme_mode,
            'folder_ratio': ratio,
            'files_columns': {col: self.file_tree.column(col, 'width')
                              for col in ('#0',) + tuple(self.file_tree['columns'])},
            'partitions_columns': {col: self.part_tree.column(col, 'width')
                                   for col in self.part_tree['columns']},
        }
        self._view_settings.update(payload)
        save_ui_preferences(payload)

    def change_theme(self, theme, *, automatic=False):
        if theme not in ('system', 'light', 'dark'):
            raise ValueError('Unbekannte Darstellung')
        self.update_idletasks()
        geometry = self.geometry() if self.state() == 'normal' else None
        sash = (self.browser_paned.sashpos(0)
                if getattr(self, '_browser_sash_initialized', False) else None)
        self.theme_mode = theme
        self.theme = (self._system_theme or 'light') if theme == 'system' else theme
        self._theme_var.set(theme)
        self._apply_theme()
        self.update_idletasks()
        if geometry is not None:
            self.geometry(geometry)
        if sash is not None:
            self.browser_paned.sashpos(0, sash)
        help_window = getattr(self, '_help_window', None)
        if help_window is not None and help_window.winfo_exists():
            help_window.refresh_theme()
        # Save the theme immediately, even if the application is terminated later.
        try:
            if not automatic:
                save_ui_preferences({'theme': theme})
        except OSError as exc:
            messagebox.showwarning('Darstellung', str(exc), parent=self)

    def _watch_system_appearance(self):
        # Only plain Python objects cross threads; Tk remains on the UI thread.
        previous = object()
        while not self._appearance_stop.is_set():
            mode = detect_system_theme()
            if self._appearance_stop.is_set():
                break
            if mode != previous:
                previous = mode
                self._post_scan_callback(lambda value=mode: self._system_appearance_changed(value))
            self._appearance_stop.wait(5)

    def _system_appearance_changed(self, mode):
        self._system_theme = mode
        if self.theme_mode == 'system' and self.theme != (mode or 'light'):
            self.change_theme('system', automatic=True)

    def _palette(self):
        return palette(self.theme)

    def _style_native_widgets(self, root):
        colors = self._palette()
        stack = [root]
        while stack:
            widget = stack.pop()
            try:
                stack.extend(widget.winfo_children())
                if isinstance(widget, (tk.Tk, tk.Toplevel, tk.Frame)):
                    widget.configure(bg=colors['bg'])
                elif isinstance(widget, tk.Text):
                    widget.configure(bg=colors['input'], fg=colors['text'],
                        insertbackground=colors['text'], selectbackground=colors['select'],
                        selectforeground=colors['selection_text'])
                elif isinstance(widget, tk.Canvas):
                    widget.configure(bg=colors['divider'])
                elif isinstance(widget, ttk.Label):
                    if str(widget.cget('foreground')) in ('#9a3412', '#ffbb75'):
                        widget.configure(foreground=colors['warning'])
                elif isinstance(widget, tk.Label):
                    fg = colors['warning'] if widget.cget('foreground') in ('#9a3412', '#ffbb75') else colors['text']
                    # Keep the original navy/cyan logo readable against dark mode.
                    # Only its backing color changes; the image pixels are untouched.
                    label_bg = '#eef4fa' if (self.theme == 'dark' and widget is getattr(self, 'logo_label', None)) else colors['bg']
                    widget.configure(bg=label_bg, fg=fg)
                elif isinstance(widget, tk.Menu):
                    widget.configure(bg=colors['panel'], fg=colors['text'],
                        activebackground=colors['select'], activeforeground=colors['selection_text'])
                elif isinstance(widget, tk.Button):
                    if widget is getattr(self, 'export_button', None):
                        widget.configure(bg=colors['accent'], fg=colors['accent_text'],
                                         activebackground=colors['accent_active'],
                                         activeforeground=colors['accent_text'],
                                         disabledforeground=colors['muted'])
                    elif widget not in getattr(self, '_nav_buttons', {}).values():
                        widget.configure(bg=colors['panel'], fg=colors['text'],
                            activebackground=colors['select'], activeforeground=colors['selection_text'])
            except (tk.TclError, AttributeError):
                continue
        if root is self:
            # The partition chart is intentionally redrawn from source-derived data.
            if hasattr(self, 'usage_canvas'):
                self._draw_usage_bar()
            if hasattr(self, 'file_tree'):
                for tree in (self.file_tree, self.folder_tree):
                    tree.tag_configure('deleted', foreground='#f1b85f' if self.theme == 'dark' else '#b45309')
                    tree.tag_configure('warning', foreground='#ff827d' if self.theme == 'dark' else '#b91c1c')
            if hasattr(self, '_nav_buttons'):
                self._update_main_tab_styles()

    def _apply_theme(self):
        c = self._palette()
        style = apply_theme(self, self.theme)
        # Keep existing Tenshi fonts and layout metrics; upstream supplies the
        # widget artwork, interaction states and colors.
        style.configure('.', background=c['bg'], foreground=c['text'],
                        font='TkDefaultFont', selectbackground=c['select'],
                        selectforeground=c['selection_text'], fieldbackground=c['input'])
        style.configure('Card.TFrame', background=c['panel'])
        style.configure('TLabel', font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 20, 'bold'))
        style.configure('Sub.TLabel', foreground=c['muted'])
        style.configure('TButton', font=('Segoe UI', 10), padding=(10, 7))
        style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'), padding=(12, 8))
        for name in ('Header.TButton', 'Header.TMenubutton'):
            style.configure(name, font=('Segoe UI', 10), padding=(10, 7))
        style.configure('Treeview', font=('Segoe UI', 10), rowheight=27)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
        style.layout('TenshiHidden.TNotebook.Tab', [])
        for option, value in (('background', c['input']), ('foreground', c['text']),
                              ('selectBackground', c['select']),
                              ('selectForeground', c['selection_text'])):
            self.option_add('*TCombobox*Listbox.' + option, value)
        self._style_native_widgets(self)
        if hasattr(self, '_nav_buttons'):
            self._update_main_tab_styles()
        if hasattr(self, '_compact_layout'):
            # Theme configuration resets padding/row heights; restore the active
            # compact metrics even when the window dimensions did not change.
            self._compact_layout = None
            self._update_compact_layout()

    def _on_popup_map(self, event):
        popup = event.widget
        if isinstance(popup, tk.Toplevel) and popup is not self and not isinstance(popup, HelpWindow):
            self.after_idle(lambda w=popup: self._style_native_widgets(w) if w.winfo_exists() else None)

    def _setup_style(self):
        self._apply_theme()

    def _build(self):
        # User-provided Tenshi logo replaces the former text title.
        header = ttk.Frame(self, padding=(22, 8, 22, 3))
        header.pack(fill="x")
        header.columnconfigure(1, weight=1)
        self._header_actions = ttk.Frame(header)
        self._header_actions.grid(row=0, column=2, sticky="ne")
        # Top-right language switcher; native names make each language findable.
        self._language_var = tk.StringVar(value=self.language)
        self._language_button = ttk.Menubutton(
            self._header_actions, text='🌐  ' + LANGUAGES[self.language], direction='below',
            style='Header.TMenubutton', width=18)
        self._language_menu = tk.Menu(self._language_button, tearoff=False)
        for language_code, native_label in LANGUAGES.items():
            self._language_menu.add_radiobutton(
                label=native_label, value=language_code, variable=self._language_var,
                command=lambda code=language_code: self.change_language(code))
        self._language_button.configure(menu=self._language_menu)
        self._language_button.grid(row=0, column=3, sticky='nsew', padx=3, pady=(9, 0))
        self._theme_var = tk.StringVar(value=self.theme_mode)
        self.theme_button = ttk.Menubutton(self._header_actions, text='◐  Darstellung', direction='below',
                                               style='Header.TMenubutton', width=18)
        self._theme_menu = tk.Menu(self.theme_button, tearoff=False)
        for label, value in (('System', 'system'), ('Hell', 'light'), ('Dunkel', 'dark')):
            self._theme_menu.add_radiobutton(label=label, value=value, variable=self._theme_var,
                command=lambda theme=value: self.change_theme(theme))
        self.theme_button.configure(menu=self._theme_menu)
        self.theme_button.grid(row=0, column=2, sticky='nsew', padx=3, pady=(9, 0))
        self.help_button = ttk.Button(self._header_actions, text='Hilfe', command=self.show_help,
                                      style='Header.TButton', width=18)
        self.help_button.grid(row=0, column=1, sticky='nsew', padx=3, pady=(9, 0))
        self.error_log_button = ttk.Button(self._header_actions, text='Fehlerprotokoll',
                                           command=self.show_error_log, style='Header.TButton', width=18)
        self.error_log_button.grid(row=0, column=0, sticky='nsew', padx=3, pady=(9, 0))
        for column in range(4):
            self._header_actions.columnconfigure(column, uniform='header_buttons')
        self.brand_logo = tk.PhotoImage(file=str(asset_path("tenshi_logo.png")))
        self.brand_icon = tk.PhotoImage(file=str(asset_path("tenshi_icon.png")))
        self.iconphoto(True, self.brand_icon)
        if os.name == "nt":
            try:
                self.iconbitmap(str(asset_path("tenshi.ico")))
            except tk.TclError:
                pass  # The embedded PNG icon remains available.
        self.logo_label = tk.Label(header, image=self.brand_logo, background="#f3f5f8", borderwidth=0,
                                   highlightthickness=0)
        self.logo_label.grid(row=0, column=0, sticky="w")
        description = ttk.Frame(header)
        self._header_description = description
        self._compact_brand_logo = self.brand_logo.subsample(2, 2)
        description.grid(row=0, column=1, sticky="ew", padx=(18, 0))
        self._header_title = ttk.Label(description, text="Datenrettung & schreibgeschützte Datenträgeranalyse",
                  font=("Segoe UI", 13, "bold"))
        self._header_title.pack(anchor="w", fill="x", pady=(2, 2))
        self._header_subtitle = ttk.Label(description, text="NTFS · FAT32 · exFAT · ext2/3/4 · Btrfs · XFS  |  Partitionen · Dateien & Ordner",
                  style="Sub.TLabel")
        self._header_subtitle.pack(anchor="w", fill="x")
        self._header_wrap_job = None
        self._header_wrap_width = None
        description.bind('<Configure>', self._schedule_header_wrap)

        # Two rows keep all source actions accessible even with Windows display scaling.
        source = ttk.Frame(self, padding=(12, 2, 12, 2))
        source.pack(fill="x")
        source.columnconfigure(1, weight=1)
        ttk.Label(source, text="Ausgewählte Quelle:").grid(row=0, column=0, sticky="w")
        source_entry = ttk.Entry(source, textvariable=self.source_path)
        source_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        source_entry.bind('<Return>', self._accept_source_entry)
        source_actions = ttk.Frame(source)
        source_actions.grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))
        ttk.Button(source_actions, text="Image auswählen", command=self.choose_source).pack(side="left")
        self.source_picker_button = ttk.Button(
            source_actions, text="Datenträger oder Laufwerk auswählen", command=self._choose_sources)
        self.source_picker_button.pack(side="left", padx=(10, 0))
        ttk.Button(source_actions, text="Image erstellen / fortsetzen",
                   command=self.open_imaging_dialog).pack(side="left", padx=(10, 0))
        session_actions = ttk.Menubutton(source_actions, text='Analysesitzung')
        session_menu = tk.Menu(session_actions, tearoff=False)
        session_menu.add_command(label='Sitzung speichern', command=self.save_analysis_session)
        session_menu.add_command(label='Sitzung laden', command=self.load_analysis_session)
        session_actions.configure(menu=session_menu)
        session_actions.pack(side='left', padx=(5, 0))
        self.session_menu_button = session_actions
        self.session_menu = session_menu

        body = ttk.Frame(self, padding=(12, 0, 12, 2))
        body.pack(fill="both", expand=True)
        # Clearly visible custom navigation instead of low-contrast native tabs.
        self._tab_nav = tk.Frame(body, bg=self._palette()['inactive'], padx=5, pady=5)
        self._tab_nav.pack(fill='x', pady=(0, 5))
        self._nav_buttons = {}
        for name, label in (('partition', '▦  Partitionen'),
                            ('files', '📁  Dateien & Ordner')):
            btn = tk.Button(self._tab_nav, text=label,
                font=('Segoe UI', 12, 'bold'), padx=14, pady=4,
                relief='flat', bd=0, cursor='hand2', takefocus=True,
                command=lambda key=name: self._select_main_tab(key))
            btn.pack(side='left', fill='x', expand=True, padx=3)
            self._nav_buttons[name] = btn
        # Hide small system-themed tab labels; the large buttons above are the navigation.
        style = ttk.Style(self)
        style.layout('TenshiHidden.TNotebook.Tab', [])
        self.tabs = ttk.Notebook(body, style='TenshiHidden.TNotebook')
        self.tabs.pack(fill="both", expand=True)
        self.partition_tab = ttk.Frame(self.tabs, padding=12)
        self.ntfs_tab = ttk.Frame(self.tabs, padding=12)
        self.ntfs_entries = []
        self.scan_report_text = None
        self.ntfs_source = None
        self.ntfs_partition_offset = 0
        self.ntfs_scanning = False
        self.partition_scanning = False
        self.partitions = []
        self.last_partition_report = None
        self.partition_source = None
        self.partition_details = {}
        self.partition_diagnosing = False
        self._source_generation = 0
        self._pending_source_quick_scan = None
        self._partition_fingerprint = None
        self._browser_fingerprint = None
        self._session_running = False
        self.tabs.add(self.partition_tab, text="Partitionen")
        self.tabs.add(self.ntfs_tab, text="Dateien & Ordner")
        self.tabs.bind('<<NotebookTabChanged>>', self._update_main_tab_styles)
        self._update_main_tab_styles()
        self._build_partitions()
        self._build_ntfs()
        self.status_bar = ttk.Frame(self, padding=(12, 2, 12, 3))
        # Reserve progress BEFORE the expanding body takes its requested space.
        self.status_bar.pack(side='bottom', fill='x', before=body)
        self.status_label = ttk.Label(self.status_bar, textvariable=self.status, style='Sub.TLabel')
        self.status_label.pack(anchor='w', fill='x')
        self._footer_warning = ttk.Label(self.status_bar, text="Bei Hardwaredefekt weitere Lesezugriffe minimieren und möglichst ein schonendes Image erstellen. Gerettete Daten nur auf einem anderen physischen Datenträger speichern.",
                                        foreground='#9a3412')
        self._footer_warning.pack(anchor='w', pady=(1, 0))

    def _schedule_header_wrap(self, event):
        self._pending_header_width = max(100, event.width)
        if self._header_wrap_job is None:
            self._header_wrap_job = self.after(40, self._flush_header_wrap)

    def _flush_header_wrap(self):
        self._header_wrap_job = None
        width = self._pending_header_width
        if width != self._header_wrap_width:
            self._header_wrap_width = width
            self._header_title.configure(wraplength=width)
            self._header_subtitle.configure(wraplength=width)

    def _update_compact_layout(self, event=None):
        """Reclaim browser height in short windows without hiding actions."""
        if event is not None and event.widget is not self:
            return
        compact = self.winfo_height() <= 800
        narrow = self.winfo_width() < 1400
        layout = (compact, narrow)
        if self._compact_layout == layout:
            return
        self._compact_layout = layout
        self.logo_label.configure(image=self._compact_brand_logo if narrow else self.brand_logo)
        self._header_description.grid_forget()
        if narrow:
            self._header_actions.grid_configure(column=1)
            self._header_description.grid(row=1, column=0, columnspan=2,
                                          sticky='ew', pady=(3, 0))
        else:
            self._header_actions.grid_configure(column=2)
            self._header_description.grid(row=0, column=1, sticky='ew', padx=(18, 0))
        self._header_title.configure(font=('Segoe UI', 10 if compact else 13, 'bold'))
        # All functional controls remain available; reduce only decorative space.
        style = ttk.Style(self)
        style.configure('TButton', padding=(7, 2) if compact else (10, 7))
        style.configure('Accent.TButton', padding=(8, 3) if compact else (12, 8))
        for name in ('Header.TButton', 'Header.TMenubutton'):
            style.configure(name, padding=(7, 2) if compact else (10, 7))
        style.configure('TCheckbutton', padding=1 if compact else 4)
        self.export_button.configure(pady=2 if compact else 7)
        for tab in (self.partition_tab, self.ntfs_tab):
            tab.configure(padding=(8, 2) if compact else 12)
        # Keep the live status line visible at every supported window size.
        # The long, repeated safety caption yields space in compact mode.
        if compact:
            self._footer_warning.pack_forget()
        else:
            self._footer_warning.pack(anchor='w', pady=(1, 0))
        for row, regular in self._browser_spacing:
            row.pack_configure(pady=(0, 2) if compact else (0, regular))
        style.configure('Treeview', rowheight=22 if compact else 27)

    def _select_main_tab(self, name: str):
        target = self.partition_tab if name == 'partition' else self.ntfs_tab
        self.tabs.select(target)
        self._update_main_tab_styles()

    def _update_main_tab_styles(self, event=None):
        selected = self.tabs.select()
        colors = self._palette()
        self._tab_nav.configure(bg=colors['inactive'])
        for name, button in self._nav_buttons.items():
            active = selected == str(self.partition_tab if name == 'partition' else self.ntfs_tab)
            button.configure(
                bg=colors['nav'] if active else colors['inactive'],
                fg='#ffffff' if active else colors['inactive_fg'],
                activebackground=colors['nav'] if active else colors['select'],
                activeforeground='#ffffff',
                relief='sunken' if active else 'flat',
                borderwidth=2 if active else 0)

    def _reset_analysis_for_source(self):
        """Prevent displaying results belonging to a previously selected source."""
        self._source_generation += 1
        self._pending_source_quick_scan = None
        self.browser_cancel.set()
        self._partition_fingerprint = None
        self._browser_fingerprint = None
        self.partitions = []
        self.last_partition_report = None
        self.partition_source = None
        self.partition_details = {}
        if hasattr(self, 'usage_canvas'):
            self._usage_for_chart = None
            self._draw_usage_bar()
        if hasattr(self, 'partition_detail_text'):
            self._write_partition_details('Partition auswählen und „Ausgewählte Partition prüfen“ anklicken.')
        self.part_tree.delete(*self.part_tree.get_children())
        self.partition_summary.set('Neue Quelle ausgewählt. Schnellanalyse startet automatisch.')
        if hasattr(self, 'partition_quality_summary'):
            self.partition_quality_summary.set('')
        self._clear_browser_results()
        if hasattr(self, 'browser_status_filter'):
            self.browser_status_filter.set(FILTER_ALL)
            if hasattr(self, 'browser_status_display'):
                self.browser_status_display.set(translate(FILTER_ALL, self.language))
        if hasattr(self, 'browser_filter_summary'):
            self.browser_filter_summary.set('')
        self.ntfs_byte_offset.set('0')
        if hasattr(self, 'browser_search'):
            self.browser_search.set('')
        if hasattr(self, 'browser_extension'):
            self.browser_extension.set('')
        if hasattr(self, 'browser_min_size'):
            self.browser_min_size.set('')
        if hasattr(self, 'browser_max_size'):
            self.browser_max_size.set('')
        if hasattr(self, 'browser_kind'):
            self.browser_kind.set('Alle')
        if hasattr(self, 'browser_kind_display'):
            self.browser_kind_display.set(translate('Alle', self.language))
        if hasattr(self, 'browser_search_paths'):
            self.browser_search_paths.set(False)

    def _clear_browser_results(self):
        """Invalidate cached entries before a replacement scan can fail."""
        self._browser_fingerprint = None
        self.browser_index = None
        self.browser_source = None
        self.ntfs_entries = []
        self.scan_report_text = None
        self.ntfs_source = None
        self.folder_tree.delete(*self.folder_tree.get_children())
        self.file_tree.delete(*self.file_tree.get_children())
        self.browser_search_generation += 1
        self.browser_entries_visible = {}
        self.browser_display = []
        self.browser_sorted_items = []
        self.browser_page_items = []
        self.browser_page = 0
        self.browser_paths = {}
        if hasattr(self, 'browser_page_caption'):
            self._update_browser_page_caption()
        self.browser_nodes = {}
        self.browser_warning_records = set()
        self.browser_warning_files = {}

    def _scan_source_matches(self, generation, source):
        return (generation == self._source_generation and
                self.source_path.get().strip() == source)

    def _activate_source_and_quick_scan(self, source: str):
        """Switch to Partitionen and scan the new source, exclusively read-only.

        A running older partition scan is allowed to finish; its results are
        discarded and the latest selected source is scanned next. This avoids
        simultaneous scans of a device and stale results in the UI.
        """
        self._reset_analysis_for_source()
        self.source_path.set(source)
        self._select_main_tab('partition')
        self.status.set(f'Quelle ausgewählt: {source} (nur lesen). Schnellanalyse startet …')
        if self.partition_scanning:
            self._pending_source_quick_scan = source
            self.status.set('Quelle gewechselt. Schnellanalyse startet nach dem laufenden Scan …')
        else:
            self.scan_partitions(False)

    def _accept_source_entry(self, _event=None):
        """Confirm an image/device path typed directly into the source field."""
        try:
            source = self.get_source()
        except (OSError, ValueError) as exc:
            messagebox.showerror('Quelle auswählen', str(exc), parent=self)
            return 'break'
        self._activate_source_and_quick_scan(source)
        return 'break'

    def choose_source(self):
        p = filedialog.askopenfilename(title="Datenträgerabbild auswählen",
             filetypes=[("Disk-Images", "*.img *.dd *.bin *.raw *.iso"), ("Alle Dateien", "*.*")])
        if p:
            self._activate_source_and_quick_scan(p)

    def get_source(self):
        p = self.source_path.get().strip()
        if not p:
            raise ValueError("Bitte zuerst ein Datenträgerabbild auswählen.")
        return validate_source(p)

    def show_volumes(self):
        return self._choose_sources()

    def _show_volume_dialog(self, volumes):
        # Compatibility entry point; the toolbar uses the combined picker.
        choices = volume_choices(volumes)
        return self._show_source_dialog(choices, preselect=not any(
            c.source.startswith('/dev/') for c in choices))

    def _choose_sources(self):
        existing = getattr(self, '_source_picker', None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            return existing
        win = self._show_source_dialog([], loading=True)
        self._source_picker = win

        def discover():
            try:
                choices, warnings = collect_choices()
            except Exception as exc:
                log_issue('source_discovery', exc)
                choices, warnings = [], ['Quellen konnten nicht ermittelt werden.']
            if not self._closing:
                self._post_scan_callback(lambda: win.populate_sources(choices, warnings)
                    if win.winfo_exists() else None)

        threading.Thread(target=discover, daemon=True, name='Tenshi source discovery').start()
        return win

    def _show_source_dialog(self, choices, *, loading=False, preselect=False):
        win = tk.Toplevel(self)
        win.title('Datenträger oder Laufwerk auswählen – nur lesen')
        win.geometry('960x560')
        win.minsize(760, 450)
        win.transient(self)
        win.columnconfigure(0, weight=1)
        win.rowconfigure(1, weight=1)
        intro = ttk.Label(win, wraplength=900, text=
            'Ein gesamter Datenträger umfasst alle Partitionen. Ein Laufwerk umfasst nur '
            'das ausgewählte Volume. Zugeordnete Laufwerke stehen unter ihrem Datenträger.')
        intro.grid(row=0, column=0, sticky='ew', padx=16, pady=(14, 8))
        panel = ttk.Frame(win)
        panel.grid(row=1, column=0, sticky='nsew', padx=16)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)
        tree = ttk.Treeview(panel, columns=('kind', 'fs', 'size'), show='tree headings', selectmode='browse')
        for column, caption, width in (('#0', 'Quelle', 300), ('kind', 'Umfang', 210),
                                       ('fs', 'Dateisystem', 100), ('size', 'Größe (GiB)', 110)):
            tree.heading(column, text=caption)
            tree.column(column, width=width, minwidth=185 if column == '#0' else 75,
                        stretch=column in ('#0', 'kind'))
        tree.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(panel, orient='vertical', command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        tree.configure(yscrollcommand=scrollbar.set)
        horizontal = ttk.Scrollbar(panel, orient='horizontal', command=tree.xview)
        horizontal.grid(row=1, column=0, sticky='ew')
        tree.configure(xscrollcommand=horizontal.set)
        selection_text = tk.StringVar(value='')
        selection_label = ttk.Label(win, textvariable=selection_text, wraplength=900)
        selection_label.grid(row=2, column=0, sticky='ew', padx=16, pady=8)
        actions = ttk.Frame(win)
        actions.grid(row=3, column=0, sticky='ew', padx=16, pady=(0, 8))
        confirm_button = ttk.Button(actions, text='Auswahl übernehmen (nur lesen)',
                                    style='Accent.TButton', state='disabled')
        confirm_button.pack(side='right')
        ttk.Button(actions, text='Abbrechen', command=win.destroy).pack(side='right', padx=(0, 10))
        hint = ('Die Auflistung bestätigt keine Leserechte. Für das tatsächliche Einlesen beider '
                'Quelltypen können Windows-Administratorrechte erforderlich sein.' if os.name == 'nt' else
                'Die Auflistung bestätigt keine Leserechte. Geräteberechtigungen gezielt prüfen lassen '
                'oder ein Image öffnen. Tenshi ohne sudo starten.')
        warning = ttk.Label(win, text=hint + '\n' +
            'Eingehängte Dateisysteme können sich durch das Betriebssystem verändern. '
            'Bei defekten Datenträgern weitere Lesezugriffe minimieren und zuerst ein Image erstellen.',
            foreground='#9a3412', wraplength=900)
        warning.grid(row=4, column=0, sticky='ew', padx=16, pady=(0, 12))
        last_wrap = [None]
        def resize_labels(event):
            if event.widget is win:
                width = max(200, event.width - 32)
                if width != last_wrap[0]:
                    last_wrap[0] = width
                    for widget in (intro, selection_label, warning):
                        widget.configure(wraplength=width)
        win.bind('<Configure>', resize_labels, add='+')
        records = {}

        def update_selection(_event=None):
            selected = tree.selection()
            record = records.get(selected[0]) if selected else None
            confirm_button.configure(state='normal' if record else 'disabled')
            if record:
                kind = 'Gesamter Datenträger' if record.kind == 'disk' else 'Laufwerk / Partition'
                selection_text.set(translate(kind, self.language) + ': ' + record.source)
            elif records:
                selection_text.set(translate('Bitte einen Datenträger oder ein Laufwerk markieren.', self.language))

        def populate(rows, warnings=()):
            records.clear()
            tree.delete(*tree.get_children())
            confirm_button.configure(state='disabled')
            for row in rows:
                if row.key in records:
                    continue
                records[row.key] = row
            for row in records.values():
                if row.kind == 'disk':
                    caption = translate('Datenträger', self.language) + ' ' + row.label if row.label else row.key
                    tree.insert('', 'end', iid=row.key, text=caption, open=True,
                        values=(translate('Gesamter Datenträger', self.language), '', f'{row.size/1024**3:.2f}'))
            ungrouped = '__unmapped_volumes__'
            for row in records.values():
                if row.kind != 'volume':
                    continue
                parent = row.parent if tree.exists(row.parent) else ''
                if not parent:
                    if not tree.exists(ungrouped):
                        tree.insert('', 'end', iid=ungrouped, open=True,
                            text=translate('Laufwerke ohne eindeutige Zuordnung', self.language))
                    parent = ungrouped
                kind = 'Laufwerk (mehrere Datenträger)' if row.mapping == 'multiple' else 'Laufwerk / Partition'
                tree.insert(parent, 'end', iid=row.key,
                    text=row.key + (' — ' + row.label if row.label else ''),
                    values=(translate(kind, self.language), row.filesystem, f'{row.size/1024**3:.2f}'))
            message = ('Bitte einen Datenträger oder ein Laufwerk markieren.' if records else
                       'Keine Quellen erkannt. Ein vorhandenes Image kann weiterhin geöffnet werden.')
            selection_text.set('\n'.join([translate(message, self.language)] +
                [translate(item, self.language) for item in warnings]))
            if preselect and records:
                key = next(iter(records))
                tree.selection_set(key)
                tree.focus(key)
                tree.see(key)
                update_selection()

        def confirm(_event=None):
            selected = tree.selection()
            row = records.get(selected[0]) if selected else None
            if row is None:
                return
            self._confirm_picked_source(row, win)

        def double_click(event):
            if tree.identify_region(event.x, event.y) not in ('tree', 'cell'):
                return
            if 'indicator' in str(tree.identify_element(event.x, event.y)).lower():
                return
            key = tree.identify_row(event.y)
            if key not in records:
                return
            tree.selection_set(key)
            tree.focus(key)
            update_selection()
            confirm()

        win.populate_sources = populate
        win._source_double_click = double_click
        win.source_tree = tree
        win.confirm_button = confirm_button
        confirm_button.configure(command=confirm)
        tree.bind('<<TreeviewSelect>>', update_selection)
        tree.bind('<Double-1>', double_click)
        tree.bind('<Return>', confirm)
        win.bind('<Escape>', lambda _event: win.destroy())
        if loading:
            selection_text.set(translate('Quellen werden ermittelt …', self.language))
        else:
            populate(choices)
        tree.focus_set()
        return win

    def _confirm_picked_source(self, row, dialog):
        kind = 'Gesamter Datenträger' if row.kind == 'disk' else 'Laufwerk / Partition'
        prompt = translate(kind, self.language) + ': ' + row.source + '\n\n' + translate(
            'Tenshi öffnet die Quelle ausschließlich lesend. Weitere Lesezugriffe können '
            'defekte Datenträger belasten. Quelle übernehmen?', self.language)
        if not messagebox.askyesno('Direkter Laufwerkszugriff', prompt, parent=dialog):
            return
        try:
            with open_source(row.source) as stream:
                stream.seek(0)
                if len(stream.read(512)) < 512:
                    raise OSError('Es konnten keine 512 Bytes gelesen werden.')
        except (OSError, ValueError) as exc:
            hint = ('Für direkte Lesezugriffe auf Datenträger und Laufwerke Windows-Administratorrechte '
                    'prüfen oder ein Image öffnen.' if os.name == 'nt' else
                    'Geräteberechtigungen gezielt prüfen lassen oder ein Image öffnen. Tenshi ohne sudo starten.')
            messagebox.showerror('Quelle nicht lesbar', str(exc) + '\n\n' + translate(hint, self.language),
                                 parent=dialog)
            return
        dialog.destroy()
        self._activate_source_and_quick_scan(row.source)

    def open_imaging_dialog(self):
        """Create a read-only source -> new regular-file image with a resumable map."""
        previous=self.__dict__.get('_imaging_dialog')
        if previous is not None and previous.winfo_exists() and self._imaging_session['running']:
            previous.show_progress()
            return previous
        try:
            src = self.get_source()
            total = source_size(src)
        except Exception as exc:
            messagebox.showerror('Image erstellen', 'Bitte zuerst einen Datenträger oder ein vorhandenes Image auswählen.\n\n' + str(exc), parent=self)
            return
        if previous is not None and previous.winfo_exists():
            if previous.imaging_source==src:
                previous.deiconify();previous.lift()
                return previous
            view=self._imaging_session.get('window')
            if view is not None and view.winfo_exists():view.destroy()
            previous.destroy()
        win = tk.Toplevel(self)
        self._imaging_dialog=win
        win.imaging_source=src
        win.title('Tenshi – Image erstellen / fortsetzen')
        win.geometry('875x475')
        win.minsize(750, 445)
        win.transient(self)
        win.columnconfigure(1, weight=1)
        src_txt = src if len(src) < 110 else src[:54] + ' … ' + src[-50:]
        ttk.Label(win, text='Quelle (nur lesen):').grid(row=0, column=0, sticky='w', padx=16, pady=(16, 6))
        ttk.Label(win, text=src_txt, wraplength=520).grid(row=0, column=1, columnspan=2, sticky='w', padx=8, pady=(16, 6))
        ttk.Label(win, text=f'Gesamtgröße: {readable_bytes(total)}').grid(row=1, column=1, sticky='w', padx=8)
        ttk.Label(win, text='Ziel-Image:').grid(row=2, column=0, sticky='w', padx=16, pady=(15, 5))
        target_var = tk.StringVar()
        ttk.Entry(win, textvariable=target_var).grid(row=2, column=1, sticky='ew', padx=8, pady=(15, 5))
        def pick_target():
            chosen = filedialog.asksaveasfilename(parent=win, title='Neues Image oder bestehendes Image zur Fortsetzung wählen',
                        defaultextension='.img', filetypes=[('Image-Datei', '*.img'), ('Alle Dateien', '*.*')])
            if chosen:
                target_var.set(chosen)
        ttk.Button(win, text='Durchsuchen …', command=pick_target).grid(row=2, column=2, padx=(0, 16), pady=(15, 5))
        ttk.Label(win, text='Blockgröße:').grid(row=3, column=0, padx=16, pady=(10, 4), sticky='w')
        block_choice = tk.StringVar(value='1 MiB')
        settings_bar = ttk.Frame(win)
        settings_bar.grid(row=3, column=1, columnspan=2, sticky='w', padx=8, pady=(10, 4))
        block_box = ttk.Combobox(settings_bar, state='readonly', values=['1 MiB', '4 MiB'],
                                 textvariable=block_choice, width=8)
        block_box.pack(side='left')
        ttk.Label(settings_bar, text='Leseversuche:').pack(side='left', padx=(12, 4))
        retry_choice = tk.StringVar(value='0')
        ttk.Combobox(settings_bar, state='readonly', values=['0', '1', '2', '3'],
                     textvariable=retry_choice, width=3).pack(side='left')
        ttk.Label(settings_bar, text='Bei Medienfehler:').pack(side='left', padx=(12, 4))
        failure_choice = tk.StringVar(value=translate('Sicher anhalten', self.language))
        ttk.Combobox(settings_bar, state='readonly',
                     values=[translate('Nullen + protokollieren', self.language),
                             translate('Sicher anhalten', self.language)],
                     textvariable=failure_choice, width=23).pack(side='left')
        verify_var = tk.BooleanVar(value=not is_device_source(src))
        ttk.Checkbutton(win, text='Image bitgenau prüfen', variable=verify_var).grid(
            row=4, column=0, sticky='w', padx=16, pady=(7, 4))
        ttk.Label(win, text=('Vollvergleich liest Quelle und Ziel nochmals vollständig. '
                             'Auf beschädigten physischen Datenträgern nur bewusst aktivieren! '
                             'Nullersatz wegen Lesefehlern kann nicht bitgenau bestätigt werden.'),
                  wraplength=600, foreground='#9a3412').grid(
                      row=4, column=1, columnspan=2, sticky='ew', padx=8, pady=(7, 4))
        progress_button=ttk.Button(win,text='Fortschritt / Ergebnis')
        progress_button.grid(row=5,column=0,columnspan=3,padx=16,pady=(12,2),sticky='ew')
        stats = tk.StringVar(value='Noch nicht gestartet.')
        ttk.Label(win, textvariable=stats, wraplength=725).grid(row=7, column=0, columnspan=3,
                                                                sticky='ew', padx=16, pady=(4, 8))
        buttons = ttk.Frame(win)
        buttons.grid(row=8, column=0, columnspan=3, padx=16, pady=(12, 6), sticky='ew')
        begin = ttk.Button(buttons, text='Image erstellen / fortsetzen', style='Accent.TButton')
        begin.pack(side='left')
        pause = ttk.Button(buttons, text='Unterbrechen', state='disabled')
        pause.pack(side='left', padx=10)
        report_button = ttk.Button(buttons, text='Fehlerstellen-Bericht', state='disabled')
        report_button.pack(side='left', padx=8)
        close_button = ttk.Button(buttons, text='Schließen')
        close_button.pack(side='right')
        ttk.Label(win, text='Schreibzugriffe erfolgen nur auf die Image-Zieldatei (neu oder fortgesetzt) und ihre Statusdateien, nicht auf das Quellmedium. '
                  'Für mechanisch defekte Laufwerke spezialisierte, schonende Imaging-Verfahren verwenden.',
                  foreground='#9a3412', wraplength=725).grid(row=9, column=0, columnspan=3,
                                                              sticky='ew', padx=16, pady=(8, 10))
        events = queue.SimpleQueue()
        stop = threading.Event()
        active = {'running': False, 'started': 0.0, 'ended': None, 'state': None,
                  'report': None, 'baseline': None, 'stop':stop,'blocks':ImagingBlocks(total=total),
                  'destination':'','error':'','saving':False,'window':None}
        self._imaging_session=active

        def save_bad_report():
            saved=active.get('report')
            if active['running'] or not saved or active['saving']:return
            folder=os.path.dirname(active['destination'])
            name=filedialog.asksaveasfilename(parent=self,initialdir=folder,
                initialfile='Tenshi_Imagebericht_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]+'.txt',
                defaultextension='.txt',filetypes=[('Textdatei','*.txt')],title='Fehlerstellen-Bericht speichern')
            if not name:return
            active['saving']=True
            def finish(error):
                active['saving']=False
                view=active.get('window')
                if view is not None and view.winfo_exists():view.refresh_display()
                if error:messagebox.showerror('Fehlerstellen-Bericht',error,parent=self)
                else:messagebox.showinfo('Fehlerstellen-Bericht','Bericht gespeichert.',parent=self)
            def write():
                try:
                    from .secure_target import open_regular_output
                    ensure_safe_destination(src,name)
                    data=describe_bad_ranges(saved).encode('utf-8')
                    with open_regular_output(name,'xb',src) as output:
                        view=memoryview(data)
                        while view:
                            written=output.write(view)
                            if not written:raise OSError('Bericht konnte nicht vollständig geschrieben werden.')
                            view=view[written:]
                        output.flush();os.fsync(output.fileno())
                    error=''
                except Exception as exc:error=export_error_message(exc,self.language)
                self._post_scan_callback(lambda error=error:finish(error))
            threading.Thread(target=write,daemon=True).start()

        def open_folder():
            folder=os.path.dirname(active['destination'])
            if not os.path.isdir(folder):return
            try:
                if os.name=='nt':os.startfile(folder)
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open',folder],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            except OSError as exc:messagebox.showerror('Image erstellen',export_error_message(exc,self.language),parent=self)

        def request_pause():
            if active['running']:
                stop.set();stats.set('Unterbrechung angefordert …')

        def show_progress():
            view=active.get('window')
            if view is not None and view.winfo_exists():
                view.deiconify();view.lift();view.refresh_display()
            else:
                view=active['window']=ImagingProgressWindow(self,active,pause=request_pause,
                    report=show_bad_report,save=save_bad_report,folder=open_folder,
                    settings=lambda:(win.deiconify(),win.lift()))
            return view
        win.show_progress=show_progress
        progress_button.configure(command=show_progress)

        def show_bad_report():
            saved = active.get('report')
            if not saved:
                return
            report = describe_bad_ranges(saved)
            dialog = tk.Toplevel(self)
            dialog.title('Tenshi – Fehlerstellen-Bericht')
            dialog.geometry('750x390')
            body = ttk.Frame(dialog, padding=12)
            body.pack(fill='both', expand=True)
            output = tk.Text(body, wrap='none', font=('Consolas', 10))
            output.pack(fill='both', expand=True)
            # Keep huge maps responsive; the text export can retain the whole map.
            output.insert('1.0', report[:128 * 1024] +
                          ('\n… (Anzeige gekürzt; vollständigen Bericht speichern)' if len(report) > 128 * 1024 else ''))
            output.configure(state='disabled')
            ttk.Button(body, text='Bericht speichern', command=save_bad_report).pack(anchor='e', pady=(8, 0))

        def leave():
            win.withdraw()

        def update_progress(item):
            active['state'] = item.state
            active['blocks'].handle(item)
            elapsed = max(time.monotonic() - active['started'], 0.001)
            if active['baseline'] is None:
                active['baseline'] = item.processed
            if item.state=='verifying':
                stats.set('Vollvergleich läuft …')
                return
            speed = max(0, item.processed - active['baseline']) / elapsed
            remaining = ((item.total - item.processed) / speed) if speed > 0 else 0
            stats.set(f'{readable_bytes(item.processed)} von {readable_bytes(item.total)} · '
                      f'{readable_bytes(speed)}/s · ca. {remaining / 60:.1f} min Restzeit · '
                      f'nicht lesbar: {readable_bytes(item.unreadable_bytes)} '
                      f'({item.bad_range_count} Bereich/e) · {item.state}')

        def poll():
            if not win.winfo_exists():
                return
            for _ in range(200):
                try:
                    kind, item = events.get_nowait()
                except queue.Empty:
                    break
                if kind == 'progress':
                    update_progress(item)
                elif kind in ('finished', 'error'):
                    active['running'] = False
                    active['ended'] = time.monotonic()
                    begin.configure(state='normal')
                    pause.configure(state='disabled')
                    if kind == 'error':
                        active['error']=str(item)
                        stats.set('Image-Erstellung fehlgeschlagen: ' + str(item))
                        messagebox.showerror('Image erstellen', str(item), parent=self)
                    else:
                        state = item
                        active['state']=state['state']
                        active['report'] = state
                        report_button.configure(state='normal')
                        status = state['state']
                        txt = (f'Status: {status} · bearbeitet: {readable_bytes(state["processed"])} · '
                               f'nicht lesbar: {readable_bytes(state["unreadable_bytes"])}')
                        verify_status = state.get('verification', {}).get('status')
                        verified_text = ('\n\nBITGENAU VERIFIZIERT: Vollvergleich mit Quelle bestanden.'
                                         if verify_status == 'verified' else
                                         '\n\nACHTUNG: KEIN bestandener Vollvergleich; '
                                         'Image nicht als bitgenau verifiziert betrachten.')
                        stats.set(txt + (' · bitgenau geprüft' if verify_status == 'verified'
                                         else ' · NICHT bitgenau verifiziert'))
                        if status == 'complete':
                            dialog_text = 'Image-Erstellung beendet.\n\n' + txt + verified_text
                            if verify_status == 'verified':
                                messagebox.showinfo('Image erstellt und geprüft', dialog_text, parent=self)
                            else:
                                messagebox.showwarning('Image erstellt – ungeprüft', dialog_text +
                                    ('\n\nNicht lesbare Bereiche wurden mit Nullen ersetzt.' if state['bad_ranges']
                                     else '\n\nKein Vollvergleich vorgenommen.'), parent=self)
            view=active.get('window')
            if view is not None and view.winfo_exists():view.refresh_display()
            if active['running']:
                self._after_window(win, 100, poll)

        def selected_policy():
            # The top-right language may change while this dialog is open.
            # Never silently change the user's selected safety strategy.
            stop_labels = {'Sicher anhalten'} | {
                translate('Sicher anhalten', lang) for lang in LANGUAGES
            }
            return 'stop' if failure_choice.get() in stop_labels else 'zero'

        def start():
            if active['running'] or active['saving']:return
            dest = target_var.get().strip()
            if not dest:
                messagebox.showwarning('Image erstellen', 'Bitte einen Zielpfad auswählen.', parent=win)
                return
            resumed = os.path.exists(dest) or os.path.exists(sidecar_path(dest))
            if resumed and not (os.path.isfile(dest) and os.path.isfile(sidecar_path(dest))):
                messagebox.showerror('Image erstellen',
                    'Es existiert bereits eine Zieldatei ohne passenden Prüfpunkt. '
                    'Bitte einen neuen Namen wählen; vorhandene Dateien werden nicht überschrieben.', parent=win)
                return
            question = ('Bestehendes Image mit passendem Prüfpunkt kontrolliert fortsetzen?' if resumed else
                        'Neues Image als separate Datei anlegen?')
            if not messagebox.askyesno('Image erstellen',
                    f'{question}\n\nQuelle: {src}\nZiel: {dest}\n\n' +
                    ('Bestätigte Medien-Lesefehler führen zum sicheren Stopp. ' if
                     selected_policy() == 'stop' else
                     'Bestätigte Medien-Lesefehler werden mit Nullen gefüllt und protokolliert. ') +
                    'Das Original wird nicht verändert.', parent=win):
                return
            if is_device_source(src) and verify_var.get():
                if not messagebox.askyesno('Zusätzliche Belastung des Quelllaufwerks',
                        'Die vollständige Integritätsprüfung liest den physischen Datenträger '
                        'nach der Image-Erstellung erneut. Das kann ein defektes Medium '
                        'zusätzlich belasten. Trotzdem durchführen?', parent=win):
                    return
            active['started'] = time.monotonic()
            active['ended'] = None
            active['error'] = ''
            active['state'] = None
            active['blocks'] = ImagingBlocks(total=total)
            active['destination'] = os.path.abspath(dest)
            active['baseline'] = None
            active['running'] = True
            stop.clear()
            active['report'] = None
            report_button.configure(state='disabled')
            begin.configure(state='disabled')
            pause.configure(state='normal')
            block = 4 * 1024 * 1024 if block_choice.get() == '4 MiB' else 1024 * 1024
            retries = int(retry_choice.get())
            policy = selected_policy()
            # Never read a Tk variable from a worker thread. Tk access must
            # stay on the UI thread (also during headless/Xvfb tests).
            verify_requested = bool(verify_var.get())
            def work():
                try:
                    state = create_image(src, dest, resume=resumed, block_size=block,
                        read_retries=retries, retry_delay_ms=250, bad_sector_policy=policy,
                        verify=verify_requested, cancel=stop.is_set,
                        progress=lambda item: events.put(('progress', item)))
                    events.put(('finished', state))
                except Exception as exc:
                    events.put(('error', export_error_message(exc,self.language)))
            show_progress()
            gc.collect()
            threading.Thread(target=work, daemon=True).start()
            self._after_window(win, 100, poll)

        begin.configure(command=start)
        report_button.configure(command=show_bad_report)
        pause.configure(command=request_pause)
        close_button.configure(command=leave)
        win.protocol('WM_DELETE_WINDOW', leave)
        return win

    def _build_partitions(self):
        controls = ttk.Frame(self.partition_tab)
        controls.pack(fill="x", pady=(0, 10))
        self.quick_btn = ttk.Button(controls, text="Schnellanalyse (64 MiB)",
                                    style="Accent.TButton", command=lambda: self.scan_partitions(False))
        self.quick_btn.pack(side="left")
        self.deep_btn = ttk.Button(controls, text="Tiefensuche starten",
                                   command=lambda: self.scan_partitions(True))
        self.deep_btn.pack(side="left", padx=6)
        ttk.Label(controls, text="Limit (MiB, 0 = alles):").pack(side="left", padx=(10, 4))
        self.deep_limit = tk.StringVar(value="4096")
        ttk.Entry(controls, textvariable=self.deep_limit, width=9).pack(side="left")
        ttk.Label(controls, text="Sektorgröße:").pack(side="left", padx=(12, 4))
        self.sector_size = tk.StringVar(value="auto")
        ss = ttk.Combobox(controls, textvariable=self.sector_size,
                          values=("auto", "512", "4096"), width=6, state="readonly")
        ss.pack(side="left")
        diagnostic_actions = ttk.Frame(self.partition_tab)
        diagnostic_actions.pack(fill='x', pady=(0, 8))
        self.detail_btn = ttk.Button(diagnostic_actions, text='Ausgewählte Partition prüfen',
                                     command=self.check_selected_partition)
        self.detail_btn.pack(side='left')
        ttk.Button(diagnostic_actions, text='Partitionsbericht speichern',
                   command=self.save_partition_details).pack(side='left', padx=8)
        ttk.Button(diagnostic_actions, text='Fundliste speichern',
                   command=self.save_partition_findings).pack(side='left', padx=5)
        ttk.Label(diagnostic_actions, text='Nur Metadatenprüfung – keine Reparatur oder Vollprüfung',
                  style='Sub.TLabel').pack(side='left', padx=8)
        # This graphic is intentionally metadata-derived, not a physical block map.
        graphic = ttk.Frame(self.partition_tab)
        graphic.pack(fill='x', pady=(6, 0))
        self.usage_caption = tk.StringVar(value='Speicherbelegung: unbekannt – Partition auswählen und prüfen.')
        ttk.Label(graphic, textvariable=self.usage_caption, style='Sub.TLabel').pack(anchor='w')
        self.usage_canvas = tk.Canvas(graphic, height=18, highlightthickness=0,
                                      background='#e5e7eb', borderwidth=0)
        self.usage_canvas.pack(fill='x', pady=(4, 4))
        self._usage_redraw_job = None
        self._usage_draw_key = None
        self.usage_canvas.bind('<Configure>', self._schedule_usage_redraw)
        self._usage_for_chart = None
        cols = ("idx", "scheme", "confidence", "offset", "size", "filesystem", "usage", "health", "sector", "type", "name")
        self.part_tree = ttk.Treeview(self.partition_tab, columns=cols, show="headings")
        titles = {"idx": "Nr.", "scheme": "Erkennung", "confidence": "Plausibilität", "offset": "Byte-Offset",
                  "size": "Größe", "filesystem": "Dateisystem", "usage": "Belegt*", "health": "Struktur", "sector": "Sektor", "type": "Typ/GUID", "name": "Name"}
        widths = {"idx": 46, "scheme": 112, "confidence": 110, "offset": 135, "size": 110,
                  "filesystem": 95, "usage": 85, "health": 140, "sector": 65, "type": 165, "name": 145}
        for c in cols:
            self.part_tree.heading(c, text=titles[c])
            self.part_tree.column(c, width=self._view_settings['partitions_columns'].get(c, widths[c]), anchor="w", stretch=False)
        scroll = ttk.Scrollbar(self.partition_tab, orient="vertical", command=self.part_tree.yview)
        scroll_x = ttk.Scrollbar(self.partition_tab, orient="horizontal", command=self.part_tree.xview)
        self.part_tree.configure(yscrollcommand=scroll.set, xscrollcommand=scroll_x.set)
        scroll.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.part_tree.pack(fill="both", expand=True)
        self.part_tree.bind('<<TreeviewSelect>>', self._on_partition_selected)
        self.part_tree.bind('<Double-1>', self._open_partition_from_double_click)
        self.partition_detail_text = tk.Text(self.partition_tab, height=7, wrap='word',
                                             font=('Consolas', 9), state='disabled')
        self.partition_detail_text.pack(fill='x', pady=(8, 0))
        self._write_partition_details('Partition auswählen und „Ausgewählte Partition prüfen“ anklicken.')
        ttk.Label(self.partition_tab,
                  text='Doppelklick auf eine Partition: Dateisystem automatisch einlesen.',
                  style='Sub.TLabel').pack(anchor='w', pady=(5, 0))
        ttk.Label(self.partition_tab,
                  text="Gefundene Bootsektoren ohne Partitionstabelle sind Kandidaten, keine bestätigten Partitionen.",
                  foreground="#9a3412").pack(anchor="w", pady=(8, 2))
        self.partition_quality_summary = tk.StringVar(value='')
        ttk.Label(self.partition_tab, textvariable=self.partition_quality_summary,
                  style='Sub.TLabel').pack(anchor='w', pady=(2, 2))
        self.partition_summary = tk.StringVar(value="Quelle auswählen: Schnellanalyse startet automatisch.")
        ttk.Label(self.partition_tab, textvariable=self.partition_summary, wraplength=970,
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 5))
        self.partition_warnings = tk.Text(self.partition_tab, height=4, wrap="word",
                                          font=("Segoe UI", 9), state="disabled")
        self.partition_warnings.pack(fill="x")

    def scan_partitions(self, deep=False):
        if self.partition_scanning:
            return
        if self._session_running:
            self.status.set('Bitte laufenden Sitzungsvorgang zuerst abschließen.')
            return
        try:
            source = self.get_source()
            limit = int(self.deep_limit.get())
            if limit < 0 or limit > 1048576:
                raise ValueError("Das Suchlimit muss zwischen 0 und 1.048.576 MiB liegen.")
            sector = self.sector_size.get()
        except Exception as e:
            messagebox.showerror("Partitionsanalyse", str(e))
            return
        self.partition_scanning = True
        self.partition_source = source
        self.partition_details = {}
        self._source_generation += 1
        generation = self._source_generation
        self.quick_btn.configure(state="disabled")
        self.deep_btn.configure(state="disabled")
        self.status.set("Suche läuft – RAW-Abbild wird ausschließlich gelesen …")
        last_progress_post = float('-inf')
        def progress(current, total):
            nonlocal last_progress_post
            now = time.monotonic()
            if current != total and now - last_progress_post < .1:
                return
            if current == total or current % (64 * 1024 * 1024) < 4 * 1024 * 1024:
                last_progress_post = now
                self._post_scan_callback(lambda c=current, t=total, g=generation: (
                    self.status.set(f"Dateisystemsuche: {c / 1024**2:,.0f} / {t / 1024**2:,.0f} MiB gelesen")
                    if g == self._source_generation else None))
        def worker():
            try:
                fp = None
                if not is_device_source(source):
                    fp = fingerprint_image(source)
                result = analyze_image(source, deep_scan=deep, max_scan_mb=limit,
                                       sector_size=sector, progress=progress)
                if fp is not None:
                    check_fingerprint(source, fp, original=source)
                self._post_scan_callback(lambda r=result, g=generation, p=source, f=fp:
                           self._show_partitions(r, g, p, fingerprint=f))
            except Exception as e:
                msg = str(e)
                self._post_scan_callback(lambda m=msg, g=generation: (
                    messagebox.showerror('Partitionsanalyse', m)
                    if g == self._source_generation else None))
            finally:
                self._post_scan_callback(self._finish_partition_scan)
        threading.Thread(target=worker, daemon=True).start()

    def _finish_partition_scan(self):
        self.partition_scanning = False
        self.quick_btn.configure(state='normal')
        self.deep_btn.configure(state='normal')
        pending = self._pending_source_quick_scan
        self._pending_source_quick_scan = None
        if pending is not None and self.source_path.get().strip() == pending:
            self.scan_partitions(False)

    def _show_partitions(self, report, generation=None, source=None, fingerprint=None):
        if generation is not None and (generation != self._source_generation or
                                       self.source_path.get().strip() != source):
            self.status.set('Ältere Partitionsanalyse verworfen: Quelle wurde geändert.')
            return
        self.last_partition_report = report
        self._partition_fingerprint = fingerprint
        self.partitions = report.partitions
        self.partition_details = {}
        self._usage_for_chart = None
        self._draw_usage_bar()
        self._write_partition_details('Partition auswählen und „Ausgewählte Partition prüfen“ anklicken.')
        self.part_tree.delete(*self.part_tree.get_children())
        for i, p in enumerate(report.partitions):
            name = p.name + (" ⚠" if p.warning else "")
            self.part_tree.insert("", "end", iid=str(i), values=(p.index, p.scheme, translate(p.confidence, self.language),
                p.offset_bytes, f"{p.size_bytes/1024**3:.3f} GiB", p.filesystem,
                '—', 'Nicht geprüft', p.sector_size, p.type_code, name))
        counts = {
            'Hoch': sum(p.confidence == 'Hoch' for p in report.partitions),
            'Mittel': sum(p.confidence == 'Mittel' for p in report.partitions),
            'Niedrig': sum(p.confidence == 'Niedrig' for p in report.partitions),
        }
        flagged = sum(bool(p.warning) for p in report.partitions)
        self.partition_quality_summary.set(
            f"{translate('Hohe Plausibilität', self.language)}: {counts['Hoch']}   ·   "
            f"{translate('Mittlere Plausibilität', self.language)}: {counts['Mittel']}   ·   "
            f"{translate('Geringe Plausibilität', self.language)}: {counts['Niedrig']}   ·   "
            f"{translate('Auffällige Partitionen', self.language)}: {flagged}")
        self.partition_summary.set(
            f"Abbild: {report.image_size / 1024**3:.3f} GiB · Schema: {report.table_type} · "
            f"{len(report.partitions)} Einträge ({report.candidates} heuristische Funde) · "
            f"Durchsucht: {report.scanned_bytes / 1024**2:.0f} MiB")
        self.partition_warnings.configure(state="normal")
        self.partition_warnings.delete("1.0", "end")
        warnings = list(report.warnings)
        warnings.extend(f"Offset {p.offset_bytes}: {p.warning}" for p in report.partitions if p.warning)
        self.partition_warnings.insert("1.0", "\n".join(warnings) or "Keine zusätzlichen Hinweise.")
        self.partition_warnings.configure(state="disabled")
        self.status.set(f"Partitionsanalyse abgeschlossen: {len(report.partitions)} Einträge. "
                        + ("Tiefensuche empfohlen." if not report.partitions else "Ergebnis prüfen."))

    def _write_partition_details(self, text):
        box = self.partition_detail_text
        box.configure(state='normal')
        box.delete('1.0', 'end')
        box.insert('1.0', text)
        box.configure(state='disabled')

    def _schedule_usage_redraw(self, event=None):
        if self._usage_redraw_job is None:
            self._usage_redraw_job = self.after(40, self._flush_usage_redraw)

    def _flush_usage_redraw(self):
        self._usage_redraw_job = None
        self._draw_usage_bar()

    def _draw_usage_bar(self, details=None):
        """Show *metadata-based* used/free ratios, or grey if not available."""
        if details is not None:
            self._usage_for_chart = details
        details = self._usage_for_chart
        canvas = self.usage_canvas
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        pct = None if details is None or details.used_percent is None else max(0., min(100., details.used_percent))
        key = (width, height, self.theme, pct)
        if key == self._usage_draw_key:
            return
        self._usage_draw_key = key
        canvas.delete('all')
        if details is None or details.used_percent is None:
            canvas.create_rectangle(0, 0, width, height, fill=self._palette()['divider'], outline='')
            text = 'Speicherbelegung: unbekannt (keine vollständigen Metadaten).'
            if self.usage_caption.get() != translate(text, self.language):
                self.usage_caption.set(text)
            return
        pct = max(0., min(100., details.used_percent))
        used_width = round(width * pct / 100)
        canvas.create_rectangle(0, 0, width, height, fill=('#294739' if self.theme == 'dark' else '#d6f0e3'), outline='')
        if used_width:
            canvas.create_rectangle(0, 0, used_width, height, fill=('#4b9ce5' if self.theme == 'dark' else '#3275c9'), outline='')
        text = (f'Belegt: {pct:.1f} % · Frei: {100-pct:.1f} % '
                '(nur Dateisystem-Metadaten; kein Integritätsnachweis)')
        if self.usage_caption.get() != translate(text, self.language):
            self.usage_caption.set(text)

    def _on_partition_selected(self, event=None):
        selected = self.part_tree.selection()
        if not selected:
            return
        try:
            idx = int(selected[0])
            part = self.partitions[idx]
        except (IndexError, ValueError):
            return
        result = self.partition_details.get(idx)
        self._usage_for_chart = result
        self._draw_usage_bar()
        if result:
            self._write_partition_details(format_partition_details(part, result,
                self.partition_source or self.source_path.get().strip(), self.language))
        else:
            self._write_partition_details(
                f'Partition {part.index}: {part.filesystem} · Offset {part.offset_bytes:,} Byte\n'
                + format_partition_confidence(part.confidence, self.language) + '\n'
                + '\n'.join('• ' + item for item in part.evidence) + '\n'
                + (('Warnung: ' + part.warning + '\n') if part.warning else '')
                + 'Noch nicht geprüft. „Ausgewählte Partition prüfen“ anklicken.')

    def check_selected_partition(self):
        if self.partition_diagnosing or self.partition_scanning:
            return
        selected = self.part_tree.selection()
        if not selected:
            messagebox.showinfo('Partitionsprüfung', 'Bitte eine Partition markieren.', parent=self)
            return
        try:
            idx = int(selected[0])
            part = self.partitions[idx]
            source = self.get_source()
            if self.partition_source and source != self.partition_source:
                raise ValueError('Quelle wurde geändert. Bitte Partitionsanalyse erneut starten.')
        except (ValueError, IndexError, OSError) as e:
            messagebox.showerror('Partitionsprüfung', str(e), parent=self)
            return
        generation = self._source_generation
        self.partition_diagnosing = True
        self.detail_btn.configure(state='disabled')
        self.status.set('Lese Dateisystem-Metadaten der ausgewählten Partition …')
        def run():
            try:
                result = inspect_partition(source, part)
            except Exception as exc:
                msg = str(exc)
                self._post_scan_callback(lambda: self._finish_partition_details_error(msg, generation, source))
            else:
                self._post_scan_callback(lambda: self._finish_partition_details(
                    generation, source, idx, part, result))
        threading.Thread(target=run, daemon=True).start()

    def _finish_partition_details_error(self, message, generation=None, source=None):
        self.partition_diagnosing = False
        self.detail_btn.configure(state='normal')
        if generation is None or self._scan_source_matches(generation, source):
            messagebox.showerror('Partitionsprüfung', message, parent=self)

    def _finish_partition_details(self, generation, source, idx, part, result):
        self.partition_diagnosing = False
        self.detail_btn.configure(state='normal')
        if not self._scan_source_matches(generation, source) or idx >= len(self.partitions) or self.partitions[idx] is not part:
            self.status.set('Partitionsdiagnose verworfen: Quelle/Partitionsliste inzwischen geändert.')
            return
        self.partition_source = source
        self.partition_details[idx] = result
        used = '—' if result.used_percent is None else f'{result.used_percent:.1f} %*'
        iid = str(idx)
        if self.part_tree.exists(iid):
            self.part_tree.set(iid, 'usage', used)
            self.part_tree.set(iid, 'health', result.status)
        if iid in self.part_tree.selection():
            self._usage_for_chart = result
            self._draw_usage_bar()
            self._write_partition_details(format_partition_details(part, result, source, self.language))
        self.status.set('Partitions-Metadaten geprüft: ' + result.status +
                        ' · * Belegung aus Dateisystem-Metadaten, keine Integritätsprüfung.')

    def save_partition_findings(self):
        report = self.last_partition_report
        if report is None:
            messagebox.showinfo('Fundliste', 'Bitte zuerst eine Partitionsanalyse durchführen.', parent=self)
            return
        try:
            source = self.get_source()
            if self.partition_source and source != self.partition_source:
                raise ValueError('Quelle geändert: zuerst eine neue Partitionsanalyse durchführen.')
        except (ValueError, OSError) as exc:
            messagebox.showerror('Fundliste', str(exc), parent=self)
            return
        target = filedialog.asksaveasfilename(parent=self, title='Partitionsfunde speichern',
            defaultextension='.txt', initialfile='Tenshi_Partitionsfunde.txt',
            filetypes=[('Textbericht', '*.txt')])
        if not target:
            return
        try:
            ensure_safe_destination(source, target)
            with open(target, 'x', encoding='utf-8') as stream:
                stream.write(format_partition_findings(source, report))
        except (ValueError, OSError) as exc:
            messagebox.showerror('Fundliste', str(exc), parent=self)
            return
        self.status.set('Partitionsfunde gespeichert: ' + target)

    def save_partition_details(self):
        selected = self.part_tree.selection()
        if not selected:
            messagebox.showinfo('Partitionsbericht', 'Bitte eine geprüfte Partition auswählen.', parent=self)
            return
        idx = int(selected[0])
        result = self.partition_details.get(idx)
        if result is None:
            messagebox.showinfo('Partitionsbericht',
                'Für die ausgewählte Partition zuerst „Ausgewählte Partition prüfen“ anklicken.', parent=self)
            return
        source = self.partition_source or self.source_path.get().strip()
        filename = filedialog.asksaveasfilename(parent=self, title='Partitionsbericht speichern',
                         defaultextension='.txt', initialfile='Tenshi_Partitionsbericht.txt',
                         filetypes=[('Textbericht', '*.txt')])
        if not filename:
            return
        try:
            # Never replace an existing report or the source itself.
            from .sources import ensure_safe_destination
            ensure_safe_destination(source, filename)
            with open(filename, 'x', encoding='utf-8') as stream:
                stream.write(format_partition_details(self.partitions[idx], result, source, self.language))
        except (OSError, ValueError) as e:
            messagebox.showerror('Partitionsbericht', str(e), parent=self)
            return
        self.status.set(f'Partitionsbericht gespeichert: {filename}')
        messagebox.showinfo('Partitionsbericht', 'Bericht erfolgreich gespeichert.', parent=self)

    def _build_ntfs(self):
        self._browser_spacing = []
        controls = ttk.Frame(self.ntfs_tab)
        controls.pack(fill='x', pady=(0, 8))
        self._browser_spacing.append((controls, 8))
        ttk.Label(controls, text='Partitionsoffset (Byte):').pack(side='left')
        self.ntfs_byte_offset = tk.StringVar(value='0')
        ttk.Entry(controls, textvariable=self.ntfs_byte_offset, width=16).pack(side='left', padx=5)
        ttk.Button(controls, text='Partition übernehmen', command=self.use_selected_partition).pack(side='left', padx=5)
        ttk.Label(controls, text='MFT-Limit (0=alle):').pack(side='left', padx=(12, 5))
        self.mft_record_limit = tk.StringVar(value='0')
        ttk.Entry(controls, textvariable=self.mft_record_limit, width=9).pack(side='left')

        tools = ttk.Frame(self.ntfs_tab)
        tools.pack(fill='x', pady=(0, 8))
        self._browser_spacing.append((tools, 8))
        self.ntfs_scan_btn = ttk.Button(tools, text='Dateisystem einlesen',
                                        style='Accent.TButton', command=self.start_ntfs_scan)
        self.ntfs_scan_btn.pack(side='left')
        self.ntfs_cancel_btn = ttk.Button(tools, text='Scan abbrechen',
                                          command=self._cancel_scan, state='disabled')
        self.ntfs_cancel_btn.pack(side='left', padx=5)
        diagnosis_row = ttk.Frame(self.ntfs_tab)
        # Keep advanced scan options in a dialog to protect the limited browser height.
        # diagnosis_row intentionally not packed (controls are recreated in the dialog).
        self.tolerant_scan = tk.BooleanVar(value=False)
        ttk.Checkbutton(diagnosis_row, text='Fehlertolerante Suche (nur Images)',
                        variable=self.tolerant_scan).pack(side='left')
        ttk.Label(diagnosis_row,
                  text='Überspringt unlesbare NTFS-Datensätze bzw. Unterordner; Ergebnis kann unvollständig sein.',
                  style='Sub.TLabel').pack(side='left', padx=8)
        ttk.Button(diagnosis_row, text='Analysebericht speichern',
                   command=self.save_scan_report).pack(side='right', padx=6)
        ttk.Button(controls, text='Diagnose…', command=self._scan_options_dialog).pack(side='right')
        self.show_deleted = tk.BooleanVar(value=True)
        self.deleted_toggle = ttk.Checkbutton(tools, text='Gelöschte Einträge anzeigen',
                                               variable=self.show_deleted, command=self._refresh_browser)
        self.deleted_toggle.pack(side='left', padx=4)
        # Match the Sun Valley accent while keeping the existing button metrics.
        self.export_button = tk.Button(
            tools, text='Stapel-Export / fortsetzen', command=self.export_browser_selection,
            bg=self._palette()['accent'], fg=self._palette()['accent_text'],
            activebackground=self._palette()['accent_active'],
            activeforeground='#ffffff', disabledforeground='#dcebdd',
            font=('Segoe UI', 10, 'bold'), relief='flat', borderwidth=0,
            cursor='hand2', padx=15, pady=7,
            highlightthickness=0)
        self.export_button.pack(side='right')
        ttk.Button(tools, text='Vorschau', command=self.preview_entry).pack(side='right', padx=6)
        ttk.Button(tools, text='Datei prüfen', command=self.inspect_file).pack(side='right', padx=6)

        searchrow = ttk.Frame(self.ntfs_tab)
        searchrow.pack(fill='x', pady=(0, 8))
        self._browser_spacing.append((searchrow, 8))
        ttk.Label(searchrow, text='Suche (alle Dateinamen):').pack(side='left')
        self.browser_search = tk.StringVar()
        entry = ttk.Entry(searchrow, textvariable=self.browser_search)
        self.browser_search_entry = entry
        entry.pack(side='left', fill='x', expand=True, padx=6)
        entry.bind('<Return>', lambda event: self._normal_search_browser())
        ttk.Button(searchrow, text='Suchen', command=self._normal_search_browser).pack(side='left')
        ttk.Button(searchrow, text='Erweiterte Suche…', command=self._advanced_search_dialog).pack(side='left', padx=(5,0))
        ttk.Button(searchrow, text='Zurück zum Ordner', command=self._show_current_directory).pack(side='left', padx=6)

        # Extra filters live in a dialog, keeping the file browser visible at
        # Windows 1024x650 and larger DPI settings.
        self.browser_extension = tk.StringVar(value='')
        self.browser_min_size = tk.StringVar(value='')
        self.browser_max_size = tk.StringVar(value='')
        self.browser_kind = tk.StringVar(value='Alle')
        self.browser_kind_display = tk.StringVar(value=translate('Alle', self.language))
        self.browser_search_paths = tk.BooleanVar(value=False)

        filterrow = ttk.Frame(self.ntfs_tab)
        filterrow.pack(fill='x', pady=(0, 6))
        self._browser_spacing.append((filterrow, 6))
        ttk.Label(filterrow, text='Rettbarkeitsfilter:').pack(side='left')
        self.browser_status_filter = tk.StringVar(value=FILTER_ALL)
        self.browser_status_display = tk.StringVar(value=translate(FILTER_ALL, self.language))
        self.browser_status_filter.trace_add('write', lambda *_: self.browser_status_display.set(
            translate(self.browser_status_filter.get(), self.language)))
        self.browser_filter_combo = ttk.Combobox(filterrow, textvariable=self.browser_status_display,
                values=[translate(key, self.language) for key in STATUS_FILTERS],
                state='readonly', width=28)
        self.browser_filter_combo.pack(side='left', padx=(8, 12))
        self.browser_filter_combo.bind('<<ComboboxSelected>>', self._on_localized_status_selected)
        self.browser_filter_summary = tk.StringVar(value='')
        ttk.Label(filterrow, textvariable=self.browser_filter_summary,
                  style='Sub.TLabel').pack(side='left', fill='x', expand=True)
        ttk.Label(filterrow, text='⚠ = Metadaten-Hinweis; kein Nachweis beschädigter Inhalte.',
                  style='Sub.TLabel').pack(side='right')

        self.browser_path = tk.StringVar(value='Noch kein Dateisystem eingelesen.')
        pathrow = ttk.Frame(self.ntfs_tab)
        pathrow.pack(fill='x', pady=(0, 5))
        self._browser_spacing.append((pathrow, 5))
        ttk.Label(pathrow, textvariable=self.browser_path,
                  style='Sub.TLabel').pack(side='left', fill='x', expand=True)
        # Presentation-only setting: never delete or alter image entries.
        # Keep it out of the already crowded export toolbar at 1024 px.
        self.show_tmp = tk.BooleanVar(value=False)
        self.tmp_toggle = ttk.Checkbutton(pathrow, text='TMP anzeigen (nur Ansicht)',
                                           variable=self.show_tmp,
                                           command=self._refresh_browser)
        self.tmp_toggle.pack(side='right', padx=(12, 0))
        # Large directories: render one bounded page at a time. The full
        # metadata index/search result remains available for sorting and search.
        pager = ttk.Frame(pathrow)
        pager.pack(side='right', padx=(8, 0))
        self.browser_prev_button = ttk.Button(pager, text='◀ Vorherige Seite',
                                               command=self._previous_browser_page)
        self.browser_prev_button.pack(side='left')
        self.browser_next_button = ttk.Button(pager, text='Nächste Seite ▶',
                                               command=self._next_browser_page)
        self.browser_next_button.pack(side='left', padx=(8, 0))
        self.browser_page_caption = tk.StringVar(value='')
        ttk.Label(pager, textvariable=self.browser_page_caption,
                  style='Sub.TLabel').pack(side='left', padx=(12, 0))
        paned = ttk.Panedwindow(self.ntfs_tab, orient='horizontal')
        self.browser_paned = paned
        # The notebook is initially on the Partitionen tab. When the file tab
        # is first shown, ttk otherwise gives the folder pane only its tiny
        # requested width (sometimes < 100 pixels). Allocate a real share after
        # it has been mapped, without overriding later user sash adjustments.
        self._browser_sash_initialized = False
        paned.bind('<Configure>', self._initialize_browser_split, add='+')
        paned.bind('<Map>', lambda event: self.after_idle(self._initialize_browser_split), add='+')
        paned.pack(fill='both', expand=True)
        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=0)
        paned.add(right, weight=1)
        ttk.Label(left, text='Ordnerstruktur').pack(anchor='w', pady=(0, 5))
        self.folder_tree = ttk.Treeview(left, show='tree', selectmode='browse')
        self.folder_tree.column('#0', width=390, minwidth=220, stretch=True)
        scroll_l = ttk.Scrollbar(left, orient='vertical', command=self.folder_tree.yview)
        self.folder_tree.configure(yscrollcommand=scroll_l.set)
        scroll_l.pack(side='right', fill='y')
        self.folder_tree.pack(fill='both', expand=True)
        self.folder_tree.bind('<<TreeviewSelect>>', self._on_folder_selection)
        self.folder_tree.bind('<<TreeviewOpen>>', self._on_folder_open)
        ttk.Label(right, text='Dateien und Unterordner').pack(anchor='w', pady=(0, 5))
        cols = ('type', 'size', 'status', 'quality', 'mft', 'extension', 'modified', 'path')
        self.file_tree = ttk.Treeview(right, columns=cols, show='tree headings', selectmode='extended')
        self.file_tree.heading('#0', text='Name', command=lambda: self._sort_browser('name'))
        self.file_tree.column('#0', width=self._view_settings['files_columns'].get('#0', 270), minwidth=180, stretch=False)
        for col, title, width in [('type', 'Typ', 105), ('size', 'Größe', 105),
                                  ('status', 'Status', 205), ('quality', 'Rettbarkeit', 210),
                                  ('mft', 'Eintrags-ID', 88), ('extension', 'Endung', 83),
                                  ('modified', 'Geändert (UTC)', 165), ('path', 'Pfad', 350)]:
            self.file_tree.heading(col, text=title, command=lambda c=col: self._sort_browser(c))
            self.file_tree.column(col, width=self._view_settings['files_columns'].get(col, width), minwidth=70, anchor='w', stretch=False)
        scroll_r = ttk.Scrollbar(right, orient='vertical', command=self.file_tree.yview)
        scroll_x = ttk.Scrollbar(right, orient='horizontal', command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=scroll_r.set, xscrollcommand=scroll_x.set)
        scroll_r.pack(side='right', fill='y')
        scroll_x.pack(side='bottom', fill='x')
        self.file_tree.pack(fill='both', expand=True)
        self.file_tree.tag_configure('deleted', foreground='#b45309')
        self.file_tree.tag_configure('warning', foreground='#b91c1c')
        self.folder_tree.tag_configure('warning', foreground='#b91c1c')
        self.folder_tree.tag_configure('deleted', foreground='#b45309')
        self.file_tree.bind('<Double-1>', self._open_selected_browser_directory)
        self.file_tree.bind('<Return>', self._open_selected_browser_directory)
        self.file_tree.bind('<Control-a>', self._select_all_browser_files)
        self.file_tree.bind('<Control-A>', self._select_all_browser_files)
        self.file_tree.bind('<Control-c>', self._copy_selected_browser_paths)
        self.file_tree.bind('<Control-C>', self._copy_selected_browser_paths)
        self.file_tree.bind('<Button-3>', self._browser_context_popup)
        self.file_tree.bind('<F5>', lambda event: self._display_browser_entries(self.browser_display))
        self.bind('<Control-f>', self._focus_browser_search)
        ttk.Label(self.ntfs_tab,
                  text='Dateiansicht: NTFS, FAT32, exFAT, ext2/3/4 sowie eingeschränkt Btrfs und XFS. '
                       'Gelöschte Dateien: NTFS, FAT32, exFAT und ext2/3/4 teilweise rettbar; Btrfs/XFS nur nicht exportierbare Metadatenhinweise. Ein Export garantiert keine intakten Inhalte.',
                  foreground='#9a3412', wraplength=980).pack(anchor='w', pady=(7, 0))
        self._build_export_actions()
        self.browser_index = None
        self.browser_source = None
        self.browser_cancel = threading.Event()
        self.export_cancel = threading.Event()
        self.export_running = False
        self.export_progress = QueueProgress()
        self.export_result = None
        self._export_events = queue.SimpleQueue()
        self.browser_nodes = {}
        self.browser_ancestors = {}
        self.browser_expanded = set()
        self.browser_sequence = 0
        self.browser_entries_visible = {}
        self.browser_display = []
        self.browser_paths = {}
        self.browser_warning_records = set()
        self.browser_warning_files = {}
        self.browser_display_token = 0
        self.browser_page_size = 750
        self.browser_page = 0
        self.browser_page_items = []
        self.browser_sorted_items = []
        self.browser_search_generation = 0
        self.browser_sort = 'name'
        self.browser_sort_reverse = False
        self.current_folder = 5
        self.browser_fs = 'NTFS'

    def _choose_device(self):
        return self._choose_sources()

    def _show_device_dialog(self, drives):
        # Compatibility entry point; the toolbar uses the combined picker.
        return self._show_source_dialog(device_choices(drives), preselect=not any(
            path.startswith('/dev/') for path, _ in drives))

    def _cancel_scan(self):
        self.browser_cancel.set()
        self.status.set('Scan-Abbruch angefordert …')

    def _open_partition_from_double_click(self, event):
        """Open precisely the clicked partition, not an older selection.

        Tk may deliver a double-click before its selection callback has run.
        Header and blank-space clicks must never start a filesystem scan.
        """
        if self.part_tree.identify_region(event.x, event.y) not in ('cell', 'tree'):
            return
        row = self.part_tree.identify_row(event.y)
        if not row or not self.part_tree.exists(row):
            return
        self.part_tree.selection_set(row)
        self.part_tree.focus(row)
        self._activate_selected_partition(scan=True)

    def use_selected_partition(self):
        """Manual offset transfer stays available without starting a scan."""
        self._activate_selected_partition(scan=False)

    def _activate_selected_partition(self, *, scan: bool):
        selected = self.part_tree.selection()
        if not selected:
            messagebox.showinfo('Partition', 'Bitte zunächst im Reiter Partitionen einen Eintrag auswählen.')
            return
        # Do not replace scan parameters while a background read is active.
        if scan and (self.ntfs_scanning or self.partition_scanning):
            self.status.set('Eine Analyse läuft bereits. Bitte erst deren Abschluss abwarten.')
            return
        try:
            idx = int(selected[0])
            part = self.partitions[idx]
            source = self.get_source()
            if self.partition_source is not None and self.partition_source != source:
                raise ValueError('Quelle wurde geändert. Bitte Partitionsanalyse erneut starten.')
        except (IndexError, ValueError, OSError) as exc:
            messagebox.showerror('Partition', str(exc), parent=self)
            return
        self.ntfs_byte_offset.set(str(part.offset_bytes))
        self._select_main_tab('files')
        self.status.set(f'Partitionsanfang: Byte {part.offset_bytes}, Dateisystem: {part.filesystem}.')
        if part.filesystem not in ('NTFS', 'FAT32', 'exFAT', 'ext2', 'ext3', 'ext4', 'Btrfs', 'XFS'):
            messagebox.showwarning('Dateisystem', 'Diese Partition ist nicht als Ordnerbaum unterstützt. '
                                   'Unterstützt: NTFS, FAT32, exFAT, ext2/ext3/ext4, Btrfs und XFS.')
            return
        if scan:
            # Uses the same read-only asynchronous parser and error handling as
            # the "Dateisystem einlesen" button. Never opens the disk for writing.
            self.start_ntfs_scan()

    def start_ntfs_scan(self):
        if self.ntfs_scanning:
            return
        if self._session_running:
            self.status.set('Bitte laufenden Sitzungsvorgang zuerst abschließen.')
            return
        try:
            source = self.get_source()
            offset = int(self.ntfs_byte_offset.get().strip(), 0)
            limit = int(self.mft_record_limit.get().strip())
            tolerant = bool(self.tolerant_scan.get())
            display_tmp = bool(self.show_tmp.get())
            scan_source_generation = self._source_generation
            if tolerant and is_device_source(source):
                raise ValueError('Fehlertolerante Suche nur für Image-Dateien; '
                                 'bei defekten Datenträgern zuerst ein Abbild erstellen.')
            if offset < 0 or offset % 512:
                raise ValueError('Der Partitionsoffset muss nichtnegativ und durch 512 teilbar sein.')
            if limit < 0 or limit > 30_000_000:
                raise ValueError('MFT-Limit muss zwischen 0 und 30.000.000 liegen.')
        except Exception as exc:
            messagebox.showerror('NTFS-Ordneransicht', str(exc))
            return
        self.ntfs_scanning = True
        self._clear_browser_results()
        self.browser_cancel.clear()
        self.ntfs_scan_btn.configure(state='disabled')
        self.ntfs_cancel_btn.configure(state='normal')
        self.status.set('Dateisystem wird schreibgeschützt gelesen …')
        last_progress_post = float('-inf')
        def progress(done, total):
            nonlocal last_progress_post
            now = time.monotonic()
            if done != total and now - last_progress_post < .1:
                return
            last_progress_post = now
            self._post_scan_callback(lambda d=done, t=total, g=scan_source_generation: (
                self.status.set(f'MFT: {d:,} / {t:,} Datensätze geprüft …')
                if self._scan_source_matches(g, source) else None))
        def worker():
            try:
                fp = None
                if not is_device_source(source):
                    fp = fingerprint_image(source, [offset])
                device_identity = capture_device_identity(source, offset)
                with open_source(source) as f:
                    from .filesystems import detect_volume
                    from .ntfs import parse_boot_sector
                    f.seek(offset)
                    signature = f.read(11)
                if signature[3:11] == b'NTFS    ':
                    index = scan_ntfs_tree(source, partition_offset=offset, max_records=limit,
                                           progress=progress, cancel=self.browser_cancel.is_set,
                                           tolerate_read_errors=tolerant)
                    fs_name = 'NTFS'
                else:
                    # Also retain conservative deleted-entry candidates for FAT32/exFAT/ext.
                    index = scan_other_tree(source, offset=offset,
                                            progress=progress, cancel=self.browser_cancel.is_set,
                                            tolerate_read_errors=tolerant)
                    fs_name = index.filesystem
                check_device_identity(source, device_identity)
                index._device_identity = device_identity
                if fp is not None:
                    check_fingerprint(source, fp, original=source)
                # Prepare the O(N) metadata maps off the GUI thread. Large
                # file systems otherwise freeze the main window after scanning.
                paths = construct_paths(index.entries, lazy=True)
                warning_records = folder_warning_records(
                    visible_entries(index.entries, display_tmp))
                self._post_scan_callback(lambda name=fs_name, g=scan_source_generation: (
                    self._set_browser_fs(name) if self._scan_source_matches(g, source) else None))
                def publish(idx=index, prepared=(paths, warning_records, display_tmp), fingerprint=fp):
                    if self._scan_source_matches(scan_source_generation, source):
                        self._browser_fingerprint = fingerprint
                        self._show_browser_index(source, idx, prepared=prepared)
                self._post_scan_callback(publish)
            except (ScanCancelled, OtherScanCancelled):
                self._post_scan_callback(lambda g=scan_source_generation: (
                    self.status.set('Scan abgebrochen.') if self._scan_source_matches(g, source) else None))
            except Exception as exc:
                msg = str(exc)
                if isinstance(exc, OSError) and getattr(exc, 'errno', None) == 22:
                    if sys.platform.startswith('linux') and is_device_source(source):
                        msg += ('\n\nLinux-Blockgerät: Logische Sektorgröße und Gerätezugriff '
                                'prüfen; alternativ ein RAW-Image verwenden. '
                                'Keine zusätzlichen Schreibrechte vergeben.')
                    else:
                        msg += ('\n\nPhysische Windows-Datenträger erfordern sektorausgerichtete Lesezugriffe. '
                                'Bitte Tenshi neu starten und die aktuelle Version verwenden. '
                                'Falls der Fehler bleibt, Laufwerk als Administrator öffnen oder RAW-Image erstellen.')
                self._post_scan_callback(lambda m=msg, g=scan_source_generation: (
                    messagebox.showerror('Dateisystem', m) if self._scan_source_matches(g, source) else None))
            finally:
                self._post_scan_callback(self._finish_ntfs_scan)
        threading.Thread(target=worker, daemon=True).start()

    def _set_browser_fs(self, fs_name):
        self.browser_fs = fs_name
        # FAT32, exFAT and ext also expose conservatively reconstructed deleted entries.
        self.deleted_toggle.configure(state='normal')

    def _finish_ntfs_scan(self):
        self.ntfs_scanning = False
        self.ntfs_scan_btn.configure(state='normal')
        self.ntfs_cancel_btn.configure(state='disabled')

    def _session_busy(self):
        return (self._session_running or self.ntfs_scanning or
                self.partition_scanning or self.partition_diagnosing or self.export_running)

    def save_analysis_session(self):
        """Persist metadata-only cached analyses; never write to source devices."""
        if self._session_busy():
            messagebox.showwarning('Analysesitzung', 'Bitte laufende Vorgänge zuerst abschließen.', parent=self)
            return
        try:
            source = self.get_source()
            if is_device_source(source):
                raise SessionError('Sitzungen erfordern ein reguläres Image. Bitte zuerst ein Image erstellen.')
            report = self.last_partition_report if self.partition_source == source else None
            index = self.browser_index if self.browser_source == source else None
            if report is None and index is None:
                raise SessionError('Bitte zuerst eine Partition oder ein Dateisystem analysieren.')
            # Never combine a recent file scan with outdated partition results.
            expected = self._browser_fingerprint if index is not None else self._partition_fingerprint
            if report is not None and self._partition_fingerprint is not None:
                check_fingerprint(source, self._partition_fingerprint, original=source)
            if expected is not None:
                check_fingerprint(source, expected, original=source)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Analysesitzung', str(exc), parent=self)
            return
        dest = filedialog.asksaveasfilename(parent=self, title='Analysesitzung speichern',
            initialfile='Tenshi_Sitzung.tenshi-session', defaultextension='.tenshi-session',
            filetypes=[('Tenshi-Sitzung', '*.tenshi-session')])
        if not dest:
            return
        self._session_running = True
        self.session_menu_button.configure(state='disabled')
        self.status.set('Analysesitzung wird gespeichert …')
        generation = self._source_generation
        filesystem = self.browser_fs if index is not None else None
        def worker():
            try:
                save_session(dest, source, report=report, index=index,
                             filesystem=filesystem, expected_fingerprint=expected)
                self._post_scan_callback(lambda: self._session_save_result(None, generation))
            except Exception as exc:
                self._post_scan_callback(lambda error=str(exc): self._session_save_result(error, generation))
        threading.Thread(target=worker, daemon=True).start()

    def _session_save_result(self, error, generation):
        self._session_running = False
        self.session_menu_button.configure(state='normal')
        if error:
            messagebox.showerror('Analysesitzung', error, parent=self)
        else:
            self.status.set('Analysesitzung gespeichert. Beim Laden wird das Image erneut geprüft.')

    def load_analysis_session(self):
        if self._session_busy():
            messagebox.showwarning('Analysesitzung', 'Bitte laufende Vorgänge zuerst abschließen.', parent=self)
            return
        filename = filedialog.askopenfilename(parent=self, title='Analysesitzung laden',
            filetypes=[('Tenshi-Sitzung', '*.tenshi-session'), ('Alle Dateien', '*.*')])
        if not filename:
            return
        # Source must be either the saved image or a manually selected, verified replacement.
        # Never use the currently selected device implicitly as the new source.
        source_override = None
        try:
            from .session_store import _read_session
            manifest, _ = _read_session(filename)
            if not os.path.isfile(manifest['source']):
                source_override = filedialog.askopenfilename(parent=self,
                    title='Ursprüngliches Image fehlt – identisches Image auswählen',
                    filetypes=[('Disk-Images', '*.img *.dd *.bin *.raw *.iso'), ('Alle Dateien', '*.*')])
                if not source_override:
                    return
        except Exception as exc:
            messagebox.showerror('Analysesitzung', str(exc), parent=self)
            return
        self._session_running = True
        self.session_menu_button.configure(state='disabled')
        generation = self._source_generation
        source_text_at_start = self.source_path.get()
        self.status.set('Sitzung und Quell-Image werden geprüft …')
        def worker():
            try:
                result = load_session(filename, source_override=source_override)
                self._post_scan_callback(lambda res=result, gen=generation:
                           self._finish_session_load(res, gen, source_text_at_start))
            except Exception as exc:
                self._post_scan_callback(lambda error=str(exc): self._finish_session_load_error(error))
        threading.Thread(target=worker, daemon=True).start()

    def _finish_session_load_error(self, error):
        self._session_running = False
        self.session_menu_button.configure(state='normal')
        messagebox.showerror('Analysesitzung', error, parent=self)

    def _finish_session_load(self, result, generation, previous_source=None):
        self._session_running = False
        self.session_menu_button.configure(state='normal')
        if (generation != self._source_generation or
            (previous_source is not None and self.source_path.get() != previous_source)):
            self.status.set('Sitzung verworfen: Datenquelle wurde inzwischen geändert.')
            return
        # No UI state is changed before the source was verified in the worker.
        self._reset_analysis_for_source()
        self.source_path.set(result.source)
        if result.report is not None:
            self.partition_source = result.source
            self._show_partitions(result.report, fingerprint=result.fingerprint)
        if result.index is not None:
            self.ntfs_byte_offset.set(str(result.offset))
            self._browser_fingerprint = result.fingerprint
            self._set_browser_fs(result.filesystem)
            self._show_browser_index(result.source, result.index)
            self._select_main_tab('files')
        else:
            self._select_main_tab('partition')
        self.status.set('Analysesitzung geladen und Image geprüft. Dateiinhalte bleiben ungeprüft.')

    def _show_browser_index(self, source, index, prepared=None):
        self.browser_index = index
        self.browser_source = source
        if prepared is None:
            # Still support direct/manual callers and existing test harnesses.
            self.browser_paths = construct_paths(index.entries, lazy=True)
            self.browser_warning_records = folder_warning_records(
                visible_entries(index.entries, self.show_tmp.get()))
        else:
            paths, warnings, prepared_show_tmp = prepared
            self.browser_paths = paths
            self.browser_warning_records = (warnings if prepared_show_tmp == self.show_tmp.get()
                else folder_warning_records(visible_entries(index.entries, self.show_tmp.get())))
        self.scan_report_text = format_scan_report(source, index)
        self._rebuild_folder_tree()
        if self.browser_fs == 'NTFS':
            self.status.set(f'NTFS: {len(index.entries):,} Einträge aus '
                            f'{index.scanned_records:,} MFT-Datensätzen; '
                            f'{index.damaged_records:,} {translate("nicht auswertbare und", self.language)} '
                            f'{index.unreadable_records:,} nicht lesbare Datensätze; '
                            f'{index.orphan_count:,} nicht zugeordnet; '
                            f'{index.reconstructed_index_hints:,} Index-Hinweise '
                            f'(davon {index.allocation_index_hints:,} aus Index-Allocation); '
                            f'{index.resolved_attribute_lists:,} Datenattributlisten zusammengesetzt.')
            limited = getattr(index, 'attribute_list_limit_skipped', 0)
            index_errors = getattr(index, 'index_parse_failures', 0)
            if index.damaged_records or index.unreadable_records or limited or index_errors:
                outside = getattr(index, 'deleted_outside_volume_records', 0)
                counts = ((index.damaged_records - outside, 'Sonstige MFT-Auswertungsfehler'),
                          (outside, 'Gelöschte Records: Clusterverweise außerhalb des Volumes'),
                          (index.unreadable_records, 'MFT-Lesefehler'),
                          (limited, 'Attributlisten-Limit: nicht untersuchte Basisrecords'),
                          (index_errors, 'Verzeichnisindex-Auswertungsmeldungen'))
                message = '\n'.join(f'{translate(label, self.language)}: {count:,}'
                                    for count, label in counts)
                message += '\n\n' + translate(
                    'Die Dateiliste kann unvollständig sein. Auswertungsfehler oder erreichte Limits beweisen keinen Datenträgerschaden. Details: Diagnose… → Analysebericht speichern.',
                    self.language)
                if outside:
                    message += '\n\n' + translate(
                        'Diese Löschverweise können veraltet sein, etwa nach einer Partitionsverkleinerung. Die Ursache ist nicht nachgewiesen. Betroffene Einträge bleiben nicht exportierbar.',
                        self.language)
                messagebox.showwarning('NTFS-Analyse unvollständig', message)

        else:
            deleted = sum(bool(e.is_deleted) for e in index.entries)
            self.status.set(f'{index.filesystem}: {len(index.entries):,} Einträge; '
                            f'{deleted:,} Löschkandidaten; '
                            f'{index.unreadable_directories} unlesbare Unterordner.')
            if index.unreadable_directories:
                messagebox.showwarning('Dateisystem nur teilweise gelesen',
                    f'{index.unreadable_directories} Verzeichnisse konnten nicht gelesen werden. '
                    'Dateiliste ist unvollständig; Details im Analysebericht.')

    def save_scan_report(self):
        if not self.scan_report_text or not self.browser_source:
            messagebox.showinfo('Analysebericht', 'Bitte zuerst ein Dateisystem einlesen.')
            return
        destination = filedialog.asksaveasfilename(
            parent=self, title='Analysebericht auf anderem Datenträger speichern',
            initialfile='Tenshi_Analysebericht.txt',
            defaultextension='.txt', filetypes=[('Textdateien', '*.txt')])
        if not destination:
            return
        try:
            ensure_safe_destination(self.browser_source, destination)
            with open(destination, 'x', encoding='utf-8') as out:
                out.write(self.scan_report_text)
            messagebox.showinfo('Analysebericht', 'Bericht wurde gespeichert.')
        except FileExistsError:
            messagebox.showerror('Analysebericht', 'Datei existiert bereits. Bitte anderen Namen auswählen.')
        except Exception as exc:
            messagebox.showerror('Analysebericht', str(exc))

    def _rebuild_folder_tree(self):
        self.browser_search_generation += 1
        self.browser_display_token += 1
        self.folder_tree.delete(*self.folder_tree.get_children())
        self.browser_nodes = {'root': 5, 'orphans': -1}
        self.browser_ancestors = {'root': frozenset({5}), 'orphans': frozenset()}
        self.browser_expanded = set()
        self.browser_sequence = 0
        self.browser_warning_files = {}
        root_warning = 5 in self.browser_warning_records
        self.folder_tree.insert('', 'end', iid='root',
                text=f'{"⚠" if root_warning else "📁"} {self.browser_fs}-Volume',
                tags=('warning',) if root_warning else (), open=True)
        self._load_folder_children('root')
        if self.browser_index and visible_entries(
                self.browser_index.list_dir(-1, self.show_deleted.get()), self.show_tmp.get()):
            self.folder_tree.insert('', 'end', iid='orphans', text='⚠ Nicht zugeordnet', open=False)
            self.folder_tree.insert('orphans', 'end', iid='dummy:orphans', text='…')
        self.folder_tree.selection_set('root')
        self.current_folder = 5
        self._show_current_directory()

    def _load_folder_children(self, node):
        if not self.browser_index or node in self.browser_expanded:
            return
        self.browser_expanded.add(node)
        parent_record = self.browser_nodes[node]
        for child in self.folder_tree.get_children(node):
            if child.startswith('dummy:'):
                self.folder_tree.delete(child)
        ancestors = self.browser_ancestors[node]
        warning_files = 0
        for entry in visible_entries(
                self.browser_index.list_dir(parent_record, self.show_deleted.get()),
                self.show_tmp.get()):
            if not entry.is_directory:
                # Directly show files whose metadata are limited/unverified in
                # the folder tree. Ordinary files stay in the right-hand list.
                prefix, tag, _ = visual_status(entry)
                if tag == 'warning' and warning_files < 100:
                    self.browser_sequence += 1
                    child_node = f'warn:{self.browser_sequence}'
                    self.browser_warning_files[child_node] = entry
                    self.folder_tree.insert(node, 'end', iid=child_node,
                        text=f'{prefix} {entry.name}', tags=('warning',))
                    warning_files += 1
                continue
            if entry.record_number in ancestors:
                continue
            self.browser_sequence += 1
            child_node = f'dir:{self.browser_sequence}'
            self.browser_nodes[child_node] = entry.record_number
            self.browser_ancestors[child_node] = ancestors | {entry.record_number}
            flagged = entry.record_number in self.browser_warning_records
            icon = '⚠' if flagged else ('✕' if entry.is_deleted else '📁')
            label = f'{icon} {entry.name}'
            self.folder_tree.insert(node, 'end', iid=child_node, text=label,
                    tags=('warning',) if flagged else (('deleted',) if entry.is_deleted else ()), open=False)
            if any(c.is_directory or visual_status(c)[1] == 'warning'
                   for c in visible_entries(
                       self.browser_index.list_dir(entry.record_number, self.show_deleted.get()),
                       self.show_tmp.get())):
                self.folder_tree.insert(child_node, 'end', iid=f'dummy:{child_node}', text='…')
        # Avoid filling the navigation tree with unlimited file nodes.
        total_warn = sum(visual_status(e)[1] == 'warning' and not e.is_directory
                         for e in visible_entries(
                             self.browser_index.list_dir(parent_record, self.show_deleted.get()),
                             self.show_tmp.get()))
        if total_warn > warning_files:
            self.browser_sequence += 1
            self.folder_tree.insert(node, 'end', iid=f'overflow:{self.browser_sequence}',
                text=f'… {total_warn - warning_files} weitere auffällige Dateien (rechts ansehen)')

    def _on_folder_open(self, event=None):
        node = self.folder_tree.focus()
        if node in self.browser_nodes:
            self._load_folder_children(node)

    def _on_folder_selection(self, event=None):
        selected = self.folder_tree.selection()
        if not selected:
            return
        node = selected[0]
        if node in self.browser_warning_files:
            item = self.browser_warning_files[node]
            self.current_folder = item.parent_record
            if not matches_status(item, self.browser_status_filter.get()):
                self.browser_status_filter.set(FILTER_ALL)
            self._show_current_directory()
            if self.file_tree.exists(item.key):
                self.file_tree.selection_set(item.key)
                self.file_tree.see(item.key)
            return
        if node not in self.browser_nodes:
            return
        self.current_folder = self.browser_nodes[node]
        self._show_current_directory()

    def _show_current_directory(self):
        if not self.browser_index:
            return
        self.browser_search_generation += 1  # Cancel an unfinished large search.
        items = visible_entries(self.browser_index.list_dir(self.current_folder, self.show_deleted.get()), self.show_tmp.get())
        node = (self.folder_tree.selection() or ('root',))[0]
        if node in self.browser_warning_files:
            node = self.folder_tree.parent(node)
        segments = []
        while node and node != 'root':
            segments.append(self.folder_tree.item(node, 'text').removeprefix('📁 ').removeprefix('✕ ').removeprefix('⚠ '))
            node = self.folder_tree.parent(node)
        self.browser_path.set(self.browser_fs + ':\\' + '\\'.join(reversed(segments)) + f'    ·    {len(items):,} Einträge')
        self._display_browser_entries(items)

    def _refresh_browser(self):
        self.browser_search_generation += 1
        if self.browser_index:
            self.browser_warning_records = folder_warning_records(
                visible_entries(self.browser_index.entries, self.show_tmp.get()))
            self._rebuild_folder_tree()

    def _on_browser_filter_change(self, event=None):
        if self.browser_index:
            # Keep the current search or folder dataset and selection context.
            self._display_browser_entries(self.browser_display)

    def _sort_browser(self, column):
        if self.browser_sort == column:
            self.browser_sort_reverse = not self.browser_sort_reverse
        else:
            self.browser_sort, self.browser_sort_reverse = column, False
        self._display_browser_entries(self.browser_display)

    def _display_browser_entries(self, entries):
        """Filter/sort metadata but display at most one page in Tk Treeview.

        Treeview becomes unresponsive and memory-heavy at hundreds of thousands
        of rows. Keep the complete result for search, but only materialize the
        visible page. All selections/exports operate on displayed rows.
        """
        self.browser_display = visible_entries(entries, self.show_tmp.get())
        filtered = filter_entries(self.browser_display, self.browser_status_filter.get())
        self.browser_sorted_items = sorted_entries(filtered, self.browser_sort,
                                                  self.browser_sort_reverse,
                                                  self.browser_paths)
        self.browser_page = 0
        self._render_browser_page()

    def _update_browser_page_caption(self):
        """Update the pager without changing file names or filter semantics."""
        total = len(self.browser_sorted_items)
        pages = max(1, (total + self.browser_page_size - 1) // self.browser_page_size)
        start = self.browser_page * self.browser_page_size
        first = start + 1 if total else 0
        last = min(start + self.browser_page_size, total)
        labels = {
            'de': ('Seite', 'Einträge', 'von'),
            'en': ('Page', 'Entries', 'of'),
            'es': ('Página', 'Entradas', 'de'),
            'zh': ('页', '条目', '共'),
            'ru': ('Страница', 'Записи', 'из'),
            'ja': ('ページ', '項目', '全'),
        }
        page_label, entries_label, of_label = labels.get(self.language, labels['de'])
        self.browser_page_caption.set(
            f'{page_label} {self.browser_page + 1:,} / {pages:,}  ·  '
            f'{entries_label} {first:,}–{last:,} {of_label} {total:,}')

    def _previous_browser_page(self):
        if self.browser_page > 0:
            self.browser_page -= 1
            self._render_browser_page()

    def _next_browser_page(self):
        total = len(self.browser_sorted_items)
        if (self.browser_page + 1) * self.browser_page_size < total:
            self.browser_page += 1
            self._render_browser_page()

    def _render_browser_page(self):
        """No huge after() insertion backlog; keep at most page_size rows."""
        self.browser_display_token += 1
        total = len(self.browser_sorted_items)
        pages = max(1, (total + self.browser_page_size - 1) // self.browser_page_size)
        self.browser_page = min(self.browser_page, pages - 1)
        start = self.browser_page * self.browser_page_size
        items = self.browser_sorted_items[start:start + self.browser_page_size]
        self.browser_page_items = items
        self.browser_filter_summary.set(
            f'{total:,} von {len(self.browser_display):,} Einträgen sichtbar')
        self._update_browser_page_caption()
        self.browser_prev_button.configure(state='normal' if self.browser_page else 'disabled')
        self.browser_next_button.configure(
            state='normal' if start + self.browser_page_size < total else 'disabled')
        self.file_tree.delete(*self.file_tree.get_children())
        self.browser_entries_visible = {e.key: e for e in items}
        for item in items:
            icon, tag, _explanation = visual_status(item)
            self.file_tree.insert('', 'end', iid=item.key, text=f'{icon} {item.name}',
                values=(display_kind_text(display_kind(item), self.language),
                        '—' if item.is_directory else display_size(item.size),
                        translate(item.status, self.language),
                        translate(assess(item).label, self.language), item.record_number,
                        file_extension(item) or '—', display_modified(item),
                        self.browser_paths.get(item.key, '—')),
                tags=(tag,) if tag != 'normal' else ())

    def _scan_options_dialog(self):
        win = tk.Toplevel(self)
        win.title('Scan-Einstellungen und Diagnose')
        # Let Tk derive the height from the themed widgets and wrapped text.
        # A fixed 210px height clips the close button on Linux/font scaling.
        win.minsize(640, 0)
        win.transient(self)
        panel = ttk.Frame(win, padding=18)
        panel.pack(fill='both', expand=True)
        ttk.Checkbutton(panel, text='Fehlertolerante Suche (nur Images)',
                        variable=self.tolerant_scan).pack(anchor='w', pady=8)
        ttk.Label(panel, text='Überspringt unlesbare Datensätze/Unterordner. '
                  'Die Ergebnisse können unvollständig bleiben.', wraplength=575).pack(anchor='w')
        ttk.Button(panel, text='Analysebericht speichern',
                   command=self.save_scan_report).pack(anchor='w', pady=13)
        ttk.Button(panel, text='Schließen', command=win.destroy).pack(anchor='e')

    def _advanced_search_dialog(self):
        win = tk.Toplevel(self)
        win.title('Erweiterte Dateisuche')
        win.geometry('610x380')
        win.minsize(520, 365)
        win.resizable(True, True)
        win.transient(self)
        panel = ttk.Frame(win, padding=18)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='Dateiendungen (z. B. pdf, .docx, *.jpg; mehrere mit Komma)').pack(anchor='w')
        extension_entry = ttk.Entry(panel, textvariable=self.browser_extension)
        extension_entry.pack(fill='x', pady=(4, 9))
        ttk.Label(panel, text='Dateitypen hinzufügen:').pack(anchor='w', pady=(0, 4))
        category_row = ttk.Frame(panel)
        category_row.pack(fill='x', pady=(0, 3))
        for column, category in enumerate(EXTENSION_CATEGORIES):
            category_row.columnconfigure(column, weight=1, uniform='category')
            ttk.Button(category_row, text=category,
                       command=lambda selected=category: self._add_search_category(selected)
                       ).grid(row=0, column=column, sticky='ew', padx=2)
        ttk.Label(panel, text='Mehrere Kategorien kombinierbar · bestehende Endungen bleiben erhalten',
                  style='Sub.TLabel').pack(anchor='w', pady=(1, 11))
        sizes = ttk.Frame(panel)
        sizes.pack(fill='x')
        ttk.Label(sizes, text='Min. MiB:').pack(side='left')
        ttk.Entry(sizes, textvariable=self.browser_min_size, width=12).pack(side='left', padx=(6, 18))
        ttk.Label(sizes, text='Max. MiB:').pack(side='left')
        ttk.Entry(sizes, textvariable=self.browser_max_size, width=12).pack(side='left', padx=(6, 0))
        ttk.Label(panel, text='Eintragstyp').pack(anchor='w', pady=(12, 4))
        self.browser_kind_display.set(translate(self.browser_kind.get(), self.language))
        self.browser_kind_combo = ttk.Combobox(panel, textvariable=self.browser_kind_display,
                     state='readonly', values=[translate(key, self.language)
                         for key in ('Alle', 'Nur Dateien', 'Nur Ordner')])
        self.browser_kind_combo.pack(fill='x')
        ttk.Checkbutton(panel, text='Dateinamen und ursprünglichen Ordnerpfad durchsuchen',
                        variable=self.browser_search_paths).pack(anchor='w', pady=(10, 8))
        actions = ttk.Frame(panel)
        actions.pack(fill='x', side='bottom')
        def apply_filters():
            try:
                self.browser_kind.set(canonical_choice(
                    self.browser_kind_display.get(), ('Alle', 'Nur Dateien', 'Nur Ordner'), self.language))
                self._read_search_criteria()
            except ValueError as exc:
                messagebox.showerror('Erweiterte Suche', str(exc), parent=win)
                return
            win.destroy()
            self._search_browser()
        ttk.Button(actions, text='Suchen', command=apply_filters).pack(side='right')
        ttk.Button(actions, text='Zurücksetzen', command=lambda: (win.destroy(),
                   self._clear_advanced_search())).pack(side='right', padx=(0, 8))
        win.bind('<Return>', lambda event: apply_filters())
        win.bind('<Escape>', lambda event: win.destroy())

    def _add_search_category(self, category: str) -> None:
        """Append common suffixes to the advanced search's extension field."""
        updated = append_category_extensions(self.browser_extension.get(), category)
        self.browser_extension.set(updated)

    def _read_search_criteria(self):
        def mib_input(value):
            value = value.strip().replace(',', '.')
            if not value:
                return None
            result = float(value)
            if not 0 <= result <= 1024**3 or not (result < float('inf')):
                raise ValueError('Größenangaben müssen endlich, positiv und höchstens 1.073.741.824 MiB sein.')
            return round(result * 1024**2)
        criteria = SearchCriteria(
            name=self.browser_search.get(), extensions=self.browser_extension.get(),
            min_bytes=mib_input(self.browser_min_size.get()),
            max_bytes=mib_input(self.browser_max_size.get()),
            kind=canonical_choice(self.browser_kind_display.get(),
                  ('Alle', 'Nur Dateien', 'Nur Ordner'), self.language),
            in_path=self.browser_search_paths.get())
        criteria.validate()
        return criteria

    def _normal_search_browser(self):
        """An empty normal search clears advanced criteria as well."""
        if not self.browser_search.get().strip():
            self._clear_advanced_search()
        self._search_browser()

    def _search_browser(self):
        if not self.browser_index:
            messagebox.showinfo('Suche', 'Zuerst ein Dateisystem einlesen.')
            return
        try:
            criteria = self._read_search_criteria()
            match = compile_search(criteria)
        except ValueError as exc:
            messagebox.showerror('Suche', str(exc), parent=self)
            return
        entries = self.browser_index.entries
        show_tmp = self.show_tmp.get()
        show_deleted = self.show_deleted.get()
        paths = self.browser_paths
        index_ref = self.browser_index
        self.browser_search_generation += 1
        generation = self.browser_search_generation
        found = []

        def search_chunk(offset=0):
            if (generation != self.browser_search_generation or
                    index_ref is not self.browser_index):
                return
            # Small searches finish synchronously (existing GUI semantics).
            # Large searches yield regularly to Tk's event loop to keep the
            # app responsive and allow source changes or a new search.
            stop = min(offset + 2000, len(entries))
            for entry in entries[offset:stop]:
                if (not show_tmp and is_temporary_file(entry)) or (
                        not show_deleted and entry.is_deleted):
                    continue
                if match(entry, paths.get(entry.key, entry.name)
                         if criteria.in_path and criteria.name.strip() else entry.name):
                    found.append(entry)
            if stop < len(entries):
                self.browser_path.set(
                    f'Suche läuft · {stop:,} / {len(entries):,} Einträge geprüft')
                self.after(1, lambda: search_chunk(stop))
            else:
                self.browser_path.set(
                    f'Erweiterte Suche · {len(found):,} Treffer in {self.browser_fs} '
                    '(Anzeige ggf. zusätzlich nach Rettbarkeit gefiltert)')
                self._display_browser_entries(found)

        search_chunk()

    def _clear_advanced_search(self):
        self.browser_search.set('')
        self.browser_extension.set('')
        self.browser_min_size.set('')
        self.browser_max_size.set('')
        self.browser_kind.set('Alle')
        self.browser_kind_display.set(translate('Alle', self.language))
        self.browser_search_paths.set(False)
        self._show_current_directory()

    def _focus_browser_search(self, event=None):
        if self.tabs.select() == str(self.ntfs_tab):
            self.browser_search_entry.focus_set()
            self.browser_search_entry.selection_range(0, 'end')
            return 'break'

    def _select_all_browser_files(self, event=None):
        self.file_tree.selection_set(self.file_tree.get_children(''))
        return 'break'

    def _copy_selected_browser_paths(self, event=None):
        selected = self._selected_browser_entries()
        if selected:
            text = '\n'.join(self.browser_paths.get(item.key, item.name) for item in selected)
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status.set(f'{len(selected)} Dateipfad/-pfade in Zwischenablage kopiert.')
        return 'break'

    def _browser_context_popup(self, event):
        item_id = self.file_tree.identify_row(event.y)
        if not item_id or item_id not in self.browser_entries_visible:
            return
        if item_id not in self.file_tree.selection():
            self.file_tree.selection_set(item_id)
        selected = self._selected_browser_entries()
        popup = tk.Menu(self.file_tree, tearoff=False)
        if len(selected) == 1 and selected[0].is_directory:
            popup.add_command(label='Ordner öffnen', command=self._open_selected_browser_directory)
        if len(selected) == 1 and not selected[0].is_directory:
            popup.add_command(label='Vorschau', command=self.preview_entry)
            popup.add_command(label='Datei prüfen', command=self.inspect_file)
        popup.add_command(label='Pfad kopieren', command=self._copy_selected_browser_paths)
        popup.add_separator()
        popup.add_command(label='Stapel-Export / fortsetzen', command=self.export_browser_selection)
        try:
            popup.tk_popup(event.x_root, event.y_root)
        finally:
            popup.grab_release()

    def _open_selected_browser_directory(self, event=None):
        selection = self.file_tree.selection()
        if not selection or not self.browser_index:
            return
        entry = self.browser_entries_visible.get(selection[0])
        if not entry:
            return
        if not entry.is_directory:
            self.preview_entry()
            return
        folder_node = (self.folder_tree.selection() or ('root',))[0]
        # Find existing directory in the current tree, or create an isolated child
        # for a search hit; use ancestry to prevent circular damaged references.
        for child in self.folder_tree.get_children(folder_node):
            if self.browser_nodes.get(child) == entry.record_number:
                self.folder_tree.selection_set(child)
                self.folder_tree.focus(child)
                self.folder_tree.see(child)
                return
        if entry.record_number in self.browser_ancestors.get(folder_node, frozenset()):
            return
        self.browser_sequence += 1
        child = f'dir:{self.browser_sequence}'
        flagged = entry.record_number in self.browser_warning_records
        icon = '⚠' if flagged else ('✕' if entry.is_deleted else '📁')
        self.folder_tree.insert(folder_node, 'end', iid=child,
                                text=f'{icon} {entry.name}',
                                tags=('warning',) if flagged else (('deleted',) if entry.is_deleted else ()),
                                open=False)
        self.browser_nodes[child] = entry.record_number
        self.browser_ancestors[child] = self.browser_ancestors.get(folder_node, frozenset()) | {entry.record_number}
        self.folder_tree.item(folder_node, open=True)
        self.folder_tree.selection_set(child)
        self.folder_tree.focus(child)
        self.folder_tree.see(child)
        self._load_folder_children(child)

    def _initialize_browser_split(self, event=None):
        """Give the folder tree a usable width on first display only.

        The files tab starts hidden, so attempting sashpos() during _build_ntfs
        has no reliable width. A Configure event on the visible paned window
        is the first opportunity for a meaningful position. Subsequent resize
        and manual dragging always remain under the user's control.
        """
        if self._browser_sash_initialized:
            return
        pane = self.browser_paned
        width = pane.winfo_width()
        if not pane.winfo_ismapped() or width < 620:
            return
        folder_ratio = self._view_settings.get('folder_ratio') or .38
        folder_width = min(max(round(width * folder_ratio), 330), width - 320)
        pane.sashpos(0, folder_width)
        self._browser_sash_initialized = True

    def _selected_browser_entries(self):
        return [self.browser_entries_visible[i] for i in self.file_tree.selection()
                if i in self.browser_entries_visible]

    def _build_export_actions(self):
        """Only entry points remain here; progress and results own their window."""
        self.export_blocks = ExportBlocks()
        self._export_started_at = self._export_ended_at = None
        self.export_actions = ttk.Frame(self.ntfs_tab)
        self.export_actions.pack(fill='x', pady=(2, 0), before=self.browser_paned)
        self.export_progress_button = ttk.Button(self.export_actions, text='Fortschritt / Ergebnis',
                                                command=self._show_export_progress)
        self.export_progress_button.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.export_preflight_button = ttk.Button(self.export_actions, text='Export prüfen',
                                                 command=self.preflight_selection)
        self.export_preflight_button.pack(side='right')

    def _cancel_export(self):
        if self.export_running:
            self.export_cancel.set()
            self.status.set('Abbruch angefordert – laufender Schreibvorgang wird sicher beendet …')
            self._refresh_export_view()

    def _refresh_export_view(self):
        window = self.__dict__.get('_export_progress_window')
        if window is not None and window.winfo_exists():
            window.refresh_display()

    def _show_export_results(self):
        report = getattr(self.export_result, 'log', '') if self.export_result else self.export_progress.log
        if not report or not os.path.isfile(report):
            messagebox.showinfo('Exportbericht', 'Noch kein vollständiger Exportbericht vorhanden.', parent=self)
            return
        win = tk.Toplevel(self)
        win.title('Tenshi – Exportergebnisse')
        win.geometry('980x620')
        ttk.Label(win, text=f'Bericht: {report}', wraplength=930).pack(anchor='w', padx=14, pady=10)
        ttk.Label(win, text=EXPORT_SCOPE + '\n' + RESUME_SCOPE,
                  wraplength=930).pack(anchor='w', padx=14, pady=(0, 8))
        ttk.Button(win, text='Exportierte ZIP-Datei prüfen …',
                   command=lambda: self._check_exported_zip(win, os.path.dirname(report))).pack(
                       anchor='w', padx=14, pady=(0, 8))
        area = ttk.Frame(win, padding=(14, 0, 14, 14))
        area.pack(fill='both', expand=True)
        scrollbar = ttk.Scrollbar(area, orient='vertical')
        scrollbar.pack(side='right', fill='y')
        tb = tk.Text(area, wrap='none', font=('Consolas', 10), yscrollcommand=scrollbar.set)
        scrollbar.configure(command=tb.yview)
        tb.pack(fill='both', expand=True)
        try:
            with open(report, 'r', encoding='utf-8', errors='replace') as f:
                report_text = f.read(5 * 1024 * 1024 + 1)
            if len(report_text) > 5 * 1024 * 1024:
                report_text = report_text[:5 * 1024 * 1024] + '\n[… Bericht im Fenster gekürzt, Originaldatei unverändert …]'
            tb.insert('1.0', report_text)
        except OSError as exc:
            tb.insert('1.0', f'Bericht konnte nicht geöffnet werden: {exc}')
        tb.configure(state='disabled')

    def _show_export_progress(self):
        window = self.__dict__.get('_export_progress_window')
        if window is not None and window.winfo_exists():
            window.deiconify()
            window.lift()
            window.refresh_display()
        else:
            window = self._export_progress_window = ExportProgressWindow(self)
        return window

    def _show_export_scope(self):
        messagebox.showinfo('Prüfumfang', translate(EXPORT_SCOPE,self.language)+'\n\n'+
                            translate(RESUME_SCOPE,self.language), parent=self)

    def _save_export_report(self):
        if self.export_running or not self.export_result or self.__dict__.get('_export_report_saving'):
            return
        report = self.export_result.log
        source = self.__dict__.get('_export_source', '')
        if not report or not os.path.isfile(report):
            return
        destination = filedialog.asksaveasfilename(parent=self, title='Bericht speichern',
            initialdir=getattr(self.export_result, 'root', '') or os.path.dirname(report),
            initialfile='Tenshi_Exportbericht_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]+'.txt', defaultextension='.txt',
            filetypes=[('Textdateien', '*.txt')])
        if not destination:
            return
        self._export_report_saving = True
        def finish(error):
            self._export_report_saving = False
            if error:
                messagebox.showerror('Exportbericht', error, parent=self)
            else:
                messagebox.showinfo('Exportbericht', 'Bericht wurde gespeichert.', parent=self)
        def worker():
            try:
                copy_export_report(source, report, destination)
                error = ''
            except Exception as exc:
                error = export_error_message(exc, self.language)
            self._post_scan_callback(lambda error=error: finish(error))
        threading.Thread(target=worker, daemon=True).start()

    def _open_export_folder(self):
        folder = self.export_progress.root
        if not folder or not os.path.isdir(folder):
            return
        try:
            if os.name == 'nt':
                os.startfile(folder)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', folder], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        except OSError as exc:
            messagebox.showerror('Export', str(exc), parent=self)

    def _check_exported_zip(self, parent, folder):
        files_folder = os.path.join(folder, 'files')
        initial_folder = files_folder if os.path.isdir(files_folder) else folder
        path = filedialog.askopenfilename(parent=parent, title='Exportierte ZIP-Datei prüfen …',
            initialdir=initial_folder, filetypes=[('ZIP', '*.zip'), ('Alle Dateien', '*')])
        if not path:
            return
        win = tk.Toplevel(parent)
        win.title('ZIP-Inhaltsprüfung')
        win.geometry('760x340')
        panel = ttk.Frame(win, padding=14)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text=path, wraplength=710).pack(anchor='w')
        ttk.Label(panel, text=ZIP_CHECK_SCOPE, wraplength=710).pack(anchor='w', pady=(10, 6))
        ttk.Label(panel, text='Grenzen: 512 MiB Archiv, 512 MiB entpackte Daten, 10.000 Einträge.',
                  wraplength=710).pack(anchor='w')
        status = ttk.Label(panel, text='ZIP-Inhalt wird geprüft …', wraplength=710)
        status.pack(anchor='w', pady=10)
        bar = ttk.Progressbar(panel, mode='indeterminate')
        bar.pack(fill='x')
        bar.start(30)
        cancel = threading.Event()
        results = queue.SimpleQueue()
        def close():
            cancel.set()
            win.destroy()
        buttons = ttk.Frame(panel)
        buttons.pack(fill='x', pady=(12, 0))
        stop = ttk.Button(buttons, text='Prüfung abbrechen', command=cancel.set)
        stop.pack(side='left')
        ttk.Button(buttons, text='Schließen', command=close).pack(side='right')
        win.protocol('WM_DELETE_WINDOW', close)
        win.bind('<Destroy>', lambda event: cancel.set() if event.widget is win else None, add='+')
        def worker():
            try:
                result = verify_zip(path, cancel=cancel.is_set,
                    progress=lambda files, count, total: results.put(('progress', (files, count, total))))
                results.put(('result', result))
            except Exception:
                results.put(('result', None))
        def drain():
            if not win.winfo_exists():
                return
            for _ in range(100):
                try:
                    kind, value = results.get_nowait()
                except queue.Empty:
                    self._after_window(win, 100, drain)
                    return
                if kind == 'result':
                    result = value
                    break
                files, count, total = value
                bar.stop()
                bar.configure(mode='determinate', maximum=100, value=min(99, 100 * count / max(1, total)))
                status.configure(text=translate('ZIP-Inhalt wird geprüft …', self.language) + '\n' +
                    translate('Geprüfte Dateien', self.language) + f': {files} · ' +
                    readable_bytes(count) + ' / ' + readable_bytes(total))
            else:
                self._after_window(win, 100, drain)
                return
            bar.stop()
            bar.configure(mode='determinate', maximum=100)
            if cancel.is_set() and result is not None:
                result = ZipCheckResult('cancelled', result.files, result.checked_bytes,
                                        'Prüfung abgebrochen.')
            if result is not None and result.status == 'cancelled':
                bar.configure(value=0)
            elif result is not None and result.status == 'passed':
                bar.configure(value=100)
            else:
                bar.configure(value=min(99, float(bar.cget('value'))))
            stop.configure(state='disabled')
            if result is None:
                status.configure(text=translate('Datei konnte nicht vollständig gelesen werden.', self.language))
            else:
                status.configure(text=translate(result.message, self.language) + '\n' +
                    translate('Geprüfte Dateien', self.language) + f': {result.files} · ' +
                    readable_bytes(result.checked_bytes))
        threading.Thread(target=worker, daemon=True).start()
        self._after_window(win, 100, drain)

    def _handle_export_event(self, data):
        kind = data.get('type')
        if kind == 'run_finish':
            self._export_ended_at = time.monotonic()
            self.export_running = False
            self.export_result = data['result']
            self.export_button.configure(state='normal')
            rep = self.export_result
            self.export_progress.failed = bool(rep.failed)
            self.export_progress.cancelled = bool(rep.cancelled)
            self.export_progress.ended = True
            label = translate('Beendet mit Fehlern', self.language) if rep.failed else (
                'Abgebrochen' if rep.cancelled else 'Beendet')
            self.status.set(f'Stapel-Export {label.lower()}: {rep.exported} neu, '
                            f'{rep.verified_existing} {translate(RESUME_LABEL, self.language)}, {rep.failed} Fehler.')
            self._refresh_export_view()
            if rep.failed:
                messagebox.showwarning(translate('Beendet mit Fehlern', self.language),
                    translate('Beim Stapel-Export sind {count} Fehler aufgetreten. Nicht alle Dateien konnten exportiert oder bestätigt werden. Details stehen im Ergebnisbericht.',
                              self.language).format(count=rep.failed), parent=self)
            return
        if kind == 'run_error':
            self._export_ended_at = time.monotonic()
            self.export_blocks.errors += 1
            self.export_progress.failed = self.export_progress.ended = True
            self.export_running = False
            self.export_button.configure(state='normal')
            self.status.set('Stapel-Export mit Fehler abgebrochen.')
            self._refresh_export_view()
            messagebox.showerror('Stapel-Export', data['error'], parent=self)
            return
        self.export_blocks.handle(data)
        self.export_progress.handle(data)
        if kind == 'plan':
            if self._export_started_at is None:
                self._export_started_at = time.monotonic()
            if data.get('resumed'):
                self.status.set('Vorhandenen Export prüfen und fortsetzen …')
        elif kind == 'done' and data['status'] in ('Fehler', 'Abgebrochen'):
            self.status.set(f'{data["status"]}: {data["path"]}: {data.get("detail", "")}')

    def _drain_export_events(self):
        count = 0
        while count < 350:
            try:
                item = self._export_events.get_nowait()
            except queue.Empty:
                break
            self._handle_export_event(item)
            count += 1
        if self.export_running or not self._export_events.empty():
            self.after(110, self._drain_export_events)

    def export_browser_selection(self):
        """Start a resumable batch and its separate progress/result window."""
        if self.export_running:
            messagebox.showinfo('Export', 'Ein Export läuft bereits.')
            return
        if not self.browser_index or not self.browser_source:
            messagebox.showinfo('Export', 'Zuerst ein Dateisystem einlesen.')
            return
        chosen = self._selected_browser_entries()
        if not chosen:
            messagebox.showinfo('Export', 'Rechts Dateien/Ordner auswählen (Strg/Umschalt für mehrere).')
            return
        target = filedialog.askdirectory(title='Zielordner auf einem anderen Datenträger wählen', parent=self)
        if not target:
            return
        try:
            ensure_safe_destination(self.browser_source, target)
        except Exception as exc:
            messagebox.showerror('Sicherer Export', str(exc))
            return
        if not messagebox.askyesno('Stapel-Export',
                f'{len(chosen)} ausgewählte Einträge samt Unterordnern exportieren?\n\n'
                f'Zielordner: {target}\n\n'
                'Ein eigener Exportordner mit Statusdatei wird angelegt. '
                'Bei gleicher Auswahl ist Fortsetzen möglich. '\
                'Vorhandene fremde Dateien bleiben unangetastet.'):
            return
        src, index = self.browser_source, self.browser_index
        self.export_cancel.clear()
        self.export_running = True
        self.export_result = None
        self._export_events = queue.SimpleQueue()
        self.export_progress = QueueProgress()
        self.export_blocks = ExportBlocks()
        self._export_started_at = time.monotonic()
        self._export_ended_at = None
        self._export_source = src
        self.export_button.configure(state='disabled')
        # Paint the main action state before starting the worker.
        self.tabs.select(self.ntfs_tab)
        self.update_idletasks()
        self.status.set('Stapel-Export gestartet …')
        self._show_export_progress()

        def worker():
            try:
                rep = export_batch(src, index, chosen, target,
                                   cancel=self.export_cancel.is_set,
                                   event=self._export_events.put)
                self._export_events.put({'type': 'run_finish', 'result': rep})
            except Exception as exc:
                self._export_events.put({'type': 'run_error', 'error': export_error_message(exc, self.language)})
        # Tkinter variables from previously closed windows must be finalized
        # on the UI thread, not later by Python's GC inside the export worker.
        # Otherwise Tcl cleanup can block an otherwise healthy background export.
        gc.collect()
        threading.Thread(target=worker, daemon=True).start()
        self.after(110, self._drain_export_events)

    def preflight_selection(self):
        """Show a read-only assessment of the same tree used by Stapel-Export.

        Disk contents are not read. Results are intentionally advisory; source
        data may change and a later export must check data while it reads.
        """
        if not self.browser_index or not self.browser_source:
            messagebox.showinfo('Export-Vorabprüfung', 'Zuerst ein Dateisystem einlesen.', parent=self)
            return
        selected = self._selected_browser_entries()
        if not selected:
            messagebox.showinfo('Export-Vorabprüfung', 'Bitte Dateien oder Ordner in der rechten Liste markieren.', parent=self)
            return
        source, index, filesystem = self.browser_source, self.browser_index, self.browser_fs
        win = tk.Toplevel(self)
        win.title('Tenshi – Export-Vorabprüfung')
        win.geometry('980x620')
        win.minsize(680, 440)
        panel = ttk.Frame(win, padding=12)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='Export-Vorabprüfung (ohne Dateiinhalte zu lesen)',
                  font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        status_text = tk.StringVar(value='Einträge werden anhand der Metadaten geprüft …')
        ttk.Label(panel, textvariable=status_text, wraplength=890).pack(anchor='w', pady=(7, 8))
        note = METADATA_SCOPE
        ttk.Label(panel, text=note, wraplength=890, foreground='#9a3412').pack(anchor='w', pady=(0, 8))
        columns = ('state', 'bytes', 'details')
        table = ttk.Treeview(panel, columns=columns, show='tree headings')
        table.heading('#0', text='Datei / Ordner')
        table.column('#0', width=340, minwidth=140)
        for key, title, width in [('state', 'Bewertung', 170), ('bytes', 'Größe', 110),
                                  ('details', 'Hinweise', 460)]:
            table.heading(key, text=title)
            table.column(key, width=width, minwidth=90)
        scroll = ttk.Scrollbar(panel, orient='vertical', command=table.yview)
        table.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        table.pack(fill='both', expand=True)
        table.tag_configure('blocked', foreground='#b91c1c')
        table.tag_configure('warn', foreground='#b45309')
        actions = ttk.Frame(panel)
        actions.pack(fill='x', pady=(8, 0))
        report_holder = {'result': None}
        save_btn = ttk.Button(actions, text='Prüfbericht speichern', state='disabled')
        save_btn.pack(side='left')
        ttk.Button(actions, text='Schließen', command=win.destroy).pack(side='right')

        def save_report():
            report = report_holder['result']
            if report is None:
                return
            filename = filedialog.asksaveasfilename(parent=win, title='Prüfbericht speichern',
                      initialfile='tenshi-vorabpruefung.txt', defaultextension='.txt',
                      filetypes=[('Text', '*.txt')])
            if not filename:
                return
            try:
                ensure_safe_destination(source, filename)
                with open(filename, 'x', encoding='utf-8') as f:
                    f.write(report.as_text())
                messagebox.showinfo('Export-Vorabprüfung', 'Bericht erfolgreich gespeichert.', parent=win)
            except (OSError, ValueError) as exc:
                messagebox.showerror('Export-Vorabprüfung', str(exc), parent=win)
        save_btn.configure(command=save_report)
        results = queue.SimpleQueue()
        def worker():
            try:
                results.put(('ok', inspect_selection(index, selected, filesystem=filesystem)))
            except Exception as exc:
                results.put(('error', str(exc)))
        def poll():
            if not win.winfo_exists():
                return
            try:
                kind, payload = results.get_nowait()
            except queue.Empty:
                self._after_window(win, 100, poll)
                return
            if source != self.browser_source or self.browser_index is not index:
                status_text.set('Quelle wurde gewechselt. Ergebnis verworfen.')
                return
            if kind == 'error':
                status_text.set('Die Vorabprüfung konnte nicht abgeschlossen werden: ' + payload)
                return
            report_holder['result'] = payload
            status_text.set(payload.summary())
            for row in payload.items[:MAX_DETAIL_ROWS]:
                tags = ('blocked',) if row.state == 'Gesperrt' else ('warn',) if row.state == 'Warnung' else ()
                table.insert('', 'end', text=row.path, tags=tags,
                             values=(translate(METADATA_LABEL if row.state == 'Bereit' else row.state, self.language), f'{row.bytes_expected:,}',
                                     '; '.join(translate(note, self.language) for note in row.details)))
            if len(payload.items) > MAX_DETAIL_ROWS:
                status_text.set(payload.summary() + f' | Liste zeigt erste {MAX_DETAIL_ROWS:,} Einträge; Bericht enthält alle.')
            save_btn.configure(state='normal')
        threading.Thread(target=worker, daemon=True).start()
        self._after_window(win, 100, poll)

    def inspect_file(self):
        """Show metadata before recovery and offer optional bounded read check."""
        selection = self._selected_browser_entries()
        if len(selection) != 1:
            messagebox.showinfo('Datei prüfen', 'Bitte genau eine Datei auswählen.', parent=self)
            return
        item = selection[0]
        quality = assess(item)
        source, index, filesystem = self.browser_source, self.browser_index, self.browser_fs
        win = tk.Toplevel(self)
        win.title('Dateiprüfung – ' + item.name)
        win.geometry('760x445')
        win.minsize(650, 390)
        panel = ttk.Frame(win, padding=18)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='Datei vor der Wiederherstellung prüfen',
                  font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        description = (f'Name: {item.name}\nDateisystem: {filesystem}\n'
                       f'Eintrag: {item.record_number}\n'
                       f'Gemeldete Dateigröße: {item.size:,} Bytes\n'
                       f'Status: {item.status}\nRettbarkeit: {quality.label}\n'
                       f'Einordnung: {quality.detail}')
        ttk.Label(panel, text=description, justify='left', wraplength=690).pack(
            anchor='w', fill='x', pady=(10, 12))
        detail = tk.StringVar(value='Noch keine vollständige Leseprüfung durchgeführt.')
        ttk.Label(panel, textvariable=detail, wraplength=700, justify='left').pack(
            anchor='w', fill='x', pady=(5, 8))
        progress = ttk.Progressbar(panel, orient='horizontal', maximum=max(1, item.size), value=0)
        progress.pack(fill='x', pady=(5, 10))
        info = tk.Text(panel, height=4, wrap='word', font=('Consolas', 9))
        info.insert('1.0', 'Die Leseprüfung vergleicht die gelesene Bytezahl mit der gemeldeten Dateigröße.\n'
                    'Sie speichert keine Daten und prüft keine bekannte Original-Prüfsumme.')
        info.configure(state='disabled')
        info.pack(fill='both', expand=True)
        buttons = ttk.Frame(panel)
        buttons.pack(fill='x', pady=(10, 0))
        cancel_event = threading.Event()
        worker_state = {'running': False}

        def set_info(message):
            if not win.winfo_exists():
                return
            info.configure(state='normal')
            info.delete('1.0', 'end')
            info.insert('1.0', message)
            info.configure(state='disabled')

        def handle_close():
            cancel_event.set()
            win.destroy()

        def set_progress(value):
            if win.winfo_exists():
                progress.configure(value=value)
                detail.set(f'{value:,} von {item.size:,} Bytes gelesen …')

        def finish_ok(report):
            worker_state['running'] = False
            if not win.winfo_exists():
                return
            start_btn.configure(state='normal')
            stop_btn.configure(state='disabled')
            detail.set(f'Lesetest abgeschlossen: {report.read_bytes:,} / {report.expected_bytes:,} Bytes')
            progress.configure(value=report.read_bytes)
            set_info(translate(READ_SCOPE, self.language) + '\n\nSHA-256: ' + report.sha256)

        def finish_error(exc):
            worker_state['running'] = False
            if not win.winfo_exists():
                return
            start_btn.configure(state='normal')
            stop_btn.configure(state='disabled')
            detail.set('Leseprüfung nicht vollständig.')
            set_info(str(exc) + '\n\nKeine Integritätsbestätigung möglich.')

        def start_verification():
            if worker_state['running']:
                return
            if item.is_directory or not item.recoverable:
                messagebox.showwarning('Dateiprüfung', quality.detail, parent=win)
                return
            if item.size > MAX_VERIFY_BYTES:
                messagebox.showinfo('Dateiprüfung',
                    f'Für die vollständige Leseprüfung gilt eine Sicherheitsgrenze von '
                    f'{MAX_VERIFY_BYTES // 1024**2} MiB. Bitte große Dateien direkt exportieren '
                    'und auf einem gesunden Zielmedium prüfen.', parent=win)
                return
            if is_device_source(source):
                if not messagebox.askyesno('Leseprüfung am Datenträger',
                    'Die Prüfung liest den vollständigen Datenstrom erneut. Bei physisch '
                    'instabilen Laufwerken kann das zusätzliche Belastung verursachen. '
                    'Möglichst zuerst ein Image erstellen. Jetzt wirklich lesen?', parent=win):
                    return
            cancel_event.clear()
            worker_state['running'] = True
            start_btn.configure(state='disabled')
            stop_btn.configure(state='normal')
            detail.set('Leseprüfung läuft …')
            progress.configure(value=0)
            # Queue the worker's result and drain on Tk main thread; no Tk calls from worker.
            results = queue.SimpleQueue()
            def worker():
                try:
                    report = verify_file(source, index, item, filesystem=filesystem,
                        cancel=cancel_event.is_set,
                        progress=lambda amount: results.put(('progress', amount)))
                    results.put(('success', report))
                except Exception as exc:
                    results.put(('error', str(exc)))
            def drain():
                if not win.winfo_exists():
                    return
                while not results.empty():
                    kind, value = results.get_nowait()
                    if kind == 'progress':
                        set_progress(value)
                    elif kind == 'success':
                        finish_ok(value)
                        return
                    elif kind == 'error':
                        finish_error(value)
                        return
                if worker_state['running']:
                    self._after_window(win, 120, drain)
            threading.Thread(target=worker, daemon=True).start()
            self._after_window(win, 120, drain)

        start_btn = ttk.Button(buttons, text='Vollständig lesend prüfen', command=start_verification)
        start_btn.pack(side='left')
        stop_btn = ttk.Button(buttons, text='Prüfung abbrechen', state='disabled',
                              command=cancel_event.set)
        stop_btn.pack(side='left', padx=8)
        ttk.Button(buttons, text='Schließen', command=handle_close).pack(side='right')
        win.protocol('WM_DELETE_WINDOW', handle_close)
        if item.is_directory or not item.recoverable or item.size > MAX_VERIFY_BYTES:
            start_btn.configure(state='disabled')

    def preview_entry(self):
        selection = self._selected_browser_entries()
        if len(selection) != 1:
            messagebox.showinfo('Vorschau', 'Bitte genau eine Datei auswählen.')
            return
        item = selection[0]
        quality = assess(item)
        if item.is_directory or not item.recoverable:
            messagebox.showwarning('Vorschau', quality.detail)
            return
        # Reading takes place on a worker thread; Tk updates stay on its main thread.
        source, index, filesystem = self.browser_source, self.browser_index, self.browser_fs
        win = tk.Toplevel(self)
        win.title('Dateivorschau – ' + item.name)
        win.geometry('850x570')
        info = (f'Name: {item.name}\nDateisystem: {filesystem}\n'
                f'Dateigröße: {item.size:,} Bytes\nStatus: {item.status}\n'
                f'Rettbarkeit: {quality.label}\n{quality.detail}\n'
                f'Vorschau: höchstens {PREVIEW_LIMIT // 1024} KiB Textdaten; keine Integritätsprüfung.')
        ttk.Label(win, text=info, wraplength=800, justify='left').pack(fill='x', padx=14, pady=(12, 8))
        content = ttk.Frame(win)
        content.pack(fill='both', expand=True, padx=14, pady=(0,12))
        notice = ttk.Label(content, text='Lese einen begrenzten Dateiausschnitt …')
        notice.pack(anchor='w')
        def worker():
            try:
                device_identity = getattr(index, '_device_identity', None)
                check_device_identity(source, device_identity)
                # Image previews only when the entire image is small enough.
                limit = IMAGE_LIMIT if item.size <= IMAGE_LIMIT else PREVIEW_LIMIT
                with open_source(source) as f:
                    if filesystem == 'NTFS' and item.data_kind == 'resident':
                        data = (item.resident_data or b'')[:limit]
                    elif filesystem == 'NTFS':
                        data = b''.join(iter_stream(f, index.info, item.data_runs,
                            0, min(item.initialized_size, limit)))
                    else:
                        data = b''.join(index.volumes.iter_file(f, item, max_bytes=limit))
                check_device_identity(source, device_identity)
                self._post_scan_callback(lambda d=data: show_preview(d))
            except Exception as exc:
                self._post_scan_callback(lambda msg=str(exc): show_error(msg))
        def show_error(message):
            if win.winfo_exists():
                notice.configure(text='Vorschau fehlgeschlagen: ' + message)
        def show_preview(data):
            if not win.winfo_exists():
                return
            preview = describe(data[:PREVIEW_LIMIT], item.size)
            notice.destroy()
            if (preview.kind == 'image' and len(data) == item.size and
                    item.size <= IMAGE_LIMIT):
                try:
                    photo = tk.PhotoImage(data=base64.b64encode(data).decode('ascii'))
                    label = ttk.Label(content, image=photo)
                    label.image = photo
                    label.pack(anchor='center', pady=10)
                    ttk.Label(content, text='Bildvorschau (Originalgröße, ggf. abgeschnitten)').pack(anchor='w')
                    return
                except tk.TclError:
                    pass
            if preview.kind == 'image':
                message = ('Bild ist für eine vollständige Vorschau zu groß oder das Format '
                           'wird von Tk nicht unterstützt. Bitte exportieren und prüfen.')
            else:
                message = preview.text
            tb = tk.Text(content, font=('Consolas', 10), wrap='word')
            scrollbar = ttk.Scrollbar(content, orient='vertical', command=tb.yview)
            tb.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side='right', fill='y')
            tb.pack(side='left', fill='both', expand=True)
            tb.insert('1.0', message)
            tb.configure(state='disabled')
        threading.Thread(target=worker, daemon=True).start()


def main():
    app = RecoveryDeskApp()
    app.mainloop()

if __name__ == "__main__":
    main()
