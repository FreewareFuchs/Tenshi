"""Non-modal export view. Closing it never changes the export worker or queue."""
import os
import time
import tkinter as tk
from tkinter import ttk

from .export_queue import readable_bytes, readable_duration
from .i18n import translate

LABELS = {'pending': 'Offen', 'copied': 'Kopiert, noch ungeprüft',
          'confirmed': 'Export bestätigt', 'error': 'Fehler im Export',
          'unconfirmed': 'Nicht bestätigt', 'mixed': 'Gemischt / teilweise'}
SYMBOLS = {'pending': '·', 'copied': '→', 'confirmed': '✓', 'error': '!',
           'unconfirmed': '?', 'mixed': '~'}


class BlockGrid(tk.Canvas):
    """Reusable bounded grid: create 200 items once, change only dirty cells."""
    def __init__(self, parent):
        super().__init__(parent, height=230, highlightthickness=0, takefocus=True)
        self.rectangles = [self.create_rectangle(0, 0, 0, 0) for _ in range(100)]
        self.symbols = [self.create_text(0, 0, text='', font=('Segoe UI', 9, 'bold')) for _ in range(100)]
        self._key = None
        self._last_states = ()

    def paint(self, states, dark, background):
        if str(self.cget('bg')) != background:
            self.configure(bg=background)
        geometry = (self.winfo_width(), self.winfo_height())
        key = (geometry, dark, background)
        changed = key != self._key
        if not changed and states == self._last_states:
            return
        colors = ({'pending': '#393939', 'copied': '#15558b', 'confirmed': '#145c3b',
                   'error': '#962d35', 'unconfirmed': '#76511a', 'mixed': '#3b5477'} if dark else
                  {'pending': '#e5e7eb', 'copied': '#c3d9f5', 'confirmed': '#b9e3cc',
                   'error': '#f5c2c6', 'unconfirmed': '#f4d89e', 'mixed': '#d3d6ef'})
        foreground = '#ffffff' if dark else '#18202c'
        self.configure(bg=background)
        width, height = geometry
        side = min(width,height)
        origin_x, origin_y = (width-side)/2, (height-side)/2
        if changed:
            scale = float(self.tk.call('tk','scaling'))
            size = max(5,min(9,int((side/10-2)/(scale*1.4))))
            for item in self.symbols:
                self.itemconfigure(item,font=('Segoe UI',size,'bold'))
        for i, state in enumerate(states):
            if changed:
                col, row = i % 10, i // 10
                x1, x2 = origin_x+col*side/10+1, origin_x+(col+1)*side/10-1
                y1, y2 = origin_y+row*side/10+1, origin_y+(row+1)*side/10-1
                self.coords(self.rectangles[i], x1, y1, max(x1, x2), max(y1, y2))
                self.coords(self.symbols[i], (x1+x2)/2, (y1+y2)/2)
            if changed or i >= len(self._last_states) or state != self._last_states[i]:
                self.itemconfigure(self.rectangles[i], fill=colors[state], outline=foreground if state=='error' else background)
                self.itemconfigure(self.symbols[i], text=SYMBOLS[state], fill=foreground)
        self._key, self._last_states = key, states


class ExportProgressWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title('Tenshi – Exportfortschritt')
        # Owned, non-modal window: stay above Tenshi without covering other apps.
        self.transient(app)
        factor = max(1., float(self.tk.call('tk','scaling'))/(4/3))
        width = min(round(760*factor), max(620, self.winfo_screenwidth()-60))
        height = min(round(650*factor), max(550, self.winfo_screenheight()-80))
        self.geometry(f'{width}x{height}')
        self.minsize(min(round(620*factor),width), min(round(550*factor),height))
        # No grab, wait_window or worker cancellation on close.
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.labels = {}
        footer = ttk.Frame(self, padding=(12, 6, 12, 12))
        footer.pack(side='bottom', fill='x')
        for col in range(2):
            footer.columnconfigure(col, weight=1, uniform='actions')
        self.report_button = ttk.Button(footer, text='Ergebnisbericht', command=app._show_export_results)
        self.save_button = ttk.Button(footer, text='Bericht speichern', command=app._save_export_report)
        self.folder_button = ttk.Button(footer, text='Zielordner öffnen', command=app._open_export_folder)
        self.pause_button = ttk.Button(footer, text='Pause', command=app._toggle_export_pause)
        self.close_button = ttk.Button(footer, text='Schließen', command=self.destroy)
        self.cancel_button = ttk.Button(footer, text='Abbrechen', command=app._cancel_export)
        for button, row, col in ((self.report_button,0,0),(self.save_button,0,1),
                                 (self.pause_button,1,0),(self.folder_button,1,1),
                                 (self.cancel_button,2,0),(self.close_button,2,1)):
            button.grid(row=row, column=col, sticky='ew', padx=3, pady=3)
        body = ttk.Frame(self, padding=(12, 10, 12, 0))
        body.pack(fill='both', expand=True)
        body.columnconfigure(0,weight=1,uniform='content')
        body.columnconfigure(1,weight=1,uniform='content')
        body.rowconfigure(1,weight=1)
        phase = ttk.Label(body,text='',anchor='w',font=('Segoe UI',11,'bold'))
        phase.grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,6))
        self.labels['phase'] = phase
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        left.grid(row=1,column=0,sticky='nsew',padx=(0,10))
        right.grid(row=1,column=1,sticky='nsew')
        scope = ttk.Label(left,text='',justify='left')
        scope.pack(fill='x',pady=(0,3))
        self.labels['scope'] = scope
        for name in ('elapsed','transfer','progress','verification','counts','path'):
            label = ttk.Label(right, text='', anchor='w', justify='left')
            label.pack(fill='x', pady=(0, 3))
            self.labels[name] = label
        legend = ttk.Frame(left)
        legend.pack(side='bottom', fill='x', pady=(3, 0))
        self.legend_labels = {}
        for i, state in enumerate(LABELS):
            label = ttk.Label(legend, text='')
            label.grid(row=i//2, column=i%2, sticky='w', padx=(0, 12))
            self.legend_labels[state] = label
        note = ttk.Label(right, text='', justify='left')
        note.pack(side='bottom', fill='x', pady=(5, 0))
        self.labels['note'] = note
        self.grid_view = BlockGrid(left)
        self.grid_view.pack(fill='both', expand=True)
        self.refresh_display()
        self._resize_job = None
        self.grid_view.bind('<Configure>', self._resize_grid)
        self.app._after_window(self, 250, self._poll)

    def present(self):
        """Center when opened/reopened, without following every owner resize."""
        self.deiconify()
        self.refresh_display()
        self.update_idletasks()
        if self.state() != 'zoomed':
            width, height = self.winfo_width(), self.winfo_height()
            cx = self.app.winfo_rootx() + self.app.winfo_width() // 2
            cy = self.app.winfo_rooty() + self.app.winfo_height() // 2
            x, y = cx-width//2, cy-height//2
            left, top = self.winfo_vrootx(), self.winfo_vrooty()
            right, bottom = left+self.winfo_vrootwidth(), top+self.winfo_vrootheight()
            # Tk on Windows may expose only the primary screen. Do not pull an
            # owner on another monitor back onto it; keep the owner's center.
            if left <= cx < right and top <= cy < bottom:
                x = max(left, min(x, right-width))
                y = max(top, min(y, bottom-height))
            self.geometry(f'+{x}+{y}')
        self.lift()
        self.focus_set()

    def _resize_grid(self, event=None):
        if self._resize_job is None:
            self._resize_job = self.app._after_window(self, 40, self._redraw)

    def _redraw(self):
        self._resize_job = None
        self.grid_view.paint(self.app.export_blocks.cell_states(), self.app.theme=='dark', self.app._palette()['bg'])

    @staticmethod
    def _state(button, enabled):
        state = 'normal' if enabled else 'disabled'
        if str(button.cget('state')) != state:
            button.configure(state=state)

    def _poll(self):
        self.refresh_display()
        self.app._after_window(self, 250, self._poll)

    def _set(self, name, value):
        widget = self.labels[name]
        if str(widget.cget('text')) != value:
            widget.configure(text=value)

    def refresh_display(self):
        app, now = self.app, time.monotonic()
        q, blocks = app.export_progress, app.export_blocks
        t = lambda text: translate(text, app.language)
        running = app.export_running
        can_resume = app._can_resume_export()
        if not running and q.ended:
            phase = 'Abgebrochen' if q.cancelled else 'Beendet mit Fehlern' if q.failed else 'Beendet'
        elif not running and app.__dict__.get('_export_started_at') is None:
            phase = 'Noch kein Stapel-Export gestartet.'
        elif app.export_cancel.is_set() and running:
            phase = 'Export-Abbruch angefordert …'
        elif app.__dict__.get('_export_restoring') and running:
            phase = 'Exportauftrag wird geprüft …'
        elif app.__dict__.get('_export_target_reviewing') and running:
            phase = 'Exportziel wird geprüft …'
        elif q.paused:
            phase = 'Export pausiert.' if app.export_pause.requested else 'Export wird fortgesetzt …'
        elif app.export_pause.requested and running:
            phase = 'Export-Pause angefordert …'
        elif q.ended:
            phase = 'Export wird abgeschlossen …'
        elif q.checksum_phase:
            phase = 'Prüfsummen zusammenfassen …' if q.checksum_phase=='summary' else 'Prüfsummendatei speichern …'
        elif q.verifying:
            phase = 'Vorhandene Datei prüfen' if q.verifying_existing else 'SHA256 prüfen'
        elif q.active_path:
            phase = 'Datei kopieren'
        elif blocks.planned:
            phase = 'Export wird abgeschlossen …' if q.done_count>=q.total else 'Export läuft …'
        else:
            phase = 'Exportplan wird erstellt …'
        self._set('phase', t(phase))
        started = app.__dict__.get('_export_started_at')
        ended = app.__dict__.get('_export_ended_at')
        elapsed = max(0, (ended if ended is not None else now)-started) if started is not None else 0
        self._set('elapsed', t('Laufzeit: {duration}').format(duration=readable_duration(elapsed)))
        rate = 0 if q.paused or q.verifying or q.checksum_phase or not running else q.speed(now)
        eta = q.eta(now) if running and not q.paused and not q.checksum_phase else None
        transfer = t('Neu übertragen: {size} · Kopiertempo: {rate}/s').format(
            size=readable_bytes(q.written_bytes),rate=readable_bytes(rate))
        if eta is not None:
            transfer += '\n'+t('Kopier-Restzeit ca. {duration}').format(duration=readable_duration(eta))
        self._set('transfer', transfer)
        self._set('progress',t('Export bestätigt: {percent:.1f} %').format(percent=100*blocks.confirmed_fraction))
        # Hashing the copied stream and checking the destination are separate
        # existing engine steps. Neither starts another graphical progress bar.
        if app.__dict__.get('_export_restoring') and running:
            notice=app.__dict__.get('_export_restore_status') or 'Quelle und Auswahl werden nach Bestätigung erneut geprüft.'
        elif q.paused or app.export_pause.requested or (q.checksum_phase and running):
            notice = ''
        elif q.verifying and running:
            notice = ('Vorhandene Datei wird geprüft, nicht erneut kopiert.' if q.verifying_existing else
                      'SHA256-Prüfung der Zieldatei läuft …')
        elif running and q.active_path and q.active_written>0:
            notice = 'SHA256 wird während des Kopierens berechnet.'
        elif not running and q.ended and app.export_result and getattr(app.export_result,'log',''):
            notice = 'SHA256: Details im Ergebnisbericht.'
        else:
            notice = ''
        self._set('verification', t(notice))
        self._set('counts', t('Einträge: {done} von {total} · Fehler: {errors} · Übersprungen: {skipped}').format(
            done=q.done_count,total=q.total,errors=blocks.errors,skipped=blocks.skipped))
        path = q.active_path
        self._set('path', t('Aktuelle Datei: {path}').format(path=path[:22]+'…'+path[-32:] if len(path)>60 else path) if path else '')
        scope = t('Noch kein Exportplan vorhanden.' if not blocks.planned else
                            'Exportplan enthält keine Einträge.' if not blocks.total else
                            '100 Felder = 100 % der Einträge.' if blocks.entries else
                            '100 Felder = 100 % der geplanten Dateigrößen.')
        if q.resumed:scope += '\n'+t('Bestehender Export erkannt.')
        self._set('scope', scope)
        self._set('note', t('Fortsetzen prüft fertige Dateien; unvollständige Dateien beginnen von vorn.' if can_resume else
                            'Pause erhält den aktuellen Stand, solange Tenshi geöffnet bleibt.')+'\n'+t('Bestätigung betrifft den Export, nicht den Originalinhalt.'))
        width = max(200, (self.winfo_width() if self.winfo_width()>1 else 760)-30)
        for name,label in self.labels.items():
            wrap = width if name=='phase' else max(150,width//2-12)
            if int(float(label.cget('wraplength') or 0)) != wrap:
                label.configure(wraplength=wrap)
        for state,label in self.legend_labels.items():
            text = SYMBOLS[state]+'  '+t(LABELS[state])
            if str(label.cget('text')) != text:
                label.configure(text=text)
            wrap = max(90,width//4-16)
            if int(float(label.cget('wraplength') or 0)) != wrap:
                label.configure(wraplength=wrap)
        report = getattr(app.export_result,'log','') if app.export_result else ''
        available = not running and bool(report) and os.path.isfile(report)
        self._state(self.report_button, available)
        self._state(self.save_button, available and not app.__dict__.get('_export_report_saving'))
        self._state(self.folder_button, bool(q.root) and os.path.isdir(q.root))
        pause_text=t('Fortsetzen' if app.export_pause.requested or can_resume else 'Pause')
        if self.pause_button.cget('text')!=pause_text:self.pause_button.configure(text=pause_text)
        self._state(self.pause_button, can_resume or (running and not app.export_cancel.is_set()
                    and not app._exit_requested and not app.__dict__.get('_export_target_reviewing')))
        self._state(self.cancel_button, running and not app.export_cancel.is_set() and not app._exit_requested)
        colors = app._palette()
        self.grid_view.paint(blocks.cell_states(), app.theme=='dark', colors['bg'])
