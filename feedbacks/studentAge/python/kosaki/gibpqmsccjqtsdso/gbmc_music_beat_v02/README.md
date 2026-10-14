# GBMC Music v0.2 — Beat comparison

This is an experimental music analysis tool, not a validated model of music cognition or neuroscience.

## Setup (Windows PowerShell / Command Prompt)

```powershell
python -m pip install -r requirements.txt
```

Place an **uncompressed PCM WAV** file alongside `gbmc_music.py` or pass the full path to it. No copyrighted tracks are included.

## Run

```powershell
python gbmc_music.py music.wav --out output_mazy --change-threshold 3.2 --transition-threshold 0.2
python gbmc_music.py doppelganger.wav --out output_doppel --change-threshold 3.2 --transition-threshold 0.2
```

If your music file is called `music.wav`, use that name in each command. **Use distinct output folders** to avoid replacing results.

Outputs:
- `events.csv`: 30ms GBMC observations, legacy event log unchanged.
- `summary.json`: legacy counters plus `beat_analysis` including estimated BPM and proximity metrics.
- `beat_times.csv`: estimated beats, times in seconds.
- `beat_comparison.csv`: every detected Genesis restart (excluding initialization), nearest beat, signed offset `restart - beat` in ms and match within tolerance.

`fraction_restarts_near_beats` = (# detected restarts near a beat) / (# detected restarts).
`fraction_beats_near_restarts` = (# estimated beats near a restart) / (# estimated beats).
These are proximity measures, **not beat accuracy or proof of musical reference-point changes**. Beat estimates can have phase/tempo errors. Check output against listening/annotations, and compare with a chance baseline.

## Options

```powershell
python gbmc_music.py music.wav --out output --beat-tolerance-ms 50 --transition-threshold 0.2
python gbmc_music.py music.wav --out output_legacy --no-beats
python -m unittest -v test_gbmc_music.py
```

`--no-beats` runs the previous GBMC logic without requiring librosa. Default GBMC threshold values stay as before (`change=3.2`, `transition=1.3`); for the earlier song comparison pass `--transition-threshold 0.2` explicitly.

**Important:** The 16 Rooms still progress in a provisional fixed sequence when the novelty threshold is met. Detecting beats has **not** been made a rule for Genesis restarts. This update only tests whether the existing restart events coincide with beat estimates.
