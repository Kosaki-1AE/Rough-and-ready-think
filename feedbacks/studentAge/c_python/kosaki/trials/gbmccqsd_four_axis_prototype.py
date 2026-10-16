"""
GBMCCQSD 4-axis prototype
=========================
Experimental implementation of:

    vertical   : viscosity (nu)
    horizontal : effective candidate count (N_eff)
    height     : update scope (Omega)
    drag       : drag / resistance (F_drag)

and a derived output:

    selection_speed

This is a prototype for testing the representation across domains such as:
- Dance / MediaPipe
- Soccer strategy
- Baseball form

IMPORTANT:
The formulas below are NOT established scientific laws.
They are deliberately simple, inspectable hypotheses for experimentation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Sequence
import math

import numpy as np

EPS = 1e-12


def softmax(scores: Sequence[float], temperature: float = 1.0) -> np.ndarray:
    x = np.asarray(scores, dtype=float)
    t = max(float(temperature), EPS)
    z = x / t
    z -= np.max(z)
    e = np.exp(z)
    return e / (np.sum(e) + EPS)


def effective_candidate_count(probabilities: Sequence[float]) -> float:
    p = np.asarray(probabilities, dtype=float)
    p = np.clip(p, EPS, None)
    p = p / np.sum(p)
    h = -np.sum(p * np.log(p))
    return float(np.exp(h))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < EPS or nb < EPS:
        return 0.0
    sim = float(np.dot(a, b) / (na * nb))
    return float(np.clip(sim, -1.0, 1.0))


@dataclass
class FourAxisState:
    t: int
    viscosity: float
    effective_candidates: float
    update_scope: float
    drag: float
    selection_speed: float
    drive: float
    load: float
    capacity: float
    candidate_entropy: float
    dominant_candidate: int


class FourAxisDynamics:
    """Generic domain-independent observer."""

    def __init__(
        self,
        feature_names: Sequence[str],
        change_threshold: float = 0.15,
        viscosity_alpha: float = 0.25,
        candidate_temperature: float = 1.0,
        viscosity_weight_on_speed: float = 0.5,
    ):
        self.feature_names = list(feature_names)
        self.change_threshold = float(change_threshold)
        self.viscosity_alpha = float(viscosity_alpha)
        self.candidate_temperature = float(candidate_temperature)
        self.viscosity_weight_on_speed = float(viscosity_weight_on_speed)
        self.prev_features: Optional[np.ndarray] = None
        self.history: List[np.ndarray] = []
        self.states: List[FourAxisState] = []
        self.similar_streak = 0

    def _viscosity(self, current: np.ndarray) -> float:
        if self.prev_features is None:
            self.similar_streak = 1
            return 0.0
        sim = max(0.0, cosine_similarity(current, self.prev_features))
        if sim >= 0.90:
            self.similar_streak += 1
        else:
            self.similar_streak = 1
        nu = 1.0 - math.exp(-self.viscosity_alpha * self.similar_streak * sim)
        return float(np.clip(nu, 0.0, 1.0))

    def _candidate_state(self, scores: Sequence[float]):
        p = softmax(scores, temperature=self.candidate_temperature)
        h = float(-np.sum(p * np.log(np.clip(p, EPS, None))))
        n_eff = float(np.exp(h))
        dominant = int(np.argmax(p))
        return p, h, n_eff, dominant

    def _update_scope(self, current: np.ndarray) -> float:
        if self.prev_features is None:
            return 0.0
        diff = np.abs(current - self.prev_features)
        scale = np.maximum(np.maximum(np.abs(current), np.abs(self.prev_features)), 1.0)
        relative_change = diff / scale
        changed = relative_change >= self.change_threshold
        return float(np.mean(changed))

    @staticmethod
    def _drag(load: float, capacity: float) -> float:
        c = max(float(capacity), EPS)
        return float(max(0.0, float(load) / c - 1.0))

    def _selection_speed(self, drive: float, drag: float, n_eff: float, viscosity: float) -> float:
        candidate_penalty = max(n_eff, 1.0)
        viscosity_penalty = 1.0 + self.viscosity_weight_on_speed * viscosity
        speed = max(float(drive), 0.0) / (1.0 + drag) / candidate_penalty / viscosity_penalty
        return float(speed)

    def step(
        self,
        features: Sequence[float],
        candidate_scores: Sequence[float],
        *,
        load: float,
        capacity: float,
        drive: float = 1.0,
    ) -> FourAxisState:
        current = np.asarray(features, dtype=float)
        if current.shape != (len(self.feature_names),):
            raise ValueError(f"Expected {len(self.feature_names)} features, got shape {current.shape}")

        viscosity = self._viscosity(current)
        probs, entropy, n_eff, dominant = self._candidate_state(candidate_scores)
        update_scope = self._update_scope(current)
        drag = self._drag(load, capacity)
        selection_speed = self._selection_speed(drive, drag, n_eff, viscosity)

        state = FourAxisState(
            t=len(self.states),
            viscosity=viscosity,
            effective_candidates=n_eff,
            update_scope=update_scope,
            drag=drag,
            selection_speed=selection_speed,
            drive=float(drive),
            load=float(load),
            capacity=float(capacity),
            candidate_entropy=entropy,
            dominant_candidate=dominant,
        )

        self.states.append(state)
        self.history.append(current.copy())
        self.prev_features = current.copy()
        return state

    def as_rows(self) -> List[Dict[str, float]]:
        return [asdict(s) for s in self.states]


DANCE_MEDIAPIPE_FEATURES = [
    "left_knee_angle", "right_knee_angle", "left_elbow_angle", "right_elbow_angle",
    "body_speed", "leg_speed_L", "leg_speed_R", "torso_rotation",
]

SOCCER_FEATURES = [
    "team_width", "team_depth", "ball_progression_speed", "pressure_level",
    "passing_lane_count", "nearest_defender_distance", "support_player_count", "possession_speed",
]

BASEBALL_FORM_FEATURES = [
    "shoulder_rotation", "hip_rotation", "elbow_angle", "knee_flexion",
    "trunk_tilt", "angular_velocity", "release_or_contact_timing", "center_of_mass_speed",
]


def run_demo(name, feature_names, sequence, candidate_scores, loads, capacities, drives):
    print(f"\n===== {name} =====")
    model = FourAxisDynamics(
        feature_names=feature_names,
        change_threshold=0.12,
        viscosity_alpha=0.30,
        candidate_temperature=1.0,
    )
    for i in range(len(sequence)):
        s = model.step(
            features=sequence[i],
            candidate_scores=candidate_scores[i],
            load=loads[i],
            capacity=capacities[i],
            drive=drives[i],
        )
        print(
            f"t={s.t:02d} | nu={s.viscosity:.3f} | N_eff={s.effective_candidates:.3f} | "
            f"Omega={s.update_scope:.3f} | drag={s.drag:.3f} | select_speed={s.selection_speed:.4f}"
        )
    return model


def dance_demo():
    seq = [
        [110, 112, 150, 149, 0.30, 0.25, 0.26, 5],
        [111, 113, 149, 150, 0.31, 0.26, 0.25, 6],
        [112, 113, 150, 149, 0.30, 0.25, 0.27, 6],
        [145, 140, 120, 122, 0.70, 0.66, 0.62, 25],
        [150, 144, 118, 120, 0.75, 0.70, 0.68, 30],
    ]
    scores = [
        [3.0, 1.0, 0.5, 0.2],
        [3.2, 0.9, 0.5, 0.2],
        [3.1, 0.9, 0.6, 0.2],
        [1.0, 1.5, 1.7, 1.4],
        [0.8, 1.2, 2.1, 1.8],
    ]
    return run_demo(
        "DANCE / MediaPipe", DANCE_MEDIAPIPE_FEATURES, seq, scores,
        loads=[0.3, 0.3, 0.35, 1.4, 1.2],
        capacities=[1.0, 1.0, 1.0, 1.0, 1.0],
        drives=[1.0, 1.0, 1.0, 1.2, 1.1],
    )


def soccer_demo():
    seq = [
        [42, 35, 1.2, 0.30, 4, 5.0, 3, 1.0],
        [43, 35, 1.2, 0.32, 4, 4.8, 3, 1.0],
        [43, 36, 1.3, 0.34, 4, 4.6, 3, 1.1],
        [58, 50, 2.4, 0.75, 2, 2.1, 1, 2.0],
        [60, 54, 2.6, 0.80, 2, 1.8, 1, 2.2],
    ]
    scores = [
        [2.5, 1.4, 1.2, 0.8],
        [2.4, 1.5, 1.1, 0.8],
        [2.3, 1.6, 1.2, 0.9],
        [0.8, 2.2, 1.6, 0.7],
        [0.6, 2.5, 1.8, 0.5],
    ]
    return run_demo(
        "SOCCER / Strategy", SOCCER_FEATURES, seq, scores,
        loads=[0.4, 0.4, 0.5, 1.5, 1.6],
        capacities=[1.2, 1.2, 1.2, 1.1, 1.1],
        drives=[1.0, 1.0, 1.0, 1.4, 1.5],
    )


def baseball_demo():
    seq = [
        [35, 42, 88, 30, 12, 2.0, 0.52, 1.1],
        [35, 43, 87, 31, 12, 2.1, 0.51, 1.1],
        [36, 43, 87, 31, 13, 2.1, 0.51, 1.2],
        [50, 60, 72, 45, 25, 3.8, 0.43, 2.1],
        [52, 62, 70, 46, 27, 4.0, 0.42, 2.2],
    ]
    scores = [
        [3.2, 0.8, 0.5],
        [3.0, 1.0, 0.5],
        [2.9, 1.1, 0.6],
        [1.0, 1.8, 2.0],
        [0.8, 1.7, 2.3],
    ]
    return run_demo(
        "BASEBALL / Form", BASEBALL_FORM_FEATURES, seq, scores,
        loads=[0.3, 0.3, 0.35, 1.3, 1.4],
        capacities=[1.0, 1.0, 1.0, 1.0, 1.0],
        drives=[1.0, 1.0, 1.0, 1.2, 1.3],
    )


if __name__ == "__main__":
    dance_demo()
    soccer_demo()
    baseball_demo()
