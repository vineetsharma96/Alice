"""Windows AppContainer with no capabilities; optional inherited IPC, never a network exemption."""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from contextlib import contextmanager
from .lease import Lease


@contextmanager
def setup_lock(root):
    directory=Path(root)/'.tools';directory.mkdir(exist_ok=True)
    deadline=time.monotonic()+30;lease=Lease(directory/'isolation-setup')
    while True:
        try:lease.__enter__();break
        except ValueError:
            if time.monotonic()>=deadline:raise ValueError('isolated runtime setup lock deadline')
            time.sleep(.05)
    try:yield
    finally:lease.__exit__(None,None,None)


def token_status():
    if os.name!="nt":return {"appcontainer":False,"supported":False}
    from ctypes import wintypes as W
    kernel=C.WinDLL("kernel32",use_last_error=True);adv=C.WinDLL("advapi32",use_last_error=True)
    kernel.GetCurrentProcess.restype=W.HANDLE
    adv.OpenProcessToken.argtypes=[W.HANDLE,W.DWORD,C.POINTER(W.HANDLE)]
    adv.GetTokenInformation.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.POINTER(W.DWORD)]
    kernel.CloseHandle.argtypes=[W.HANDLE]
    handle=W.HANDLE();value=W.DWORD();size=W.DWORD()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(),8,C.byref(handle)):raise C.WinError(C.get_last_error())
    try:
        if not adv.GetTokenInformation(handle,29,C.byref(value),C.sizeof(value),C.byref(size)):raise C.WinError(C.get_last_error())
        return {"supported":True,"appcontainer":bool(value.value),"network_capabilities_requested":0}
    finally:kernel.CloseHandle(handle)


