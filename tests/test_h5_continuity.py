"""Supplementary retention checks; never change the frozen H5 scoring mechanism."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from underworld import composition as comp, developmental as dev, storage, wayfinding as wf


class H5ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'continuity.sqlite'
        comp.initialize(self.path, 47)
        wf.walk(self.path, 'agent-2', [3, 3])

    def test_pending_attention_crosses_epoch_and_learns_once_in_new_process(self):
        dev.execute(self.path, 'agent-1', 'gather', ['resource-1'], {'mass_kg': .002}, update_memory=False)
        text = comp.encode(self.path, 'agent-1', 'resource-1', learn=True)
        comp.begin(self.path, 'agent-2', 'epoch-attention', ['resource-1'])
        dev.execute(self.path, 'agent-1', 'deposit', ['resource-1'], {'mass_kg': .001}, update_memory=False)
        comp.send(self.path, 'agent-1', 'epoch-message', text)
        before = comp.audit(self.path)
        dev.archive(self.path)
        self.assertEqual(comp.audit(self.path), before)
        code = ('import sys,json; from underworld import composition as c; '
                'print(json.dumps(c.learn(sys.argv[1],"agent-2","agent-1","epoch-attention")))')
        child = subprocess.run([sys.executable, '-c', code, str(self.path)],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 0, child.stderr)
        result = json.loads(child.stdout)
        state = comp.audit(self.path)
        self.assertEqual(state['people']['agent-2']['h5']['external_teaching'], 1)
        self.assertEqual(comp.learn(self.path, 'agent-2', 'agent-1', 'epoch-attention'), result)
        self.assertEqual(comp.audit(self.path), state)
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_pending_message_snapshot_recovers_without_a_second_utterance(self):
        def crash(stage):
            if stage == 'after_message_intent':
                raise RuntimeError(stage)
        with self.assertRaises(RuntimeError):
            comp.send(self.path, 'agent-1', 'epoch-intent', 's00 s01', crash)
        before = comp.audit(self.path)
        dev.archive(self.path)
        self.assertEqual(comp.audit(self.path), before)
        result = comp.send(self.path, 'agent-1', 'epoch-intent', 's00 s01')
        native_head = storage.inspect(self.path)['state_hash']
        self.assertEqual(comp.send(self.path, 'agent-1', 'epoch-intent', 's00 s01'), result)
        self.assertEqual(storage.inspect(self.path)['state_hash'], native_head)
        self.assertTrue(storage.replay(self.path)['replay_matches'])


if __name__ == '__main__':
    unittest.main()
