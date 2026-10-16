import unittest
from pathlib import Path
import tempfile
import numpy as np
from gbmc_music import ROUTES, route_next, GatedLayerGBMC, run

class RouteTests(unittest.TestCase):
    def test_two_explicit_paths(self):
        self.assertEqual(ROUTES['normal'], 'F0123456789ABCDE')
        self.assertEqual(ROUTES['bypass'], 'F14679BC')
        self.assertEqual(route_next('9','normal'), 10)
        self.assertEqual(route_next('9','bypass'), 11)
        for mode, sequence in ROUTES.items():
            self.assertEqual(len(sequence), len(set(sequence)))
            self.assertEqual(sequence[0], 'F')
            walked = [15]
            for _ in range(len(sequence)):
                walked.append(route_next(walked[-1], mode))
            self.assertEqual(''.join(format(x,'X') for x in walked), sequence+'F')

    def test_gated_uses_route_at_9(self):
        # Seed the baseline to force an onset-driven novel rhythmic-position event.
        for mode, expected in [('normal',10),('bypass',11)]:
            rt = GatedLayerGBMC(route_mode=mode, transition_threshold=0.00001,
                                change_threshold=999, min_transition_ms=0)
            rt.restart(time_s=0, frame=0, rms=.1, spectral_flux=.1)
            rt.room = 9
            rt.baseline.extend([np.array([0.,0.])] * 5)
            ev = rt.observe_gated(dict(time_s=.3,frame=10,rms=.6,spectral_flux=1.),
                                  onset=True,beat_times=np.array([0.,.5,1.]))
            self.assertEqual(rt.room, expected)
            self.assertEqual(ev.event, 'room_transition')

    def test_demo_files_and_summary(self):
        with tempfile.TemporaryDirectory() as d:
            for mode in ('normal','bypass'):
                result=run(Path(__file__).parent/'demo.wav', Path(d)/mode,
                           route_mode=mode,transition_threshold=.2)
                self.assertEqual(result['gated_layer_rules']['route_mode'],mode)
                self.assertEqual(result['gated_layer_rules']['route_hex'],ROUTES[mode])
                self.assertTrue((Path(d)/mode/'gated_layer_timeline.csv').exists())
                self.assertTrue((Path(d)/mode/'drum_melody_offsets.csv').exists())

if __name__ == '__main__':
    unittest.main()
