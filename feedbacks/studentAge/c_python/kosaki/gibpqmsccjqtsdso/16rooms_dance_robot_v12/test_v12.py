import copy
import os
import unittest
from rooms_v11 import read_csv, extract_urdf, mapping_config
from mental_loop import replay, simulate, plan_event, mapped_targets

BASE = os.path.join(os.path.dirname(__file__), 'sample')

class MentalLoopTests(unittest.TestCase):
    def setUp(self):
        self.ref = read_csv(os.path.join(BASE, 'reference.csv'))
        self.obs = read_csv(os.path.join(BASE, 'observations.csv'))
        self.config = mapping_config(os.path.join(BASE, 'mapping.json'))
        self.urdf = extract_urdf(os.path.join(BASE, 'mini_robot.urdf'))
        self.memory = {'chunks': {}, 'residuals': {}}

    def test_replay_interpolation(self):
        frames, reason = replay(self.ref, 'sixstep', 0.0, 7)
        self.assertEqual(reason, 'ok')
        self.assertEqual(len(frames), 7)
        self.assertAlmostEqual(frames[2]['features']['shoulder_left_deg'], 95)

    def test_unknown_requests_reobserve(self):
        s, frames, pred, requests, _ = plan_event(self.obs[-1], self.ref, self.config, self.urdf, self.memory)
        self.assertEqual(s['next_action'], 'REOBSERVE')
        self.assertFalse(pred)
        self.assertTrue(requests)

    def test_simulation_is_not_learning(self):
        before = copy.deepcopy(self.memory)
        s, frames, pred, req, _ = plan_event(self.obs[0], self.ref, self.config, self.urdf, self.memory)
        self.assertEqual(s['next_action'], 'SIMULATED_NOT_EXECUTED')
        self.assertTrue(pred)
        self.assertEqual(self.memory, before)

    def test_limits_rejected(self):
        bad = [dict(self.config[0], neutral_rad=100)]
        s, _, pred, req, _ = plan_event(self.obs[0], self.ref, bad, self.urdf, self.memory)
        self.assertEqual(s['next_action'], 'REOBSERVE')
        self.assertFalse(pred)

    def test_no_extrapolation(self):
        frames, reason = replay(self.ref, 'sixstep', 0.9)
        self.assertFalse(frames)
        self.assertEqual(reason, 'phase_outside_observed_range')

    def test_simulation_lag(self):
        frames, _ = replay(self.ref, 'sixstep', 0.0, 9)
        pred, reason = simulate(frames, self.config, self.urdf, self.memory)
        self.assertEqual(reason, 'ok')
        self.assertTrue(any(x['predicted_tracking_error_rad'] > 0 for x in pred))

if __name__ == '__main__':
    unittest.main()
