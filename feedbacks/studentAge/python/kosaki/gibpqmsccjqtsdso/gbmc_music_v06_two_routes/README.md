# GBMC Music v0.6 — two selectable paths (v0.5 preserved)

The v0.5 onset-gated drum/melody runtimes now support two paths **through the same 16 Room IDs**:

- `--route normal` (default): `F0123456789ABCDE` (`9 -> A`), a 16-state cycle.
- `--route bypass`: `F14679BC` (`9 -> B`), an 8-state cycle.

The cycle returns to `F` after `E` (normal) or `C` (bypass). A reference change restarts at `F` regardless of route. Other Room IDs still exist but are skipped on the bypass route.

## Windows

Install dependencies:

```bat
python -m pip install -r requirements.txt
```

Place a *real PCM WAV* in this folder, or pass its full path. Then run:

```bat
python gbmc_music.py doppelganger.wav --out output_normal --transition-threshold 0.2 --route normal
python gbmc_music.py doppelganger.wav --out output_bypass --transition-threshold 0.2 --route bypass
```

The existing full-audio GBMC and **legacy** independent-layer comparators retain their v0.5 behavior, for comparability. The route selection **only** affects the new onset-gated layer runtimes (`gated_layer_timeline.csv`, `gated_layer_runtimes` in `summary.json`). All original CSV files remain. `summary.json` includes `gated_layer_rules.route_mode` and `.route_hex`.

`--route` is an explicit experimental choice, **not** an automated neural/music decision. Do not conclude bypass is superior just from higher/lower transition counts: it changes which Rooms are visited, not the onset/novelty detector. The system retains v0.5 experimental rules, including the 180ms minimum transition separation, 2s minimum restart separation, and the pattern-memory limitation. Names attached to Rooms are placeholders and not validated neuroscience.

Run tests: `python -m unittest discover -v`.
