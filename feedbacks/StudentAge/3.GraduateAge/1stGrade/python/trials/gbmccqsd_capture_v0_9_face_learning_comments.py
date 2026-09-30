"""
GBMCCQSD Capture v0.9
=====================

全面見直し版。

入力:
  1) 動画ファイル
  2) カメラ撮影
  3) OptiTrack

主な設計:
- MediaPipe Tasks API / PoseLandmarker
- FPSを解析基準にしない
- timestamp の t - 0.030 s を基準姿勢として補間
- 4軸:
    viscosity              : 30 msでどれだけ姿勢を維持したか
    effective_candidates   : 身体5領域の活動分布entropyから作る proxy
    update_scope           : 30 msで有意に更新されたlandmark割合
    drag                   : 速度変化量から作る bounded proxy (0..1)
- selection_speed は上記から作る実験的な派生量
- CSV + 4bit state + .bin
- .task は内部モデル。ユーザーが開く必要はない

注意:
この4軸の数式は研究用の仮説実装であり、確立された科学法則ではありません。

--- 学習用コメントの読み方 ---
この版では「なぜこの処理が必要か」を一言で追えるように、
  # Pythonの仕様: ...
  # OpenCVの仕様: ...
  # MediaPipeの仕様: ...
  # この研究の仕様: ...
の形でコメントを追加しています。
まずコメントだけ追い、細かい構文は後から見る想定です。
"""

# Pythonの仕様: 型ヒントを後から評価できるようにして、型名の扱いを楽にする。
from __future__ import annotations

# Python標準ライブラリの仕様: コマンドライン引数を受け取るための道具。
import argparse
# Python標準ライブラリの仕様: CSVを書き出すための道具。
import csv
import math
import os
# Python標準ライブラリの仕様: カメラ実行時の経過時間を測るための道具。
import time
import urllib.request
# Pythonの仕様: dequeは古い履歴を自動で捨てながら時系列を保持しやすい入れ物。
from collections import deque
# Pythonの仕様: dataclassは「状態データをまとめる箱」を少ない記述で作れる。
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# NumPyの仕様: 座標・ベクトル・平均との差分などをまとめて高速計算する。
import numpy as np


EPS = 1e-12
# この研究の仕様: 「変化」は現在と30ms前を比較して測る。
REFERENCE_WINDOW_SEC = 0.030

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_full/float16/1/"
    "pose_landmarker_full.task"
)
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "pose_landmarker_full.task"
FACE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/"
    "face_landmarker.task"
)
DEFAULT_FACE_MODEL_PATH = Path(__file__).resolve().parent / "face_landmarker.task"


# MediaPipe Pose 33 landmarks
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
# Lazy runtime imports
# ============================================================

# 設計上の仕様: 動画/カメラを使う時だけOpenCVとMediaPipeを読み込む。
def load_runtime():
    """
    MediaPipe / OpenCV は動画・カメラ利用時だけ読み込む。
    OptiTrack CSV確認や --self-test では不要。
    """
    # Pythonの仕様: tryは「失敗する可能性がある処理」を安全に試す。
    try:
        import cv2
    except Exception as e:
        raise RuntimeError(
            "OpenCVを読み込めません。\n"
            "python -m pip install --upgrade opencv-python"
        ) from e

    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except Exception as e:
        raise RuntimeError(
            "MediaPipe Tasks APIを読み込めません。\n"
            "確認:\n"
            'python -c "import mediapipe as mp; '
            'print(mp.__version__); print(mp.__file__)"\n'
            "必要なら:\n"
            "python -m pip install --upgrade mediapipe"
        ) from e

    return cv2, mp, mp_python, vision


# ============================================================
# Model file
# ============================================================

# MediaPipeの仕様: 推論には.taskモデルが必要なので、無ければ取得する。
def ensure_model(model_path: Path, url: str = MODEL_URL, label: str = "Pose Landmarker") -> Path:
    """
    .task は MediaPipe が内部で読むモデルファイル。
    ユーザーが開くものではない。
    """
    if model_path.exists() and model_path.stat().st_size > 100_000:
        return model_path

    if model_path.exists():
        print("既存の.taskが小さすぎるため再取得します。")
        try:
            model_path.unlink()
        except OSError:
            pass

    print("")
    print("Pose Landmarkerモデルを初回取得します。")
    print(f"保存先: {model_path}")
    print("※ .task は内部用なので、開く必要はありません。")

    try:
        model_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, model_path)
    except Exception as e:
        raise RuntimeError(
            "Pose Landmarkerモデルの取得に失敗しました。\n"
            "ネット接続を確認するか、pose_landmarker_full.task を\n"
            f"次の場所へ置いてください:\n{model_path}"
        ) from e

    if not model_path.exists() or model_path.stat().st_size <= 100_000:
        raise RuntimeError("モデルファイルの取得結果が不正です。")

    return model_path


# ============================================================
# Math
# ============================================================

def angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba = a - b
    bc = c - b
    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)

    if nba < EPS or nbc < EPS:
        return 0.0

    cosv = np.dot(ba, bc) / (nba * nbc)
    cosv = np.clip(cosv, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosv)))


def entropy_effective_count(values: Sequence[float]) -> Tuple[float, float]:
    p = np.asarray(values, dtype=float)
    p = np.clip(p, EPS, None)
    p = p / np.sum(p)

    h = float(-np.sum(p * np.log(p)))
    return h, float(np.exp(h))


# ============================================================
# Output state
# ============================================================

# Pythonの仕様: 1フレーム分の解析結果をStateという1つの箱にまとめる。
@dataclass
class State:
    frame: int
    time_sec: float

    reference_ready: int
    reference_time_sec: float
    reference_delta_sec: float

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

    face_detected: int = 0
    face_motion: float = 0.0
    face_update_scope: float = 0.0

    binary_state: str = "0000"
    state_id: int = 0
    hex_state: str = "0x0"


# ============================================================
# 4-bit encoding
# ============================================================

# この研究の仕様: 4つの連続値を高/低の4bitに落として16状態にする。
def encode_binary_state(
    viscosity: float,
    effective_candidates: float,
    update_scope: float,
    drag: float,
    *,
    reference_ready: bool,
    viscosity_threshold: float = 0.50,
    candidate_threshold: float = 2.50,
    update_scope_threshold: float = 0.40,
    drag_threshold: float = 0.30,
) -> Tuple[str, int, str]:
    """
    bit3: viscosity
    bit2: effective_candidates
    bit1: update_scope
    bit0: drag

    warm-up中(reference_ready=False)は 0000。
    """
    # この研究の仕様: 30ms前がまだ無いwarm-up中は状態判定しない。
    if not reference_ready:
        return "0000", 0, "0x0"

    bits = [
        int(viscosity >= viscosity_threshold),
        int(effective_candidates >= candidate_threshold),
        int(update_scope >= update_scope_threshold),
        int(drag >= drag_threshold),
    ]

    # Pythonの仕様: 0/1のリストを"1101"のような文字列へ連結する。
    binary_state = "".join(str(x) for x in bits)
    state_id = int(binary_state, 2)
    return binary_state, state_id, hex(state_id)


# ============================================================
# Pose observer
# ============================================================

