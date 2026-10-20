"""A bounded current-runtime model-off survival regression; no inference or downloads."""
from pathlib import Path
import json
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import storage
from underworld.config import load
from underworld.resources import process_memory

config = load(ROOT / "config/survival.toml")
with tempfile.TemporaryDirectory(prefix="underworld-phase3-off-") as directory:
    path = Path(directory) / "baseline.sqlite"
    initial = storage.create(path, config)
    start = time.perf_counter()
    final = storage.advance(path, 1500)
    elapsed = time.perf_counter() - start
    alive = sum(e["body"]["alive"] for e in final["entities"] if e["kind"] == "actor")
    report = {"phase": 3, "provider": "disabled", "ticks": 1500, "population": 8, "alive": alive,
        "simulated_time_s": final["simulated_time_s"], "wall_time_s": elapsed,
        "simulated_s_per_wall_s": final["simulated_time_s"] / elapsed,
        "cognition_calls": final["cognition_calls"], "episodes": final["episodes"], "recorded_decisions": final["recorded_decisions"],
        "process_memory": process_memory(), "database_bytes": path.stat().st_size,
        "initial_material_totals_ug": initial["material_totals_ug"], "final_material_totals_ug": final["material_totals_ug"],
        "replay": storage.replay(path), "orchestration_id": storage.orchestration_id()}
    if alive != 8 or final["cognition_calls"] != 0:raise RuntimeError("model-off regression failed")
(ROOT / "artifacts/phase3_baseline.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
