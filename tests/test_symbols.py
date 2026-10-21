from contextlib import closing
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from underworld import developmental as dev, symbols, storage

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from symbol_study import move_listener  # noqa: E402
from developmental_study import introduce  # noqa: E402


class SymbolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'world.sqlite'
        symbols.initialize(self.path,41);move_listener(self.path)

    def teach(self):
        token=symbols.coin(self.path,'agent-1','resource-1')
        dev.execute(self.path,'agent-1','gather',['resource-1'],{'mass_kg':.01})
        symbols.begin_attention(self.path,'agent-2',['resource-1','resource-2'])
        dev.execute(self.path,'agent-1','deposit',['resource-1'],{'mass_kg':.001})
        spoken=dev.execute(self.path,'agent-1','speak',parameters={'text':token})
        return token,spoken,symbols.learn_attention(self.path,'agent-2','agent-1')

    def test_empty_independent_vocabularies_and_private_coinage(self):
        for target in ('resource-1','resource-2','resource-3'):
            symbols.coin(self.path,'agent-1',target)
        before=dev.private_state(self.path,'agent-2','agent-2')
        self.assertEqual(before['production'],{})
        self.assertEqual(before['comprehension'],{})
        for target in ('resource-1','resource-2','resource-3'):
            symbols.coin(self.path,'agent-2',target)
        a=dev.private_state(self.path,'agent-1','agent-1')
        b=dev.private_state(self.path,'agent-2','agent-2')
        self.assertNotEqual([v['token'] for v in a['production'].values()],
                            [v['token'] for v in b['production'].values()])

    def test_native_demonstration_then_message_only_reference(self):
        token,spoken,feedback=self.teach()
        self.assertTrue(feedback['grounded'])
        self.assertEqual(spoken['request']['target_ids'],[])
        self.assertEqual(set(spoken['request']['parameters']),{'text'})
        self.assertNotIn('resource-1',json.dumps(feedback['message']))
        dev.execute(self.path,'agent-1','speak',parameters={'text':token})
        decision=symbols.select_reference(self.path,'agent-2','agent-1',['resource-2','resource-1'])
        self.assertEqual(decision['target'],'resource-1')
        result=dev.execute(self.path,'agent-2','inspect',[decision['target']])
        self.assertTrue(result['receipt']['observable_effects']['description'].startswith('resource-1:'))
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_signal_without_observable_demonstration_teaches_no_meaning(self):
        symbols.begin_attention(self.path,'agent-2',['resource-1','resource-2'])
        dev.execute(self.path,'agent-1','speak',parameters={'text':'s00'})
        feedback=symbols.learn_attention(self.path,'agent-2','agent-1')
        self.assertFalse(feedback['grounded'])
        self.assertEqual(dev.private_state(self.path,'agent-2','agent-2')['comprehension'],{})

    def test_duplicate_grounding_cannot_double_update(self):
        self.teach()
        before=dev.private_state(self.path,'agent-2','agent-2')
        with self.assertRaisesRegex(ValueError,'prior attention'):
            symbols.learn_attention(self.path,'agent-2','agent-1')
        self.assertEqual(before['comprehension'],dev.private_state(self.path,'agent-2','agent-2')['comprehension'])

    def test_stale_token_is_not_new_delivery(self):
        _,_,feedback=self.teach()
        seq=int(feedback['message']['source_event_seq'])
        with self.assertRaisesRegex(ValueError,'no new natively delivered'):
            symbols.select_reference(self.path,'agent-2','agent-1',['resource-1'],seq)

    def test_native_occlusion_blocks_tokens(self):
        dev.execute(self.path,'agent-2','move',parameters={'x_m':4,'y_m':3})
        introduce(self.path,'occluder','inert_material',1,[3,3])
        dev.execute(self.path,'agent-1','speak',parameters={'text':'s00'})
        own=dev.own_observation(self.path,'agent-2')
        self.assertFalse(any(r['text']=='s00' for r in own['audible_reports']))
        with self.assertRaisesRegex(ValueError,'no new natively delivered'):
            symbols.select_reference(self.path,'agent-2','agent-1',['resource-2'])

    def test_old_text_speech_is_not_an_invented_symbol(self):
        dev.execute(self.path,'agent-1','speak',parameters={'text':'food'})
        with self.assertRaisesRegex(ValueError,'no new natively delivered'):
            symbols.select_reference(self.path,'agent-2','agent-1',['resource-1'])

    def test_listener_never_queries_speakers_private_state(self):
        self.teach()
        with patch.object(dev,'_person',wraps=dev._person) as private:
            symbols.select_reference(self.path,'agent-2','agent-1',['resource-1','resource-2'])
        self.assertTrue(private.call_args_list)
        self.assertTrue(all(c.args[1:] == ('agent-2','agent-2') for c in private.call_args_list))

    def test_frozen_production_refuses_unknown_percept(self):
        symbols.coin(self.path,'agent-1','resource-1')
        introduce(self.path,'new-small','food',.05,[1,3])
        with self.assertRaisesRegex(ValueError,'frozen production'):
            symbols.production_token(self.path,'agent-1','new-small')

    def test_missing_grounding_source_is_not_fabricated(self):
        self.teach()
        with closing(storage._connect(self.path)) as db:
            db.execute("DELETE FROM development_records WHERE agent='agent-2' AND kind='grounding'")
        with self.assertRaisesRegex(ValueError,'missing private grounding'):
            symbols.select_reference(self.path,'agent-2','agent-1',['resource-1','resource-2'])

    def test_archive_preserves_both_private_vocabularies(self):
        self.teach();before=symbols.audit(self.path)['vocabulary_hashes']
        dev.archive(self.path)
        self.assertEqual(symbols.audit(self.path)['vocabulary_hashes'],before)

    def test_native_speech_crash_resume_delivers_only_once(self):
        def fault(stage):
            if stage=='after_native_commit':raise RuntimeError('crash')
        with self.assertRaises(RuntimeError):
            dev.execute(self.path,'agent-1','speak',parameters={'text':'s00'},fault=fault)
        before=dev.own_observation(self.path,'agent-2')['audible_reports']
        dev.reconcile(self.path,'agent-1')
        self.assertIsNone(dev.reconcile(self.path,'agent-1'))
        self.assertEqual(before,dev.own_observation(self.path,'agent-2')['audible_reports'])
        self.assertEqual(sum(r['text']=='s00' for r in before),1)

    def test_grounding_rollback_retries_without_physical_replay(self):
        token=symbols.coin(self.path,'agent-1','resource-1')
        dev.execute(self.path,'agent-1','gather',['resource-1'],{'mass_kg':.01})
        symbols.begin_attention(self.path,'agent-2',['resource-1','resource-2'])
        dev.execute(self.path,'agent-1','deposit',['resource-1'],{'mass_kg':.001})
        dev.execute(self.path,'agent-1','speak',parameters={'text':token})
        head=storage.inspect(self.path)['state_hash']
        with patch.object(dev,'_put',side_effect=RuntimeError('crash')):
            with self.assertRaises(RuntimeError):symbols.learn_attention(self.path,'agent-2','agent-1')
        self.assertTrue(symbols.learn_attention(self.path,'agent-2','agent-1')['grounded'])
        self.assertEqual(storage.inspect(self.path)['state_hash'],head)
        entry=dev.private_state(self.path,'agent-2','agent-2')['comprehension']['agent-1:'+token]
        self.assertEqual(sum(v['n'] for v in entry.values()),1)

    def test_out_of_hearing_range_does_not_deliver_a_token(self):
        dev.execute(self.path,'agent-2','move',parameters={'x_m':12,'y_m':3},duration=9)
        dev.execute(self.path,'agent-1','speak',parameters={'text':'s00'})
        with self.assertRaisesRegex(ValueError,'no new natively delivered'):
            symbols.select_reference(self.path,'agent-2','agent-1',['tree-2'])

    def test_same_seed_reproduces_coinage_without_a_shared_store(self):
        token=symbols.coin(self.path,'agent-1','resource-1')
        independent=self.path.parent/'independent.sqlite'
        symbols.initialize(independent,41)
        self.assertEqual(symbols.coin(independent,'agent-1','resource-1'),token)


if __name__=='__main__':unittest.main()
