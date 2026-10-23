"""Run a bounded survival check with the F6--F12 overlays attached.

The native/stabilization controller remains the only action executor. The
relationship, public-understanding, regulation, communication, social-emotion,
identity and value layers are attached as copy-only sidecars and record actual
observations/results around the run. This measures survival with all requested
sidecars present; it does not claim that proposal-only F8--F11 choices drive the
native scheduler.
"""

from contextlib import closing, nullcontext
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import uuid
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from underworld import integration_f12 as f12
from underworld import others_store_f7 as f7
from underworld import relationship_store_f6 as f6
from underworld import stabilization
from underworld import storage
from underworld.config import load


F8_ACTIONS = {
    "rest": "rest",
    "move": "move_to_safety",
    "request_help": "request_help",
    "reconsider": "reconsider",
    "switch_plan": "switch_plan",
}


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _copy_world(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("survival control destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as origin:
        with closing(sqlite3.connect(destination)) as target:
            origin.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("survival control backup integrity check failed")


def _actors(snapshot):
    return sorted(entity["entity_id"] for entity in snapshot["entities"]
                  if entity.get("kind") == "actor")


def _terminal_receipts(observation, after_tick):
    receipts = []
    for receipt in observation.get("recent_action_results", []):
        if receipt.get("status") not in {"completed", "failed", "rejected"}:
            continue
        completed_tick = receipt.get("completed_tick", after_tick)
        try:
            completed_tick = int(completed_tick)
        except (TypeError, ValueError):
            completed_tick = after_tick
        if completed_tick > after_tick:
            continue
        receipts.append((completed_tick, str(receipt.get("request_id", "")), receipt))
    return [item[2] for item in sorted(receipts)]


def _stabilization_receipts(path, owner, after_tick):
    """Read only controller-recorded terminal receipts from native work."""
    receipts = []
    with closing(storage._connect(path, readonly=True)) as db:
        for payload, in db.execute("SELECT payload FROM stabilization_events ORDER BY id"):
            event = json.loads(payload)
            if event.get("agent") != owner or int(event.get("tick", 0)) <= after_tick:
                continue
            if event.get("kind") != "terminal_receipt":
                continue
            data = event.get("data", {})
            receipt = data.get("receipt")
            if isinstance(receipt, dict) and receipt.get("status") in {"completed", "failed", "rejected"}:
                receipt = dict(receipt)
                request = data.get("request", {})
                receipt.setdefault("action_type", request.get("action_type"))
                receipts.append(receipt)
    return receipts


def _decision_cost(path, request_id):
    with closing(storage._connect(path, readonly=True)) as db:
        row = next((json.loads(text) for text, in db.execute("SELECT request FROM decisions")
                    if json.loads(text).get("request_id") == request_id), None)
    return float(row.get("requested_duration", 0.0)) if row else 0.0


def _native_metrics(path):
    native = storage.inspect(path)
    actors = [entity for entity in native["entities"] if entity.get("kind") == "actor"]
    alive = [entity for entity in actors if entity.get("alive") and entity.get("present", True)]
    body = [entity.get("body", {}) for entity in actors]
    def mean(key):
        values = [float(item.get(key, 0.0)) for item in body]
        return sum(values) / len(values) if values else 0.0
    return {
        "tick": int(native["tick"]),
        "simulated_time_s": float(native["simulated_time_s"]),
        "alive": len(alive),
        "population": len(actors),
        "health_min": min((float(item.get("health", 0.0)) for item in body), default=0.0),
        "hunger_mean": mean("hunger"),
        "thirst_mean": mean("thirst"),
        "fatigue_mean": mean("fatigue"),
        "material_totals_ug": native["material_totals_ug"],
        "state_hash": native["state_hash"],
        "replay": storage.replay(path),
    }


def _controller_metrics(path, actors):
    states = {agent: stabilization.status(path, agent) for agent in actors}
    return {
        "goals_completed": sum(item["goals_completed"] for item in states.values()),
        "goals_blocked": sum(item["goals_blocked"] for item in states.values()),
        "submitted": sum(item["submitted"] for item in states.values()),
        "authored_steps": sum(item["authored_steps"] for item in states.values()),
        "fallback_goals": sum(item["fallback_goals"] for item in states.values()),
        "per_actor": states,
    }


def _record_overlay_telemetry(path, actors, before_observations, before_tick):
    telemetry = {"f8_outcomes": 0, "f6_observations": 0, "f7_observations": 0,
                 "f10_events": 0, "f11_events": 0, "f11_summaries": 0}
    for owner in actors:
        after = f12.observe_current(path, owner)["observation"]
        receipts = _stabilization_receipts(path, owner, before_tick)
        for receipt in receipts:
            strategy = F8_ACTIONS.get(receipt.get("action_type"))
            if strategy is not None:
                learned=f12.record_native_outcome(path,owner,receipt['request_id'],
                                    operation_id=f"survival-f8-{owner}-{receipt['request_id']}")
                telemetry["f8_outcomes"] += not learned['idempotent']

            value_event = {
                "evidence_id": f"survival-value-{owner}-{receipt['request_id']}",
                "kind": "native_outcome", "owner": owner,
                "run_id": after["run_id"], "provenance": "native",
                "status": "succeeded" if receipt["status"] == "completed" else "failed",
                "value": "survival", "outcome": receipt["action_type"],
                "context": ["survival"], "source": f"native:{receipt['request_id']}",
            }
            learned=f12.revise_identity(path, owner, value_event,
                                operation_id=f"survival-f11-{owner}-{receipt['request_id']}")
            telemetry["f11_events"] += not learned['idempotent']

            if receipt["status"] == "completed":
                achievement = {
                    "evidence_id": f"survival-achievement-{owner}-{receipt['request_id']}",
                    "kind": "own_observation", "owner": owner,
                    "run_id": after["run_id"], "provenance": "learned",
                    "predicate": "completed_achievement", "subject": receipt["request_id"],
                    "value": True, "other": None,
                }
                standard = {
                    "evidence_id": f"survival-standard-{owner}-{receipt['request_id']}",
                    "kind": "own_observation", "owner": owner,
                    "run_id": after["run_id"], "provenance": "seeded",
                    "predicate": "represented_standard", "subject": receipt["request_id"],
                    "value": True, "other": None,
                }
                for event, suffix in ((achievement, "achievement"), (standard, "standard")):
                    f12.observe_social(path, owner, event,
                                       operation_id=f"survival-f10-{owner}-{receipt['request_id']}-{suffix}")
                    telemetry["f10_events"] += 1

                summary = {"summary": {"text": "persisted survival practice",
                                        "claims": ["survival"], "contexts": ["survival"]},
                           "evidence_id": value_event["evidence_id"]}
                f12.revise_identity(path, owner, summary,
                                    operation_id=f"survival-f11-summary-{owner}-{receipt['request_id']}")
                telemetry["f11_summaries"] += 1

        f6.record_observation(path, owner)
        telemetry["f6_observations"] += 1
        for entity in after.get("visible_entities", []):
            if entity.get("kind") == "actor" and entity.get("entity_id") != owner:
                f7.record_current_observation(path, owner, entity["entity_id"])
                telemetry["f7_observations"] += 1
                break
    return telemetry


def _communication_handshake(path, actors):
    if len(actors) < 2:
        return {"performed": False}
    speaker, receiver = actors[:2]
    sent = f12.send_signal(path, speaker, "help", receiver, "survival-signal-send")
    received = f12.receive_signal(path, receiver, speaker, sent["token"],
                                  "survival-signal-receive")
    feedback = f12.feedback_signal(path, receiver, sent["token"], "help", True,
                                   "survival-signal-feedback", speaker)
    return {"performed": True, "speaker": speaker, "receiver": receiver,
            "provenance":"guided authored-feedback fixture; not an observed native delivery",
            "native_delivery_verified":False,"language_emergence_gate_passed":False,
            "token": sent["token"], "initial_meaning": received["interpretation"]["meaning"],
            "feedback_changed": feedback["changed"]}


def _branch_report(path, actors, overlays=False):
    native = _native_metrics(path)
    result = {"native": native, "controller": _controller_metrics(path, actors)}
    if overlays:
        result.update({"f12": f12.inspect(path), "f12_replay": f12.replay(path),
                       "f6_replay": f6.replay(path), "f7_replay": f7.replay(path)})
    return result


def run_check(output=None, seconds=90.0, segment_seconds=30.0,
              config_path=None, population=None, folder=None):
    started=time.perf_counter()
    if not 0 < seconds <= 3600 or not 0 < segment_seconds <= seconds:
        raise ValueError("bounded survival duration required")
    if output is not None and Path(output).exists():raise FileExistsError('Refuse replacing survival evidence')
    config_path = Path(config_path or ROOT / "config/living-world.toml")
    config = copy.deepcopy(load(config_path))
    if population is not None:
        if not 1 <= population <= config["world"]["population_limit"]:
            raise ValueError("invalid population override")
        config["world"]["population"] = population
    folder=Path(folder) if folder is not None else ROOT/'data'/('f12-check-'+uuid.uuid4().hex)
    folder.mkdir(parents=True,exist_ok=False)
    (folder/'manifest.json').write_text(json.dumps(dict(profile='UW9 integration slice',requested_seconds=seconds,
                  config=config,unverified=['F0-F5/weather integration','scientific F12 gate'])),encoding='utf8')
    with nullcontext(folder) as raw:
        folder = Path(raw)
        source = folder / "source.sqlite"
        control = folder / "control.sqlite"
        f6_world = folder / "f6.sqlite"
        f7_world = folder / "f7.sqlite"
        integrated = folder / "integrated.sqlite"
        storage.create(source, config, scripted=False)
        source_bytes = source.read_bytes()
        source_hash = _hash(source)
        _copy_world(source, control)

        # Chain the copy-only overlays so the final branch contains F6 through
        # F12 while preserving one native source and one matched control.
        f6.attach(source, f6_world)
        f7.attach(f6_world, f7_world)
        f12.attach(f7_world, integrated, declared_values=["survival", "care"])
        stabilization.attach(control, model=False, call_limit=0)
        stabilization.attach(integrated, model=False, call_limit=0)

        actors = _actors(storage.inspect(integrated))
        communication = _communication_handshake(integrated, actors)
        integrated_stages = []
        control_stages = []
        elapsed_target = 0.0
        while elapsed_target < seconds:
            duration = min(segment_seconds, seconds - elapsed_target)
            before_observations = {
                agent: f12.observe_current(integrated, agent)["observation"]
                for agent in actors
            }
            before_tick = min(int(item["tick"]) for item in before_observations.values())
            control_result = stabilization.run(control, duration, 240)
            integrated_result = stabilization.run(integrated, duration, 240)
            telemetry = _record_overlay_telemetry(integrated, actors,
                                                  before_observations, before_tick)
            integrated_stages.append({"duration_s": duration, "stabilization": integrated_result,
                                      "telemetry": telemetry,
                                      **_branch_report(integrated, actors, overlays=True)})
            control_stages.append({"duration_s": duration, "stabilization": control_result,
                                   **_branch_report(control, actors)})
            if control_result["status"] != "target_reached":
                break
            if integrated_result["status"] != "target_reached":
                break
            elapsed_target = min(storage.inspect(control)['simulated_time_s'],storage.inspect(integrated)['simulated_time_s'])

        integrated_final = _branch_report(integrated, actors, overlays=True)
        control_final = _branch_report(control, actors)
        result = {
            "rule": f12.RULE,
            "config": config,
            "requested_seconds": seconds,
            "segment_seconds": segment_seconds,
            "world_folder":str(folder.resolve()),"native_profile":"UW9; no UW10W weather/F0-F5 integration",
            "duration_completed":min(integrated_final['native']['simulated_time_s'],control_final['native']['simulated_time_s'])>=seconds,
            "wall_time_s":time.perf_counter()-started,
            "source_sha256": source_hash,
            "source_unchanged": source.read_bytes() == source_bytes and _hash(source) == source_hash,
            "actors": actors,
            "communication_handshake": communication,
            "integrated": {"stages": integrated_stages, "final": integrated_final},
            "control": {"stages": control_stages, "final": control_final},
            "native_state_hash_matches_control": integrated_final["native"]["state_hash"] == control_final["native"]["state_hash"],
            "integrated_all_alive": integrated_final["native"]["alive"] == integrated_final["native"]["population"],
            "control_all_alive": control_final["native"]["alive"] == control_final["native"]["population"],
            "integrated_replay_matches": integrated_final["native"]["replay"]["replay_matches"] and
                                         integrated_final["f12_replay"]["replay_matches"] and
                                         integrated_final["f6_replay"]["replay_matches"] and
                                         integrated_final["f7_replay"]["replay_matches"],
            "unverified": [
                "F8-F11 proposal choices are not native scheduler inputs",
                "no humanlike emotion or communication claim",
                "no indefinite lifelong survival claim",
                "no multi-seed scientific survival gate",
                "F0-F5, UW10W weather and H language are not integrated",
                "F9 handshake uses guided authored feedback, not native signal grounding",
            ],
        }
        if output is not None:
            output = Path(output).resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n",
                              encoding="utf-8")
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=90.0)
    parser.add_argument("--segment-seconds", type=float, default=30.0)
    parser.add_argument("--population", type=int)
    parser.add_argument("--config", type=Path, default=ROOT / "config/living-world.toml")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument('--folder',type=Path,help='Unused folder; all native saves are retained, including on failure')
    args = parser.parse_args(argv)
    result = run_check(args.output, args.seconds, args.segment_seconds, args.config, args.population,args.folder)
    print(json.dumps({
        "artifact": str(args.output),
        "integrated_alive": result["integrated_all_alive"],
        "control_alive": result["control_all_alive"],
        "native_state_hash_matches_control": result["native_state_hash_matches_control"],
        "integrated_replay_matches": result["integrated_replay_matches"],
        "source_unchanged": result["source_unchanged"],
        "communication_feedback_changed": result["communication_handshake"].get("feedback_changed"),
        "integrated_overlay_operations": result["integrated"]["final"]["f12"]["operation_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