class AppContainer:
    def __init__(self,workspace,writable):
        if os.name!="nt":raise RuntimeError("This host implementation requires Windows AppContainer")
        self.root=Path(workspace).resolve();self.writable=Path(writable).resolve()
        if not self.writable.is_relative_to(self.root):raise ValueError("isolated output must stay inside workspace")
        self.name="underworld7-"+uuid.uuid4().hex;self.grants=[];self.process=None;self.job=None

    def __enter__(self):
        with setup_lock(self.root):return self._prepare()

    def _prepare(self):
        from ctypes import wintypes as W
        self.kernel=C.WinDLL("kernel32",use_last_error=True);self.adv=C.WinDLL("advapi32",use_last_error=True);self.user=C.WinDLL("userenv",use_last_error=True)
        self.user.CreateAppContainerProfile.argtypes=[W.LPCWSTR,W.LPCWSTR,W.LPCWSTR,C.c_void_p,W.DWORD,C.POINTER(C.c_void_p)]
        self.user.CreateAppContainerProfile.restype=C.c_long
        self.user.DeleteAppContainerProfile.argtypes=[W.LPCWSTR];self.user.DeleteAppContainerProfile.restype=C.c_long
        self.adv.ConvertSidToStringSidW.argtypes=[C.c_void_p,C.POINTER(W.LPWSTR)]
        self.adv.FreeSid.argtypes=[C.c_void_p];self.adv.FreeSid.restype=C.c_void_p
        self.kernel.LocalFree.argtypes=[C.c_void_p]
        self.kernel.CloseHandle.argtypes=[W.HANDLE]
        self.sid=C.c_void_p()
        hr=self.user.CreateAppContainerProfile(self.name,self.name,"Underworld bounded network-isolated worker",None,0,C.byref(self.sid))
        if hr<0:raise OSError(f"CreateAppContainerProfile HRESULT 0x{hr&0xffffffff:08x}")
        value=W.LPWSTR()
        if not self.adv.ConvertSidToStringSidW(self.sid,C.byref(value)):raise C.WinError(C.get_last_error())
        self.sid_text=value.value;self.kernel.LocalFree(value)
        try:
            self.writable.mkdir(parents=True,exist_ok=True)
            (self.writable/"temp").mkdir(exist_ok=True)
            self.launcher=self.root/".tools/isolated-python";self.launcher.mkdir(parents=True,exist_ok=True)
            base=Path(sys.base_prefix);version=f"python{sys.version_info.major}{sys.version_info.minor}"
            # A Store venv launcher cannot start its packaged parent inside an AppContainer.
            # Copy the already installed CPython runtime; no installation/download or dependency change.
            if not (self.launcher/"runtime-ready").exists():
                shutil.copy2(base/"python.exe",self.launcher/"python.exe")
                for dll in base.glob("*.dll"):shutil.copy2(dll,self.launcher/dll.name)
                shutil.copytree(base/"DLLs",self.launcher/"DLLs",dirs_exist_ok=True)
                with zipfile.ZipFile(self.launcher/(version+".zip"),"w",compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
                    for source in (base/"Lib").rglob("*.py"):
                        relative=source.relative_to(base/"Lib")
                        if not any(p in {"site-packages","test","tests","ensurepip","idlelib","turtledemo"} for p in relative.parts):archive.write(source,relative.as_posix())
                for license_file in base.glob("LICENSE*"):shutil.copy2(license_file,self.launcher/license_file.name)
                (self.launcher/"runtime-ready").write_text(sys.version)
            search_path=self.launcher/(version+"._pth");content=f"{version}.zip\nDLLs\n{self.root}\nimport site\n"
            if not search_path.exists() or search_path.read_text()!=content:search_path.write_text(content)
            for name in ("libstdc++-6.dll","libgcc_s_seh-1.dll","libwinpthread-1.dll"):
                source=Path(os.environ.get("UNDERWORLD_TOOLCHAIN",r"C:\mingw64\bin"))/name
                target=self.launcher/name
                if source.is_file():
                    if not target.exists():shutil.copy2(source,target)
                    elif hashlib.sha256(source.read_bytes()).digest()!=hashlib.sha256(target.read_bytes()).digest():raise ValueError("isolated runtime DLL differs from selected toolchain; use a fresh runtime directory")
            for path,rights in ((self.root,"RX"),(self.root/"underworld","(OI)(CI)(RX)"),(self.root/"build","(OI)(CI)(RX)"),(self.root/"config","(OI)(CI)(RX)"),(self.launcher,"(OI)(CI)(RX)"),(self.writable,"(OI)(CI)(M)")):
                self._acl(path,"/grant",f"*{self.sid_text}:{rights}");self.grants.append(path)
            self.manifest=self.writable/"isolation-profile.json"
            self.manifest.write_text(json.dumps({"profile":self.name,"sid":self.sid_text,"grants":[str(p) for p in self.grants],"cleaned":False},indent=2))
            return self
        except BaseException:
            self.__exit__(None,None,None);raise

    def _acl(self,path,operation,principal):
        result=subprocess.run(["icacls",str(path),operation,principal,"/Q"],capture_output=True,text=True,timeout=30)
        if result.returncode:raise RuntimeError(f"Scoped AppContainer ACL failed for {path}: {result.stderr.strip()}")

    def launch(self,args,stdout,stderr,handles=(),memory_mb=512):
        from ctypes import wintypes as W
        import msvcrt
        class SI(C.Structure):
            _fields_=[("cb",W.DWORD),("reserved",W.LPWSTR),("desktop",W.LPWSTR),("title",W.LPWSTR),
                *[(n,W.DWORD) for n in ("x","y","xsize","ysize","xchars","ychars","fill","flags")],
                ("show",W.WORD),("reserved2size",W.WORD),("reserved2",C.c_void_p),("stdin",W.HANDLE),("stdout",W.HANDLE),("stderr",W.HANDLE)]
        class SIX(C.Structure):_fields_=[("info",SI),("attributes",C.c_void_p)]
        class PI(C.Structure):_fields_=[("process",W.HANDLE),("thread",W.HANDLE),("pid",W.DWORD),("tid",W.DWORD)]
        class Caps(C.Structure):_fields_=[("sid",C.c_void_p),("capabilities",C.c_void_p),("count",W.DWORD),("reserved",W.DWORD)]
        class Basic(C.Structure):
            _fields_=[("process_time",C.c_int64),("job_time",C.c_int64),("flags",W.DWORD),("min_ws",C.c_size_t),("max_ws",C.c_size_t),("active",W.DWORD),("affinity",C.c_size_t),("priority",W.DWORD),("scheduling",W.DWORD)]
        class IO(C.Structure):_fields_=[(n,C.c_uint64) for n in ("read_ops","write_ops","other_ops","read_bytes","write_bytes","other_bytes")]
        class Limits(C.Structure):_fields_=[("basic",Basic),("io",IO),("process_memory",C.c_size_t),("job_memory",C.c_size_t),("peak_process",C.c_size_t),("peak_job",C.c_size_t)]
        k=self.kernel
        k.InitializeProcThreadAttributeList.argtypes=[C.c_void_p,W.DWORD,W.DWORD,C.POINTER(C.c_size_t)]
        k.UpdateProcThreadAttribute.argtypes=[C.c_void_p,W.DWORD,C.c_size_t,C.c_void_p,C.c_size_t,C.c_void_p,C.c_void_p]
        k.DeleteProcThreadAttributeList.argtypes=[C.c_void_p]
        k.CreateProcessW.argtypes=[W.LPCWSTR,W.LPWSTR,C.c_void_p,C.c_void_p,W.BOOL,W.DWORD,C.c_void_p,W.LPCWSTR,C.POINTER(SIX),C.POINTER(PI)]
        k.CreateJobObjectW.argtypes=[C.c_void_p,W.LPCWSTR];k.CreateJobObjectW.restype=W.HANDLE
        k.SetInformationJobObject.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD]
        k.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE];k.ResumeThread.argtypes=[W.HANDLE]
        k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.GetExitCodeProcess.argtypes=[W.HANDLE,C.POINTER(W.DWORD)]
        k.TerminateJobObject.argtypes=[W.HANDLE,W.UINT]
        k.TerminateProcess.argtypes=[W.HANDLE,W.UINT]
        self.files=[open(stdout,"wb"),open(stderr,"wb"),open(os.devnull,"rb")]
        std=[msvcrt.get_osfhandle(f.fileno()) for f in self.files]
        inherited=std+list(handles)
        for h in inherited:os.set_handle_inheritable(h,True)
        length=C.c_size_t();k.InitializeProcThreadAttributeList(None,2,0,C.byref(length));buffer=C.create_string_buffer(length.value)
        if not k.InitializeProcThreadAttributeList(buffer,2,0,C.byref(length)):raise C.WinError(C.get_last_error())
        caps=Caps(self.sid,None,0,0);handle_array=(W.HANDLE*len(inherited))(*inherited)
        try:
            if not k.UpdateProcThreadAttribute(buffer,0,0x20009,C.byref(caps),C.sizeof(caps),None,None):raise C.WinError(C.get_last_error())
            if not k.UpdateProcThreadAttribute(buffer,0,0x20002,handle_array,C.sizeof(handle_array),None,None):raise C.WinError(C.get_last_error())
            start=SIX();start.info.cb=C.sizeof(start);start.info.flags=0x100;start.info.stdin=std[2];start.info.stdout=std[0];start.info.stderr=std[1];start.attributes=C.cast(buffer,C.c_void_p)
            env=os.environ|{"PYTHONPATH":str(self.root),"PYTHONDONTWRITEBYTECODE":"1","UNDERWORLD_TOOLCHAIN":str(self.launcher),"UNDERWORLD_CONTAINER":self.name,"TEMP":str(self.writable/"temp"),"TMP":str(self.writable/"temp")}
            env_buffer=C.create_unicode_buffer("\0".join(f"{key}={value}" for key,value in sorted(env.items()))+"\0\0")
            command=C.create_unicode_buffer(subprocess.list2cmdline([str(self.launcher/"python.exe"),*map(str,args)]));info=PI()
            if not k.CreateProcessW(None,command,None,None,True,0x80000|0x8000000|0x400|0x4,env_buffer,str(self.root),C.byref(start),C.byref(info)):raise C.WinError(C.get_last_error())
            self.process=info.process;self.pid=info.pid
            try:
                self.job=k.CreateJobObjectW(None,None)
                if not self.job:raise C.WinError(C.get_last_error())
                limits=Limits();limits.basic.flags=0x2000|0x200;limits.job_memory=memory_mb*1024*1024
                if not k.SetInformationJobObject(self.job,9,C.byref(limits),C.sizeof(limits)) or not k.AssignProcessToJobObject(self.job,self.process):raise C.WinError(C.get_last_error())
                if k.ResumeThread(info.thread)==0xffffffff:raise C.WinError(C.get_last_error())
            except BaseException:k.TerminateProcess(self.process,137);raise
            finally:k.CloseHandle(info.thread)
            return self.pid
        finally:
            k.DeleteProcThreadAttributeList(buffer)
            for h in inherited:os.set_handle_inheritable(h,False)

    def poll(self):
        from ctypes import wintypes as W
        if self.kernel.WaitForSingleObject(self.process,0)==0x102:return None
        result=W.DWORD();self.kernel.GetExitCodeProcess(self.process,C.byref(result));return result.value

    def kill(self,code=137):
        if self.job:self.kernel.TerminateJobObject(self.job,code)

    def __exit__(self,*_):
        with setup_lock(self.root):self._cleanup()

    def _cleanup(self):
        if self.job:self.kernel.CloseHandle(self.job)
        if self.process and hasattr(self.kernel,"WaitForSingleObject"):self.kernel.WaitForSingleObject(self.process,3000)
        if self.process:self.kernel.CloseHandle(self.process)
        for f in getattr(self,"files",[]):f.close()
        errors=[]
        for path in reversed(self.grants):
            try:self._acl(path,"/remove:g",f"*{self.sid_text}")
            except Exception as error:errors.append(str(error))
        hr=self.user.DeleteAppContainerProfile(self.name)
        if self.sid:self.adv.FreeSid(self.sid)
        if hasattr(self,"manifest"):
            self.manifest.write_text(json.dumps({"profile":self.name,"sid":self.sid_text,"grants":[str(p) for p in self.grants],"network_capabilities":[],"job_memory_limit_bytes":512*1024*1024,"cleaned":not errors and hr>=0,"cleanup_errors":errors},indent=2))


def network_probe():
    import socket
    results=[]
    for host in ("1.1.1.1","10.255.255.1","127.0.0.1"):
        with socket.socket() as sock:
            sock.settimeout(.5)
            try:code=sock.connect_ex((host,443))
            except OSError as error:code=error.winerror or error.errno
        results.append({"host":host,"code":code,"access_denied":code in (10013,13)})
    return {"token":token_status(),"connections":results}
