"""
GBMCCQSD Capture v0.7 - Timestamp 30ms Reference
===========================================

Modes:
1) Video file
2) Camera capture
3) OptiTrack

Video mode:
- basic
- detailed

Camera mode:
- real-time MediaPipe Pose Landmarker
- live overlay
- CSV recording

OptiTrack mode:
- Motive CSV inspection
- Live NatNet placeholder

This version uses the modern MediaPipe Tasks API (PoseLandmarker),
not the removed classic mp.solutions.pose API.

IMPORTANT
---------
The GBMCCQSD four-axis formulas in this program are experimental hypotheses,
not validated scientific laws.
"""

from __future__ import annotations

import argparse
import csv
import math
import time
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from collections import deque

import cv2
import numpy as np

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
except Exception as e:
    raise SystemExit(
        "\nMediaPipe Tasks API を読み込めませんでした。\n"
        "現在の環境で次を確認してください:\n"
        "  python -c \"import mediapipe as mp; print(mp.__version__); print(mp.__file__)\"\n\n"
        "必要なら:\n"
        "  python -m pip install --upgrade mediapipe opencv-python numpy\n"
    ) from e


EPS = 1e-12

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_full/float16/1/"
    "pose_landmarker_full.task"
)

DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parent
    / "pose_landmarker_full.task"
)

# MediaPipe Pose 33 landmarks connection pairs.
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12),
    (11, 13), (13, 15),
    (15, 17), (15, 19), (15, 21),
    (17, 19),
    (12, 14), (14, 16),
    (16, 18), (16, 20), (16, 22),
    (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27),
    (27, 29), (29, 31), (27, 31),
    (24, 26), (26, 28),
    (28, 30), (30, 32), (28, 32),
]


# ============================================================
# Model handling
# ============================================================

def ensure_model(model_path: Path) -> Path:
    if model_path.exists():
        return model_path

    print("")
    print("Pose Landmarker model が見つかりません。")
    print(f"保存先: {model_path}")
    print("公式モデルをダウンロードします...")

    try:
        model_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        urllib.request.urlretrieve(
            MODEL_URL,
            model_path,
        )

    except Exception as e:
        raise RuntimeError(
            "\nモデルの自動ダウンロードに失敗しました。\n"
            "手動で pose_landmarker_full.task を "
            "このPythonファイルと同じフォルダに置いてください。\n"
            f"保存先: {model_path}\n"
            f"URL: {MODEL_URL}\n"
        ) from e

    print("モデルをダウンロードしました。")
    return model_path


# ============================================================
# Basic math
# ============================================================

def angle_deg(
    a: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
) -> float:
    ba = a - b
    bc = c - b

    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)

    if nba < EPS or nbc < EPS:
        return 0.0

    cosv = np.dot(ba, bc) / (nba * nbc)
    cosv = np.clip(cosv, -1.0, 1.0)

    return float(
        np.degrees(
            np.arccos(cosv)
        )
    )


def entropy_effective_count(
    p: Sequence[float],
) -> Tuple[float, float]:
    p = np.asarray(
        p,
        dtype=float,
    )

    p = np.clip(
        p,
        EPS,
        None,
    )

    p = p / np.sum(p)

    h = float(
        -np.sum(
            p * np.log(p)
        )
    )

    return (
        h,
        float(np.exp(h)),
    )


def cosine_similarity(
    a: np.ndarray,
    b: np.ndarray,
) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)

    if na < EPS or nb < EPS:
        return 0.0

    return float(
        np.clip(
            np.dot(a, b)
            / (na * nb),
            -1.0,
            1.0,
        )
    )


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

    body_speed: float = 0.0
    left_knee_angle: float = 0.0
    right_knee_angle: float = 0.0
    left_elbow_angle: float = 0.0
    right_elbow_angle: float = 0.0
    torso_rotation: float = 0.0

    # binary state representation
    binary_state: str = "0000"
    state_id: int = 0
    hex_state: str = "0x0"

    # timestamp-based 30 ms reference diagnostics
    reference_time_sec: float = -1.0
    reference_delta_sec: float = 0.0


# ============================================================
# MediaPipe Tasks Pose Landmarker
# ============================================================

