import unittest
import numpy as np
from pathlib import Path
from tempfile import TemporaryDirectory
from gbmc_music import GatedLayerGBMC, run

class TestRepeatReevaluation(unittest.TestCase):
    def rt(self, limit, mode='normal'):
        r = GatedLayerGBMC(repeat_limit=limit, route_mode=mode,
                           transition_threshold=.00001, change_threshold=999,
                           min_transition_ms=0)
        r.restart(time_s=0, frame=0, rms=.1, spectral_flux=.1)
        r.known_positions.add(('beat', 0.0))
        r.baseline.extend([np.array([0.,0.])] * 5)
        return r

    def test_three_same_room_decisions_trigger_and_hold(self):
        r=self.rt(3)
        beats=np.array([0.,.5,1.,1.5,2.,2.5])
        e1=r.observe_gated(dict(time_s=.5,frame=17,rms=.2,spectral_flux=.2),onset=True,beat_times=beats)
        e2=r.observe_gated(dict(time_s=1.0,frame=33,rms=.2,spectral_flux=.2),onset=True,beat_times=beats)
        self.assertEqual(e1.event,'hold')
        self.assertEqual(e2.event,'reevaluate')
        self.assertEqual(e2.room_before, e2.room_after)
        self.assertEqual(r.reevaluation_count,1)
        self.assertEqual(r.room,15)
        # Observations without onset do not count toward repeat limit.
        for i in range(100):
            r.observe_gated(dict(time_s=1.01+i*.003,frame=40+i,rms=.2,spectral_flux=.2),onset=False,beat_times=beats)
        self.assertEqual(r.reevaluation_count,1)

    def test_two_repeat_and_routes_still_work(self):
        beats=np.array([0.,.5,1.,1.5,2.])
        for mode in ('normal','bypass'):
            r=self.rt(2,mode)
            r.room=9
            e=r.observe_gated(dict(time_s=.5,frame=17,rms=.2,spectral_flux=.2),onset=True,beat_times=beats)
            self.assertEqual(e.event,'reevaluate')
            self.assertEqual(r.room,9)
            # A genuinely new signature still follows selected route.
            e=r.observe_gated(dict(time_s=.7,frame=23,rms=.2,spectral_flux=.2),onset=True,beat_times=beats)
            self.assertEqual(e.event,'room_transition')
            self.assertEqual(r.room,10 if mode=='normal' else 11)

    def test_integration_exports_reevaluation(self):
        demo=Path(__file__).parent/'demo.wav'
        with TemporaryDirectory() as d:
            out=Path(d)
            s=run(demo,out,transition_threshold=.2,repeat_limit=2)
            self.assertEqual(s['gated_layer_rules']['repeat_limit'],2)
            self.assertTrue((out/'gated_layer_timeline.csv').exists())
            self.assertIn('reevaluations',s['gated_layer_runtimes']['drum'])

if __name__=='__main__': unittest.main()
