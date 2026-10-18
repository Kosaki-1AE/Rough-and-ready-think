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



def detect_beats(samples: np.ndarray, sr: int) -> tuple[float | None, np.ndarray]:
    """Estimate beat positions from audio using librosa (independent of GBMC)."""
    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError("Beat tracking requires librosa: python -m pip install librosa soundfile") from exc
    # 512-sample hops offer finer-than-30ms timing at 44.1 kHz.
    hop_length = 512
    tempo, beat_frames = librosa.beat.beat_track(
        y=np.asarray(samples, dtype=np.float32), sr=sr,
        hop_length=hop_length, trim=False, units="frames"
    )
    times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)
    tempo_arr = np.asarray(tempo).reshape(-1)
    bpm = float(tempo_arr[0]) if tempo_arr.size and len(times) >= 2 else None
    return bpm, np.asarray(times, dtype=float)


def nearest_beat(time_s: float, beat_times: np.ndarray) -> tuple[float | None, float | None]:
    """Return closest beat timestamp and signed offset (event - beat)."""
    if not len(beat_times):
        return None, None
    i = int(np.searchsorted(beat_times, time_s))
    candidates = [j for j in (i - 1, i) if 0 <= j < len(beat_times)]
    j = min(candidates, key=lambda index: abs(time_s - beat_times[index]))
    return float(beat_times[j]), float(time_s - beat_times[j])


def compare_restarts_to_beats(events: list[Event], beat_times: np.ndarray,
                              tolerance_ms: float) -> tuple[list[dict], dict]:
    """Compare detected Genesis restarts to independently estimated beats.

    This is proximity, NOT proof that a restart was caused by a beat.
    Initial reference creation is excluded.
    """
    if tolerance_ms < 0:
        raise ValueError("tolerance_ms must be >= 0")
    restarts = [e for e in events if e.detail == "detected_reference_change"]
    tolerance_s = tolerance_ms / 1000.0
    rows = []
    for e in restarts:
        nearest, delta = nearest_beat(e.time_s, beat_times)
        rows.append({
            "restart_time_s": round(e.time_s, 6),
            "reference_id": e.reference_id,
            "nearest_beat_s": "" if nearest is None else round(nearest, 6),
            "offset_ms": "" if delta is None else round(1000 * delta, 3),
            "within_tolerance": bool(delta is not None and abs(delta) <= tolerance_s),
        })
    matched_restarts = sum(row["within_tolerance"] for row in rows)
    restart_times = np.array([e.time_s for e in restarts], dtype=float)
    matched_beats = sum(
        (lambda offset: offset is not None and abs(offset) <= tolerance_s)(
            nearest_beat(float(beat), restart_times)[1]
        ) for beat in beat_times
    )
    result = {
        "tolerance_ms": tolerance_ms,
        "detected_restarts": len(restarts),
        "estimated_beats": int(len(beat_times)),
        "restarts_near_beats": matched_restarts,
        "fraction_restarts_near_beats": round(matched_restarts / len(restarts), 4) if restarts else None,
        "beats_near_restarts": matched_beats,
        "fraction_beats_near_restarts": round(matched_beats / len(beat_times), 4) if len(beat_times) else None,
        "median_absolute_offset_ms": round(float(np.median([abs(row["offset_ms"]) for row in rows if row["within_tolerance"]])), 3)
        if matched_restarts else None,
        "interpretation": "Estimated beat proximity only; timing and BPM can have half/double-tempo or offset errors."
    }
    return rows, result


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)



