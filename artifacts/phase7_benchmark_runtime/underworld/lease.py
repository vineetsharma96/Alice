"""OS-released, process-safe writer leases. Read-only connections never acquire a lease."""
import os
from pathlib import Path
import threading

_local=threading.local()


class Lease:
    def __init__(self,path):self.path=str(Path(path).resolve());self.file=None
    def __enter__(self):
        owned=getattr(_local,"owned",None)
        if owned is None:_local.owned={};owned=_local.owned
        if self.path in owned:owned[self.path]+=1;return self
        self.file=open(self.path+".lease","a+b")
        self.file.seek(0,2)
        if self.file.tell()==0:self.file.write(b"0");self.file.flush()
        self.file.seek(0)
        try:
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close();self.file=None
            raise ValueError("another writer owns the run lease") from None
        owned[self.path]=1;return self
    def __exit__(self,*_):
        _local.owned[self.path]-=1
        if _local.owned[self.path]:return
        del _local.owned[self.path]
        if self.file:
            self.file.seek(0)
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
            self.file.close();self.file=None