class PoseExtractor:
    def __init__(
        self,
        model_path: Path,
        running_mode,
    ):
        base_options = mp_python.BaseOptions(
            model_asset_path=str(model_path)
        )

        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=running_mode,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )

        self.landmarker = (
            vision.PoseLandmarker.create_from_options(
                options
            )
        )

        self.running_mode = running_mode

    def process(
        self,
        frame_bgr,
        timestamp_ms: int,
    ):
        rgb = cv2.cvtColor(
            frame_bgr,
            cv2.COLOR_BGR2RGB,
        )

        rgb = np.ascontiguousarray(rgb)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb,
        )

        # We use VIDEO mode for both file video and camera.
        # It is synchronous and simpler for logging/CSV alignment.
        result = self.landmarker.detect_for_video(
            mp_image,
            timestamp_ms,
        )

        if (
            result is None
            or not result.pose_landmarks
            or len(result.pose_landmarks) == 0
        ):
            return None, None

        landmarks = result.pose_landmarks[0]

        pts = np.array(
            [
                [lm.x, lm.y, lm.z]
                for lm in landmarks
            ],
            dtype=float,
        )

        return pts, landmarks

    def close(self):
        self.landmarker.close()


# ============================================================
# Drawing
# ============================================================

def draw_pose(
    frame,
    landmarks,
):
    if landmarks is None:
        return

    h, w = frame.shape[:2]

    xy = []

    for lm in landmarks:
        x = int(lm.x * w)
        y = int(lm.y * h)
        xy.append((x, y))

    for a, b in POSE_CONNECTIONS:
        if (
            a < len(xy)
            and b < len(xy)
        ):
            cv2.line(
                frame,
                xy[a],
                xy[b],
                (220, 220, 220),
                2,
                cv2.LINE_AA,
            )

    for x, y in xy:
        cv2.circle(
            frame,
            (x, y),
            3,
            (255, 255, 255),
            -1,
            cv2.LINE_AA,
        )


# ============================================================
# GBMCCQSD observer
# ============================================================

