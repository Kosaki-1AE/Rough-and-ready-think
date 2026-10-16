# 16Rooms × Dance × NAO/G1 — v1.2 (v1.1 + mental rehearsal)

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

---

# v1.2 add-on: Refrain / Simulation / Reobserve

`mental_loop.py` adds a **non-executing mental-rehearsal pipeline** to v1.1. It keeps the 16Rooms engine, camera adapter, URDF reader, CSV feedback and memory system from v1.1. No per-Room numerical scoring formula is added.

```bash
python mental_loop.py --input sample/observations.csv --reference sample/reference.csv --mapping sample/mapping.json --urdf sample/mini_robot.urdf --out output/mental
python -m unittest discover -p 'test_v*.py' -v
```

The pipeline:

1. **REPLAY**: find an observed chunk and interpolate its recorded reference angles across the observed phase interval. This is not an extra camera observation. The reference currently ends at phase 0.75, so 0.75..1.0 is not extrapolated.
2. **SIMULATE**: generate upper-body demonstration joint targets and predict tracking using a simple first-order lag `q_next = q + response*(target - q)`. This is **not** MuJoCo, dynamics, contact, collision, balance, inverse kinematics, or hardware-ready motion.
3. **REOBSERVE**: create explicit CSV requests for unknown chunks, insufficient reference data, absent landmarks, and invalid targets. Requests are **not automatically fulfilled**: a person or camera capture pipeline must supply fresh observations and rerun the analysis.
4. **MEMORY**: simulated results never increment experience counts or update residuals. Only independently verified measured feedback in the existing v1.1 pipeline may update memory.

Outputs:
- `output/mental/mental_loop.csv`: action and explanation per event.
- `output/mental/refrain.csv`: reference replay angles with interpolation flags.
- `output/mental/SIMULATED_NOT_FOR_HARDWARE.csv`: predicted joint positions.
- `output/mental/reobserve_requests.csv`: evidence that needs new observation.
- `output/mental/room_history.csv`: trace of the existing 16Rooms evaluation.

**Limitations:** Replay uses time-normalized phase and 2D MediaPipe-derived joint angles. Real music onset/tempo inference, loopback to camera on HOLD, physical robot simulation, sensor fusion, robot inverse kinematics, and reinforcement learning remain future work. Do not send CSV targets to real NAO/G1. On low-spec machines, this offline mental loop requires only Python 3.8+ standard library; live camera still requires compatible MediaPipe and OpenCV. The 3-experience reuse heuristic in v1.1 is unchanged.

---

# v1.3 — Integrated offline pipeline (recommended entry point)

**Scope:** integrates all *implemented* non-physics/non-actuator modules in one command: measured/reference pose angles, configurable eight-count synchronization, chunk reference indexing, 16Rooms trace, replay, first-order imaginary prediction, re-observation queue, proposed upper-body targets, verified passive feedback learning, Backrooms JSON and diagnostic CSVs. It does **not** make automatic choreography discovery, full human-to-G1/NAO motion planning, intelligent musical beat tracking or real-world self-learning complete. Those are still research problems, even without real hardware or a physics simulator.

## Run integrated sample with no downloads

From this extracted directory:

```bash
python pipeline_v13.py \
  --input sample/observations.csv \
  --reference sample/reference.csv \
  --mapping sample/mapping.json \
  --urdf sample/mini_robot.urdf \
  --feedback sample/feedback.csv \
  --entry-ms 0 --eight-ms 4000 \
  --memory output/v13_backrooms.json --out output/v13

python -m unittest discover -p 'test_v*.py' -v
```

For reproducible re-runs delete `output/v13_backrooms.json`; otherwise verified experiences intentionally accumulate on each run. The sample is *synthetic* and must not be mistaken for real robot feedback.

Output artifacts (all under `output/v13/`):

