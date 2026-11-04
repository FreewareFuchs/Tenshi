"""Metadata-only signature result view; actions reuse the application's readers."""
from tkinter import ttk


class SignatureResults(ttk.Frame):
    def __init__(self,parent,*,action,open_browser,export_running=lambda:False):
        super().__init__(parent,padding=(12,0,12,8))
        self.entries={}
        self.export_running=export_running
        self.sort_column='offset';self.reverse=False
        buttons=ttk.Frame(self);buttons.pack(side='bottom',fill='x',pady=(8,0))
        buttons.columnconfigure((0,1),weight=1,uniform='actions')
        self.preview=ttk.Button(buttons,text='Vorschau',state='disabled',command=lambda:action('preview'))
        self.preview.grid(row=0,column=0,sticky='ew',padx=(0,3),pady=(0,4))
        self.inspect=ttk.Button(buttons,text='Datei prüfen',state='disabled',command=lambda:action('inspect'))
        self.inspect.grid(row=0,column=1,sticky='ew',padx=(3,0),pady=(0,4))
        self.export=ttk.Button(buttons,text='Stapel-Export / fortsetzen',style='Accent.TButton',
            state='disabled',command=lambda:action('export'))
        self.export.grid(row=1,column=0,sticky='ew',padx=(0,3))
        self.browser=ttk.Button(buttons,text='In Dateiansicht anzeigen',state='disabled',command=open_browser)
        self.browser.grid(row=1,column=1,sticky='ew',padx=(3,0))
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

    def show_entries(self,entries):
        self.tree.delete(*self.tree.get_children())
        self.entries={str(entry.key):entry for entry in entries}
        for key,entry in self.entries.items():
            self.tree.insert('', 'end',iid=key,text=entry.name,
                values=(entry.name.split('_',1)[0],f'{entry.size:,}',f'{entry.locator[1]:,}'))
        self.sort(self.sort_column,toggle=False)
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
        for position,key in enumerate(sorted(self.entries,key=value,reverse=self.reverse)):
            self.tree.move(key,'',position)

    def selected_entries(self):
        selected=set(self.tree.selection())
        return tuple(self.entries[key] for key in self.tree.get_children() if key in selected)

    def _selection_changed(self):
        count=len(self.tree.selection())
        self.preview.configure(state='normal' if count else 'disabled')
        self.inspect.configure(state='normal' if count==1 else 'disabled')
        self.export.configure(state='normal' if count or self.export_running() else 'disabled')

    def select_all(self,event=None):
        self.tree.selection_set(self.tree.get_children())
        self._selection_changed()
        return 'break'