# この研究の仕様: 過去を保持しながら、現在のPoseから状態を計算する本体。
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
        *,
        detailed: bool,
        reference_window_sec: float = REFERENCE_WINDOW_SEC,
        update_threshold: float = 0.035,
        viscosity_scale: float = 0.080,
        drag_scale: float = 2.0,
    ):
        self.detailed = detailed
        self.reference_window_sec = float(reference_window_sec)
        self.update_threshold = float(update_threshold)
        self.viscosity_scale = float(viscosity_scale)
        self.drag_scale = float(drag_scale)

        # Enough for many seconds even at high camera rates.
        # Pythonの仕様: 過去Poseを時刻付きで保存し、30ms前の参照に使う。
        self.history: deque[Tuple[float, np.ndarray]] = deque(maxlen=2400)
        self.face_history: deque[Tuple[float, np.ndarray]] = deque(maxlen=2400)
        self.prev_body_speed: Optional[float] = None
        self.face_update_threshold = 0.010

    # この研究の仕様: 画面位置や体格差より「動きの差」を見たいのでPoseを正規化する。
    def _normalize_pose(self, pose: np.ndarray) -> np.ndarray:
        """
        Camera translation / scale の影響を軽減:
        - hip midpointを原点
        - shoulder widthでscale
        """
        # 幾何の仕様: 左右の腰の中点を身体の基準位置にする。
        hip_mid = (pose[self.L_HIP] + pose[self.R_HIP]) / 2.0
        centered = pose - hip_mid

        shoulder_width = np.linalg.norm(
            pose[self.L_SHOULDER] - pose[self.R_SHOULDER]
        )
        shoulder_width = max(float(shoulder_width), 1e-6)

        # 数学の仕様: 肩幅で割ると身体サイズの違いを小さくできる。
        return centered / shoulder_width

    # この研究の仕様: FPSではなくtimestampから「ちょうど30ms前」のPoseを作る。
    def _reference_pose(
        self,
        current_pose: np.ndarray,
        t_sec: float,
    ) -> Tuple[Optional[float], Optional[np.ndarray]]:
        """
        t - 30ms の姿勢を timestamp 基準で線形補間する。

        FPSは使用しない。
        current_pose を上側の補間点として使えるため、
        低FPSでも target が直前frameとcurrentの間なら補間可能。
        """
        target = float(t_sec) - self.reference_window_sec

        if target < 0 or not self.history:
            return None, None

        # 30ms分の履歴がまだ無ければwarm-up。
        if self.history[0][0] > target:
            return None, None

        prev_t = None
        prev_pose = None

        # target以下で最後のサンプルを探す。
        # Pythonの仕様: forで履歴を古い順に1件ずつ調べる。
        for hist_t, hist_pose in self.history:
            if hist_t <= target:
                prev_t = hist_t
                prev_pose = hist_pose
            else:
                # targetを挟む過去2点が見つかった。
                next_t = hist_t
                next_pose = hist_pose
                if prev_t is None:
                    return None, None

                span = next_t - prev_t
                if span <= EPS:
                    return target, prev_pose.copy()

                alpha = (target - prev_t) / span
                # 数学の仕様: 前後2点の間を線形補間して30ms前の推定Poseを作る。
                interp = prev_pose + alpha * (next_pose - prev_pose)
                return target, interp

        # historyの最後とcurrentでtargetを挟む場合。
        if prev_t is not None and prev_pose is not None:
            next_t = float(t_sec)
            next_pose = current_pose

            if next_t >= target:
                span = next_t - prev_t

                if span <= EPS:
                    return target, prev_pose.copy()

                alpha = (target - prev_t) / span
                alpha = float(np.clip(alpha, 0.0, 1.0))
                interp = prev_pose + alpha * (next_pose - prev_pose)
                return target, interp

        return None, None

    # この研究の仕様: 身体を5領域に分け、どこへ活動が分散したかを見る。
    def _region_activity(
        self,
        current_norm: np.ndarray,
        ref_norm: np.ndarray,
    ) -> np.ndarray:
        displacement = np.linalg.norm(
            current_norm - ref_norm,
            axis=1,
        )

        regions = [
            [self.L_SHOULDER, self.L_ELBOW, self.L_WRIST],
            [self.R_SHOULDER, self.R_ELBOW, self.R_WRIST],
            [self.L_HIP, self.L_KNEE, self.L_ANKLE],
            [self.R_HIP, self.R_KNEE, self.R_ANKLE],
            [self.L_SHOULDER, self.R_SHOULDER, self.L_HIP, self.R_HIP],
        ]

        return np.array(
            [float(np.mean(displacement[idx])) for idx in regions],
            dtype=float,
        ) + EPS

    # この研究の仕様: 顔も位置や顔サイズの影響を減らして「顔の動き」を比較する。
    def _normalize_face(self, face: np.ndarray) -> np.ndarray:
        if face.shape[0] <= 263:
            return face
        left_eye = face[33]
        right_eye = face[263]
        center = (left_eye + right_eye) / 2.0
        scale = max(float(np.linalg.norm(right_eye - left_eye)), 1e-6)
        return (face - center) / scale

    def _face_reference(self, face: np.ndarray, t_sec: float):
        target = float(t_sec) - self.reference_window_sec
        if target < 0 or not self.face_history:
            return None
        if self.face_history[0][0] > target:
            return None
        prev_t = None
        prev_face = None
        for hist_t, hist_face in self.face_history:
            if hist_t <= target:
                prev_t, prev_face = hist_t, hist_face
            else:
                if prev_t is None:
                    return None
                span = hist_t - prev_t
                if span <= EPS:
                    return prev_face.copy()
                a = (target - prev_t) / span
                return prev_face + a * (hist_face - prev_face)
        if prev_t is not None and prev_face is not None:
            span = float(t_sec) - prev_t
            if span <= EPS:
                return prev_face.copy()
            a = float(np.clip((target - prev_t) / span, 0.0, 1.0))
            return prev_face + a * (face - prev_face)
        return None

    def _face_metrics(self, face: Optional[np.ndarray], t_sec: float):
        if face is None:
            return 0, 0.0, 0.0
        ref = self._face_reference(face, t_sec)
        if ref is None or ref.shape != face.shape:
            return 1, 0.0, 0.0
        cur_n = self._normalize_face(face)
        ref_n = self._normalize_face(ref)
        d = np.linalg.norm(cur_n - ref_n, axis=1)
        return 1, float(np.mean(d)), float(np.mean(d >= self.face_update_threshold))

    # この研究の仕様: 1フレーム分のPose/Faceを受け取り、4軸と状態を1回更新する。
    def step(
        self,
        pose: np.ndarray,
        face: Optional[np.ndarray] = None,
        *,
        frame: int,
        t_sec: float,
    ) -> State:
        # MediaPipe Poseの仕様: この実装では33点×xyzの形だけを正しいPoseとして扱う。
        if pose.shape != (33, 3):
            raise ValueError(f"Pose shape must be (33,3), got {pose.shape}")

        face_detected, face_motion, face_update_scope = self._face_metrics(face, t_sec)

        # この研究の仕様: 現在との差を見るため、30ms前の基準Poseを取得する。
        ref_t, ref_pose = self._reference_pose(pose, t_sec)
        ready = ref_pose is not None and ref_t is not None

        # この研究の仕様: 30ms前が無い最初の区間では4軸をまだ計算できない。
        if not ready:
            state = State(
                frame=frame,
                time_sec=float(t_sec),
                reference_ready=0,
                reference_time_sec=-1.0,
                reference_delta_sec=0.0,
                viscosity=0.0,
                effective_candidates=0.0,
                update_scope=0.0,
                drag=0.0,
                selection_speed=0.0,
                face_detected=face_detected,
                face_motion=face_motion,
                face_update_scope=face_update_scope,
            )
        else:
            # この研究の仕様: 現在と過去を同じ基準へ揃えてから比較する。
            current_norm = self._normalize_pose(pose)
            ref_norm = self._normalize_pose(ref_pose)

            # 数学の仕様: xyz差分を1個の距離にまとめて「各関節がどれだけ動いたか」にする。
            displacement = np.linalg.norm(
                current_norm - ref_norm,
                axis=1,
            )
            mean_displacement = float(np.mean(displacement))

            # 0..1: 30msで変化が小さいほど高い。
            # この研究の仕様: 変化が小さいほど高い値になる「姿勢維持度」のproxy。
            viscosity = float(
                np.exp(-mean_displacement / max(self.viscosity_scale, EPS))
            )

            # 1..5 proxy:
            # 5 body regionsの活動が均等 -> 高い
            # 1 regionに集中 -> 低い
            # この研究の仕様: 5身体領域への活動分散からeffective_candidatesを作る。
            activity = self._region_activity(current_norm, ref_norm)
            _, n_eff = entropy_effective_count(activity)

            # 0..1: 30msで有意に変わったlandmark割合
            # この研究の仕様: 閾値以上動いたlandmarkの割合を「更新範囲」とする。
            update_scope = float(
                np.mean(displacement >= self.update_threshold)
            )

            actual_dt = max(float(t_sec - ref_t), EPS)
            # 物理量の仕様: 変位を経過時間で割って身体変化の速度にする。
            body_speed = mean_displacement / actual_dt

            # Drag proxy:
            # 速度そのものではなく「直前の速度からどれだけ急変したか」。
            # tanhで0..1へbounded化して、以前の巨大drag問題を避ける。
            # Python/研究の仕様: 前回速度が無い初回だけは速度変化を計算できない。
            if self.prev_body_speed is None:
                drag = 0.0
            else:
                speed_change = abs(body_speed - self.prev_body_speed)
                drag = float(
                    np.tanh(speed_change / max(self.drag_scale, EPS))
                )

            self.prev_body_speed = body_speed

            # 実験的派生量。絶対的な「人間の選択速度」ではない。
            # この研究の仕様: 3指標から作る実験的な派生値で、確立した人間特性ではない。
            selection_speed = float(
                1.0
                / max(n_eff, 1.0)
                / (1.0 + viscosity)
                / (1.0 + drag)
            )

            state = State(
                frame=frame,
                time_sec=float(t_sec),
                reference_ready=1,
                reference_time_sec=float(ref_t),
                reference_delta_sec=float(actual_dt),
                viscosity=viscosity,
                effective_candidates=n_eff,
                update_scope=update_scope,
                drag=drag,
                selection_speed=selection_speed,
                body_speed=body_speed,
                face_detected=face_detected,
                face_motion=face_motion,
                face_update_scope=face_update_scope,
            )

            # UIの仕様: 詳細モードだけ関節角や体幹回転まで追加計算する。
            if self.detailed:
                state.left_knee_angle = angle_deg(
                    pose[self.L_HIP],
                    pose[self.L_KNEE],
                    pose[self.L_ANKLE],
                )
                state.right_knee_angle = angle_deg(
                    pose[self.R_HIP],
                    pose[self.R_KNEE],
                    pose[self.R_ANKLE],
                )
                state.left_elbow_angle = angle_deg(
                    pose[self.L_SHOULDER],
                    pose[self.L_ELBOW],
                    pose[self.L_WRIST],
                )
                state.right_elbow_angle = angle_deg(
                    pose[self.R_SHOULDER],
                    pose[self.R_ELBOW],
                    pose[self.R_WRIST],
                )

                shoulder_vec = (
                    current_norm[self.R_SHOULDER]
                    - current_norm[self.L_SHOULDER]
                )
                state.torso_rotation = float(
                    np.degrees(
                        np.arctan2(shoulder_vec[2], shoulder_vec[0])
                    )
                )

        (
            state.binary_state,
            state.state_id,
            state.hex_state,
        # この研究の仕様: 最後に4軸を4bit化して状態IDへ変換する。
        ) = encode_binary_state(
            state.viscosity,
            state.effective_candidates,
            state.update_scope,
            state.drag,
            reference_ready=bool(state.reference_ready),
        )

        # 最後に現在Poseをtimestamp付きで保存。
        # 状態遷移の仕様: 今回の結果を次回の「過去」として使うため履歴へ戻す。
        self.history.append((float(t_sec), pose.copy()))
        if face is not None:
            self.face_history.append((float(t_sec), face.copy()))

        return state


