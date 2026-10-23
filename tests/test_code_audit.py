"""Integration regressions for launcher, transaction boundaries and action wiring."""
from contextlib import closing
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from underworld import storage,stabilization
from underworld.config import load
from underworld.observer import Controller

ROOT=Path(__file__).resolve().parents[1]


class ConnectionAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'world with spaces.sqlite'
        self.config=load(ROOT/'config/living-world-d.toml');self.config['world']['population']=1

    def tearDown(self):self.tmp.cleanup()

    def test_invalid_handoff_does_not_publish_a_world_or_mutate_config(self):
        before=copy.deepcopy(self.config)
        with self.assertRaisesRegex(ValueError,'inference attempt'):
            stabilization.initialize(self.path,self.config,call_limit=17)
        self.assertFalse(self.path.exists());self.assertEqual(before,self.config)
        with self.assertRaisesRegex(RuntimeError,'test native failure'):
            with patch('underworld.storage.load_native',side_effect=RuntimeError('test native failure')):
                storage.create(self.path,self.config)
        self.assertFalse(self.path.exists())

    def test_external_generator_is_not_consumed_by_interval_validation(self):
        self.config['cognition']['provider']='baseline'
        storage.create(self.path,self.config,scripted=True);o=storage.observe(self.path,['agent-1'])[0]
        req=dict(schema_version=1,run_id=o['run_id'],agent_id='agent-1',request_id='generator-gather',observation_version=o['tick'],
                 action_type='gather',target_ids=['resource-1'],parameters={'mass_kg':.1},requested_duration=1)
        with patch('underworld.storage.think'):
            storage.advance(self.path,5,((t,r) for t,r in [(0,req)]))
        own=storage.observe(self.path,['agent-1'])[0]
        self.assertEqual(own['own_state']['inventory_ug']['food'],'100000000')
        self.assertEqual(own['recent_action_results'][-1]['status'],'completed')
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_both_ui_projections_use_one_validated_read_transaction(self):
        self.config=load(ROOT/'config/culture.toml');storage.create(self.path,self.config)
        c=Controller(self.path,readonly=True);connect=storage._connect
        with patch('underworld.storage._connect',wraps=connect) as connections:
            state=c.state('agent-1')
        self.assertEqual(connections.call_count,1)
        self.assertEqual(state['snapshot']['tick'],state['selected']['tick'])
        self.assertEqual(state['mind']['agent'],'agent-1')
        self.assertIsNotNone(state['procedure']);self.assertTrue(state['controls']['read_only'])
        self.assertIsInstance(state['operator_history']['interventions'],list)
        self.assertEqual(state['operator_history']['branch_id'],state['snapshot']['branch_id'])

    def test_stopping_a_runner_preserves_the_committed_head(self):
        stabilization.initialize(self.path,self.config,call_limit=0)
        before=storage.inspect(self.path)
        result=stabilization.run(self.path,30,stop_requested=lambda:True)
        self.assertEqual(result['status'],'stopped');self.assertEqual(result['simulated_s'],0)
        self.assertEqual(storage.inspect(self.path),before)
        stabilization.run(self.path,.4)
        self.assertEqual(storage.inspect(self.path)['tick'],'2')

    def test_new_and_saved_launcher_runs_from_an_unrelated_directory(self):
        env=os.environ|{'PYTHONPATH':str(ROOT)}
        command=[sys.executable,'-m','underworld.app','--db',str(self.path),'--config',str(ROOT/'config/living-world-d.toml'),
                 '--no-browser','--exit-after-run','--port','0','--seconds','.4']
        for tick in ('2','4'):
            result=subprocess.run(command,cwd=self.tmp.name,env=env,text=True,capture_output=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stderr)
            lines=[json.loads(line) for line in result.stdout.splitlines()]
            self.assertTrue(lines[0]['viewer_read_only']);self.assertFalse(lines[0]['model_calls_enabled'])
            self.assertEqual(lines[-1]['run']['tick'],tick)
        self.assertEqual(storage.inspect(self.path)['tick'],'4')

    def test_cli_defaults_resolve_resources_outside_the_checkout(self):
        result=subprocess.run([sys.executable,'-m','underworld','living-world','init','--db',str(self.path),'--calls','0'],
                              cwd=self.tmp.name,env=os.environ|{'PYTHONPATH':str(ROOT)},text=True,capture_output=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(stabilization.status(self.path)['calls'],0)

    def test_relative_native_build_overrides_resolve_from_checkout(self):
        env=os.environ|{'PYTHONPATH':str(ROOT),'UNDERWORLD_BUILD':'build/living-d',
                        'UNDERWORLD_TOOLCHAIN':r'C:\mingw64\bin'}
        result=subprocess.run([sys.executable,'-c',
                               'from underworld.native_paths import configure_build; configure_build(); '
                               'from underworld.native import load_native; '
                               'print(load_native().world_format)'],
                              cwd=self.tmp.name,env=env,text=True,capture_output=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'UW9')

    def test_checkpoint_schema_has_one_authority(self):
        storage.create(self.path,self.config,scripted=False);storage.save(self.path,'snapshot')
        with closing(storage._connect(self.path,readonly=True)) as db:
            versions={x[0] for x in db.execute('SELECT schema_version FROM checkpoints')}
        self.assertEqual(versions,{storage.CHECKPOINT_SCHEMA})


if __name__=='__main__':unittest.main()
