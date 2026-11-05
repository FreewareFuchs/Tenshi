"""Metadata-only signature result view; actions reuse the application's readers."""
import tkinter as tk
from tkinter import ttk
from .i18n import translate


class SignatureResults(ttk.Frame):
    def __init__(self,parent,*,action,open_browser,export_running=lambda:False,language='de'):
        super().__init__(parent,padding=(12,0,12,8))
        self.entries={}
        self.language=language
        self._updating=False
        self._minimum_valid=True
        self.query=tk.StringVar(value='')
        self.kind=tk.StringVar(value='')
        self.kind_display=tk.StringVar(value=translate('Alle Dateitypen',language))
        self.minimum_kib=tk.StringVar(value='0')
        self.export_running=export_running
        self._action=action
        self._context_menu=None
        self.sort_column='offset';self.reverse=False
        buttons=ttk.Frame(self);buttons.pack(side='bottom',fill='x',pady=(8,0))
        buttons.columnconfigure((0,1,2),weight=1,uniform='actions')
        self.preview=ttk.Button(buttons,text='Vorschau',state='disabled',command=lambda:action('preview'))
        self.preview.grid(row=0,column=0,sticky='ew',padx=(0,3),pady=(0,4))
        self.inspect=ttk.Button(buttons,text='Datei prüfen',state='disabled',command=lambda:action('inspect'))
        self.inspect.grid(row=0,column=1,sticky='ew',padx=(3,0),pady=(0,4))
        self.export=ttk.Button(buttons,text='Stapel-Export / fortsetzen',style='Accent.TButton',
            state='disabled',command=lambda:action('export'))
        self.export.grid(row=1,column=0,columnspan=2,sticky='ew',padx=(0,3))
        self.browser=ttk.Button(buttons,text='In Dateiansicht anzeigen',state='disabled',command=open_browser)
        self.browser.grid(row=1,column=2,sticky='ew',padx=(3,0))
        self.report=ttk.Button(buttons,text='Fundliste speichern…',state='disabled',
            command=lambda:action('report'))
        self.report.grid(row=0,column=2,sticky='ew',padx=(3,0),pady=(0,4))
        filters=ttk.Frame(self);filters.pack(fill='x',pady=(0,3))
        filters.columnconfigure(1,weight=1)
        ttk.Label(filters,text='Suchtext:').grid(row=0,column=0,sticky='w')
        self.query_entry=ttk.Entry(filters,textvariable=self.query,width=16)
        self.query_entry.grid(row=0,column=1,sticky='ew',padx=(4,10))
        ttk.Label(filters,text='Typ:').grid(row=0,column=2,sticky='w')
        self.kind_combo=ttk.Combobox(filters,textvariable=self.kind_display,state='readonly',width=12)
        self.kind_combo.grid(row=0,column=3,padx=(4,10))
        self.kind_combo.bind('<<ComboboxSelected>>',self._select_kind)
        ttk.Label(filters,text='Ab (KiB):').grid(row=0,column=4,sticky='w')
        self.minimum_entry=ttk.Entry(filters,textvariable=self.minimum_kib,width=8)
        self.minimum_entry.grid(row=0,column=5,padx=(4,10))
        self.reset=ttk.Button(filters,text='Zurücksetzen',command=self.reset_filters)
        self.reset.grid(row=0,column=6)
        self.caption=ttk.Label(self,style='Sub.TLabel',wraplength=950)
        self.caption.pack(fill='x',pady=(0,3))
        table=ttk.Frame(self);table.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(table,columns=('type','size','offset'),show='tree headings',selectmode='extended',height=5)
        for key,title,width in (('#0','Name',340),('type','Typ',100),('size','Größe (Bytes)',125),('offset','Fundposition (Bytes)',180)):
            self.tree.heading(key,text=title,command=lambda col=key:self.sort(col))
            self.tree.column(key,width=width,minwidth=80,stretch=(key=='#0'))
        ys=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview)
        xs=ttk.Scrollbar(table,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set)
        ys.pack(side='right',fill='y');xs.pack(side='bottom',fill='x')
        self.tree.pack(fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>',lambda event:self._selection_changed())
        self.tree.bind('<Double-1>',lambda event:action('preview') if self.tree.identify_row(event.y) else None)
        self.tree.bind('<Return>',lambda event:action('preview'))
        self.tree.bind('<Control-a>',self.select_all)
        self.tree.bind('<Control-A>',self.select_all)
        self.tree.bind('<Escape>',self.clear_selection)
        self.tree.bind('<Button-3>',self._context_popup)
        self.tree.bind('<Shift-F10>',self._keyboard_context_popup)
        for variable in (self.query,self.kind,self.minimum_kib):
            variable.trace_add('write',lambda *_:self._apply_filters())
        self.refresh_language(language)

    def show_entries(self,entries):
        # Detached rows also belong to this view and must not survive a new scan.
        self.tree.delete(*self.entries)
        self.entries={str(entry.key):entry for entry in entries}
        for key,entry in self.entries.items():
            self.tree.insert('', 'end',iid=key,text=entry.name,
                values=(entry.name.split('_',1)[0],f'{entry.size:,}',f'{entry.locator[1]:,}'))
        self.reset_filters()
        self.browser.configure(state='normal' if self.entries else 'disabled')
        self._selection_changed()

    def clear(self):
        self.show_entries(())

    def sort(self,column,*,toggle=True):
        if toggle:self.reverse=not self.reverse if column==self.sort_column else False
        self.sort_column=column
        def value(key):
            e=self.entries[key]
            return {'#0':e.name.casefold(),'type':e.name.split('_',1)[0],'size':e.size,'offset':e.locator[1]}[column]
        for position,key in enumerate(sorted(self.tree.get_children(),key=value,reverse=self.reverse)):
            self.tree.move(key,'',position)

    def selected_entries(self):
        selected=set(self.tree.selection())
        return tuple(self.entries[key] for key in self.tree.get_children() if key in selected)

    def visible_entries(self):
        return tuple(self.entries[key] for key in self.tree.get_children())

    def _selection_changed(self):
        count=len(self.selected_entries())
        self.preview.configure(state='normal' if count else 'disabled')
        self.inspect.configure(state='normal' if count==1 else 'disabled')
        self.export.configure(state='normal' if count or self.export_running() else 'disabled')
        self.report.configure(state='normal' if self.tree.get_children() else 'disabled')
        text=translate('{visible} von {total} Funden sichtbar · {selected} ausgewählt',self.language).format(
            visible=len(self.tree.get_children()),total=len(self.entries),selected=count)
        if not self._minimum_valid:
            text+=' · '+translate('Mindestgröße: ganze Zahl von 0 bis 4294967296 KiB eingeben.',self.language)
        self.caption.configure(text=text)

    def _select_kind(self,event=None):
        position=self.kind_combo.current()
        if position>=0:
            self.kind.set('' if position==0 else self.kind_display.get())

    def _sync_kind_choices(self):
        choices=[translate('Alle Dateitypen',self.language)]+sorted({e.name.split('_',1)[0] for e in self.entries.values()})
        self.kind_combo.configure(values=choices)
        self.kind_display.set(self.kind.get() or choices[0])

    def refresh_language(self,language):
        self.language=language
        self._sync_kind_choices()
        self._selection_changed()

    def reset_filters(self):
        self._updating=True
        try:
            self.query.set('');self.kind.set('');self.minimum_kib.set('0')
            self._sync_kind_choices()
        finally:self._updating=False
        self._apply_filters()

    def _apply_filters(self):
        if self._updating:return
        raw=self.minimum_kib.get().strip()
        self._minimum_valid=(not raw or (raw.isascii() and raw.isdecimal() and len(raw)<=10 and int(raw)<=4294967296))
        minimum=int(raw or '0')*1024 if self._minimum_valid else 0
        query=self.query.get().strip().casefold();kind=self.kind.get()
        visible={key for key,e in self.entries.items() if self._minimum_valid and e.size>=minimum and
                 (not kind or e.name.split('_',1)[0]==kind) and query in e.name.casefold()}
        selected=set(self.tree.selection()) & visible
        self.tree.selection_set(tuple(selected))
        hidden=[key for key in self.tree.get_children() if key not in visible]
        if hidden:self.tree.detach(*hidden)
        for key in self.entries:
            if key in visible:self.tree.move(key,'','end')
        self.sort(self.sort_column,toggle=False)
        self._selection_changed()

    def select_all(self,event=None):
        self.tree.selection_set(self.tree.get_children())
        self._selection_changed()
        return 'break'

    def clear_selection(self,event=None):
        self.tree.selection_set(())
        self._selection_changed()
        return 'break'

    def _context_popup(self,event):
        key=self.tree.identify_row(event.y)
        if key not in self.tree.get_children():return 'break'
        if key not in self.tree.selection():self.tree.selection_set(key)
        self.tree.focus(key)
        self._selection_changed()
        if self._context_menu is not None:self._context_menu.destroy()
        popup=self._context_menu=tk.Menu(self.tree,tearoff=False)
        count=len(self.selected_entries())
        for text,action,state in (
                ('Vorschau','preview','normal'),
                ('Datei prüfen','inspect','normal' if count==1 else 'disabled'),
                ('Stapel-Export / fortsetzen','export','normal'),
                ('Fundliste speichern…','report','normal')):
            popup.add_command(label=translate(text,self.language),state=state,
                command=lambda action=action:self._action(action))
        try:popup.tk_popup(event.x_root,event.y_root)
        finally:
            popup.grab_release()
        return 'break'

    def _keyboard_context_popup(self,event=None):
        visible=self.tree.get_children()
        key=self.tree.focus()
        if key not in visible:
            chosen=self.selected_entries()
            key=str(chosen[0].key) if chosen else (visible[0] if visible else '')
        if not key:return 'break'
        self.tree.see(key)
        self.tree.update_idletasks()
        box=self.tree.bbox(key)
        if not box:return 'break'
        from types import SimpleNamespace
        x,y,width,height=box
        return self._context_popup(SimpleNamespace(y=y+height//2,
            x_root=self.tree.winfo_rootx()+x+min(width,20),
            y_root=self.tree.winfo_rooty()+y+height))
