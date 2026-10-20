"""Windows PSAPI measurements; peak working set includes mapped model pages."""
import ctypes
import os


def process_memory(pid=None):
    if os.name != "nt":return {"measurement": "Windows PSAPI unavailable"}
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
            "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x410, False, pid or os.getpid())
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = Counters()
        info.cb = ctypes.sizeof(info)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(info), info.cb):raise ctypes.WinError(ctypes.get_last_error())
        return {"working_set_bytes": info.WorkingSetSize, "peak_working_set_bytes": info.PeakWorkingSetSize,
                "private_commit_bytes": info.PagefileUsage}
    finally:kernel.CloseHandle(handle)
