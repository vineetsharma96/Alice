import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class LearnerCliTests(unittest.TestCase):
    def test_h5_cli_send_retry_keeps_one_native_utterance(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'h5.sqlite'
            def run(*args):
                return subprocess.run([sys.executable,str(ROOT/'scripts/learner.py'),*args,'--db',str(db)],
                                      cwd=ROOT,capture_output=True,text=True,timeout=30)
            init=run('sequence-init');self.assertEqual(init.returncode,0,init.stderr)
            args=('sequence-send','--message-id','operator-example','--text','s00 s01')
            first=run(*args);self.assertEqual(first.returncode,0,first.stderr)
            state=run('sequence-status');self.assertEqual(state.returncode,0,state.stderr)
            second=run(*args);self.assertEqual(second.returncode,0,second.stderr)
            self.assertEqual(json.loads(first.stdout),json.loads(second.stdout))
            self.assertEqual(json.loads(run('sequence-status').stdout),json.loads(state.stdout))
            self.assertNotEqual(run('sequence-init').returncode,0)

    def test_h4_cli_continues_native_experience_without_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'h4.sqlite'
            def run(command):
                return subprocess.run([sys.executable,str(ROOT/'scripts/learner.py'),command,'--db',str(db),'--agent','agent-2'],
                                      cwd=ROOT,capture_output=True,text=True,timeout=30)
            init=run('wayfinding-init');self.assertEqual(init.returncode,0,init.stderr)
            step=run('need-step');self.assertEqual(step.returncode,0,step.stderr)
            result=json.loads(step.stdout)
            self.assertIsNone(result['decision']['goal'])
            state=run('wayfinding-status');self.assertEqual(state.returncode,0,state.stderr)
            self.assertEqual(json.loads(state.stdout)['people']['agent-2']['h4']['policy_decisions'],1)
            self.assertNotEqual(run('wayfinding-init').returncode,0)
            self.assertEqual(json.loads(run('wayfinding-status').stdout),json.loads(state.stdout))

    def test_community_cli_preserves_recruited_life_across_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'community.sqlite'
            def run(*args):
                return subprocess.run([sys.executable,str(ROOT/'scripts/learner.py'),*args,'--db',str(db)],
                                      cwd=ROOT,capture_output=True,text=True,timeout=30)
            initialized=run('community-init')
            self.assertEqual(initialized.returncode,0,initialized.stderr)
            recruited=run('recruit','--agent','agent-3')
            self.assertEqual(recruited.returncode,0,recruited.stderr)
            before=run('community-status')
            self.assertEqual(before.returncode,0,before.stderr)
            self.assertEqual(json.loads(before.stdout)['community']['agent-3']['cohort_role'],'recruited_newcomer')
            self.assertNotEqual(run('recruit','--agent','agent-3').returncode,0)
            self.assertNotEqual(run('community-init').returncode,0)
            self.assertEqual(json.loads(run('community-status').stdout),json.loads(before.stdout))

    def test_existing_life_learns_across_processes_and_init_cannot_reset_it(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'world.sqlite'
            def run(*args):
                return subprocess.run([sys.executable,str(ROOT/'scripts/learner.py'),*args,'--db',str(db)],
                                      cwd=ROOT,capture_output=True,text=True,timeout=30)
            initialized=run('init');self.assertEqual(initialized.returncode,0,initialized.stderr)
            for target in ('resource-1','resource-2'):
                result=run('food-trial','--alternatives',target)
                self.assertEqual(result.returncode,0,result.stderr)
            before=run('status');self.assertEqual(before.returncode,0,before.stderr)
            state=json.loads(before.stdout)
            self.assertEqual(state['people']['agent-1']['experiences'],2)
            self.assertTrue(state['people']['agent-1']['associations'])
            self.assertNotEqual(run('init').returncode,0)
            after=run('status');self.assertEqual(after.returncode,0,after.stderr)
            self.assertEqual(json.loads(after.stdout),state)


if __name__=='__main__':unittest.main()
