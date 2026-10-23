from copy import deepcopy
import unittest
from underworld import regulation_f8, integration_f12


class ReviewRegressions(unittest.TestCase):
    def test_receipt_missing_action_with_error_code_is_value_error(self):
        with self.assertRaises(ValueError):
            regulation_f8._receipt({'strategy':'rest', 'receipt':{
                'request_id':'bad','status':'failed','error_code':'BUSY'},
                'result':{},'estimated_cost_s':0})

    def test_nonfinite_candidate_coordinates_are_rejected(self):
        with self.assertRaises(ValueError):
            regulation_f8._candidate({'strategy':'move_to_safety','action_type':'move',
                'parameters':{'target_position':[float('nan'),0]},
                'requested_duration':1,'estimated_cost_s':1})

    def test_embedded_private_state_cannot_change_owner(self):
        state=integration_f12._initial_states(['agent-1'],'test-run',[])['agent-1']
        state=deepcopy(state);state['f9']['owner']='agent-2'
        with self.assertRaises(ValueError):integration_f12._validate_state('agent-1',state)
