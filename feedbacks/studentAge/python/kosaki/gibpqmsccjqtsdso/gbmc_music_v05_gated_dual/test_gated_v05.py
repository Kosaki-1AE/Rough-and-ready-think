import unittest
import numpy as np
from gbmc_music import GatedLayerGBMC

class TestGated(unittest.TestCase):
    def test_no_onset_means_no_advancement(self):
        rt=GatedLayerGBMC(transition_threshold=.2)
        for i in range(30):
            rt.observe_gated(dict(frame=i,time_s=i*.03,rms=.01 if i%2 else .7,
                                  spectral_flux=3. if i%2 else 0.),
                             onset=False,beat_times=np.array([]))
        self.assertEqual(sum(e.event=='room_transition' for e in rt.events),0)
        self.assertEqual(sum(e.detail=='persistent_new_pattern' for e in rt.events),0)
    def test_independent_instance(self):
        a,b=GatedLayerGBMC(),GatedLayerGBMC()
        a.observe_gated(dict(frame=0,time_s=0,rms=.1,spectral_flux=0),onset=False,beat_times=np.array([]))
        self.assertEqual(len(b.events),0)
        self.assertEqual(a.reference_id,1)