def analyze_drum_melody(samples: np.ndarray, sr: int, observation_rows: list[dict],
                        gbmc_events: list[Event], beat_times: np.ndarray,
                        *, analysis_sr: int = 11025) -> tuple[list[dict], list[dict], dict]:
    """Approximate HPSS separation followed by independent onset detection.

    Percussive != isolated drum stems; harmonic != isolated melody stems.
    This is an observational side-channel and NEVER changes the GBMC runtime.
    """
    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError("Drum/melody analysis requires librosa: pip install -r requirements.txt") from exc
    # Downsample for manageable whole-song STFT/HPSS memory and runtime.
    y = librosa.resample(np.asarray(samples, dtype=np.float32), orig_sr=sr, target_sr=analysis_sr)
    hop = 256
    n_fft = 1024
    stft = librosa.stft(y, n_fft=n_fft, hop_length=hop)
    harmonic, percussive = librosa.decompose.hpss(stft, margin=(2.0, 2.0))
    # Positive spectral change, measured independently in two components.
    drum_curve = librosa.onset.onset_strength(S=librosa.amplitude_to_db(np.abs(percussive), ref=np.max),
                                               sr=analysis_sr, hop_length=hop)
    melody_curve = librosa.onset.onset_strength(S=librosa.amplitude_to_db(np.abs(harmonic), ref=np.max),
                                                 sr=analysis_sr, hop_length=hop)
    def peaks(curve):
        indices = librosa.onset.onset_detect(onset_envelope=curve, sr=analysis_sr,
                                            hop_length=hop, backtrack=False, units="frames")
        return np.asarray(librosa.frames_to_time(indices, sr=analysis_sr, hop_length=hop), dtype=float)

    drum_times, melody_times = peaks(drum_curve), peaks(melody_curve)
    curve_times = librosa.frames_to_time(np.arange(len(drum_curve)), sr=analysis_sr, hop_length=hop)
    times = np.array([r["time_s"] for r in observation_rows], dtype=float)
    step = (times[1] - times[0]) if len(times) > 1 else 0.03
    mid_times = times + step / 2
    drum_values = np.interp(mid_times, curve_times, drum_curve, left=0, right=0)
    melody_values = np.interp(mid_times, curve_times, melody_curve, left=0, right=0)
    drum_hit = np.zeros(len(times), dtype=int)
    melody_hit = np.zeros(len(times), dtype=int)
    # Map HPSS detections into the same 30-ms bins as existing GBMC observations.
    for event_times, dest in ((drum_times, drum_hit), (melody_times, melody_hit)):
        for onset_time in event_times:
            index = int(np.floor(onset_time / step))
            if 0 <= index < len(dest):
                dest[index] = 1
    timeline = []
    for i, row in enumerate(observation_rows):
        event = gbmc_events[i]
        timeline.append({
            "time_s": round(float(times[i]), 6),
            "drum_strength": round(float(drum_values[i]), 5),
            "melody_strength": round(float(melody_values[i]), 5),
            "drum_onset": int(drum_hit[i]),
            "melody_onset": int(melody_hit[i]),
            "gbmc_event": event.event,
            "room_before": event.room_before,
            "room_after": event.room_after,
            "reference_id": event.reference_id,
        })
    restart_times = np.array([e.time_s for e in gbmc_events
                              if e.detail == "detected_reference_change"], dtype=float)
    def append_events(kind, ts):
        for t in ts:
            beat, beat_offset = nearest_beat(float(t), beat_times)
            restart, restart_offset = nearest_beat(float(t), restart_times)
            events.append({
                "source": kind,
                "time_s": round(float(t), 6),
                "nearest_beat_s": "" if beat is None else round(beat, 6),
                "offset_from_beat_ms": "" if beat_offset is None else round(1000 * beat_offset, 3),
                "nearest_restart_s": "" if restart is None else round(restart, 6),
                "offset_from_restart_ms": "" if restart_offset is None else round(1000 * restart_offset, 3),
            })
    events = []
    append_events("drum_like", drum_times)
    append_events("melody_like", melody_times)
    events.sort(key=lambda e: (e["time_s"], e["source"]))
    details = {
        "method": "librosa HPSS + onset detection (approximate, non-causal, full-song)",
        "analysis_sample_rate": analysis_sr,
        "drum_like_onsets": int(len(drum_times)),
        "melody_like_onsets": int(len(melody_times)),
        "disclaimer": "Percussive component may include non-drum transients; harmonic component may include vocals and bass. Not isolated instrument stems. No new GBMC reference decisions are made."
    }
    return timeline, events, details


def run(input_path: Path, output_dir: Path, *, hop_ms: float = 30.0,
        change_threshold: float = 3.2, transition_threshold: float = 1.3,
        beat_tolerance_ms: float = 50.0, analyze_beats: bool = True,
        analyze_layers: bool = True) -> dict:
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
    beat_times = np.array([], dtype=float)
    if analyze_beats:
        bpm, beat_times = detect_beats(samples, sr)
        comparison_rows, beat_metrics = compare_restarts_to_beats(runtime.events, beat_times, beat_tolerance_ms)
        write_csv(output_dir / "beat_times.csv",
                  [{"beat_index": i + 1, "time_s": round(float(t), 6)} for i, t in enumerate(beat_times)],
                  ["beat_index", "time_s"])
        write_csv(output_dir / "beat_comparison.csv", comparison_rows,
                  ["restart_time_s", "reference_id", "nearest_beat_s", "offset_ms", "within_tolerance"])
        summary["beat_analysis"] = {"estimated_bpm": None if bpm is None else round(bpm, 2), **beat_metrics}
    if analyze_layers:
        timeline, layer_events, layer_summary = analyze_drum_melody(
            samples, sr, features, runtime.events, beat_times
        )
        write_csv(output_dir / "drum_melody_timeline.csv", timeline,
                  ["time_s", "drum_strength", "melody_strength", "drum_onset",
                   "melody_onset", "gbmc_event", "room_before", "room_after", "reference_id"])
        write_csv(output_dir / "drum_melody_events.csv", layer_events,
                  ["source", "time_s", "nearest_beat_s", "offset_from_beat_ms",
                   "nearest_restart_s", "offset_from_restart_ms"])
        summary["layer_analysis"] = layer_summary
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Experimental GBMC 16-Room music instance")
    ap.add_argument("wav", type=Path, help="Uncompressed PCM WAV")
    ap.add_argument("--out", type=Path, default=Path("gbmc_music_output"))
    ap.add_argument("--hop-ms", type=float, default=30.0)
    ap.add_argument("--change-threshold", type=float, default=3.2)
    ap.add_argument("--transition-threshold", type=float, default=1.3)
    ap.add_argument("--beat-tolerance-ms", type=float, default=50.0,
                    help="Allowed distance between a restart and estimated beat")
    ap.add_argument("--no-beats", action="store_true", help="Skip beat analysis")
    ap.add_argument("--no-layers", action="store_true", help="Skip drum/melody HPSS analysis")
    args = ap.parse_args()
    print(json.dumps(run(args.wav, args.out, hop_ms=args.hop_ms,
                         change_threshold=args.change_threshold,
                         transition_threshold=args.transition_threshold,
                         beat_tolerance_ms=args.beat_tolerance_ms, analyze_beats=not args.no_beats,
                         analyze_layers=not args.no_layers),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
