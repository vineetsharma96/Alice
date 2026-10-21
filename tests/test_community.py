from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from underworld import community  # noqa: E402
import community_study  # noqa: E402


class CommunityH3Tests(unittest.TestCase):
    def test_four_agent_isolated_communities_coin_distinct_conventions(self):
        case = community_study.run_seed_case(8101)
        self.assertTrue(case['conventions_distinct'])
        self.assertTrue(case['conventions_not_merged'])
        self.assertTrue(case['private_isolation_verified'])

    def test_newcomer_recruitment_preserves_existing_vocabularies(self):
        case = community_study.run_seed_case(8111)
        self.assertTrue(case['cohort_recruitment_preserved_existing'])
        learned = next(r for r in case['arms'] if r['arm'] == 'newcomer_learned')
        untrained = next(r for r in case['arms'] if r['arm'] == 'untrained_newcomer')
        self.assertEqual(learned['rate'], 1.0)
        self.assertGreater(learned['rate'], untrained['rate'])

    def test_finite_memory_budget_protects_consolidated_and_archives_distractors(self):
        state = community_study._make_person_state(41, 'agent-2', 'community-a', 'founder',
                                                   active_budget=6, protection_threshold=3)
        for i, pkey in enumerate(community_study.PERCEPTS):
            tok = f's0{i}'
            for _ in range(4):
                community_study._ground_private(state, 'agent-1', tok, pkey, tag='core')
        for j, dpkey in enumerate(community_study.DISTRACTOR_PERCEPTS):
            dtok = f's0{j+4:x}'
            community_study._ground_private(state, 'agent-1', dtok, dpkey, tag='distract')
        active_count = sum(len(v) for v in state['comprehension'].values())
        archived_count = sum(len(v) for v in state['archived_comprehension'].values())
        self.assertEqual(active_count, 6)
        self.assertEqual(archived_count, 3)
        for i, pkey in enumerate(community_study.PERCEPTS):
            tok = f's0{i}'
            self.assertTrue(state['comprehension'][f'agent-1:{tok}'][pkey]['protected'])

    def test_ambiguity_detection_and_authored_repair(self):
        state = community_study._make_person_state(41, 'agent-2', 'community-a', 'founder')
        community_study._ground_private(state, 'agent-4', 's0a', community_study.PERCEPTS[0])
        community_study._ground_private(state, 'agent-4', 's0a', community_study.PERCEPTS[1])
        unc_before = community.partner_uncertainty(state, 'agent-4', 's0a', community_study.PERCEPTS)
        self.assertTrue(unc_before['ambiguous'])
        community_study._ground_private(state, 'agent-4', 's0a', community_study.PERCEPTS[0], tag='repair')
        unc_after = community.partner_uncertainty(state, 'agent-4', 's0a', community_study.PERCEPTS)
        self.assertFalse(unc_after['ambiguous'])
        self.assertEqual(unc_after['best_count'], 2)

    def test_five_seed_confirmation_passes_h3_gate(self):
        cases = [community_study.run_seed_case(s) for s in community_study.SEEDS]
        rep = community_study.summary(cases)
        self.assertTrue(rep['h3_gate'])
        self.assertEqual(rep['rates']['newcomer_learned'], 1.0)
        self.assertEqual(rep['rates']['post_interference_retained'], 1.0)
        self.assertEqual(rep['rates']['ambiguous_repaired'], 1.0)


if __name__ == '__main__':
    unittest.main()
