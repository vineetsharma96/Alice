import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class LearnerCliTests(unittest.TestCase):
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
