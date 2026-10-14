# GBMC Music Instance — exploratory prototype

This project implements **one music instance** of a generic 16-Room transition runtime. It is **not** a recreation of the medaka study or a validated model of musical cognition.

## Quick start

```bash
pip install numpy
python gbmc_music.py input.wav --out output
python -m unittest -v
```

Accepts **uncompressed PCM WAV**. Convert MP3/M4A externally to WAV first, e.g. `ffmpeg -i song.mp3 -ac 1 -ar 16000 song.wav` if FFmpeg is available.

Outputs: `output/events.csv` (all observations, transitions, restarts, and reasons) and `output/summary.json`.

## Behavior

- `0..F` are the **16 Rooms** (not 16 Rooms each containing 16 Hex slots). `F` is named Genesis here; the operation is also called `G` for “restart from Genesis”.
- Sample audio approximately every 30 ms; **a sample does not automatically mean a transition**.
- Extract two simple audio features: RMS energy and positive spectral flux (change of normalized FFT spectrum).
- Build a robust rolling baseline (median, median absolute deviation); detect candidate reference changes by novelty exceeding a threshold.
- On reference change: set Room to `F`, increment reference ID, reset only the *local baseline*, **preserve full event history**.
- If a smaller novelty threshold is crossed, advance one Room according to the **provisional** linear cycle `F→0→1→…→E→F`; otherwise remain in place.
- Two instances can operate independently; the dance instance can be added later without changing the core approach.

**Important limits:** The names of Rooms do not yet have executable music-domain operators. The linear order is a test scaffold, not proof of the theory. Novelty-triggered “reference changes” are engineering choices; music accents are not universally equivalent to reference changes. Exact 30 ms real-time guarantees are not claimed, since this version analyzes an existing WAV offline. The baseline warm-up requires 4 observations, and very short bursts may be missed or ignored by the 120 ms restart refractory period.

## Commands

```bash
python gbmc_music.py input.wav --hop-ms 30 \
    --change-threshold 3.2 --transition-threshold 1.3 --out results
```

To test the distinction between reference reset and continuation, compare runs with different `--change-threshold` settings (e.g. `3.2` vs `100000`), **holding all other settings fixed**. This is not yet a clean causal experiment because the changing baseline also differs. The next step is to add a fixed set of external reference-change markers and compare with/without G restart using identical detected events.
