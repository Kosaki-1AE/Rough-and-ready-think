# 16 Rooms: minimal 8-bit state machine demo v0.1

This is a **toy demonstration**, not a validated dance AI or a full implementation of the GBMCCQSD Room Operators.

## State layout

`BB O RRRR I` (bits 7..0)

- BB: last two input bits, a tiny *history summary*, not external/virtual Backrooms storage
- O: binary output flag
- RRRR: Room index (0..F)
- I: current binary input (`1` = タン, `0` = タッ, arbitrary convention)

## Rules (temporary demo policy)

- Advance 2 Rooms on input 1, 1 Room on input 0, modulo 16.
- Shift the latest input into the two-bit history summary.
- Output 1 when the new Room is 4, 8, C, or F **and** the last two inputs are 11.

These rules are placeholders for later experimentally defined transitions and thresholds. The demo does not infer human intent or choose robot joint trajectories.

## Run

Python 3.6+:

```sh
python3 demo.py 101100101011
```

C99 compiler:

```sh
cc -std=c99 -O2 -Wall -Wextra demo.c -o demo
./demo 101100101011
```

Python and C should print identical tables for the same binary input. On older school PCs, check `python --version` and `cc --version` first.

## Next experiments

1. Compare Python/C outputs for identical inputs.
2. Measure process memory and binary size (separately from the 1-byte state).
3. Define actual 16 Rooms operators, transitions, and passage thresholds.
4. Specify the source/cost of virtual Backrooms data and a history reconstruction test.
5. Add dance-derived features and eventually a robot simulator with safety constraints.
