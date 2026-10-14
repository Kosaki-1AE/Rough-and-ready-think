import tempfile
import unittest
from pathlib import Path
from gbmc_music import room_operator, run
from compare_routes import compare


class RoomOperatorTests(unittest.TestCase):
    def test_every_room_has_an_independent_operator(self):
        found=set()
        values=set()
        for i in range(16):
            name,value=room_operator(i,rms=.24,spectral_flux=1.4,novelty=2.3)
            found.add(name);values.add(value)
            self.assertTrue(0<=value<=1)
        self.assertEqual(len(found),16)
        self.assertGreater(len(values),7)

    def test_normal_bypass_gate_identical_but_outputs_can_differ(self):
        demo=Path(__file__).parent/'demo.wav'
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d)
            for mode in ('normal','bypass'):
                run(demo,parent/mode,route_mode=mode,transition_threshold=.2)
            result=compare(parent/'normal'/'gated_layer_timeline.csv',
                           parent/'bypass'/'gated_layer_timeline.csv')
            self.assertTrue(result['gate_decisions_identical'])
            self.assertGreater(result['different_room_rows'],0)
            self.assertGreater(result['different_operator_output_rows'],0)

if __name__=='__main__':unittest.main()
