from contextlib import closing
import copy
import json
import io
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from underworld import storage, memory, cognition
from underworld.config import load
from underworld.wire import dumps, loads

ROOT = Path(__file__).resolve().parents[1]


def plan(intent="rest", target="", text="", evidence=None):
    return dumps({"intent": intent, "target": target, "text": text,
                  "interpretation": "This is a tentative inference.", "evidence": evidence or []})


class MockProvider:
    def __init__(self, raw=None, delay=0):
        self.raw, self.delay = raw or plan(), delay

    def generate(self, context, budget):
        time.sleep(self.delay)
        return self.raw, {"model": "mock-only"}


class CognitionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="underworld-minds-")
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "run.sqlite"
        self.config = load(ROOT / "config/cognition.toml")
        self.config["world"]["population"] = 2
        self.initial = storage.create(self.path, self.config, scripted=False)

    def query(self, sql, args=()):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute(sql, args).fetchall()

    def request(self, kind, tick=0, params=None, targets=None, duration=1):
        return {"schema_version": 1, "run_id": self.initial["run_id"], "request_id": f"test-{kind}-{tick}",
                "agent_id": "agent-1", "observation_version": str(tick), "action_type": kind,
                "target_ids": targets or [], "parameters": params or {}, "requested_duration": duration}

    def test_perception_plan_consequence_memory_retrieval_restart_and_replay(self):
        storage.advance(self.path, 5, [(0, self.request("gather", params={"mass_kg": .4}, targets=["resource-1"]))])
        thought = storage.think(self.path, "agent-1", MockProvider(plan("eat")))
        self.assertEqual(thought["status"], "planned")
        storage.advance(self.path, 10)
        own = storage.observe(self.path, ["agent-1"])[0]["own_state"]
        self.assertEqual(own["body"]["food_ingested_ug"], "200000000")
        with closing(sqlite3.connect(self.path)) as db:
            retrieved = memory.retrieve(db, "agent-1", "ingested", 3)
            originals = db.execute("SELECT COUNT(*) FROM episodes WHERE kind='action_result'").fetchone()[0]
        self.assertTrue(any(e["record"].get("observable_effects", {}).get("description", "") == "ingested_ug=200000000" for e in retrieved))
        self.assertGreaterEqual(originals, 2)
        before = storage.mind(self.path, "agent-1", "ingested")
        backup = Path(self.tmp.name) / "backup.sqlite"
        storage.save(self.path, "memory", backup)
        storage.recover(backup)
        self.assertEqual(before, storage.mind(backup, "agent-1", "ingested"))
        with patch("underworld.cognition.bounded_call", side_effect=AssertionError("replay must not infer")):
            self.assertTrue(storage.replay(backup)["replay_matches"])

    def test_bad_json_fabricated_target_tool_and_foreign_memory_fall_back(self):
        for raw in ("{broken", plan("inspect", "nonexistent"), plan("read_private_memory"), plan(evidence=[999])):
            result = storage.think(self.path, "agent-1", MockProvider(raw))
            self.assertEqual(result["status"], "fallback")
            self.assertTrue(result["error"])
        self.assertEqual(storage.inspect(self.path)["tick"], "0")
        self.assertEqual(len(self.query("SELECT * FROM cognition_calls")), 4)

    def test_timeout_is_killable_and_does_not_advance_logical_time(self):
        # Supply a short timeout without mutating persisted config/code fingerprints.
        original = cognition.bounded_call
        started = time.perf_counter()
        with patch("underworld.cognition.bounded_call", side_effect=lambda p,c,b: original(p,c,b | {"timeout_s": .2})):
            result = storage.think(self.path, "agent-1", MockProvider(delay=60))
        self.assertEqual(result["status"], "fallback")
        self.assertIn("Timeout", result["error"])
        self.assertLess(time.perf_counter() - started, 3)
        self.assertEqual(storage.inspect(self.path)["tick"], "0")
        self.assertEqual(storage.advance(self.path, 1)["tick"], "1")

    def test_private_memories_and_lexical_ranking_are_bounded(self):
        with closing(sqlite3.connect(self.path)) as db:
            for i in range(70):
                memory.episode(db, "agent-1", f"e{i}", i, "experience", {"text": "water landmark" if i == 10 else "walking"})
            memory.episode(db, "agent-2", "secret", 0, "experience", {"text": "PRIVATE CANARY 817"})
            memory.seal(db)
            db.commit()
            results = memory.retrieve(db, "agent-1", "water", 3)
            self.assertEqual(results[0]["tick"], 10)
            self.assertEqual(len(results), 3)
            with self.assertRaises(ValueError):memory.retrieve(db, "agent-1", "", 9)
        context = cognition.context_for(storage.observe(self.path, ["agent-1"])[0], storage.mind(self.path, "agent-1"))
        self.assertNotIn("CANARY", dumps(context))
        self.assertNotIn("position_m", dumps(context))
        self.assertNotIn("state_hash", dumps(context))

    def test_local_conversation_creates_only_observed_relationship(self):
        path = Path(self.tmp.name) / "speech.sqlite"
        config = copy.deepcopy(self.config)
        config["world"]["population"] = 8
        storage.create(path, config, scripted=False)
        result = storage.think(path, "agent-1", MockProvider(plan("speak", text="The red stone is water. Could be wrong.")))
        storage.advance(path, 5)
        heard = storage.observe(path, ["agent-3"])[0]["audible_reports"]
        relationships = storage.mind(path, "agent-3")["relationships"]
        self.assertTrue(heard)
        self.assertTrue(relationships)
        self.assertEqual(result["status"], "planned")
        self.assertEqual(relationships[0]["evidence"], [heard[0]["source_event_seq"]])
        self.assertIn("unverified", dumps(storage.mind(path, "agent-3")))
        self.assertEqual(storage.mind(path, "agent-2")["relationships"], [])

    def test_tampered_identity_or_memory_fails_closed(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE identities SET payload='{}' WHERE agent='agent-1'")
            db.commit()
        with self.assertRaisesRegex(ValueError, "cognitive store checksum"):
            storage.recover(self.path)

    def test_invalid_native_preconditions_do_not_become_physical_facts(self):
        storage.think(self.path, "agent-1", MockProvider(plan("eat")))
        storage.advance(self.path, 1)
        result = loads(self.query("SELECT result FROM decisions WHERE source='cognition'")[0][0])
        self.assertEqual(result["error_code"], "INSUFFICIENT_RESOURCE")
        self.assertEqual(storage.observe(self.path,["agent-1"])[0]["own_state"]["body"]["food_ingested_ug"], "0")

    def test_run_changed_during_inference_discards_stale_plan(self):
        def concurrent(provider, context, budget):
            storage.advance(self.path, 1)
            return plan(), {}, .01
        with patch("underworld.cognition.bounded_call", side_effect=concurrent):
            with self.assertRaisesRegex(ValueError, "changed during inference"):
                storage.think(self.path, "agent-1", MockProvider())
        self.assertEqual(self.query("SELECT COUNT(*) FROM plans")[0][0], 0)
        record = loads(self.query("SELECT payload FROM cognition_calls")[0][0])
        self.assertEqual(record["status"], "interrupted_or_in_progress")

    def test_quota_counts_interrupted_attempt_and_concurrency_rejects(self):
        storage.INFERENCE_LOCK.acquire()
        try:
            with self.assertRaisesRegex(ValueError, "concurrency"):
                storage.think(self.path, "agent-1", MockProvider())
        finally:storage.INFERENCE_LOCK.release()
        # Separate new run with a one-call day budget.
        path = Path(self.tmp.name) / "quota.sqlite"
        config = copy.deepcopy(self.config)
        config["cognition"]["calls_per_simulated_day"] = 1
        storage.create(path, config, scripted=False)
        storage.think(path, "agent-1", MockProvider())
        self.assertEqual(storage.think(path, "agent-2", MockProvider())["status"], "quota")

    def test_endpoint_rejects_external_urls_credentials_and_redirects(self):
        for endpoint in ("https://127.0.0.1", "http://example.com", "http://localhost:8081", "http://x:y@127.0.0.1", "http://127.0.0.1/secret"):
            with self.assertRaises(ValueError):cognition.LlamaCpp(endpoint)
        with self.assertRaises(ValueError):cognition.NoRedirect().redirect_request(None,None,None,None,None,None)

    def test_llama_protocol_keeps_server_metadata_and_generation_budgets(self):
        context = cognition.context_for(storage.observe(self.path,["agent-1"])[0],storage.mind(self.path,"agent-1"))
        responses = [{"build_info":"b11721-ff5a23376","model_path":"models/smollm2-360m-instruct-q8_0.gguf"},
                     {"tokens":[1,2,3]}, {"content":plan(),"tokens_predicted":30}]
        with patch("underworld.cognition.build_opener") as opener:
            opener.return_value.open.side_effect = [io.BytesIO(dumps(r).encode()) for r in responses]
            raw, metadata = cognition.LlamaCpp().generate(context,self.config["cognition"])
            self.assertEqual(raw,plan())
            self.assertEqual(metadata["server_build"],"b11721-ff5a23376")
            self.assertEqual(metadata["input_tokens"],3)
            sent = json.loads(opener.return_value.open.call_args_list[2].args[0].data)
            self.assertEqual(sent["n_predict"],self.config["cognition"]["max_output_tokens"])
            self.assertEqual(sent["temperature"],0)
            self.assertEqual(len(sent["json_schema"]["oneOf"]),5)

    def test_input_token_limit_prevents_generation(self):
        context = cognition.context_for(storage.observe(self.path,["agent-1"])[0],storage.mind(self.path,"agent-1"))
        responses = [{"build_info":"b11721-ff5a23376","model_path":"smollm2-360m-instruct-q8_0.gguf"}, {"tokens":[1]*2048}]
        with patch("underworld.cognition.build_opener") as opener:
            opener.return_value.open.side_effect = [io.BytesIO(dumps(r).encode()) for r in responses]
            with self.assertRaisesRegex(ValueError,"token quota"):
                cognition.LlamaCpp().generate(context,self.config["cognition"])
            self.assertEqual(opener.return_value.open.call_count,2)

    def test_scheduler_uses_one_shared_budget_and_model_off_keeps_working(self):
        path = Path(self.tmp.name) / "scheduled.sqlite"
        config = copy.deepcopy(self.config)
        config["cognition"]["interval_ticks"] = 5
        config["cognition"]["calls_per_simulated_day"] = 1
        storage.create(path, config)
        storage.advance(path, 15)
        self.assertEqual(storage.inspect(path)["cognition_calls"], 1)
        self.assertTrue(storage.replay(path)["replay_matches"])
        off = Path(self.tmp.name) / "off.sqlite"
        config["cognition"]["provider"] = "disabled"
        storage.create(off, config)
        storage.advance(off, 15)
        self.assertEqual(storage.inspect(off)["cognition_calls"], 0)
        self.assertGreater(storage.inspect(off)["recorded_decisions"], 0)

    def test_failed_tick_rolls_back_consumed_plan_and_memory(self):
        storage.think(self.path, "agent-1", MockProvider())
        before = storage.inspect(self.path)
        def crash(stage, tick):
            if stage == "before_commit":raise RuntimeError("crash")
        with self.assertRaises(RuntimeError):storage.advance(self.path, 1, fault=crash)
        self.assertEqual(before, storage.inspect(self.path))
        self.assertEqual(storage.mind(self.path,"agent-1")["plan"]["status"], "pending")