class GBMObserver:
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
        detailed: bool = False,
        viscosity_alpha: float = 0.25,
        change_threshold: float = 0.02,
        capacity: float = 0.08,
    ):
        self.prev_pose: Optional[np.ndarray] = None
        self.pose_streak = 0

        self.detailed = detailed
        self.viscosity_alpha = viscosity_alpha
        self.change_threshold = change_threshold
        self.capacity = capacity

        # Timestamp-based reference settings
        # Compare every state against approximately 30 ms earlier.
        self.reference_window_sec = 0.030
        self.history = deque(maxlen=600)

    def _pose_vector(
        self,
        p: np.ndarray,
    ) -> np.ndarray:
        hip_mid = (
            p[self.L_HIP]
            + p[self.R_HIP]
        ) / 2.0

        q = p - hip_mid

        shoulder_width = np.linalg.norm(
            p[self.L_SHOULDER]
            - p[self.R_SHOULDER]
        )

        shoulder_width = max(
            shoulder_width,
            EPS,
        )

        q = q / shoulder_width
        return q.flatten()

    def _viscosity(
        self,
        pose: np.ndarray,
        t_sec: float,
    ) -> float:
        """
        Timestamp-based viscosity:
        compare current normalized pose to ~30 ms earlier.
        High similarity over 30 ms -> high viscosity.
        """
        ref_pose, _, _ = self._delta_from_reference(pose, t_sec)

        if ref_pose is None:
            return 0.0

        cur = self._pose_vector(pose)
        prv = self._pose_vector(ref_pose)

        sim = max(
            0.0,
            cosine_similarity(cur, prv),
        )

        # Direct 30 ms local similarity, mapped to [0,1].
        return float(np.clip(sim, 0.0, 1.0))

    def _region_activity(
        self,
        pose: np.ndarray,
        t_sec: float,
    ) -> np.ndarray:
        ref_pose, _, _ = self._delta_from_reference(pose, t_sec)

        if ref_pose is None:
            return np.ones(
                5,
                dtype=float,
            )

        d = np.linalg.norm(
            pose - ref_pose,
            axis=1,
        )

        regions = [
            [
                self.L_SHOULDER,
                self.L_ELBOW,
                self.L_WRIST,
            ],
            [
                self.R_SHOULDER,
                self.R_ELBOW,
                self.R_WRIST,
            ],
            [
                self.L_HIP,
                self.L_KNEE,
                self.L_ANKLE,
            ],
            [
                self.R_HIP,
                self.R_KNEE,
                self.R_ANKLE,
            ],
            [
                self.L_SHOULDER,
                self.R_SHOULDER,
                self.L_HIP,
                self.R_HIP,
            ],
        ]

        return (
            np.array(
                [
                    np.mean(d[idx])
                    for idx in regions
                ],
                dtype=float,
            )
            + EPS
        )

    def _n_eff(
        self,
        pose: np.ndarray,
        t_sec: float,
    ) -> float:
        activity = self._region_activity(
            pose,
            t_sec,
        )

        p = (
            activity
            / np.sum(activity)
        )

        _, n_eff = (
            entropy_effective_count(p)
        )

        return n_eff

    def _update_scope(
        self,
        pose: np.ndarray,
        t_sec: float,
    ) -> float:
        ref_pose, _, _ = self._delta_from_reference(pose, t_sec)

        if ref_pose is None:
            return 0.0

        d = np.linalg.norm(
            pose - ref_pose,
            axis=1,
        )

        return float(
            np.mean(
                d >= self.change_threshold
            )
        )

    def _body_speed(
        self,
        pose: np.ndarray,
        t_sec: float,
    ) -> float:
        ref_pose, _, actual_dt = self._delta_from_reference(pose, t_sec)

        if ref_pose is None:
            return 0.0

        d = np.linalg.norm(
            pose - ref_pose,
            axis=1,
        )

        return float(
            np.mean(d)
            / max(actual_dt, EPS)
        )

    def _drag(
        self,
        load: float,
    ) -> float:
        return float(
            max(
                0.0,
                load
                / max(
                    self.capacity,
                    EPS,
                )
                - 1.0,
            )
        )

    def _selection_speed(
        self,
        n_eff: float,
        viscosity: float,
        drag: float,
        drive: float = 1.0,
    ) -> float:
        return float(
            drive
            / max(
                n_eff,
                1.0,
            )
            / (
                1.0
                + viscosity
            )
            / (
                1.0
                + drag
            )
        )

    def step(
        self,
        pose: np.ndarray,
        frame: int,
        t_sec: float,
        dt: float,
    ) -> State:
        viscosity = (
            self._viscosity(
                pose,
                t_sec,
            )
        )

        n_eff = (
            self._n_eff(
                pose,
                t_sec,
            )
        )

        update_scope = (
            self._update_scope(
                pose,
                t_sec,
            )
        )

        body_speed = (
            self._body_speed(
                pose,
                t_sec,
            )
        )

        drag = (
            self._drag(
                body_speed
            )
        )

        selection_speed = (
            self._selection_speed(
                n_eff=n_eff,
                viscosity=viscosity,
                drag=drag,
            )
        )

        state = State(
            frame=frame,
            time_sec=t_sec,
            viscosity=viscosity,
            effective_candidates=n_eff,
            update_scope=update_scope,
            drag=drag,
            selection_speed=selection_speed,
        )

        if self.detailed:
            state.body_speed = (
                body_speed
            )

            state.left_knee_angle = (
                angle_deg(
                    pose[self.L_HIP],
                    pose[self.L_KNEE],
                    pose[self.L_ANKLE],
                )
            )

            state.right_knee_angle = (
                angle_deg(
                    pose[self.R_HIP],
                    pose[self.R_KNEE],
                    pose[self.R_ANKLE],
                )
            )

            state.left_elbow_angle = (
                angle_deg(
                    pose[self.L_SHOULDER],
                    pose[self.L_ELBOW],
                    pose[self.L_WRIST],
                )
            )

            state.right_elbow_angle = (
                angle_deg(
                    pose[self.R_SHOULDER],
                    pose[self.R_ELBOW],
                    pose[self.R_WRIST],
                )
            )

            shoulder_vec = (
                pose[self.R_SHOULDER]
                - pose[self.L_SHOULDER]
            )

            state.torso_rotation = float(
                np.degrees(
                    np.arctan2(
                        shoulder_vec[2],
                        shoulder_vec[0],
                    )
                )
            )

        (
            state.binary_state,
            state.state_id,
            state.hex_state,
        ) = encode_binary_state(
            viscosity=state.viscosity,
            effective_candidates=state.effective_candidates,
            update_scope=state.update_scope,
            drag=state.drag,
        )

        ref_t, _ = self._reference_pose(t_sec)
        if ref_t is not None:
            state.reference_time_sec = float(ref_t)
            state.reference_delta_sec = float(t_sec - ref_t)

        # Keep timestamped pose history for the next 30 ms comparison.
        self.history.append(
            (
                float(t_sec),
                pose.copy(),
            )
        )

        self.prev_pose = (
            pose.copy()
        )

        return state



# ============================================================
# Binary-state encoding
# ============================================================

