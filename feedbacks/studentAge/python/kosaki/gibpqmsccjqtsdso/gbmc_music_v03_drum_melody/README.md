# GBMC Music v0.3 — Drum-like / Melody-like timeline

This version **retains** the v0.2 GBMC 16-Room runtime, 30-ms observation interval, thresholds, Genesis resets (F), the complete event history, beat estimation and beat/restart comparison. The new analysis is observation-only and does **not** change Room transitions or restart counts.

## Windows quick start

Open Command Prompt or PowerShell **in this folder** and run:

```bat
python -m pip install -r requirements.txt
python gbmc_music.py "doppelganger.wav" --out output_doppel_v03 --change-threshold 3.2 --transition-threshold 0.2
python gbmc_music.py "mazy_metroplex.wav" --out output_mazy_v03 --change-threshold 3.2 --transition-threshold 0.2
```

If your WAV is named `music.wav`, use that filename instead. Each command writes its own folder so earlier runs are not overwritten. Use **uncompressed PCM WAV** (16-bit recommended). FLAC/M4A need conversion; renaming extensions does not convert the audio.

To test:

```bat
python -m unittest test_gbmc_music.py -v
```

## Outputs

- `events.csv`: **unchanged** legacy GBMC trace, every ~30ms.
- `summary.json`: previous GBMC results, existing `beat_analysis`, plus new `layer_analysis`.
- `beat_times.csv`: estimated beat times in seconds.
- `beat_comparison.csv`: distance of Genesis restart times to estimated beats.
- `drum_melody_timeline.csv`: one row per ~30ms, with `time_s`, `drum_strength`, `melody_strength`, `drum_onset` (0/1), `melody_onset` (0/1), and original GBMC event/Room/reference ID.
- `drum_melody_events.csv`: one row for each drum-like or melody-like onset time; nearest beat and Genesis restart, signed time differences in ms.

## Important interpretation

**Drum-like** means the *percussive component* returned by Harmonic–Percussive Source Separation (HPSS). It can contain consonants, plucked notes, and other attacks that aren't drums. **Melody-like** means the *harmonic component*, which can contain vocal harmonics, bass, chords and sustained sounds. It is NOT a melody-only stem, not a note transcription, and may miss legato note changes. Both use onset detection to approximate change/attack times. Values called `*_strength` are arbitrary algorithmic onset strength, **not loudness**, and should not be compared across different songs as though calibrated physical units.

This v0.3 analyzes the whole file using median filtering (non-causal) and estimates onset events; it is suitable for offline song comparison, not live prediction. The 30ms timeline maps the results to GBMC observation bins; underlying HPSS/onset detection has a different, coarser time resolution and estimated timing errors. Beats are also estimates and may exhibit half-/double-tempo ambiguities. There is no ground truth annotation of the drum/melody onsets in this prototype.

The G-restart/Room decision rules remain heuristic. Finding correlations with music features does not validate the GBMC semantics.

## Optional arguments

- `--hop-ms 30` controls GBMC observation bins.
- `--beat-tolerance-ms 50` controls beat/restart comparison.
- `--no-beats` skips beat detection; other analysis can still run (beat columns blank).
- `--no-layers` skips HPSS analysis and produces only the v0.2 outputs.

The separation step processes the song in memory and may take longer than the earlier runs, especially on long songs.