# ============================================================
# MediaPipe Tasks wrapper
# ============================================================

# MediaPipeとの境界: 生の画像を33点のPose座標へ変換するラッパー。
class PoseExtractor:
    def __init__(self, model_path: Path):
        cv2, mp, mp_python, vision = load_runtime()
        self.cv2 = cv2
        self.mp = mp
        self.vision = vision

        options = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(
                model_asset_path=str(model_path)
            ),
            # MediaPipeの仕様: VIDEOモードでは各フレームに単調増加timestampが必要。
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )

        self.landmarker = vision.PoseLandmarker.create_from_options(options)

    def process(
        self,
        frame_bgr: np.ndarray,
        task_timestamp_ms: int,
    ) -> Tuple[Optional[np.ndarray], object]:
        # OpenCV/MediaPipeの仕様: OpenCVはBGR、MediaPipeへ渡す画像はRGBに揃える。
        rgb = self.cv2.cvtColor(
            frame_bgr,
            self.cv2.COLOR_BGR2RGB,
        )
        rgb = np.ascontiguousarray(rgb)

        mp_image = self.mp.Image(
            image_format=self.mp.ImageFormat.SRGB,
            data=rgb,
        )

        # MediaPipeの仕様: VIDEOモードは画像とtimestampをセットで推論する。
        result = self.landmarker.detect_for_video(
            mp_image,
            int(task_timestamp_ms),
        )

        # MediaPipeの仕様: 人体を検出できないフレームではpose_landmarksが空になる。
        if not result.pose_landmarks:
            return None, None

        landmarks = result.pose_landmarks[0]

        # この実装の仕様: MediaPipeのlandmarkオブジェクトを計算しやすいNumPy配列へ変換する。
        pose = np.array(
            [[lm.x, lm.y, lm.z] for lm in landmarks],
            dtype=float,
        )

        if pose.shape != (33, 3):
            return None, landmarks

        return pose, landmarks

    def close(self):
        self.landmarker.close()