def encode_binary_state(
    viscosity: float,
    effective_candidates: float,
    update_scope: float,
    drag: float,
    *,
    viscosity_threshold: float = 0.50,
    candidate_threshold: float = 2.50,
    update_scope_threshold: float = 0.40,
    drag_threshold: float = 0.30,
) -> Tuple[str, int, str]:
    """
    4-bit state:

        bit3 = viscosity
        bit2 = effective candidate amount
        bit1 = update scope
        bit0 = drag

    Example:
        1010
        = viscosity high
        = candidate amount low
        = update scope high
        = drag low

    Thresholds are experimental and easy to change.
    """

    bits = [
        int(viscosity >= viscosity_threshold),
        int(effective_candidates >= candidate_threshold),
        int(update_scope >= update_scope_threshold),
        int(drag >= drag_threshold),
    ]

    binary_state = "".join(str(b) for b in bits)
    state_id = int(binary_state, 2)
    hex_state = hex(state_id)

    return binary_state, state_id, hex_state


def write_binary_file(
    rows: List[Dict],
    output_bin: Path,
):
    """
    Store one state per byte.

    Only the low 4 bits are currently used:
        0000 ... 1111  ->  0 ... 15
    """
    if not rows:
        return

    output_bin.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = bytes(
        int(row["state_id"]) & 0x0F
        for row in rows
    )

    output_bin.write_bytes(payload)

    print(
        f"BIN saved: {output_bin}"
    )


# ============================================================
# CSV + display helpers
# ============================================================

def state_to_row(
    s: State,
    detailed: bool,
) -> Dict:
    row = asdict(s)

    if detailed:
        return row

    return {
        "frame":
            row["frame"],
        "time_sec":
            row["time_sec"],
        "viscosity":
            row["viscosity"],
        "effective_candidates":
            row["effective_candidates"],
        "update_scope":
            row["update_scope"],
        "drag":
            row["drag"],
        "selection_speed":
            row["selection_speed"],
        "binary_state":
            row["binary_state"],
        "state_id":
            row["state_id"],
        "hex_state":
            row["hex_state"],
        "reference_time_sec":
            row["reference_time_sec"],
        "reference_delta_sec":
            row["reference_delta_sec"],
    }


def save_rows(
    rows: List[Dict],
    output_csv: Path,
):
    if not rows:
        print(
            "有効なPoseが取れませんでした。"
        )
        return

    output_csv.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_csv.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(rows)

    print(
        f"CSV saved: {output_csv}"
    )


