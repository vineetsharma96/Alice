import copy
import math
from pathlib import Path
import sqlite3
import tempfile
import unittest

from underworld import storage
from underworld.config import load, validate
from underworld.native import load_native


ROOT = Path(__file__).resolve().parents[1]


def request(world, kind, targets=(), parameters=None, duration=1, request_id=None):
    observation = world.observe_batch(["agent-1"])[0]
    return {
        "schema_version": 1,
        "run_id": observation["run_id"],
        "request_id": request_id or f"{kind}-{observation['tick']}",
        "agent_id": "agent-1",
        "observation_version": observation["observation_version"],
        "action_type": kind,
        "target_ids": list(targets),
        "parameters": parameters or {},
        "requested_duration": duration,
    }


class TreeActionTests(unittest.TestCase):
    def setUp(self):
        self.world = load_native().World(
            seed=21,
            population=1,
            width=16,
            height=16,
            dt=0.2,
            scripted=False,
            bodies=True,
            food_kg=8,
            water_kg=16,
            tree_growth_kg_s=0,
        )

    def act(self, kind, targets=(), parameters=None, duration=1, request_id=None):
        action = request(self.world, kind, targets, parameters, duration, request_id)
        result = self.world.submit(action, "agent-1")
        self.assertIn(result["status"], ("accepted", "completed"))
        if result["status"] == "accepted":
            self.world.step(max(1, math.ceil(duration / self.world.snapshot()["dt_s"] - 1e-12)))
        return next(
            result
            for result in self.world.observe_batch(["agent-1"])[0]["recent_action_results"]
            if result["request_id"] == action["request_id"]
        )

    def test_tree_observation_harvest_and_collection_are_authoritative(self):
        move = request(self.world, "move", parameters={"x_m": 2.4, "y_m": 13.0}, duration=12, request_id="approach")
        self.assertEqual(self.world.submit(move, "agent-1")["status"], "accepted")
        self.world.step(70)

        observation = self.world.observe_batch(["agent-1"])[0]
        tree = next(entity for entity in observation["visible_entities"] if entity["entity_id"] == "tree-1")
        self.assertEqual(tree["stage"], "young")
        self.assertEqual(tree["biomass_ug"], "2000000000")

        inspected = self.act("inspect_tree", ["tree-1"], duration=0.2, request_id="inspect")
        self.assertEqual(inspected["status"], "completed")
        self.assertIn("stage=young", inspected["observable_effects"]["description"])

        before = self.world.snapshot()["material_totals_ug"]
        harvested = self.act("harvest_branch", ["tree-1"], {"mass_kg": 0.5}, request_id="branch")
        self.assertEqual(harvested["status"], "completed")
        self.assertEqual(harvested["observable_effects"]["description"], "wood_ug=450000000:fiber_ug=50000000")
        after = self.world.snapshot()["material_totals_ug"]
        self.assertEqual(int(after["tree"]) + int(after["wood"]) + int(after["fiber"]), int(before["tree"]))

        wood = next(entity for entity in self.world.snapshot()["entities"] if entity["kind"] == "wood")
        collected = self.act(
            "collect_wood",
            [wood["entity_id"]],
            {"material": "wood", "mass_kg": 0.45},
            request_id="collect",
        )
        self.assertEqual(collected["status"], "completed")
        own = self.world.observe_batch(["agent-1"])[0]["own_state"]
        self.assertEqual(own["inventory_ug"]["wood"], "450000000")
        self.world.check_invariants()

    def test_growth_is_bounded_and_checkpoint_deterministic(self):
        world = load_native().World(
            seed=22,
            population=1,
            width=8,
            height=8,
            dt=1,
            scripted=False,
            tree_growth_kg_s=0.01,
        )
        initial = world.snapshot()["initial_mass_ug"]["tree"]
        world.step(600)
        tree = next(entity for entity in world.snapshot()["entities"] if entity["entity_id"] == "tree-1")
        self.assertEqual(tree["stage"], "mature")
        self.assertEqual(world.snapshot()["boundary_sources_ug"]["tree"], 6000000000)
        self.assertEqual(int(world.snapshot()["material_totals_ug"]["tree"]), int(initial) + 6000000000)
        resumed = load_native().World.restore(world.checkpoint())
        world.step(10)
        resumed.step(10)
        self.assertEqual(world.checkpoint(), resumed.checkpoint())


class TreePersistenceTests(unittest.TestCase):
    def test_living_config_and_database_version_are_explicit(self):
        config = load(ROOT / "config/living-world.toml")
        self.assertEqual(config["agency"]["tree_growth_kg_s"], 0.005)
        for value in (-1, 0.011):
            invalid = copy.deepcopy(config)
            invalid["agency"]["tree_growth_kg_s"] = value
            with self.assertRaises(ValueError):
                validate(invalid)

        with tempfile.TemporaryDirectory(prefix="underworld-trees-") as folder:
            path = Path(folder) / "run.sqlite"
            backup = Path(folder) / "backup.sqlite"
            storage.create(path, config, scripted=False)
            snapshot = storage.inspect(path)
            self.assertIn("tree-1", {entity["entity_id"] for entity in snapshot["entities"]})
            storage.save(path, "tree-state", backup)
            self.assertEqual(storage.inspect(path)["state_hash"], storage.inspect(backup)["state_hash"])
            db = sqlite3.connect(backup)
            try:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 10)
                self.assertEqual(db.execute("SELECT schema_version FROM checkpoints WHERE name='initial'").fetchone()[0], 9)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
