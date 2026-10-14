import unittest
import tempfile
import wave
from pathlib import Path
import numpy as np
from gbmc_music import MusicGBMC, extract_features, run, compare_restarts_to_beats

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
            summary = run(wav, Path(temp)/'out', analyze_beats=False, analyze_layers=False)
            self.assertGreater(summary['observation_frames'], 30)
            self.assertTrue((Path(temp)/'out'/'events.csv').is_file())
            self.assertTrue((Path(temp)/'out'/'summary.json').is_file())

    def test_beat_comparison(self):
        runtime = MusicGBMC()
        runtime.restart(time_s=0.0, frame=0, rms=0.0, spectral_flux=0.0,
                        reason="initial_reference")
        runtime.restart(time_s=0.52, frame=17, rms=0.1, spectral_flux=1.0,
                        reason="detected_reference_change")
        runtime.restart(time_s=1.20, frame=40, rms=0.1, spectral_flux=1.0,
                        reason="detected_reference_change")
        rows, metrics = compare_restarts_to_beats(runtime.events, np.array([0.5, 1.0, 1.5]), 50)
        self.assertEqual(metrics["detected_restarts"], 2)
        self.assertEqual(metrics["restarts_near_beats"], 1)
        self.assertEqual(metrics["beats_near_restarts"], 1)
        self.assertAlmostEqual(rows[0]["offset_ms"], 20)

    def test_layers_and_original_events_coexist(self):
        sr = 11025
        t = np.arange(sr * 3) / sr
        melody = 0.18 * np.sin(2 * np.pi * 440 * t)
        clicks = np.zeros_like(t)
        for sec in np.arange(0.3, 2.9, 0.5):
            idx = int(sec * sr)
            clicks[idx:idx + 30] += np.hanning(30) * 0.7
        x = np.clip(melody + clicks, -1, 1)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.wav"
            with wave.open(str(path), "wb") as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
                wf.writeframes((x * 32767).astype("<i2").tobytes())
            out = Path(temp) / "out"
            summary = run(path, out, analyze_beats=False, analyze_layers=True)
            self.assertEqual(summary["observation_frames"], len(extract_features(x, sr)))
            self.assertTrue((out / "drum_melody_timeline.csv").exists())
            self.assertTrue((out / "drum_melody_events.csv").exists())
            with (out / "drum_melody_timeline.csv").open(encoding="utf-8-sig") as fp:
                rows = list(__import__("csv").DictReader(fp))
            self.assertEqual(len(rows), summary["observation_frames"])
            self.assertIn("drum_like_onsets", summary["layer_analysis"])

if __name__ == '__main__':
    unittest.main()