def draw_overlay(
    frame,
    state: State,
):
    text = (
        f"nu={state.viscosity:.2f} "
        f"N_eff={state.effective_candidates:.2f} "
        f"Omega={state.update_scope:.2f} "
        f"drag={state.drag:.2f} "
        f"speed={state.selection_speed:.3f} "
        f"bin={state.binary_state}"
    )

    cv2.putText(
        frame,
        text,
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.60,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


# ============================================================
# Video detail menu
# ============================================================

def ask_video_detail() -> bool:
    print("")
    print(
        "動画解析の詳細度を選んでください。"
    )

    print("1: 簡易解析")
    print(
        "   nu / N_eff / Omega "
        "/ drag / selection_speed"
    )

    print("")
    print("2: 詳細解析")
    print(
        "   4軸 + body_speed "
        "/ knee / elbow / torso_rotation"
    )
    print("")

    while True:
        choice = input(
            "詳細度 > "
        ).strip()

        if choice == "1":
            return False

        if choice == "2":
            return True

        print(
            "1 または 2 を入力してください。"
        )


# ============================================================
# Video mode
# ============================================================

def run_video(
    video_path: str,
    output_csv: Path,
    detailed: bool,
    model_path: Path,
):
    cap = cv2.VideoCapture(
        video_path
    )

    if not cap.isOpened():
        raise RuntimeError(
            f"動画を開けませんでした: {video_path}"
        )

    extractor = PoseExtractor(
        model_path=model_path,
        running_mode=vision.RunningMode.VIDEO,
    )

    observer = GBMObserver(
        detailed=detailed
    )

    rows: List[Dict] = []

    frame_i = 0
    last_timestamp_ms = -1
    last_t_sec = None

    print("")
    print(
        "解析モード:",
        "詳細"
        if detailed
        else "簡易",
    )
    print(
        "ESC または q で途中終了できます。"
    )
    print("")

    try:
        while True:
            ok, frame = cap.read()

            if not ok:
                break

            # Use the video's own timestamp instead of FPS.
            t_sec = (
                cap.get(
                    cv2.CAP_PROP_POS_MSEC
                )
                / 1000.0
            )

            if last_t_sec is None:
                dt = 0.0
            else:
                dt = max(
                    t_sec - last_t_sec,
                    EPS,
                )

            last_t_sec = t_sec

            timestamp_ms = int(
                round(
                    t_sec
                    * 1000.0
                )
            )

            # Tasks VIDEO mode requires monotonically increasing timestamps.
            if (
                timestamp_ms
                <= last_timestamp_ms
            ):
                timestamp_ms = (
                    last_timestamp_ms
                    + 1
                )

            last_timestamp_ms = (
                timestamp_ms
            )

            pose, landmarks = (
                extractor.process(
                    frame,
                    timestamp_ms,
                )
            )

            if pose is not None:
                s = observer.step(
                    pose=pose,
                    frame=frame_i,
                    t_sec=t_sec,
                    dt=dt,
                )

                rows.append(
                    state_to_row(
                        s,
                        detailed,
                    )
                )

                draw_pose(
                    frame,
                    landmarks,
                )

                draw_overlay(
                    frame,
                    s,
                )

            else:
                cv2.putText(
                    frame,
                    "Pose not detected",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

            cv2.imshow(
                "GBMCCQSD Video",
                frame,
            )

            key = (
                cv2.waitKey(1)
                & 0xFF
            )

            if key in (
                27,
                ord("q"),
            ):
                break

            frame_i += 1

    finally:
        cap.release()
        extractor.close()
        cv2.destroyAllWindows()

    save_rows(
        rows,
        output_csv,
    )

    write_binary_file(
        rows,
        output_csv.with_suffix(".bin"),
    )


# ============================================================
# Camera mode
# ============================================================

def run_camera(
    camera_index: int,
    output_csv: Path,
    model_path: Path,
    detailed: bool = True,
):
    cap = cv2.VideoCapture(
        camera_index
    )

    if not cap.isOpened():
        raise RuntimeError(
            f"カメラを開けませんでした: {camera_index}"
        )

    extractor = PoseExtractor(
        model_path=model_path,
        running_mode=vision.RunningMode.VIDEO,
    )

    observer = GBMObserver(
        detailed=detailed
    )

    rows: List[Dict] = []

    frame_i = 0
    start_time = (
        time.perf_counter()
    )
    prev_time = (
        start_time
    )
    last_timestamp_ms = -1

    print("")
    print(
        f"Camera {camera_index} を開始しました。"
    )
    print(
        "ESC または q で撮影終了します。"
    )
    print("")

    try:
        while True:
            ok, frame = cap.read()

            if not ok:
                break

            now = (
                time.perf_counter()
            )

            dt = max(
                now - prev_time,
                EPS,
            )

            prev_time = now

            t_sec = (
                now - start_time
            )

            timestamp_ms = int(
                round(
                    t_sec
                    * 1000.0
                )
            )

            if (
                timestamp_ms
                <= last_timestamp_ms
            ):
                timestamp_ms = (
                    last_timestamp_ms
                    + 1
                )

            last_timestamp_ms = (
                timestamp_ms
            )

            pose, landmarks = (
                extractor.process(
                    frame,
                    timestamp_ms,
                )
            )

            if pose is not None:
                s = observer.step(
                    pose=pose,
                    frame=frame_i,
                    t_sec=t_sec,
                    dt=dt,
                )

                rows.append(
                    state_to_row(
                        s,
                        detailed,
                    )
                )

                draw_pose(
                    frame,
                    landmarks,
                )

                draw_overlay(
                    frame,
                    s,
                )

            else:
                cv2.putText(
                    frame,
                    "Pose not detected",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

            cv2.imshow(
                "GBMCCQSD Camera",
                frame,
            )

            key = (
                cv2.waitKey(1)
                & 0xFF
            )

            if key in (
                27,
                ord("q"),
            ):
                break

            frame_i += 1

    finally:
        cap.release()
        extractor.close()
        cv2.destroyAllWindows()

    save_rows(
        rows,
        output_csv,
    )

    write_binary_file(
        rows,
        output_csv.with_suffix(".bin"),
    )


# ============================================================
# OptiTrack mode
# ============================================================

def run_optitrack_csv(
    csv_path: Path,
):
    if not csv_path.exists():
        raise FileNotFoundError(
            csv_path
        )

    print("")
    print(
        f"OptiTrack CSV: {csv_path}"
    )
    print("")
    print(
        "現段階では Motive CSV の"
        "構造確認モードです。"
    )
    print(
        "実際のCSVを1つ確認後、"
        "4軸adapterを確定できます。"
    )
    print("")
    print("先頭10行:")

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
    ) as f:
        for i, line in enumerate(f):
            print(
                line.rstrip()
            )

            if i >= 9:
                break


def optitrack_menu():
    print("")
    print("OptiTrack")
    print("=========")
    print(
        "1: Motive CSVを読む"
    )
    print(
        "2: Live NatNet [今後実装]"
    )
    print("")

    choice = input(
        "OptiTrack入力 > "
    ).strip()

    if choice == "1":
        path = input(
            "Motive CSVパス > "
        ).strip().strip('"')

        run_optitrack_csv(
            Path(path)
        )

    elif choice == "2":
        print("")
        print(
            "Live NatNetは研究室PCの"
            "Motive/NatNet設定が分かれば追加できます。"
        )

    else:
        print(
            "1 または 2 を選んでください。"
        )


# ============================================================
# Interactive launcher
# ============================================================

def interactive(
    model_path: Path,
):
    print("")
    print(
        "GBMCCQSD Capture v0.7"
    )
    print(
        "MediaPipe Tasks API / PoseLandmarker"
    )
    print(
        "※ .task は内部モデルです。開く必要はありません。"
    )
    print(
        "※ 解析基準はFPSではなく timestamp の約30 ms前です。"
    )
    print(
        "===================================="
    )
    print("1: 動画ファイル")
    print("2: カメラ撮影")
    print("3: OptiTrack")
    print("")

    mode = input(
        "入力方式 > "
    ).strip()

    if mode == "1":
        video = input(
            "動画パス > "
        ).strip().strip('"')

        detailed = (
            ask_video_detail()
        )

        default_name = (
            "gbmccqsd_video_detailed.csv"
            if detailed
            else
            "gbmccqsd_video_basic.csv"
        )

        out = input(
            f"出力CSV [{default_name}] > "
        ).strip()

        out = (
            out
            or default_name
        )

        run_video(
            video_path=video,
            output_csv=Path(out),
            detailed=detailed,
            model_path=model_path,
        )

    elif mode == "2":
        idx_text = input(
            "カメラ番号 [0] > "
        ).strip()

        camera_index = (
            int(idx_text)
            if idx_text
            else 0
        )

        out = input(
            "出力CSV "
            "[gbmccqsd_camera.csv] > "
        ).strip()

        out = (
            out
            or "gbmccqsd_camera.csv"
        )

        print("")
        print(
            "カメラ撮影は詳細モードで記録します。"
        )

        run_camera(
            camera_index=camera_index,
            output_csv=Path(out),
            model_path=model_path,
            detailed=True,
        )

    elif mode == "3":
        optitrack_menu()

    else:
        print(
            "1 / 2 / 3 を選んでください。"
        )


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--video",
        type=str,
        help="動画ファイルへのパス",
    )

    parser.add_argument(
        "--detail",
        choices=[
            "basic",
            "detailed",
        ],
        help="動画解析の詳細度",
    )

    parser.add_argument(
        "--camera",
        type=int,
        help="カメラindex (例: 0)",
    )

    parser.add_argument(
        "--optitrack-csv",
        type=str,
        help="Motive export CSV",
    )

    parser.add_argument(
        "--model",
        type=str,
        help="pose_landmarker_full.task のパス",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="gbmccqsd_output.csv",
    )

    args = parser.parse_args()

    requested_model = (
        Path(args.model)
        if args.model
        else DEFAULT_MODEL_PATH
    )

    model_path = (
        ensure_model(
            requested_model
        )
    )

    if args.video:
        if args.detail is None:
            detailed = (
                ask_video_detail()
            )
        else:
            detailed = (
                args.detail
                == "detailed"
            )

        run_video(
            video_path=args.video,
            output_csv=Path(args.output),
            detailed=detailed,
            model_path=model_path,
        )

    elif args.camera is not None:
        run_camera(
            camera_index=args.camera,
            output_csv=Path(args.output),
            model_path=model_path,
            detailed=True,
        )

    elif args.optitrack_csv:
        run_optitrack_csv(
            Path(
                args.optitrack_csv
            )
        )

    else:
        interactive(
            model_path=model_path
        )


if __name__ == "__main__":
    main()
