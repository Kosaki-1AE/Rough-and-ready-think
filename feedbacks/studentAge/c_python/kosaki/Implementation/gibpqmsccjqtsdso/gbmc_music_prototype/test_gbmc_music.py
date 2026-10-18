import unittest
import tempfile
import wave
from pathlib import Path
import numpy as np
from gbmc_music import MusicGBMC, extract_features, run

class TestMusicGBMC(unittest.TestCase):
    def test_two_independent_instances(self):
        a, b = MusicGBMC(), MusicGBMC()
        row = dict(time_s=0.0, frame=0, rms=0.2, spectral_flux=0.0)
        a.observe(row)
        b.observe(row)
        a.restart(time_s=0.03, frame=1, rms=0.2, spectral_flux=0.0)
        self.assertEqual(a.reference_id, 2)
        self.assertEqual(b.reference_id, 1)
        self.assertEqual(a.room, 15)
        self.assertEqual(len(a.events), 2)
    def test_read_and_export(self):
        sr = 8000
        x = np.concatenate([np.zeros(sr//2), 0.8*np.sin(2*np.pi*440*np.arange(sr//2)/sr)])
        with tempfile.TemporaryDirectory() as temp:
            wav = Path(temp)/'sample.wav'
            with wave.open(str(wav), 'wb') as f:
                f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
                f.writeframes((x*32767).astype('<i2').tobytes())
            summary = run(wav, Path(temp)/'out')
            self.assertGreater(summary['observation_frames'], 30)
            self.assertTrue((Path(temp)/'out'/'events.csv').is_file())
            self.assertTrue((Path(temp)/'out'/'summary.json').is_file())

if __name__ == '__main__':
    unittest.main()