# MediaPipeとの境界: 生の画像を顔landmark座標へ変換するラッパー。
class FaceExtractor:
    def __init__(self, model_path: Path):
        cv2, mp, mp_python, vision = load_runtime()
        self.cv2 = cv2
        self.mp = mp
        options = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self.landmarker = vision.FaceLandmarker.create_from_options(options)

    def process(self, frame_bgr: np.ndarray, task_timestamp_ms: int):
        rgb = self.cv2.cvtColor(frame_bgr, self.cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        mp_image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect_for_video(mp_image, int(task_timestamp_ms))
        if not result.face_landmarks:
            return None, None
        landmarks = result.face_landmarks[0]
        face = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=float)
        return face, landmarks

    def close(self):
        self.landmarker.close()


# ============================================================
# Drawing / output
# ============================================================

# 表示の仕様: landmark座標を画像上のピクセル座標へ直して骨格を描く。
def draw_pose(frame, landmarks, cv2):
    if landmarks is None:
        return

    h, w = frame.shape[:2]
    xy = [
        (int(lm.x * w), int(lm.y * h))
        for lm in landmarks
    ]

    for a, b in POSE_CONNECTIONS:
        if a < len(xy) and b < len(xy):
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


def draw_face(frame, landmarks, cv2):
    if landmarks is None:
        return
    h, w = frame.shape[:2]
    xy = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    # Dense but light mesh: connect neighboring indices and key facial structures.
    key_pairs = [
        (10,338),(338,297),(297,332),(332,284),(284,251),(251,389),(389,356),(356,454),
        (454,323),(323,361),(361,288),(288,397),(397,365),(365,379),(379,378),(378,400),
        (400,377),(377,152),(152,148),(148,176),(176,149),(149,150),(150,136),(136,172),
        (172,58),(58,132),(132,93),(93,234),(234,127),(127,162),(162,21),(21,54),(54,103),(103,67),(67,109),(109,10),
        (33,7),(7,163),(163,144),(144,145),(145,153),(153,154),(154,155),(155,133),
        (263,249),(249,390),(390,373),(373,374),(374,380),(380,381),(381,382),(382,362),
        (70,63),(63,105),(105,66),(66,107),(336,296),(296,334),(334,293),(293,300),
        (168,6),(6,197),(197,195),(195,5),(5,4),(4,1),(1,19),(19,94),(94,2),
        (61,146),(146,91),(91,181),(181,84),(84,17),(17,314),(314,405),(405,321),(321,375),(375,291),
    ]
    for a,b in key_pairs:
        if a < len(xy) and b < len(xy):
            cv2.line(frame, xy[a], xy[b], (255,255,255), 1, cv2.LINE_AA)


def draw_overlay(frame, state: State, cv2):
    if state.reference_ready:
        text = (
            f"nu={state.viscosity:.2f} "
            f"N_eff={state.effective_candidates:.2f} "
            f"Omega={state.update_scope:.2f} "
            f"drag={state.drag:.2f} "
            f"bin={state.binary_state} "
            f"face={state.face_motion:.3f}"
        )
    else:
        text = "warming up: collecting 30 ms history"

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


# 出力の仕様: StateオブジェクトをCSVへ書ける辞書形式へ変換する。
def state_to_row(state: State, detailed: bool) -> Dict:
    row = asdict(state)

    if detailed:
        return row

    keep = [
        "frame",
        "time_sec",
        "reference_ready",
        "reference_time_sec",
        "reference_delta_sec",
        "viscosity",
        "effective_candidates",
        "update_scope",
        "drag",
        "selection_speed",
        "face_detected",
        "face_motion",
        "face_update_scope",
        "binary_state",
        "state_id",
        "hex_state",
    ]
    return {key: row[key] for key in keep}


