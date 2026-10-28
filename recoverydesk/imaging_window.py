"""Reopenable imaging view; destroying this window never cancels the job."""
import os
import time
import tkinter as tk
from tkinter import ttk
from .progress_window import BlockGrid, SYMBOLS
from .export_queue import readable_bytes, readable_duration
from .i18n import translate

LEGEND={'pending':'Offen','confirmed':'Lesbar gespeichert',
        'error':'Lesefehler / Nullersatz','mixed':'Teilweise gespeichert',
        'unconfirmed':'Fehlerzuordnung unvollständig'}


class ImagingProgressWindow(tk.Toplevel):
    def __init__(self, app, session, *, pause, report, save, folder, settings):
        super().__init__(app)
        self.app,self.session=app,session
        self.title('Tenshi – Imaging')
        scale=max(1.,float(self.tk.call('tk','scaling'))/(4/3))
        width=min(round(800*scale),max(660,self.winfo_screenwidth()-60))
        height=min(round(670*scale),max(590,self.winfo_screenheight()-80))
        self.geometry(f'{width}x{height}')
        self.minsize(min(round(660*scale),width),min(round(590*scale),height))
        self.protocol('WM_DELETE_WINDOW',self.destroy)
        footer=ttk.Frame(self,padding=(12,6,12,12));footer.pack(side='bottom',fill='x')
        self.buttons={}
        for col in range(2):footer.columnconfigure(col,weight=1,uniform='actions')
        for index,(key,text,command) in enumerate([
                ('report','Fehlerstellen-Bericht',report),('save','Bericht speichern',save),
                ('folder','Zielordner öffnen',folder),('pause','Unterbrechen',pause),
                ('settings','Einstellungen / fortsetzen',settings),('close','Schließen',self.destroy)]):
            button=ttk.Button(footer,text=text,command=command)
            button.grid(row=index//2,column=index%2,sticky='ew',padx=3,pady=3)
            self.buttons[key]=button
        body=ttk.Frame(self,padding=(12,10,12,0));body.pack(fill='both',expand=True)
        for col in range(2):body.columnconfigure(col,weight=1,uniform='content')
        body.rowconfigure(1,weight=1)
        self.labels={}
        phase=ttk.Label(body,anchor='w',font=('Segoe UI',11,'bold'))
        phase.grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,6));self.labels['phase']=phase
        left=ttk.Frame(body);left.grid(row=1,column=0,sticky='nsew',padx=(0,10))
        right=ttk.Frame(body);right.grid(row=1,column=1,sticky='nsew')
        scope=ttk.Label(left,justify='left');scope.pack(fill='x');self.labels['scope']=scope
        self.legend={}
        legend=ttk.Frame(left);legend.pack(side='bottom',fill='x',pady=(4,0))
        for key in LEGEND:
            label=ttk.Label(legend,justify='left');label.pack(anchor='w',fill='x',pady=(0,2));self.legend[key]=label
        self.grid_view=BlockGrid(left);self.grid_view.pack(fill='both',expand=True)
        for key in ('elapsed','progress','transfer','errors','verification','path'):
            label=ttk.Label(right,justify='left');label.pack(fill='x',pady=(0,5));self.labels[key]=label
        note=ttk.Label(right,justify='left');note.pack(side='bottom',fill='x',pady=(5,0));self.labels['note']=note
        self._resize_job=None
        self.grid_view.bind('<Configure>',self._resize)
        self.refresh_display()
        app._after_window(self,250,self._poll)

    def _resize(self,event=None):
        if self._resize_job is None:self._resize_job=self.app._after_window(self,40,self._redraw)

    def _redraw(self):
        self._resize_job=None
        self.grid_view.paint(self.session['blocks'].cell_states(),self.app.theme=='dark',self.app._palette()['bg'])

    def _poll(self):
        self.refresh_display()
        self.app._after_window(self,250,self._poll)

    def refresh_display(self):
        s=self.session;b=s['blocks'];t=lambda text:translate(text,self.app.language)
        running=s['running'];state=s.get('state')
        if running and s['stop'].is_set():phase='Unterbrechung angefordert …'
        elif s.get('error'):phase='Image-Erstellung fehlgeschlagen'
        elif state=='verifying':phase='Vollvergleich läuft …'
        elif state=='paused':phase='Image-Erstellung unterbrochen'
        elif state=='complete':phase='Image-Erstellung beendet.'
        elif running:phase='Image wird erstellt …'
        else:phase='Noch nicht gestartet.'
        ended=s.get('ended')
        elapsed=max(0,(ended if ended is not None else time.monotonic())-s['started']) if s['started'] else 0
        baseline=s.get('baseline')
        rate=max(0,b.processed-baseline)/max(.001,elapsed) if running and state!='verifying' and baseline is not None else 0
        verification=(s.get('report') or {}).get('verification',{}).get('status')
        check=('BITGENAU VERIFIZIERT: Vollvergleich mit Quelle bestanden.' if verification=='verified' else
               'Vollvergleich läuft …' if running and state=='verifying' else
               'NICHT bitgenau verifiziert')
        values={'phase':t(phase),'scope':t('100 Felder = 100 % der Quellbytes.'),
                'elapsed':t('Laufzeit: {duration}').format(duration=readable_duration(elapsed)),
                'progress':t('Gespeichert: {percent:.1f} %').format(percent=100*b.processed/b.total if b.total else 0),
                'transfer':f'{readable_bytes(b.processed)} / {readable_bytes(b.total)}\n{readable_bytes(rate)}/s',
                'errors':t('Nullersatz: {size} · Fehlerbereiche: {count}').format(size=readable_bytes(b.unreadable),count=b.ranges),
                'verification':t(check),'path':s.get('destination',''),
                'note':t('Quellbereiche, keine einzelnen Sektoren. Grün bedeutet lesbar gespeichert, keinen bestandenen Vollvergleich.')}
        width=max(200,(self.winfo_width() if self.winfo_width()>1 else 800)-30)
        for key,text in values.items():
            label=self.labels[key]
            if str(label.cget('text'))!=text:label.configure(text=text)
            wrap=width if key=='phase' else max(150,width//2-12)
            if int(float(label.cget('wraplength') or 0))!=wrap:label.configure(wraplength=wrap)
        for key,label in self.legend.items():
            text=SYMBOLS[key]+'  '+t(LEGEND[key])
            if str(label.cget('text'))!=text:label.configure(text=text)
            wrap=max(150,width//2-15)
            if int(float(label.cget('wraplength') or 0))!=wrap:label.configure(wraplength=wrap)
        available=not running and bool(s.get('report'))
        for key,enabled in [('report',available),('save',available and not s.get('saving')),
                            ('pause',running and not s['stop'].is_set()),
                            ('folder',bool(s.get('destination')) and os.path.isdir(os.path.dirname(s['destination']))),
                            ('settings',not running)]:
            button=self.buttons[key];value='normal' if enabled else 'disabled'
            if str(button.cget('state'))!=value:button.configure(state=value)
        self.grid_view.paint(b.cell_states(),self.app.theme=='dark',self.app._palette()['bg'])
