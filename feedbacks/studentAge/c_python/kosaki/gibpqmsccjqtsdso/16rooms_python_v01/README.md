# 16Rooms Python prototype v0.1

**Source basis:** `261016.md` (the 16 Room names and their intended activities). All scores, criteria, shortcuts, and symbolic demo data below are **temporary implementation assumptions**, not established user-defined rules or findings.

## Requirements

- Python 2.7-compatible syntax (not tested on a live Python 2.7 interpreter); tested with Python 3.13.
- No pip packages, GPU, network, or downloaded model. Suitable for trying on lightweight Linux terminals if Python is installed.

## Run

```sh
python rooms16.py --test
python rooms16.py --demo
python rooms16.py --memory backrooms.json
```

`--memory` loads and saves learned observation counters to a local JSON file. Without it, memory is held only in the process.

## Spec

- 8-bit control state: `BB|O|RRRR|I`, where `BB` is a 2-bit candidate slot, not a 2-bit entire Backrooms; `O` is output-ready flag, not the answer; `RRRR` the Room ID; `I` the symbolic input-ready bit.
- One call processes one already-symbolized event, such as `tan` or `ta`. No audio inference, video ingestion, MNIST classification or autonomous gate synthesis is provided.
- All 16 named Rooms correspond to the named responsibilities in `261016.md`. The concrete numeric gate checks are provisional placeholders, currently explicit in code. `Quality` checks against an externally supplied target `expected` (teacher label), so running without a target can legitimately produce `HOLD`.
- Default `Stillness` branching: unconfirmed event -> `Depth` -> `Straight` -> `Output`, confirmed reusable event -> `Output`; forced deep path is available. These branch *conditions* were not fixed by the supplied document.
- 16 **room visits** is the demo budget, not 16 proven constant-time machine operations or guaranteed 30ms responsiveness. Holding/stopping counts as an incomplete decision.
- The three observations rule grants reuse, not ground-truth certainty. Mismatch revokes reuse.
- The explanations reflect explicit program rules; the code does NOT invent or discover its own logic or explain unseen real-world dance behavior.

## What to implement next

1. Specify objective domain-independent gates, especially Coherence/Capacity/Quality and what passes without an external label.
2. Replace event string with incremental binary event input and a separately designed input adapter for MediaPipe CSV or digit raster data.
3. Add experimentally measured CPU/RAM/time and a demonstrable failure/recovery case, then test on the actual target school computer.
