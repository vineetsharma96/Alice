"""Model-off mechanics benchmark, with isolated worker processes for peak RSS."""
import argparse
import ctypes
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld.config import load
from underworld.native import load_native
from underworld import storage


def peak_rss():
    if sys.platform == "win32":
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        info = Counters()
        info.cb = ctypes.sizeof(info)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(info), info.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return info.PeakWorkingSetSize
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == "darwin" else value*1024


parser = argparse.ArgumentParser()
parser.add_argument("--ticks", type=int, default=10000)
parser.add_argument("--config", type=Path, default=ROOT / "config/baseline.toml")
parser.add_argument("--output", type=Path, default=ROOT / "artifacts/phase1_benchmark.json")
parser.add_argument("--worker", choices=["native", "durable"], help=argparse.SUPPRESS)
args = parser.parse_args()
if not 1 <= args.ticks <= 100000:
    parser.error("ticks must be in [1,100000]")
config = load(args.config)
if args.worker:
    native = load_native()
    w = config["world"]
    extra = {}
    if args.worker == "native":
        world = native.World(config["seed"],w["population"],w["width_m"],w["height_m"],w["dt_s"],
                             config["cognition"]["interval_ticks"])
        start = time.perf_counter()
        left = args.ticks
        while left:
            chunk = min(left,10000)
            world.step(chunk)
            left -= chunk
        elapsed = time.perf_counter()-start
        world.check_invariants()
        snapshot = world.snapshot()
        state_hash = storage.digest(world.checkpoint())
    else:
        with tempfile.TemporaryDirectory(prefix="underworld-benchmark-") as directory:
            path = Path(directory) / "run.sqlite"
            storage.create(path, config)
            start = time.perf_counter()
            snapshot = storage.advance(path,args.ticks)
            elapsed = time.perf_counter()-start
            state_hash = snapshot["state_hash"]
            extra["database_bytes"] = path.stat().st_size
            extra["retained_events"] = snapshot["retained_events"]
            extra["external_decisions"] = snapshot["recorded_decisions"]
            extra["replay"] = storage.replay(path)
    seconds = args.ticks*w["dt_s"]
    print(json.dumps({"mode":args.worker,"ticks":args.ticks,"population":w["population"],
        "wall_time_s":elapsed,"simulated_time_s":seconds,"ticks_per_wall_s":args.ticks/elapsed,
        "simulated_s_per_wall_s":seconds/elapsed,"peak_process_rss_bytes":peak_rss(),
        "state_hash":state_hash,"solar_input_j":snapshot["solar_input_j"],
        "material_totals_ug":snapshot["material_totals_ug"],**extra}))
else:
    report = {"phase":1,"python":sys.version,"platform":platform.platform(),
              "build_id":load_native().build_id,"config":config,"measurements":[]}
    for mode in ("native","durable"):
        print(f"Measuring {mode}: {args.ticks} ticks", file=sys.stderr, flush=True)
        command = [sys.executable,str(Path(__file__).resolve()),"--ticks",str(args.ticks),
                   "--config",str(args.config),"--worker",mode]
        result = subprocess.run(command,check=True,capture_output=True,text=True,timeout=1800)
        report["measurements"].append(json.loads(result.stdout))
        report["measurements"][-1]["command"] = command
    report["native_and_durable_hash_match"] = len({v["state_hash"] for v in report["measurements"]}) == 1
    if not report["native_and_durable_hash_match"]:
        raise RuntimeError("native/durable benchmark states diverged")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
