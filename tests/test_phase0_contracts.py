import copy
import unittest

from underworld import life_contracts as contracts


class Phase0ContractTests(unittest.TestCase):
    def test_all_shadow_records_are_sealed_and_deterministic(self):
        records = [
            contracts.identity(agent_id='agent-1', run_id='run-1', public_name='Ari-1', authored_traits={'seed': 1}),
            contracts.observation(agent_id='agent-1', run_id='run-1', native_tick=4, observation_version=4,
                                  own_state={'position_m': [1, 2]}, visible_entities=[]),
            contracts.memory(agent_id='agent-1', run_id='run-1', native_tick=4, observation_version=4,
                            memory_id='memory-1', memory_kind='episode', content={'text': 'saw tree'}, source_refs=['event-1']),
            contracts.body_need(agent_id='agent-1', run_id='run-1', native_tick=4, observation_version=4,
                               hunger=.2, thirst=.3, fatigue=.1, health=1, alive=True),
            contracts.affect_trace(agent_id='agent-1', run_id='run-1', tick_before=3, tick_after=4,
                                  observation_version=4, body_signals={'hunger': .2}, appraisal={'kind': 'relief'},
                                  fast_affect={'valence': .1}, slow_mood={'stress': .2}),
        ]
        for record in records:
            self.assertEqual(record['checksum'], contracts.checksum(record))
            self.assertEqual(record, contracts.verify(copy.deepcopy(record)))

    def test_private_owner_and_provenance_boundaries(self):
        observation = contracts.observation(agent_id='agent-1', run_id='run-1', native_tick=1,
                                            observation_version=1, own_state={}, visible_entities=[])
        tampered = copy.deepcopy(observation); tampered['privacy_scope'] = 'operator_projection'
        with self.assertRaisesRegex(ValueError, 'observations must be private native'):
            contracts.verify(tampered)
        tampered = copy.deepcopy(observation); tampered['checksum'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            contracts.verify(tampered)

    def test_invalid_ranges_and_versions_fail_closed(self):
        with self.assertRaises(ValueError):
            contracts.body_need(agent_id='agent-1', run_id='run-1', native_tick=0, observation_version=0,
                                hunger=1.1, thirst=.1, fatigue=.1, health=1, alive=True)
        record = contracts.identity(agent_id='agent-1', run_id='run-1', public_name='Ari-1', authored_traits={})
        record['profile'] = 'ALICE-LIFE-1'
        with self.assertRaisesRegex(ValueError, 'unsupported Phase-0 profile/version'):
            contracts.verify(record)
        record = contracts.identity(agent_id='agent-1', run_id='run-1', public_name='Ari-1', authored_traits={})
        record['unexpected'] = True
        with self.assertRaisesRegex(ValueError, 'unknown fields'):
            contracts.verify(record)


if __name__ == '__main__':
    unittest.main()
