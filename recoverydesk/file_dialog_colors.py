"""Color only Linux/X11's Tcl-owned file lists; keep the standard dialogs.

Tk creates their canvas with an explicit white background. Tkinter's widget
walk cannot see these Tcl-owned widgets. Selection redraws also reset text
colors, so repaint after those events and after directory/filter updates.
No polling, replacement dialog, Tcl procedure patch or file access is used.
"""
import sys
import tkinter as tk


class FileDialogColors:
    def __init__(self, app):
        self.app=app
        self.enabled=sys.platform.startswith('linux') and str(app.tk.call('tk','windowingsystem'))=='x11'
        self.dialogs=set();self.pending={};self.traced=False
        self.tag='TenshiFileListColors'+str(id(self))
        self.command=None
        if self.enabled:
            self.command=app.register(self._updated)
            for dialog_class in ('TkFDialog','TkChooseDir'):
                app.bind_class(dialog_class,'<Map>',lambda event:self.on_map(str(event.widget)),add='+')
            for event in ('<Button-1>','<B1-Motion>','<KeyPress>','<FocusIn>','<FocusOut>','<Configure>','<<ListboxSelect>>'):
                app.bind_class(self.tag,event,lambda event:self.on_map(str(event.widget)),add='+')

    def on_map(self,path):
        if not self.enabled:return
        try:
            dialog=str(self.app.tk.call('winfo','toplevel',path))
            if str(self.app.tk.call('winfo','class',dialog)) not in ('TkFDialog','TkChooseDir'):return
            self.dialogs.add(dialog)
            # Observe completion of Tk's standard refresh without modifying it.
            if not self.traced and self.app.tk.call('info','commands','::tk::dialog::file::Update'):
                self.app.tk.call('trace','add','execution','::tk::dialog::file::Update','leave',self.command)
                self.traced=True
            self._schedule(dialog)
        except tk.TclError:
            pass

    def _updated(self,command,code,result,operation):
        if str(code)!='0':return
        parts=self.app.tk.splitlist(command)
        if len(parts)>1:self.on_map(str(parts[1]))

    def refresh(self):
        for dialog in tuple(self.dialogs):
            if self.app.tk.call('winfo','exists',dialog):self.on_map(dialog)
            else:self.dialogs.discard(dialog)

    def _schedule(self,dialog):
        if dialog not in self.pending:
            self.pending[dialog]=self.app.after_idle(lambda:self._paint(dialog))

    def _paint(self,dialog):
        self.pending.pop(dialog,None)
        tcl=self.app.tk
        try:
            if not tcl.call('winfo','exists',dialog):
                self.dialogs.discard(dialog);return
            colors=self.app._palette()
            stack=[dialog]
            while stack:
                widget=stack.pop()
                stack.extend(tcl.splitlist(tcl.call('winfo','children',widget)))
                if str(tcl.call('winfo','class',widget))!='Canvas':continue
                tags=tcl.splitlist(tcl.call('bindtags',widget))
                if self.tag not in tags:tcl.call('bindtags',widget,(*tags,self.tag))
                icons=str(tcl.call('winfo','parent',widget))
                tags=tcl.splitlist(tcl.call('bindtags',icons))
                if self.tag not in tags:tcl.call('bindtags',icons,(*tags,self.tag))
                # Keep the traversal and canvas-item updates inside Tcl, rather
                # than making Python/Tcl round trips for every directory entry.
                tcl.call('apply',(('canvas','bg','fg','selectedBg','selectedFg'),'''
                    if {[$canvas cget -background] ne $bg} {
                        $canvas configure -background $bg
                    }
                    set selected [dict create]
                    foreach id [$canvas find withtag selectionText] {dict set selected $id 1}
                    foreach id [$canvas find all] {
                        if {[$canvas type $id] ne "text"} {continue}
                        set color [expr {[dict exists $selected $id] ? $selectedFg : $fg}]
                        if {[$canvas itemcget $id -fill] ne $color} {
                            $canvas itemconfigure $id -fill $color
                        }
                    }
                    $canvas itemconfigure selection -fill $selectedBg -outline $selectedBg
                '''),widget,colors['input'],colors['text'],colors['select'],colors['selection_text'])
        except tk.TclError:
            # A cancelled/destroyed dialog may disappear before this idle task.
            pass

    def close(self):
        if self.traced:
            try:self.app.tk.call('trace','remove','execution','::tk::dialog::file::Update','leave',self.command)
            except tk.TclError:pass
            self.traced=False
        for job in self.pending.values():
            try:self.app.after_cancel(job)
            except tk.TclError:pass
        self.pending.clear()
