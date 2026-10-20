"""Retain stabilization validation output; preserve earlier-phase evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
parser = argparse.ArgumentParser()
parser.add_argument("--core", required=True, type=Path)
parser.add_argument("--ctest", default="ctest")
parser.add_argument("--timeout", type=int, default=240, help="wall seconds allowed per check subprocess")
args = parser.parse_args()
core = args.core.resolve()
env = os.environ | {"UNDERWORLD_CORE": str(core)}
build = core.parent if (core.parent / "CMakeCache.txt").exists() else core.parent.parent
env["UNDERWORLD_BUILD"] = str(build)
os.environ["UNDERWORLD_BUILD"] = str(build)
if os.name == "nt":
    toolchain = env.get("UNDERWORLD_TOOLCHAIN", r"C:\mingw64\bin")
    if Path(toolchain).is_dir():
        env["PATH"] = toolchain + os.pathsep + env["PATH"]
commands = [[args.ctest, "--test-dir", str(build), "-C", "Release", "--output-on-failure"],
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            [sys.executable, "-m", "underworld", "inspect", "--core", str(core)]]
report = {"milestone": "stabilization", "python": sys.version, "os": platform.platform(),
          "sqlite": sqlite3.sqlite_version, "checks": []}
from underworld import storage
report.update(native_build_id=storage.load_native().build_id,orchestration_id=storage.orchestration_id(),
    original_spec_sha256=hashlib.sha256((ROOT/'docs/PROJECT_SPEC.md').read_bytes()).hexdigest())
from phase8_manifest import build as viewer_manifest
report['viewer_source_build_id']=viewer_manifest()['source_build_id']
(ROOT / "artifacts").mkdir(exist_ok=True)
for command in commands:
    start = time.perf_counter()
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=args.timeout)
    except subprocess.TimeoutExpired as error:
        def decoded(value):
            return value.decode(errors='replace') if isinstance(value, bytes) else (value or '')
        result = subprocess.CompletedProcess(command,124,decoded(error.stdout),decoded(error.stderr)+f'\nTimeout after {args.timeout} seconds\n')
    check = {"command": command, "returncode": result.returncode,
             "wall_time_s": time.perf_counter() - start, "stdout": result.stdout, "stderr": result.stderr}
    report["checks"].append(check)
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        break
if len(report["checks"]) == len(commands) and report["checks"][-1]["returncode"] == 0:
    scene = json.loads(report["checks"][2]["stdout"])
    report["initial_scene_sha256"] = hashlib.sha256(
        json.dumps(scene, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    report["config_sha256"] = hashlib.sha256((ROOT / "config/baseline.toml").read_bytes()).hexdigest()
(ROOT / "artifacts/stabilization_checks.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
sys.exit(0 if len(report["checks"]) == len(commands) and all(c["returncode"] == 0 for c in report["checks"]) else 1)

