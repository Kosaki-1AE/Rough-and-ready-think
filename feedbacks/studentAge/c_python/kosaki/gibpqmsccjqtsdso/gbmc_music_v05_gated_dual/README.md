# GBMC Music v0.5 — onset gated dual runtime (research prototype)

## Usage (Windows)
```bat
python -m pip install -r requirements.txt
python gbmc_music.py doppelganger.wav --out output_doppel_v05 --change-threshold 3.2 --transition-threshold 0.2
```

**Important:** Input must be an actual PCM WAV file in the working directory or given as a full path. Demo: `python gbmc_music.py demo.wav --out demo_output`.

## Main improvement
- Retains all v0.4 outputs, original `events.csv`, beat matching and HPSS drum/melody decomposition.
- Adds `gated_layer_timeline.csv`: 30ms observations, drum/melody independent 16-room instances, `hold` or `room_transition` or `genesis_restart` plus explicit `reason`.
- `summary.json` adds `gated_layer_runtimes` and `gated_layer_rules`; legacy `independent_layer_runtimes` remains as a comparator.
- New engine evaluates transitions **only at detected onset bins**, remembers recurring quantized offset from a detected beat (or onset spacing when no beat data), and holds on recurring patterns.
- Genesis restart needs **3 consecutive surprising detected onset events** and a 2-second minimum between restarts; normal transitions have a 180ms minimum spacing. All are *tunable experimental safety gates, not scientifically validated thresholds*.

## Options
`--min-transition-ms 180 --min-restart-ms 2000 --pattern-persistence 3`

## Limits / stopping point
HPSS does not isolate actual instrument stems. Onset detection can be wrong, especially with dense music. Beat grid may be half/double tempo. Recording uses whole-song offline HPSS and beat estimation (not real time); no future-data-safe predictions are claimed. Quantized rhythm matching is simple, will sometimes merge distinct patterns, and state names are **not** evidence of distinct musical functions. The Room transition F→0→1 etc. remains an exploratory ordered index.

Interpret the v0.5 result as an engineering comparison of two state machines, **not a proof of GBMC's neuroscience/music validity**. This is a reasonable checkpoint before adding complexity.