# CSVの仕様: 1フレーム=1行として解析結果を保存する。
def save_rows(rows: List[Dict], output_csv: Path):
    if not rows:
        print("有効なPoseデータがありません。")
        return

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV saved: {output_csv}")


# この研究の仕様: 16状態は4bitで表せるのでstate_idを1byteずつBINへ保存する。
def write_binary_file(rows: List[Dict], output_bin: Path):
    if not rows:
        return

    output_bin.parent.mkdir(parents=True, exist_ok=True)

    payload = bytes(
        int(row["state_id"]) & 0x0F
        for row in rows
    )
    output_bin.write_bytes(payload)

    print(f"BIN saved: {output_bin}")


# ============================================================
# Timestamp helpers
# ============================================================

# 動画解析の仕様: FPSではなく動画自身のtimestampを解析時間として使う。
class VideoTimestampReader:
    """
    OpenCVの CAP_PROP_POS_MSEC を利用。
    解析基準としてFPSは使わない。

    同じtimestampが少数回出る場合はMediaPipe Tasks用timestampだけ
    1msずつ進めるが、解析用time_secは動画timestampを保持する。

    timestampが長時間進まない動画は明示的に停止する。
    """

    def __init__(self):
        self.last_video_time: Optional[float] = None
        self.last_task_ms = -1
        self.stalled_count = 0

    def read(self, cap, cv2) -> Tuple[float, int]:
        # OpenCVの仕様: CAP_PROP_POS_MSECで現在フレーム位置をミリ秒として取得する。
        time_sec = float(cap.get(cv2.CAP_PROP_POS_MSEC)) / 1000.0

        if not math.isfinite(time_sec) or time_sec < 0:
            raise RuntimeError("動画timestampが取得できません。")

        if self.last_video_time is not None:
            if time_sec <= self.last_video_time + EPS:
                self.stalled_count += 1
            else:
                self.stalled_count = 0

        if self.stalled_count >= 10:
            raise RuntimeError(
                "この動画ではOpenCVからtimestampを安定取得できません。\n"
                "VFR/codec依存の可能性があります。"
            )

        self.last_video_time = time_sec

        task_ms = int(round(time_sec * 1000.0))
        # MediaPipe VIDEOの仕様: timestampは必ず前回より大きくする必要がある。
        if task_ms <= self.last_task_ms:
            task_ms = self.last_task_ms + 1
        self.last_task_ms = task_ms

        return time_sec, task_ms


# ============================================================
# Video
# ============================================================

def ask_video_detail() -> bool:
    print("")
    print("動画解析の詳細度:")
    print("1: 簡易 - 4軸 + binary")
    print("2: 詳細 - 上記 + body_speed / 関節角 / torso_rotation")

    while True:
        choice = input("詳細度 > ").strip()
        if choice == "1":
            return False
        if choice == "2":
            return True
        print("1 または 2 を入力してください。")


# アプリの流れ: 動画を1枚ずつ読み、検出→状態計算→表示→保存を繰り返す。
def run_video(
    video_path: str,
    output_csv: Path,
    detailed: bool,
    model_path: Path,
    face_model_path: Path,
):
    cv2, _, _, _ = load_runtime()

    # OpenCVの仕様: VideoCaptureは動画を1フレームずつ読むための入口。
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"動画を開けません: {video_path}")

    extractor = PoseExtractor(model_path)
    face_extractor = FaceExtractor(face_model_path)
    observer = GBMObserver(detailed=detailed)
    ts_reader = VideoTimestampReader()

    rows: List[Dict] = []
    frame_i = 0

    print("q または ESC で途中終了。")

    try:
        # Pythonの仕様: 動画終了かユーザー終了まで同じ処理を繰り返す。
        while True:
            # OpenCVの仕様: read()は「成功したか」と「画像1枚」を同時に返す。
            ok, frame = cap.read()
            # OpenCVの仕様: フレームを読めなければ動画終了とみなしてループを抜ける。
            if not ok:
                break

            time_sec, task_ms = ts_reader.read(cap, cv2)

            # MediaPipeの仕様: 同じ画像から身体landmarkを推論する。
            pose, landmarks = extractor.process(frame, task_ms)
            # MediaPipeの仕様: 同じ画像から顔landmarkも別モデルで推論する。
            face, face_landmarks = face_extractor.process(frame, task_ms)

            # MediaPipeの仕様: 検出失敗時はPoseがNoneなので、存在確認してから計算する。
            if pose is not None:
                # この研究の仕様: 検出したPose/Faceを4軸と16状態へ変換する。
                state = observer.step(
                    pose,
                    face,
                    frame=frame_i,
                    t_sec=time_sec,
                )
                # Pythonの仕様: appendで今回の結果をCSV保存用リストの末尾へ追加する。
                rows.append(state_to_row(state, detailed))

                draw_pose(frame, landmarks, cv2)
                draw_face(frame, face_landmarks, cv2)
                draw_overlay(frame, state, cv2)
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

            cv2.imshow("GBMCCQSD Video", frame)

            # OpenCVの仕様: waitKeyで画面イベントを処理しつつ押されたキーを読む。
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break

            frame_i += 1

    # Pythonの仕様: finallyは途中エラーでも必ず後片付けを実行する。
    finally:
        # OpenCVの仕様: 使い終わった動画/カメラをreleaseしてOSへ返す。
        cap.release()
        extractor.close()
        face_extractor.close()
        cv2.destroyAllWindows()

    save_rows(rows, output_csv)
    write_binary_file(rows, output_csv.with_suffix(".bin"))


