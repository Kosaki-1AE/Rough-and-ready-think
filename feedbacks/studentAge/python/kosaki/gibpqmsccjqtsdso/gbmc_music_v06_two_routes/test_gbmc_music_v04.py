import unittest
from gbmc_music import MusicGBMC, match_layer_onsets, run_independent_layers

class TestDualRuntime(unittest.TestCase):
    def test_time_offset_sign_and_unmatched(self):
        events = [dict(source='drum_like', time_s=1.0),
                  dict(source='drum_like', time_s=2.0),
                  dict(source='melody_like', time_s=1.035),
                  dict(source='melody_like', time_s=3.0)]
        pairs, metrics = match_layer_onsets(events, 100.0)
        self.assertEqual(len(pairs), 1)
        self.assertAlmostEqual(pairs[0]['offset_ms'], 35.0)
        self.assertEqual(metrics['unmatched_drum_events'], 1)
        self.assertEqual(metrics['unmatched_melody_events'], 1)

    def test_independent_genesis_and_history(self):
        def row(i, rms):
            return dict(frame=i,time_s=i*.03,rms=rms,spectral_flux=0.)
        features = {'drum':[row(i, .0 if i<5 else .9) for i in range(10)],
                    'melody':[row(i, 0.02) for i in range(10)]}
        timeline, events, summary = run_independent_layers(
            features, features['drum'], change_threshold=3.2, transition_threshold=.2, hop_ms=30.)
        self.assertEqual(len(timeline), 10)
        self.assertGreater(summary['drum']['reference_count'], 1)
        self.assertEqual(summary['melody']['reference_count'], 1)
        self.assertTrue(any(e['source']=='drum' and e['event']=='genesis_restart' for e in events))

if __name__ == '__main__':
    unittest.main()
