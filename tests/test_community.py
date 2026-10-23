from contextlib import closing
import inspect
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from underworld import community, developmental as dev, symbols, storage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import community_study as study  # noqa: E402


class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'world.sqlite'
        community.initialize(self.path, 41)

    def test_new_four_person_world_keeps_h2_and_g_defaults(self):
        self.assertEqual(len(community.audit(self.path)['people']), 4)
        old = Path(self.tmp.name) / 'h2.sqlite'
        symbols.initialize(old, 41)
        self.assertEqual(len(symbols.audit(old)['people']), 2)

    def test_recruitment_is_once_and_preserves_other_people(self):
        before = community.audit(self.path)['people']
        community.recruit_newcomer(self.path, 'agent-3')
        after = community.audit(self.path)['people']
        for a in ('agent-1', 'agent-2', 'agent-4'):
            self.assertEqual(before[a], after[a])
        with self.assertRaisesRegex(ValueError, 'untrained, unrecruited'):
            community.recruit_newcomer(self.path, 'agent-3')

    def test_trained_person_cannot_be_reset_as_newcomer(self):
        # Coins from a real native percept; not a manually inserted association.
        symbols.coin(self.path, 'agent-1', 'resource-1')
        with self.assertRaises(ValueError):
            community.recruit_newcomer(self.path, 'agent-1')

    def test_private_boundaries_and_no_hidden_target_api(self):
        with self.assertRaisesRegex(ValueError, 'private learner access'):
            dev.private_state(self.path, 'agent-1', 'agent-2')
        self.assertNotIn('target', inspect.signature(community.select_reference).parameters)
        self.assertEqual(list(inspect.signature(community.learn_attention).parameters), ['path', 'listener', 'speaker'])
        with self.assertRaisesRegex(ValueError, 'no new natively delivered token'):
            community.select_reference(self.path, 'agent-1', 'agent-4', ['resource-1'])

    def test_native_grounding_survives_budget_interruption(self):
        study.move(self.path, 'agent-2', [3, 3])
        dev.execute(self.path, 'agent-1', 'gather', ['resource-1'], {'mass_kg': .01}, update_memory=False)
        token = symbols.coin(self.path, 'agent-1', 'resource-1')
        symbols.begin_attention(self.path, 'agent-2', ['resource-1'])
        dev.execute(self.path, 'agent-1', 'deposit', ['resource-1'], {'mass_kg': .001}, update_memory=False)
        dev.execute(self.path, 'agent-1', 'speak', parameters={'text': token}, update_memory=False)
        real = community.reconcile_budget
        calls = []
        def fault(path, agent):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError('interruption after native grounding')
            return real(path, agent)
        with patch.object(community, 'reconcile_budget', side_effect=fault):
            with self.assertRaisesRegex(RuntimeError, 'interruption'):
                community.learn_attention(self.path, 'agent-2', 'agent-1')
        real(self.path, 'agent-2')
        real(self.path, 'agent-2')
        state = community.audit(self.path)['people']['agent-2']
        self.assertEqual(sum(e['n'] for v in state['comprehension'].values() for e in v.values()), 1)
        self.assertTrue(storage.replay(self.path)['replay_matches'])
        # Valid record checksums do not license changing the learned meaning.
        with closing(storage._connect(self.path)) as db:
            state = dev._person(db, 'agent-2', 'agent-2')
            channel = next(iter(state['comprehension']))
            entry = next(iter(state['comprehension'][channel].values()))
            state['comprehension'][channel] = {'fabricated-feature': entry}
            dev._put(db, 'development_people', 'agent-2', state)
            db.commit()
        with self.assertRaisesRegex(ValueError, 'differs from native grounding meaning'):
            community.audit(self.path)

    def test_auditor_rejects_association_without_native_evidence(self):
        with closing(storage._connect(self.path)) as db:
            state = dev._person(db, 'agent-2', 'agent-2')
            state['comprehension'] = {'agent-1:s00': {'fabricated': {'n': 1, 'evidence': ['missing']}}}
            dev._put(db, 'development_people', 'agent-2', state)
            db.commit()
        with self.assertRaisesRegex(ValueError, 'native private grounding evidence'):
            community.audit(self.path)

    def test_budget_has_hard_protected_and_archive_limits(self):
        # Pure memory-algorithm check; these fabricated entries never enter a save.
        state = {'active_budget': 2, 'protection_threshold': 3, 'archived_comprehension': {},
                 'comprehension': {'a:s00': {str(i): {'n': 3, 'evidence': []} for i in range(3)}}}
        with self.assertRaisesRegex(ValueError, 'protected memory quota'):
            community.enforce_memory_budget(state)
        state['active_budget'] = 1
        state['comprehension'] = {'a:s00': {str(i): {'n': 1, 'evidence': []} for i in range(66)}}
        with self.assertRaisesRegex(ValueError, 'archived memory quota'):
            community.enforce_memory_budget(state)

    def test_budget_evicts_only_weak_entries_and_uncertainty_deduplicates(self):
        state = {'active_budget': 2, 'protection_threshold': 3, 'archived_comprehension': {},
                 'comprehension': {'a:s00': {'x': {'n': 3, 'evidence': []},
                                             'y': {'n': 1, 'evidence': []}, 'z': {'n': 1, 'evidence': []}}}}
        report = community.enforce_memory_budget(state)
        self.assertEqual(report, {'active': 2, 'protected': 1, 'evicted': 1, 'archived': 1})
        self.assertIn('x', state['comprehension']['a:s00'])
        self.assertFalse(community.partner_uncertainty(state, 'a', 's00', ['x', 'x', 'y'])['ambiguous'])


if __name__ == '__main__':
    unittest.main()
