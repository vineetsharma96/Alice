from contextlib import closing
from pathlib import Path
import tempfile
import unittest

from underworld import adaptive as ad,context_teaching as ct,developmental as dev,storage,wayfinding as wf


class ContextTeachingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'world.sqlite';ad.initialize(self.path,53)
        wf.walk(self.path,'agent-2',[3,3]);ct.attach(self.path,['agent-1','agent-2'])

    def supplies(self):
        for target in ('resource-1','resource-2'):
            dev.execute(self.path,'agent-1','gather',[target],{'mass_kg':.01},update_memory=False)

    def test_teaching_self_selects_local_information_and_stops_after_disclosures(self):
        self.supplies();proofs=[]
        for _ in range(2):
            ct.observe(self.path,'agent-2')
            teaching=ct.teacher_step(self.path,'agent-1');self.assertTrue(teaching['taught'])
            heard=ct.observe(self.path,'agent-2');self.assertTrue(heard['learned']);proofs.append(heard['proof'])
        self.assertFalse(ct.teacher_step(self.path,'agent-1')['taught'])
        audit=ct.audit(self.path)
        self.assertEqual(audit['people']['agent-2']['adaptive']['external_teaching'],2)
        self.assertEqual(len(audit['people']['agent-1']['teaching_context']['disclosures']),2)
        self.assertEqual({x['understanding'] for x in audit['people']['agent-1']['teaching_context']['disclosures'].values()},{'unverified'})
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_no_inventory_does_not_fabricate_a_demonstration(self):
        head=storage.inspect(self.path)['state_hash']
        self.assertFalse(ct.teacher_step(self.path,'agent-1')['taught'])
        self.assertEqual(storage.inspect(self.path)['state_hash'],head)

    def test_native_teaching_interruption_does_not_duplicate_deposit(self):
        self.supplies();ct.observe(self.path,'agent-2')
        def fail(stage):
            if stage=='after_teaching_native':raise RuntimeError(stage)
        with self.assertRaises(RuntimeError):ct.teacher_step(self.path,'agent-1',fail)
        head=storage.inspect(self.path)['state_hash']
        taught=ct.teacher_step(self.path,'agent-1');self.assertTrue(taught['taught'])
        self.assertEqual(storage.inspect(self.path)['state_hash'],head)
        self.assertTrue(ct.observe(self.path,'agent-2')['learned'])
        with closing(storage._connect(self.path,readonly=True)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM development_records WHERE agent='agent-1' AND kind='gap_context_teaching'").fetchone()[0],1)


if __name__=='__main__':unittest.main()
