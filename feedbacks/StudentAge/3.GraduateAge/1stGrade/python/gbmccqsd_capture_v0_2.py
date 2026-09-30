"""
GBMCCQSD Live / Video Capture Prototype v0.2
============================================

Input modes
-----------
1) video path
2) webcam / USB camera
3) OptiTrack CSV (offline; live NatNet adapter is left as an extension point)

Pipeline
--------
video/camera
 -> MediaPipe Pose
 -> pose-derived kinematics
 -> GBMCCQSD observation variables
    - viscosity nu
    - effective candidate amount N_eff  [proxy: active body-channel entropy]
    - update scope Omega
    - drag F_drag
    - derived selection speed

IMPORTANT
---------
This is an experimental observer, not a validated scientific model.
N_eff here is a proxy based on distribution of activity across body channels.
For a true "next-action candidate" model, replace candidate_probs() with
a learned transition model / clustering model later.
"""

from __future__ import annotations

import argparse
import csv
import math
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError as e:
    raise SystemExit(
        "mediapipe が入っていません。\n"
        "pip install mediapipe opencv-python numpy"
    ) from e


EPS = 1e-12


# ============================================================
# Basic math
# ============================================================

def angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle ABC in degrees."""
    ba = a - b
    bc = c - b
    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)
    if nba < EPS or nbc < EPS:
        return 0.0
    cosv = np.dot(ba, bc) / (nba * nbc)
    cosv = np.clip(cosv, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosv)))


def entropy_effective_count(p: Sequence[float]) -> Tuple[float, float]:
    p = np.asarray(p, dtype=float)
    p = np.clip(p, EPS, None)
    p = p / np.sum(p)
    h = float(-np.sum(p * np.log(p)))
    return h, float(np.exp(h))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < EPS or nb < EPS:
        return 0.0
    return float(np.clip(np.dot(a, b) / (na * nb), -1.0, 1.0))


# ============================================================
# State
# ============================================================

@dataclass
class State:
    frame: int
    time_sec: float
    viscosity: float
    effective_candidates: float
    update_scope: float
    drag: float
    selection_speed: float
    body_speed: float
    left_knee_angle: float
    right_knee_angle: float
    left_elbow_angle: float
    right_elbow_angle: float
    torso_rotation: float


# ============================================================
# MediaPipe extractor
# ============================================================

class PoseExtractor:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def process(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self.pose.process(rgb)
        if not result.pose_landmarks:
            return None, result

        pts = np.array(
            [[lm.x, lm.y, lm.z] for lm in result.pose_landmarks.landmark],
            dtype=float,
        )
        return pts, result

    def close(self):
        self.pose.close()


# ============================================================
# GBMCCQSD observer
# ============================================================

class GBMObserver:
    """
    Experimental mapping from pose time series to:
      nu, N_eff, Omega, drag

    N_eff proxy:
      entropy of motion activity across five body channels:
      left arm / right arm / left leg / right leg / torso
    """

    # MediaPipe Pose indices
    L_SHOULDER = 11
    R_SHOULDER = 12
    L_ELBOW = 13
    R_ELBOW = 14
    L_WRIST = 15
    R_WRIST = 16
    L_HIP = 23
    R_HIP = 24
    L_KNEE = 25
    R_KNEE = 26
    L_ANKLE = 27
    R_ANKLE = 28

    def __init__(
        self,
        viscosity_alpha: float = 0.25,
        change_threshold: float = 0.02,
        capacity: float = 0.08,
    ):
        self.prev_pose: Optional[np.ndarray] = None
        self.pose_streak = 0

        self.viscosity_alpha = viscosity_alpha
        self.change_threshold = change_threshold
        self.capacity = capacity

    def _pose_vector(self, p: np.ndarray) -> np.ndarray:
        # Translation-invariant: center at hip midpoint.
        hip_mid = (p[self.L_HIP] + p[self.R_HIP]) / 2.0
        q = p - hip_mid

        # Scale-invariant: divide by shoulder width.
        sw = np.linalg.norm(p[self.L_SHOULDER] - p[self.R_SHOULDER])
        sw = max(sw, EPS)
        q = q / sw
        return q.flatten()

    def _viscosity(self, pose: np.ndarray) -> float:
        if self.prev_pose is None:
            self.pose_streak = 1
            return 0.0

        cur = self._pose_vector(pose)
        prv = self._pose_vector(self.prev_pose)
        sim = max(0.0, cosine_similarity(cur, prv))

        if sim >= 0.995:
            self.pose_streak += 1
        else:
            self.pose_streak = 1

        nu = 1.0 - math.exp(-self.viscosity_alpha * self.pose_streak * sim)
        return float(np.clip(nu, 0.0, 1.0))

    def _region_activity(self, pose: np.ndarray) -> np.ndarray:
        if self.prev_pose is None:
            return np.ones(5, dtype=float)

        d = np.linalg.norm(pose - self.prev_pose, axis=1)

        regions = [
            [self.L_SHOULDER, self.L_ELBOW, self.L_WRIST],
            [self.R_SHOULDER, self.R_ELBOW, self.R_WRIST],
            [self.L_HIP, self.L_KNEE, self.L_ANKLE],
            [self.R_HIP, self.R_KNEE, self.R_ANKLE],
            [self.L_SHOULDER, self.R_SHOULDER, self.L_HIP, self.R_HIP],
        ]

        activity = np.array([np.mean(d[idx]) for idx in regions], dtype=float)
        activity += EPS
        return activity

    def _n_eff(self, pose: np.ndarray) -> Tuple[float, float]:
        activity = self._region_activity(pose)
        p = activity / np.sum(activity)
        return entropy_effective_count(p)

    def _update_scope(self, pose: np.ndarray) -> float:
        if self.prev_pose is None:
            return 0.0
        d = np.linalg.norm(pose - self.prev_pose, axis=1)
        return float(np.mean(d >= self.change_threshold))

    def _body_speed(self, pose: np.ndarray, dt: float) -> float:
        if self.prev_pose is None:
            return 0.0
        dt = max(dt, EPS)
        d = np.linalg.norm(pose - self.prev_pose, axis=1)
        return float(np.mean(d) / dt)

    def _drag(self, load: float) -> float:
        # capacity is a tunable system limit.
        return float(max(0.0, load / max(self.capacity, EPS) - 1.0))

    def _selection_speed(
        self,
        n_eff: float,
        viscosity: float,
        drag: float,
        drive: float = 1.0,
    ) -> float:
        return float(
            drive
            / max(n_eff, 1.0)
            / (1.0 + viscosity)
            / (1.0 + drag)
        )

    def step(self, pose: np.ndarray, frame: int, t_sec: float, dt: float) -> State:
        viscosity = self._viscosity(pose)
        _, n_eff = self._n_eff(pose)
        update_scope = self._update_scope(pose)

        body_speed = self._body_speed(pose, dt)

        # Here load is a normalized motion demand.
        load = body_speed
        drag = self._drag(load)

        selection_speed = self._selection_speed(
            n_eff=n_eff,
            viscosity=viscosity,
            drag=drag,
        )

        l_knee = angle_deg(
            pose[self.L_HIP], pose[self.L_KNEE], pose[self.L_ANKLE]
        )
        r_knee = angle_deg(
            pose[self.R_HIP], pose[self.R_KNEE], pose[self.R_ANKLE]
        )
        l_elbow = angle_deg(
            pose[self.L_SHOULDER], pose[self.L_ELBOW], pose[self.L_WRIST]
        )
        r_elbow = angle_deg(
            pose[self.R_SHOULDER], pose[self.R_ELBOW], pose[self.R_WRIST]
        )

        shoulder_vec = pose[self.R_SHOULDER] - pose[self.L_SHOULDER]
        torso_rotation = float(
            np.degrees(np.arctan2(shoulder_vec[2], shoulder_vec[0]))
        )

        state = State(
            frame=frame,
            time_sec=t_sec,
            viscosity=viscosity,
            effective_candidates=n_eff,
            update_scope=update_scope,
            drag=drag,
            selection_speed=selection_speed,
            body_speed=body_speed,
            left_knee_angle=l_knee,
            right_knee_angle=r_knee,
            left_elbow_angle=l_elbow,
            right_elbow_angle=r_elbow,
            torso_rotation=torso_rotation,
        )

        self.prev_pose = pose.copy()
        return state


# ============================================================
# Input sources
# ============================================================

def open_video_source(source: str, camera_index: int):
    if source == "camera":
        cap = cv2.VideoCapture(camera_index)
        label = f"camera:{camera_index}"
    else:
        cap = cv2.VideoCapture(source)
        label = source

    if not cap.isOpened():
        raise RuntimeError(f"入力を開けませんでした: {label}")

    return cap


def run_video_or_camera(
    source: str,
    camera_index: int,
    output_csv: Path,
):
    cap = open_video_source(source, camera_index)
    extractor = PoseExtractor()
    observer = GBMObserver()

    rows: List[Dict] = []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 1e-3 or math.isnan(fps):
        fps = 30.0

    frame_i = 0
    prev_time = None

    print("ESC または q で終了します。")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if source == "camera":
                now = time.perf_counter()
                if prev_time is None:
                    dt = 1.0 / fps
                else:
                    dt = now - prev_time
                prev_time = now
                t_sec = frame_i * dt if frame_i == 0 else rows[-1]["time_sec"] + dt if rows else 0.0
            else:
                t_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                dt = 1.0 / fps

            pose, result = extractor.process(frame)

            if pose is not None:
                s = observer.step(
                    pose=pose,
                    frame=frame_i,
                    t_sec=t_sec,
                    dt=dt,
                )
                row = asdict(s)
                rows.append(row)

                text = (
                    f"nu={s.viscosity:.2f} "
                    f"N_eff={s.effective_candidates:.2f} "
                    f"Omega={s.update_scope:.2f} "
                    f"drag={s.drag:.2f} "
                    f"speed={s.selection_speed:.3f}"
                )
                cv2.putText(
                    frame, text, (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (255, 255, 255), 2, cv2.LINE_AA
                )

                mp.solutions.drawing_utils.draw_landmarks(
                    frame,
                    result.pose_landmarks,
                    mp.solutions.pose.POSE_CONNECTIONS,
                )
            else:
                cv2.putText(
                    frame, "Pose not detected", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (255, 255, 255), 2, cv2.LINE_AA
                )

            cv2.imshow("GBMCCQSD Capture", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break

            frame_i += 1

    finally:
        cap.release()
        extractor.close()
        cv2.destroyAllWindows()

    if rows:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"CSV saved: {output_csv}")
    else:
        print("有効なPoseが取れなかったためCSVは作成しませんでした。")


# ============================================================
# OptiTrack CSV adapter
# ============================================================

def run_optitrack_csv(csv_path: Path):
    """
    OptiTrack/Motive export CSV support is schema-dependent.

    This function currently inspects the file header only.
    Once the lab's actual Motive CSV column layout is known,
    map marker / rigid-body / skeleton columns here and feed them
    into the same GBMObserver-style 4-axis layer.
    """
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    print(f"OptiTrack CSV: {csv_path}")
    print("")
    print("OptiTrack は MediaPipe より高精度な3D計測系として別入力にできます。")
    print("ただし Motive の export 形式（Skeleton / Rigid Body / Marker、列名）が必要です。")
    print("研究室で実際に出力したCSVを1個使えば、この adapter を確定できます。")
    print("")
    print("先頭10行:")
    with csv_path.open("r", encoding="utf-8-sig", errors="replace") as f:
        for i, line in enumerate(f):
            print(line.rstrip())
            if i >= 9:
                break


# ============================================================
# Interactive launcher
# ============================================================

def interactive():
    print("")
    print("GBMCCQSD Capture v0.2")
    print("=====================")
    print("1: 動画ファイル")
    print("2: カメラ")
    print("3: OptiTrack CSV")
    mode = input("入力方式 > ").strip()

    if mode == "1":
        video = input("動画パス > ").strip().strip('"')
        out = input("出力CSV [gbmccqsd_capture.csv] > ").strip()
        out = out or "gbmccqsd_capture.csv"
        run_video_or_camera(video, 0, Path(out))

    elif mode == "2":
        idx = input("カメラ番号 [0] > ").strip()
        idx = int(idx) if idx else 0
        out = input("出力CSV [gbmccqsd_camera.csv] > ").strip()
        out = out or "gbmccqsd_camera.csv"
        run_video_or_camera("camera", idx, Path(out))

    elif mode == "3":
        path = input("OptiTrack CSVパス > ").strip().strip('"')
        run_optitrack_csv(Path(path))

    else:
        print("1 / 2 / 3 を選んでください。")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, help="動画ファイルへのパス")
    parser.add_argument("--camera", type=int, help="カメラindex (例: 0)")
    parser.add_argument("--optitrack-csv", type=str, help="Motive export CSV")
    parser.add_argument("--output", type=str, default="gbmccqsd_capture.csv")
    args = parser.parse_args()

    if args.video:
        run_video_or_camera(args.video, 0, Path(args.output))
    elif args.camera is not None:
        run_video_or_camera("camera", args.camera, Path(args.output))
    elif args.optitrack_csv:
        run_optitrack_csv(Path(args.optitrack_csv))
    else:
        interactive()


if __name__ == "__main__":
    main()