# ============================================================
# Camera
# ============================================================

# OpenCVの仕様: カメラ番号0,1,...をVideoCaptureへ渡して実機カメラを開く。
def open_camera(camera_index: int, cv2):
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened() and os.name == "nt":
        cap.release()
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

    if not cap.isOpened():
        raise RuntimeError(f"カメラを開けません: index={camera_index}")

    return cap


# アプリの流れ: カメラは動画timestampが無いのでPCの経過時間をtimestampにする。
def run_camera(
    camera_index: int,
    output_csv: Path,
    model_path: Path,
    face_model_path: Path,
):
    cv2, _, _, _ = load_runtime()

    cap = open_camera(camera_index, cv2)
    extractor = PoseExtractor(model_path)
    face_extractor = FaceExtractor(face_model_path)
    observer = GBMObserver(detailed=True)

    rows: List[Dict] = []
    frame_i = 0

    start = time.perf_counter()
    last_task_ms = -1

    print("カメラ開始。q または ESC で終了。")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("カメラframe取得に失敗しました。")

            # Pythonの仕様: perf_counterは高精度の経過時間測定に向く。
            time_sec = time.perf_counter() - start

            task_ms = int(round(time_sec * 1000.0))
            if task_ms <= last_task_ms:
                task_ms = last_task_ms + 1
            last_task_ms = task_ms

            pose, landmarks = extractor.process(frame, task_ms)
            face, face_landmarks = face_extractor.process(frame, task_ms)

            if pose is not None:
                state = observer.step(
                    pose,
                    face,
                    frame=frame_i,
                    t_sec=time_sec,
                )
                rows.append(state_to_row(state, detailed=True))

                draw_pose(frame, landmarks, cv2)
                draw_face(frame, face_landmarks, cv2)
                draw_overlay(frame, state, cv2)
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

            cv2.imshow("GBMCCQSD Camera", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break

            frame_i += 1

    finally:
        cap.release()
        extractor.close()
        face_extractor.close()
        cv2.destroyAllWindows()

    save_rows(rows, output_csv)
    write_binary_file(rows, output_csv.with_suffix(".bin"))


# ============================================================
# OptiTrack
# ============================================================

def run_optitrack_csv(csv_path: Path):
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    print("")
    print(f"OptiTrack CSV: {csv_path}")
    print("現段階ではMotive CSVの形式確認モードです。")
    print("研究室の実CSVを確認後、4軸adapterを固定します。")
    print("")
    print("先頭10行:")

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
    ) as f:
        for i, line in enumerate(f):
            print(line.rstrip())
            if i >= 9:
                break


def optitrack_menu():
    print("")
    print("OptiTrack")
    print("1: Motive CSV")
    print("2: Live NatNet [未実装]")

    choice = input("OptiTrack入力 > ").strip()

    if choice == "1":
        path = input("Motive CSVパス > ").strip().strip('"')
        run_optitrack_csv(Path(path))
    elif choice == "2":
        print("NatNetは研究室PCのMotive/NatNet設定確認後に接続します。")
    else:
        print("1 または 2 を選んでください。")


# ============================================================
# Self test
# ============================================================

def self_test():
    """
    Camera / MediaPipeを使わず、
    timestamp補間と4軸計算の最低限を検証する。
    """
    observer = GBMObserver(detailed=True)

    base = np.zeros((33, 3), dtype=float)

    # normalizationに必要な肩・腰幅を作る
    base[11] = [-0.2, 0.3, 0.0]
    base[12] = [ 0.2, 0.3, 0.0]
    base[23] = [-0.15, 0.0, 0.0]
    base[24] = [ 0.15, 0.0, 0.0]
    base[25] = [-0.15, -0.4, 0.0]
    base[26] = [ 0.15, -0.4, 0.0]
    base[27] = [-0.15, -0.8, 0.0]
    base[28] = [ 0.15, -0.8, 0.0]
    base[13] = [-0.35, 0.1, 0.0]
    base[14] = [ 0.35, 0.1, 0.0]
    base[15] = [-0.45, -0.1, 0.0]
    base[16] = [ 0.45, -0.1, 0.0]

    times = [0.000, 0.016, 0.033, 0.050, 0.067]
    states = []

    for i, t in enumerate(times):
        pose = base.copy()
        pose[15, 1] -= i * 0.01
        pose[16, 1] += i * 0.005

        s = observer.step(
            pose,
            frame=i,
            t_sec=t,
        )
        states.append(s)

    assert states[0].reference_ready == 0
    assert states[-1].reference_ready == 1
    assert abs(states[-1].reference_delta_sec - 0.030) < 1e-6
    assert 0.0 <= states[-1].viscosity <= 1.0
    assert 1.0 <= states[-1].effective_candidates <= 5.0
    assert 0.0 <= states[-1].update_scope <= 1.0
    assert 0.0 <= states[-1].drag <= 1.0

    b, sid, hx = encode_binary_state(
        0.8, 3.0, 0.5, 0.4,
        reference_ready=True,
    )
    assert b == "1111"
    assert sid == 15
    assert hx == "0xf"

    print("SELF-TEST: PASS")
    print(
        "timestamp interpolation / four axes / binary encoding: OK"
    )


