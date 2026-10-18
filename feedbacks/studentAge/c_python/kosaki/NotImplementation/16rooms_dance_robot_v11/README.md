# 16Rooms × Dance × NAO/G1 — v1.1 (offline/simulation-ready)

**Research prototype — NEVER sends commands to real robots.** Python 3.8+ standard library for core. Optional live camera needs OpenCV and a compatible MediaPipe version. NAO/G1 actuator SDK integrations, hardware/simulator inverse kinematics, balance control and actual reinforcement learning are NOT included; avoid confusing a pose *proposal* with a safe executable command.

## Major changes from v1.0

- No manually assigned per-Room quality scores or PASS cutoffs. Rooms represent **processing stages and trace**, while missing data and physical joint limits are hard constraints. `PROPOSED` means *candidate available for simulation*, not physically safe or learned-correct.
- Real-time camera capture to pose features is available in `live_camera.py` (optional dependencies). It processes frames live and logs decision timing, but **does not stream motor commands**.
- Reference dance chunks indexed by music eight-count phase (0..1); an entry timestamp is recorded, but robust live audio beat detection is not yet implemented. Phase in the demo is driven by a user-supplied duration and start offset.
- A small, transparent retargeting **placeholder** maps a pose angle to an operator-calibrated URDF upper-body target. It is NOT human-to-robot inverse kinematics, does not model balance, does not support six-step footwork as actuator targets, and is NOT suitable for hardware execution.
- Feedback adapter reads passive feedback CSV; the `residuals` dictionary learns a small running correction to each joint's demonstration target using *verified* measured errors. This is simple supervised online error adaptation, **not reinforcement learning or independent discovery of criteria**. `Backrooms` also stores events and recent errors. A three-example rule triggers a shorter read path, not a guarantee of correctness.
- `legacy_v10.py` kept only for comparison; it contains the former hand-authored gates.

## Quick start (no pip / Internet / robot)

From this directory:

```bash
python rooms_v11.py run --input sample/observations.csv --reference sample/reference.csv --mapping sample/mapping.json --urdf sample/mini_robot.urdf --feedback sample/feedback.csv --memory output/backrooms.json --out output
python test_v11.py
```

Outputs:
- `output/decisions.csv`: status, timing, chunk experience, posture and feedback errors
- `output/room_history.csv`: 16Rooms trace and 8bit `[BB][O][RRRR][I]` per stage
- `output/PROPOSED_TARGETS_NOT_FOR_HARDWARE.csv`: **demonstration upper-body targets only**
- `output/backrooms.json`: learned residual biases and experience counts

For a reproducible demo, delete `output/backrooms.json` before running again.

## Live camera (requires appropriate MediaPipe + OpenCV)

```bash
python -m pip install opencv-python "mediapipe<0.10.21"
python live_camera.py --camera 0 --reference sample/reference.csv --mapping sample/mapping.json --urdf sample/mini_robot.urdf --chunk sixstep --eight-ms 4000 --memory output/live_backrooms.json
```

If your MediaPipe build lacks `mp.solutions.pose`, use a supported older `0.10.x` build or adapt to the Tasks Pose Landmarker. Python interpreter and package wheels must be mutually compatible. Press `q` to stop. Output `output/live_observations.csv` contains image-projected 2D joint angles with a monotonic timestamp. **No robot driver is opened**, no motion is commanded. The demo reference/mapping uses synthetic illustrative angles, and camera visibility/occlusion can invalidate the measurements.

For existing videos use `--camera your_video.mp4`; time from `monotonic()` then represents playback processing elapsed time rather than the original media timestamp. For scientifically aligned reference comparisons, export and synchronize frame timestamps separately.

## URDF

```bash
python rooms_v11.py urdf --urdf your_nao_or_g1.urdf --out output/joints.csv
```

Export `local_x/y/z`, `complex_xy`, `abs_xy`, joint limits. These coordinates are **local joint origins in the parent-link frame**; do not interpret `abs_xy` as world-coordinate or pelvis-coordinate position. For global pelvis-relative coordinates compute full forward kinematics (see earlier v1.0 URDF exporter for zero configuration). A robot model alone cannot supply live perception or joint feedback. Use exactly the URDF corresponding to the real robot and calibrate frame conventions.

## Research design and safety

1. Human dance video (reference + self) -> pose features; segment by music entry/one-eight/chunk.
2. 16Rooms chooses/schedules a *candidate*, logs experience, records missing evidence instead of inventing a score.
3. Candidate converted to robot-relative movement **in simulator** via proper inverse kinematics, constraints and balance planner (future integration).
4. Hardware feedback (joint/IMU/contact) synchronized by timestamps -> residual/coordination learning, saved in Backrooms.
5. Compare with no-memory baseline; measure physical imitation and timing error, coverage, unsafe candidate rate, decision time, error reduction over trials.

**For actual hardware:** use your lab's validated NAO/G1 controller and simulator, follow local safety procedures, retain low-level posture stabilization and E-stop, use speed/torque/range constraints and supervised testing. This prototype intentionally has no `--enable-motors` feature. Do not attempt headspin/hollowback on either physical robot. A robot executing standing footwork cannot be made safe by URDF limits alone.

### Meaning of "experience" and absolute conditions

Observed joint alignment and timing are not proof of skill. Experience count is increased only for rows marked externally verified AND passing basic schema; this is a heuristic. The empirical residual update uses joint measured errors but does not infer dynamics or cause. Safety constraints, camera validity, coordinate units and joint identities remain fixed checks independent of learned performance. Decisions are not guaranteed in 30ms; timings measured exclude the MediaPipe frame inference time.
