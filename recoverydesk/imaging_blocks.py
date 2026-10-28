"""Bounded, integer-exact projection of committed source ranges; no I/O."""
from dataclasses import dataclass, field


@dataclass
class ImagingBlocks:
    total: int = 0
    processed: int = 0
    unreadable: int = 0
    ranges: int = 0
    bad: list[int] = field(default_factory=lambda:[0]*100)
    mapped_bad: int = 0

    def handle(self, item):
        self.total=max(0,int(item.total))
        self.processed=max(self.processed,min(self.total,max(0,int(item.processed))))
        self.unreadable=max(0,int(item.unreadable_bytes))
        self.ranges=max(0,int(item.bad_range_count))
        if not self.total:return
        for offset,length in item.bad_ranges:
            start=max(0,int(offset))*100
            end=min(self.processed,int(offset)+max(0,int(length)))*100
            if end<=start:continue
            self.mapped_bad+=(end-start)//100
            for cell in range(max(0,start//self.total),min(100,(end-1)//self.total+1)):
                self.bad[cell]+=max(0,min(end,(cell+1)*self.total)-max(start,cell*self.total))

    def cell_states(self):
        if not self.total:return ('pending',)*100
        states=[]
        for cell in range(100):
            copied=max(0,min(self.processed*100,(cell+1)*self.total)-cell*self.total)
            if self.bad[cell]:state='error'
            elif not copied:state='pending'
            elif self.mapped_bad!=self.unreadable:state='unconfirmed'
            elif copied<self.total:state='mixed'
            else:state='confirmed'
            states.append(state)
        return tuple(states)
