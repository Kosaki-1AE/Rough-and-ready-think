"""Experimental GBMC music runtime (not a validated neuroscience model).

16 Room IDs (0..F). Genesis restart is Room F.
Audio is observed every ~30 ms; Room progression is event-driven, NOT clock-driven.
All Room semantics and thresholds are provisional.
"""
from __future__ import annotations

import argparse
import csv
import json
import wave
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np

ROOMS = (
    "Input", "Buffer", "Pool", "Queue", "Motion", "Stack", "Coherence",
    "Capacity", "Jab", "Quality", "Twist", "Stillness", "Depth",
    "Straight", "Output", "Genesis",
)
GENESIS = 15


@dataclass
class Event:
    time_s: float
    frame: int
    room_before: str
    room_after: str
    event: str
    reference_id: int
    rms: float
    novelty: float
    spectral_flux: float
    detail: str = ""


def load_wav(path: Path) -> tuple[np.ndarray, int]:
    """Read uncompressed PCM WAV (8/16/24/32-bit), convert to mono float."""
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        if wf.getcomptype() != "NONE":
            raise ValueError("Only uncompressed PCM WAV is supported")
        raw = wf.readframes(wf.getnframes())
    if width == 1:
        a = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0) / 128
    elif width == 2:
        a = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768
    elif width == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        x = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        x = np.where(x & 0x800000, x - 0x1000000, x)
        a = x.astype(np.float64) / 8388608
    elif width == 4:
        a = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648
    else:
        raise ValueError(f"Unsupported PCM sample width: {width}")
    if len(a) % channels:
        raise ValueError("Incomplete WAV samples")
    return a.reshape(-1, channels).mean(axis=1), sr


def extract_features(samples: np.ndarray, sr: int, hop_ms: float = 30.0) -> list[dict]:
    """Non-overlapping observation frames. FFT flux is relative to prior frame."""
    if hop_ms <= 0:
        raise ValueError("hop_ms must be positive")
    hop = max(1, round(sr * hop_ms / 1000))
    prev_spectrum: Optional[np.ndarray] = None
    result = []
    for index, start in enumerate(range(0, len(samples), hop)):
        frame = np.zeros(hop, dtype=float)
        chunk = samples[start:start+hop]
        frame[:len(chunk)] = chunk
        rms = float(np.sqrt(np.mean(frame * frame)))
        spectrum = np.abs(np.fft.rfft(frame * np.hanning(hop)))
        spectrum /= max(float(np.linalg.norm(spectrum)), 1e-12)
        flux = 0.0 if prev_spectrum is None else float(np.sum(np.maximum(0, spectrum - prev_spectrum)))
        prev_spectrum = spectrum
        result.append({"frame": index, "time_s": start / sr, "rms": rms, "spectral_flux": flux})
    return result


