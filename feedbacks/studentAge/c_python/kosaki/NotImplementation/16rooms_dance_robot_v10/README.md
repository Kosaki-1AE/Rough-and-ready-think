# 16Rooms × Dance × NAO/G1 — offline prototype v1.0

**Read-only evaluation prototype** (NO ACTUATOR COMMANDS). Standard library, Python 2.7+ syntax (Python 2.7 not verified). Tests run on Python 3.13. Video-to-CSV is a separate, optional preprocessing stage; this package does not perform live MediaPipe inference nor real-time robot integration. The demonstration rows are SYNTHETIC, not experimentally measured.

## Run demo

From this folder:

```sh
python rooms_dance.py run --input sample/dance_events.csv --robot-feedback sample/robot_feedback.csv --memory output/backrooms.json --out output
```

Outputs: `decisions.csv` (decision time measured only for CPU processing of event row, not camera preprocessing or communication), `room_history.csv` (per-Room values and 8-bit register), `chunks.csv` (verified experience counts), `backrooms.json` (persistent memory). **To reset demonstration**, delete `output/backrooms.json` before rerun. Reusing memory across runs intentionally increases experience counts.

Extract zero-pose joint reference and complex projections from URDF:

```sh
python rooms_dance.py urdf --urdf sample/mini_robot.urdf --out output/mini_joints.csv
python rooms_dance.py urdf --urdf PATH_TO_NAO_OR_G1.urdf --out output/robot_joints.csv
```

This URDF parser reads `joint`, `origin xyz/rpy`, `axis`, `limit`, traverses joint/link tree and accumulates reference transforms. It assumes the URDF standard fixed-base zero joint configuration; movable joints set at q=0. It does not read xacro directly. It does not obtain physical sensor calibration, stability, live pose, camera coordinate transforms or account for calibration errors. The projection magnitudes `abs_xy`, `abs_xz`, `abs_yz` do **not** distinguish left/right by themselves; signed coordinates and joint identifiers are preserved.

## Data contract

Each row of `dance_events.csv` is **one decision event/chunk observation**, not a camera frame. `entry_time_ms` = desired musical entry; `observed_time_ms` = observed onset; `eight_duration_ms` = nominal 8-beat duration; `beat_phase` is normalized position [0,1]; `visibility` = user-supplied proxy [0,1]. `ref_*` fields are teacher pose features; `obs_*` are measured pose features. `teacher_verified` is an externally provided label; verified experiences increment only if teacher_verified=yes AND all current gates pass. Quality labels cannot be inferred from MediaPipe visibility. Demo angle data are placeholders in **degrees**; `robot_feedback.csv` joint angles are in **radians**.

MediaPipe exports landmarks (33 points) and observation timestamps using a separate capture adapter; to use here, derive angles from matching landmarks, align timestamps to beat / reference chunk events, and combine the features into this CSV. A single frame cannot directly determine tactile contact, ground reaction force, fall safety or intention. Observed reference angles should be extracted using identical calculations; human-robot retargeting requires a separate checked controller.

The `robot_feedback.csv` columns: `event_id,robot,joint,target_rad,actual_rad`. These are **logged observations**, not commands. The demo values are fictitious. The robot metric is only reported; it is **not** incorporated into autonomous actuation. Hardware-specific feedback should be sampled and timestamp-aligned externally.

## Room semantics

Room IDs F=Genesis; 0=Input; 1=Buffer; 2=Pool; 3=Queue; 4=Motion; 5=Stack; 6=Coherence; 7=Capacity; 8=Jab; 9=Quality; A=Twist; B=Stillness; C=Depth; D=Straight; E=Output. Baseline F→0→...→B→C→D→E uses **16 visits**, reused-chunk F→0→...→B→E uses **14**. This is a prototype scheduling policy, not evidence of a universal ≤16 transition property. Only a successful externally verified decision counts toward the 3-example reuse heuristic. Gates, weights, thresholds, and fallback are provisional *handwritten* rules; automatic discovery/learning is NOT implemented. Scores are heuristic and must not be interpreted as physical safety scores or learned causal explanations.

8-bit status register layout `[BB][O][RRRR][I]`: BB is a 2-bit reference **code** (0=not reused,1=reused in demo), not total memory capacity; O is output flag; R is Room index; I indicates valid input record, not a whole camera image. The full trace is in CSV; not encoded into 8 bits.

## Research roadmap / safety

1. MediaPipe video capture and beat annotations to event CSV; validation of footwork, headspin and hollowback landmark occlusion.
2. Compare reference/observed inter-joint coordination and temporal alignment; obtain user-defined success criteria.
3. NAO/G1 URDF data plus passive joint/IMU/camera measurements; record timing in a consistent clock frame.
4. Compare repeated chunks against nonreused baselines, decision correctness versus runtime; test unknown conditions.
5. Only after simulation and supervision, use a **separate, safety-certified low-level controller** to execute very small feasible motions, retaining emergency stop, collision and fall protections. Never direct-copy MediaPipe joints to robot motor commands. Do not attempt headspin on NAO/G1.

Copyright and consent: obtain lawful dance-video training data and permissions; never scrape private videos.

## Optional real-video MediaPipe pipeline

For an environment with supported OpenCV and MediaPipe `solutions`:

```sh
python extract_mediapipe.py --video reference.mp4 --out reference_landmarks.csv
python extract_mediapipe.py --video my_dance.mp4 --out my_landmarks.csv
python landmarks_to_events.py --reference reference_landmarks.csv --observed my_landmarks.csv --segments sample/segments.csv --out events.csv
python rooms_dance.py run --input events.csv --memory output/real_backrooms.json --out output
```

Replace `sample/segments.csv` with **real annotations** for matching chunk/beat time windows. The 2D angles are calculated from **left-side** landmarks only (11, 13, 23, 25, 27, 31). Headspin, floor contact, occlusion, camera angle and mirroring require validation and frequently invalidate the estimates. `teacher_verified=yes` must be provided after external inspection, NOT assumed from motion alone. Optional extractor is version-dependent; MediaPipe newer Tasks-only releases require updating this adapter. For live inference, capture+tracking latency and synchronization need additional engineering; this version is offline batch.
