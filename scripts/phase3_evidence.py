"""Real local-model trace. Never substitutes a mock for inference evidence."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import storage, memory
from underworld.config import load
from underworld.resources import process_memory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-pid", type=int, required=True)
    parser.add_argument("--db", type=Path, default=ROOT / "data/phase3-local.sqlite")
    args = parser.parse_args()
    config = load(ROOT / "config/local-model.toml")
    config["cognition"]["calls_per_simulated_day"] = 3
    initial = storage.create(args.db, config, scripted=False)
    before = storage.observe(args.db, ["agent-1"])[0]
    gather = {"schema_version": 1, "run_id": initial["run_id"], "request_id": "authored-food-setup",
        "agent_id": "agent-1", "observation_version": "0", "action_type": "gather",
        "target_ids": ["resource-1"], "parameters": {"mass_kg": .4}, "requested_duration": 1}
    storage.advance(args.db, 5, [(0, gather)])
    thoughts = []
    started = time.perf_counter()
    for _ in range(3):
        thoughts.append(storage.think(args.db, "agent-1"))
        storage.advance(args.db, 25)  # Let even a five-second rest finish before another thought.
    elapsed = time.perf_counter() - started
    quota = storage.think(args.db, "agent-2")
    after = storage.inspect(args.db)
    observation = storage.observe(args.db, ["agent-1"])[0]
    with closing(sqlite3.connect(args.db)) as db:
        calls = [json.loads(r[0]) for r in db.execute("SELECT payload FROM cognition_calls ORDER BY id")]
        for call in calls:
            call.pop("context", None)
            call.get("details", {}).pop("prompt", None)
        retrieval = memory.retrieve(db, "agent-1", "ingested", 3)
        events = [json.loads(r[0]) for r in db.execute("SELECT payload FROM events WHERE json_extract(payload,'$.agent_id')='agent-1' ORDER BY seq")]
        decisions = [{"request": json.loads(r[0]), "result": json.loads(r[1]), "source": r[2]}
                     for r in db.execute("SELECT request,result,source FROM decisions ORDER BY id")]
        day_counts = list(db.execute("SELECT day,COUNT(*) FROM cognition_calls GROUP BY day"))
    meal = [r for r in observation["recent_action_results"] if r["observable_effects"]["description"] == "ingested_ug=200000000"]
    if not meal or not any(c["status"] == "planned" for c in calls):
        raise RuntimeError("real model did not produce the required physical meal; retained DB has failure evidence")
    backup = args.db.with_name(args.db.stem + "-resume.sqlite")
    view = storage.mind(args.db, "agent-1", "ingested")
    storage.save(args.db, "real-model-memory", backup)
    storage.recover(backup)
    preserved = view == storage.mind(backup, "agent-1", "ingested")
    if not preserved:raise RuntimeError("identity/memory restart mismatch")
    command = [sys.executable, "-m", "underworld", "mind", "--db", str(backup), "--agent", "agent-1", "--query", "ingested"]
    restarted = json.loads(subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True, timeout=15).stdout)
    if restarted != view:raise RuntimeError("separate-process identity/memory restart mismatch")
    report = {"phase": 3, "type": "real CPU local-model run", "model": "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF Q8_0",
        "config": config, "build_id": initial["build_id"], "orchestration_id": storage.orchestration_id(),
        "setup": "Authored .4 kg food gathering; all later cognition requests came from the real model or explicitly logged fallback.",
        "initial_observation": before, "final_observation": observation, "thoughts": thoughts, "calls": calls,
        "decisions": decisions, "events": events, "later_lexical_retrieval": retrieval,
        "server_memory": process_memory(args.server_pid), "parent_memory": process_memory(),
        "dedicated_vram_bytes": 0, "gpu_layers": 0, "context_size_tokens": 2048,
        "wall_time_s": elapsed, "simulated_time_s": after["simulated_time_s"],
        "day_bucket_call_counts": day_counts, "daily_shared_quota": 3, "next_call": quota,
        "daily_measurement_limit": "Partial simulated day, not a 24-hour throughput benchmark; no extrapolated daily rate.",
        "restart_identity_memory_equal": preserved, "separate_process_identity_memory_equal": restarted == view,
        "replay": storage.replay(backup),
        "initial_material_totals_ug": initial["material_totals_ug"], "final_material_totals_ug": after["material_totals_ug"],
        "database_bytes": args.db.stat().st_size, "prompts": "private cognition_calls rows in ignored data DB; excluded from this public artifact"}
    path = ROOT / "artifacts/phase3_local_model.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(path), "thoughts": thoughts, "ingested_food_ug": observation["own_state"]["body"]["food_ingested_ug"],
                      "server_memory": report["server_memory"], "restart_equal": preserved, "replay": report["replay"]}, indent=2))


if __name__ == "__main__":main()