class MusicGBMC:
    """One independently running 16-Room instance for audio features.

    Rules (provisional):
      - reset reference when combined novelty relative to recent history is large;
      - restart at F/Genesis, keeping complete event history;
      - advance to next Room only on a smaller distinct feature-change event;
      - stay in the current Room otherwise.
    """

    def __init__(self, *, change_threshold: float = 3.2,
                 transition_threshold: float = 1.3, refractory_ms: float = 120,
                 reference_window: int = 20):
        if not (0 < transition_threshold < change_threshold):
            raise ValueError("Require 0 < transition_threshold < change_threshold")
        self.change_threshold = change_threshold
        self.transition_threshold = transition_threshold
        self.refractory_s = refractory_ms / 1000
        self.room = GENESIS
        self.reference_id = 0
        self.reference: Optional[np.ndarray] = None
        self.baseline: deque[np.ndarray] = deque(maxlen=reference_window)
        self.last_restart_time = float("-inf")
        self.events: list[Event] = []

    @staticmethod
    def _features(row: dict) -> np.ndarray:
        return np.array([np.log1p(100 * row["rms"]), row["spectral_flux"]], dtype=float)

    def _novelty(self, v: np.ndarray) -> float:
        if len(self.baseline) < 4:
            return 0.0
        base = np.stack(self.baseline)
        center = np.median(base, axis=0)
        mad = np.median(np.abs(base - center), axis=0)
        # Floors avoid infinite scores in quiet, constant-value regions.
        scale = 1.4826 * mad + np.array([0.15, 0.25])
        return float(np.linalg.norm((v - center) / scale))

    def restart(self, *, time_s: float, frame: int, rms: float,
                spectral_flux: float, novelty: float = 0, reason: str = "external") -> Event:
        before = self.room
        self.reference_id += 1
        self.room = GENESIS
        self.last_restart_time = time_s
        v = self._features({"rms": rms, "spectral_flux": spectral_flux})
        self.reference = v.copy()
        self.baseline.clear()
        self.baseline.append(v)
        event = Event(time_s, frame, f"{before:X}", "F", "genesis_restart", self.reference_id,
                      rms, novelty, spectral_flux, reason)
        self.events.append(event)
        return event

    def observe(self, row: dict) -> Event:
        t, frame = float(row["time_s"]), int(row["frame"])
        rms, flux = float(row["rms"]), float(row["spectral_flux"])
        v = self._features(row)
        if self.reference is None:
            return self.restart(time_s=t, frame=frame, rms=rms, spectral_flux=flux, reason="initial_reference")
        novelty = self._novelty(v)
        if novelty >= self.change_threshold and t - self.last_restart_time >= self.refractory_s:
            return self.restart(time_s=t, frame=frame, rms=rms, spectral_flux=flux,
                                novelty=novelty, reason="detected_reference_change")
        before = self.room
        if novelty >= self.transition_threshold:
            self.room = (self.room + 1) % 16
            label = "room_transition"
        else:
            label = "hold"
        self.baseline.append(v)
        event = Event(t, frame, f"{before:X}", f"{self.room:X}", label,
                      self.reference_id, rms, novelty, flux)
        self.events.append(event)
        return event


def run(input_path: Path, output_dir: Path, *, hop_ms: float = 30.0,
        change_threshold: float = 3.2, transition_threshold: float = 1.3) -> dict:
    samples, sr = load_wav(input_path)
    features = extract_features(samples, sr, hop_ms)
    runtime = MusicGBMC(change_threshold=change_threshold, transition_threshold=transition_threshold)
    for row in features:
        runtime.observe(row)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "events.csv").open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(Event.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(event) for event in runtime.events)
    summary = {
        "input": str(input_path), "sample_rate": sr, "duration_s": round(len(samples) / sr, 3),
        "hop_ms_requested": hop_ms, "hop_ms_actual": 1000 * round(sr * hop_ms / 1000) / sr,
        "observation_frames": len(features), "rooms": {f"{i:X}": name for i, name in enumerate(ROOMS)},
        "reference_count": runtime.reference_id,
        "detected_reference_changes": sum(e.detail == "detected_reference_change" for e in runtime.events),
        "room_transitions": sum(e.event == "room_transition" for e in runtime.events),
        "final_room": f"{runtime.room:X}",
        "note": "Exploratory engine. Room order and event thresholds are hypotheses, not proven brain or music semantics."
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Experimental GBMC 16-Room music instance")
    ap.add_argument("wav", type=Path, help="Uncompressed PCM WAV")
    ap.add_argument("--out", type=Path, default=Path("gbmc_music_output"))
    ap.add_argument("--hop-ms", type=float, default=30.0)
    ap.add_argument("--change-threshold", type=float, default=3.2)
    ap.add_argument("--transition-threshold", type=float, default=1.3)
    args = ap.parse_args()
    print(json.dumps(run(args.wav, args.out, hop_ms=args.hop_ms,
                         change_threshold=args.change_threshold,
                         transition_threshold=args.transition_threshold), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