- `aligned.csv`: timestamp/entry/eight-count phase aligned events. Source phase is preserved only if no timestamp exists and tagged as supplied.
- `catalog.csv`: reference chunks, actual earliest/latest recorded phase, start/end teacher poses, provenance tag.
- `decisions.csv`, `room_history.csv`: 16Rooms trace, register, HOLD/PROPOSED, elapsed **decision-only** time.
- `proposals_NOT_FOR_HARDWARE.csv`: operator-calibrated illustrative upper-body joint angles **not executable trajectories**.
- `refrain.csv`: observed or interpolated teacher angles; no extrapolation outside recorded phase.
- `imagined_NOT_FOR_HARDWARE.csv`: first-order approximate joint predictions. No contact, gravity, dynamics or collisions.
- `requests.csv`: what needs more observation; requests can only be *marked* fresh evidence received, not automatically confirmed correct.
- `mental.csv`: per-event REOBSERVE / SIMULATED_NOT_EXECUTED decisions.
- `experience.csv`, `stats.csv`, `backrooms.json`: verified-feedback distinction, descriptive error distribution, persistent chunk counts and small empirical residual adaptation.
- `summary.json`: counts, including hard-coded `hardware_commands: 0`.

No Room's learning rule uses arbitrary Coherence/Quality PASS score thresholds. Hard constraints such as valid data, joint identity, joint limits remain. The three-verified-experience shortcut remains a **heuristic** and must be validated before claims of learning efficiency.

## Real videos or webcam, then the whole pipeline

Optional packages compatible with your Python version: OpenCV (`opencv-python`) and MediaPipe with the `mp.solutions.pose` API. The core pipeline above uses standard library only (Python 3.8+). For camera/video:

```bash
python live_integrated.py \
  --source path/to/dance.mp4 --chunk sixstep \
  --reference sample/reference.csv \
  --mapping sample/mapping.json \
  --urdf sample/mini_robot.urdf \
  --entry-ms 0 --eight-ms 4000 \
  --out output/video_v13
```

Use `--source 0` for webcam; optional `--preview` opens a display window and `--max-frames 100` limits processing. For video files, uses OpenCV's media timestamp; webcams use elapsed monotonic time. Landmark data are two-dimensional projected angles extracted using MediaPipe, and a dropout can leave a frame without features. `live_integrated.py` does **not** read robot sensors or train using its predictions. Existing `extract_mediapipe_batch.py` can export raw MediaPipe landmarks if needed. The bundled sample calibration/robot are **not** representative of NAO/G1 and must be replaced with appropriate robot-specific URDF and mapping for meaningful adaptation.

## Audio and eight-count onset support

With a PCM WAV file (8/16-bit, mono/stereo), detect **energy transient candidates**:

```bash
python audio_clock.py --wav track.wav --out output/audio_onsets.csv --bpm 120
```

You then choose the actual musical entry from the candidates and set `--entry-ms` and `--eight-ms` (for 4/4 dance counting, BPM=120 gives 4000ms per eight). Energy peaks are **not** beat, bar, meter, or downbeat inference; do not claim audio-video automatic synchronization. MP3/M4A must be decoded to WAV with a separate trusted tool before this command.

## Re-observation feedback loop

`requests.csv` explicitly identifies the event/chunk/phase. Collect a genuinely **new observation** into a CSV with `event_id`, `original_event_id` (the old event ID), `chunk_id`, `phase`, `measured=yes`, and at least one finite pose feature such as `hip_left_deg`. Then add `--fresh new_measurements.csv` to `pipeline_v13.py`. A matching request becomes `FRESH_EVIDENCE_RECEIVED`; otherwise remains `OPEN`. This does not automatically resolve missing teacher-reference data or certify observational correctness. A revised reference recording and a rerun are needed to actually change teacher samples. No claimed autonomous camera aiming or source retrieval.

## Remaining non-physics, non-hardware research limitations

1. Real music-downbeat/tempo tracking, tempo drift correction, objective audio-video alignment (currently user-set clock plus WAV transient candidates).
2. Automatic dance segmentation and chunk naming from unlabeled movement; start/end keyframes currently rely on annotated chunk IDs and measured reference frames.
3. Learning a predictive kinematic/world model from observed trajectories (instead of first-order demo tracking), and proving robust/causally meaningful self-improvement.
4. Reliable 3D pose calibration, occlusion handling, skeleton-to-NAO/G1 pose retargeting with inverse kinematics and feasible motions. URDF readout alone is insufficient.
5. Automatic active perception/reobservation using uncertainty and new camera capture, rather than producing a request to fulfill.
6. Real-time benchmarking on intended school PC, older Python 2.x compatibility (not provided), and camera dependency integration tests in a real device environment.

**Safety:** no motor control API, no hardware-ready trajectories, no headspins or other unsafe movement instructions. Lab-provided controllers and physical simulators remain out of scope.