# ============================================================
# Interactive
# ============================================================

# UIの仕様: 起動後に1/2/3を選ばせ、対応する処理へ分岐する。
def interactive():
    print("")
    print("GBMCCQSD Capture v0.9")
    print("=====================")
    print("1: 動画ファイル")
    print("2: カメラ撮影")
    print("3: OptiTrack")
    print("")
    print("基準: timestampの30ms前")
    print("出力: CSV + 4bit state + .bin")
    print("※ .task は内部モデルなので開く必要なし")
    print("")

    # Pythonの仕様: inputは文字列を受け取り、stripで前後の空白を消す。
    mode = input("入力方式 > ").strip()

    # Pythonの仕様: if/elif/elseでユーザーの選択ごとに実行ルートを変える。
    if mode == "1":
        model_path = ensure_model(DEFAULT_MODEL_PATH)
        face_model_path = ensure_model(DEFAULT_FACE_MODEL_PATH, FACE_MODEL_URL, "Face Landmarker")

        video = input("動画パス > ").strip().strip('"')
        detailed = ask_video_detail()

        default_name = (
            "gbmccqsd_video_detailed.csv"
            if detailed
            else "gbmccqsd_video_basic.csv"
        )
        out = input(f"出力CSV [{default_name}] > ").strip() or default_name

        run_video(
            video,
            Path(out),
            detailed,
            model_path,
            face_model_path,
        )

    elif mode == "2":
        model_path = ensure_model(DEFAULT_MODEL_PATH)
        face_model_path = ensure_model(DEFAULT_FACE_MODEL_PATH, FACE_MODEL_URL, "Face Landmarker")

        index_text = input("カメラ番号 [0] > ").strip()
        camera_index = int(index_text) if index_text else 0

        out = (
            input("出力CSV [gbmccqsd_camera.csv] > ").strip()
            or "gbmccqsd_camera.csv"
        )

        run_camera(
            camera_index,
            Path(out),
            model_path,
            face_model_path,
        )

    elif mode == "3":
        optitrack_menu()

    else:
        print("1 / 2 / 3 を選んでください。")


# ============================================================
# CLI
# ============================================================

# Pythonアプリの仕様: mainを「起動後の交通整理役」にして各モードへ振り分ける。
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--video", type=str)
    parser.add_argument("--detail", choices=["basic", "detailed"])
    parser.add_argument("--camera", type=int)
    parser.add_argument("--optitrack-csv", type=str)
    parser.add_argument("--model", type=str)
    parser.add_argument("--face-model", type=str)
    parser.add_argument("--output", type=str, default="gbmccqsd_output.csv")
    parser.add_argument("--self-test", action="store_true")

    # argparseの仕様: 実行時に渡された --video などをまとめてargsへ入れる。
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    if args.optitrack_csv:
        run_optitrack_csv(Path(args.optitrack_csv))
        return

    if args.video:
        model_path = ensure_model(
            Path(args.model) if args.model else DEFAULT_MODEL_PATH
        )
        face_model_path = ensure_model(
            Path(args.face_model) if args.face_model else DEFAULT_FACE_MODEL_PATH,
            FACE_MODEL_URL,
            "Face Landmarker",
        )
        detailed = (
            ask_video_detail()
            if args.detail is None
            else args.detail == "detailed"
        )
        run_video(
            args.video,
            Path(args.output),
            detailed,
            model_path,
            face_model_path,
        )
        return

    if args.camera is not None:
        model_path = ensure_model(
            Path(args.model) if args.model else DEFAULT_MODEL_PATH
        )
        face_model_path = ensure_model(
            Path(args.face_model) if args.face_model else DEFAULT_FACE_MODEL_PATH,
            FACE_MODEL_URL,
            "Face Landmarker",
        )
        run_camera(
            args.camera,
            Path(args.output),
            model_path,
            face_model_path,
        )
        return

    interactive()


# Pythonの仕様: このファイルを直接実行した時だけmain()から開始する。
if __name__ == "__main__":
    main()
