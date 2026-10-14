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

# One Room set, two permitted full-cycle paths. Strings are hexadecimal Room IDs.
ROUTES = {
    "normal": "F0123456789ABCDE",  # 9 -> A
    "bypass": "F14679BC",          # 9 -> B
}


def route_next(room: int | str, mode: str = "normal") -> int:
    """Next Room by chosen path (including wraparound to Genesis/F)."""
    if mode not in ROUTES:
        raise ValueError(f"Unknown route mode: {mode}")
    token = f"{room:X}" if isinstance(room, int) else room.upper()
    route = ROUTES[mode]
    if token not in route:
        raise ValueError(f"Room {token} is not on {mode} path; restart at F first")
    i = route.index(token)
    return int(route[(i + 1) % len(route)], 16)


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
                        *, analysis_sr: int = 11025, layer_hop_ms: float = 30.0) -> tuple[list[dict], list[dict], dict, dict]:
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
    # Separate 30ms audio feature streams for two independent GBMC runtimes.
    # These are approximate components, NOT physical drum/melody stems.
    drum_audio = librosa.istft(percussive, hop_length=hop, length=len(y))
    melody_audio = librosa.istft(harmonic, hop_length=hop, length=len(y))
    layer_features = {
        "drum": extract_features(drum_audio, analysis_sr, layer_hop_ms),
        "melody": extract_features(melody_audio, analysis_sr, layer_hop_ms),
    }
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
    return timeline, events, details, layer_features



def run_independent_layers(layer_features: dict[str, list[dict]], observation_rows: list[dict],
                           *, change_threshold: float, transition_threshold: float,
                           hop_ms: float) -> tuple[list[dict], list[dict], dict]:
    """Run two genuinely independent 16-Room state machines on HPSS audio.

    The same engine/rules are used, but reference, baseline, Room and history
    belong to each layer. The master music runtime is left untouched.
    """
    runtimes = {name: MusicGBMC(change_threshold=change_threshold,
                                transition_threshold=transition_threshold)
                for name in ("drum", "melody")}
    per_layer = {}
    for name, runtime in runtimes.items():
        rows = layer_features[name]
        for row in rows:
            runtime.observe(row)
        per_layer[name] = runtime.events
    combined = []
    event_rows = []
    n = len(observation_rows)
    # The layer audio was resampled to 11025 Hz and its hop rounds to 331 samples,
    # so layer timestamps can drift relative to the original 30ms observation grid.
    # Align by nearest physical timestamp; do NOT align by frame index.
    aligned = {}
    for name, events in per_layer.items():
        event_times = np.asarray([e.time_s for e in events])
        aligned[name] = []
        for row in observation_rows:
            t = float(row['time_s'])
            k = int(np.searchsorted(event_times, t))
            candidates = [i for i in (k-1, k) if 0 <= i < len(events)]
            if not candidates:
                raise ValueError('Layer feature stream is empty')
            j = min(candidates, key=lambda i: abs(event_times[i]-t))
            aligned[name].append(events[j])
        for e in events:
            if e.event != 'hold' and e.detail != 'initial_reference':
                event_rows.append({
                    'source': name, 'time_s': round(e.time_s, 6),
                    'event': e.event, 'room_before': e.room_before,
                    'room_after': e.room_after, 'reference_id': e.reference_id,
                    'novelty': round(e.novelty, 6)
                })
    for k, row in enumerate(observation_rows):
        d, m = aligned['drum'][k], aligned['melody'][k]
        combined.append({
            'time_s': round(float(row['time_s']), 6),
            'drum_room': d.room_after, 'drum_event': d.event,
            'drum_reference_id': d.reference_id, 'drum_novelty': round(d.novelty, 6),
            'melody_room': m.room_after, 'melody_event': m.event,
            'melody_reference_id': m.reference_id, 'melody_novelty': round(m.novelty, 6),
        })
    event_rows.sort(key=lambda r: (r['time_s'], r['source']))
    metrics = {}
    for name, runtime in runtimes.items():
        metrics[name] = {
            'reference_count': runtime.reference_id,
            'detected_reference_changes': sum(e.detail == 'detected_reference_change' for e in runtime.events),
            'room_transitions': sum(e.event == 'room_transition' for e in runtime.events),
            'final_room': f'{runtime.room:X}',
            'observation_frames': len(runtime.events),
        }
    return combined, event_rows, metrics



class GatedLayerGBMC(MusicGBMC):
    """Experimental onset-gated runtime with recurring rhythmic-position memory.

    No automatic transitions on every 30-ms observation. A candidate event is
    evaluated only at an independently detected onset. Similar rhythmic positions
    can recur without resetting Genesis. Restarts require sustained surprising
    onset events and a cooldown. This is a test heuristic, not a music ground truth.
    """
    def __init__(self, *, change_threshold=3.2, transition_threshold=0.2,
                 min_transition_ms=180., min_restart_ms=2000., persistence=3,
                 route_mode="normal", repeat_limit=3):
        if repeat_limit < 2:
            raise ValueError("repeat_limit must be >= 2")
        self.repeat_limit = repeat_limit
        self.same_room_decisions = 1  # entered the current Room; count only onset-time decisions
        self.reevaluation_count = 0
        if route_mode not in ROUTES:
            raise ValueError(f"route_mode must be one of {tuple(ROUTES)}")
        self.route_mode = route_mode
        super().__init__(change_threshold=change_threshold,
                         transition_threshold=transition_threshold)
        self.min_transition_s = min_transition_ms / 1000.
        self.min_restart_s = min_restart_ms / 1000.
        self.persistence = persistence
        self.last_transition_time = float('-inf')
        self.known_positions = set()
        self.previous_onset_time = None
        self.last_candidate = None
        self.surprise_run = 0
        self.last_reset_reason = 'initial_reference'

    def restart(self, **kwargs) -> Event:
        ev = super().restart(**kwargs)
        self.same_room_decisions = 1
        return ev

    def observe_gated(self, row: dict, *, onset: bool, beat_times: np.ndarray) -> Event:
        t, frame = float(row['time_s']), int(row['frame'])
        rms, flux = float(row['rms']), float(row['spectral_flux'])
        if self.reference is None:
            return self.restart(time_s=t, frame=frame, rms=rms,
                                spectral_flux=flux, reason='initial_reference')
        v = self._features(row)
        novelty = self._novelty(v)
        before = self.room
        event, detail = 'hold', 'no_onset'
        if onset:
            # Quantized onset position relative to local estimated beat grid.
            # Phase bin distinguishes offbeats and repeated displacement patterns.
            if len(beat_times) >= 2:
                k = int(np.searchsorted(beat_times, t))
                nearest_i = min((max(0,k-1), min(k,len(beat_times)-1)),
                                key=lambda j: abs(float(beat_times[j])-t))
                step = float(np.median(np.diff(beat_times)))
                phase = (t-float(beat_times[nearest_i])) / max(step, .001)
                signature = ('beat', round(phase * 8) / 8.)
            elif self.previous_onset_time is not None:
                signature = ('ioi', round((t-self.previous_onset_time)/.06))
            else:
                signature = ('first', 0)
            familiar = signature in self.known_positions
            self.known_positions.add(signature)
            self.previous_onset_time = t
            # 'Unexpected' only when stronger-than-usual acoustic novelty AND
            # rhythmic-position pattern is new; repeated offsets remain familiar.
            surprising = novelty >= self.change_threshold and not familiar
            if surprising:
                self.surprise_run += 1
            else:
                self.surprise_run = 0
            if (self.surprise_run >= self.persistence and
                t-self.last_restart_time >= self.min_restart_s):
                ev = self.restart(time_s=t, frame=frame, rms=rms,
                                  spectral_flux=flux, novelty=novelty,
                                  reason='persistent_new_pattern')
                self.surprise_run = 0
                self.last_transition_time = t
                return ev
            if (not familiar and novelty >= self.transition_threshold and
                t-self.last_transition_time >= self.min_transition_s):
                self.room = route_next(self.room, self.route_mode)
                self.last_transition_time = t
                self.same_room_decisions = 1
                event, detail = 'room_transition', 'novel_rhythmic_position'
            else:
                detail = ('recurring_rhythm' if familiar else
                          'cooldown_or_low_novelty')
                # A decision means a detected onset, not a 30ms audio sample.
                # Consecutive same-Room decisions trigger reconsideration only.
                self.same_room_decisions += 1
                if self.same_room_decisions >= self.repeat_limit:
                    self.reevaluation_count += 1
                    # Do not force a Room change: familiar rhythm may be intentional.
                    # A novel signal would have followed the ordinary transition logic above.
                    event = 'reevaluate'
                    detail = ('repeat_limit_reached_keep_familiar' if familiar else
                              'repeat_limit_reached_keep_insufficient_evidence')
                    self.same_room_decisions = 1  # start a new decision streak
        self.baseline.append(v)
        ev = Event(t,frame,f'{before:X}',f'{self.room:X}',event,
                   self.reference_id,rms,novelty,flux,detail)
        self.events.append(ev)
        return ev


def run_gated_layers(layer_features, layer_timeline, beat_times,
                     *, change_threshold=3.2, transition_threshold=.2,
                     min_transition_ms=180., min_restart_ms=2000., persistence=3,
                     route_mode="normal", repeat_limit=3):
    """Independent history/Room/Genesis per stem proxy, event-gated."""
    outputs=[]; metrics={}
    for name in ('drum','melody'):
        rt=GatedLayerGBMC(change_threshold=change_threshold,
                          transition_threshold=transition_threshold,
                          min_transition_ms=min_transition_ms,
                          min_restart_ms=min_restart_ms,persistence=persistence,
                          route_mode=route_mode, repeat_limit=repeat_limit)
        timeline_times=np.array([r['time_s'] for r in layer_timeline])
        onset_times=timeline_times[[r[f'{name}_onset']==1 for r in layer_timeline]]
        onset_i=0
        for row in layer_features[name]:
            t=float(row['time_s'])
            hop=(float(layer_features[name][1]['time_s']) if len(layer_features[name])>1 else .03)
            # timestamps from two sample rates may drift: map onset to nearest layer frame.
            onset=False
            while onset_i < len(onset_times) and onset_times[onset_i] < t-hop/2:
                onset_i+=1
            if onset_i<len(onset_times) and abs(onset_times[onset_i]-t)<=hop/2:
                onset=True
                onset_i+=1
            rt.observe_gated(row,onset=onset,beat_times=beat_times)
        outputs += [dict(source=name,time_s=round(e.time_s,6),room_before=e.room_before,
                         room_after=e.room_after,event=e.event,reference_id=e.reference_id,
                         novelty=round(e.novelty,6),reason=e.detail) for e in rt.events]
        metrics[name]={
          'reference_count':rt.reference_id,
          'detected_reference_changes':sum(e.detail=='persistent_new_pattern' for e in rt.events),
          'room_transitions':sum(e.event=='room_transition' for e in rt.events),
          'held_frames':sum(e.event in ('hold','reevaluate') for e in rt.events),
          'final_room':f'{rt.room:X}', 'observation_frames':len(rt.events),
          'route_mode':route_mode,
          'reevaluations':rt.reevaluation_count, 'repeat_limit':repeat_limit}
    outputs.sort(key=lambda e:(e['time_s'],e['source']))
    return outputs,metrics

def match_layer_onsets(layer_events: list[dict], tolerance_ms: float = 100.0) -> tuple[list[dict], dict]:
    """Nearest-time unique matching in a ±window, not semantic note pairing."""
    if tolerance_ms < 0:
        raise ValueError('pair tolerance must be nonnegative')
    drum = sorted(float(e['time_s']) for e in layer_events if e['source'] == 'drum_like')
    melody = sorted(float(e['time_s']) for e in layer_events if e['source'] == 'melody_like')
    # Generate candidate pair distances, then shortest first, one-to-one.
    import bisect
    candidates = []
    tol = tolerance_ms / 1000.0
    for i, d in enumerate(drum):
        start = bisect.bisect_left(melody, d - tol)
        stop = bisect.bisect_right(melody, d + tol)
        for j in range(start, stop):
            candidates.append((abs(melody[j] - d), i, j))
    candidates.sort()
    used_d, used_m = set(), set()
    rows = []
    for _, i, j in candidates:
        if i in used_d or j in used_m:
            continue
        used_d.add(i); used_m.add(j)
        delta = 1000.0 * (melody[j] - drum[i])
        rows.append({
            'drum_time_s': round(drum[i], 6),
            'melody_time_s': round(melody[j], 6),
            'offset_ms': round(delta, 3),
            'relation': 'melody_later' if delta > 0.001 else ('melody_earlier' if delta < -0.001 else 'simultaneous'),
        })
    rows.sort(key=lambda r: r['drum_time_s'])
    deltas = np.array([r['offset_ms'] for r in rows], dtype=float)
    summary = {
        'pair_tolerance_ms': tolerance_ms,
        'matched_pairs': len(rows),
        'unmatched_drum_events': len(drum) - len(rows),
        'unmatched_melody_events': len(melody) - len(rows),
        'median_signed_offset_ms': round(float(np.median(deltas)), 3) if len(deltas) else None,
        'median_abs_offset_ms': round(float(np.median(np.abs(deltas))), 3) if len(deltas) else None,
        'note': 'Nearest-time one-to-one heuristic. Does not establish music-theoretic correspondence or intentional syncopation.',
    }
    return rows, summary


def run(input_path: Path, output_dir: Path, *, hop_ms: float = 30.0,
        change_threshold: float = 3.2, transition_threshold: float = 1.3,
        beat_tolerance_ms: float = 50.0, analyze_beats: bool = True,
        analyze_layers: bool = True, pair_tolerance_ms: float = 100.0,
        min_transition_ms: float = 180., min_restart_ms: float = 2000.,
        pattern_persistence: int = 3, route_mode: str = "normal",
        repeat_limit: int = 3) -> dict:
    if route_mode not in ROUTES:
        raise ValueError(f"route_mode must be one of {tuple(ROUTES)}")
    if repeat_limit < 2:
        raise ValueError('repeat_limit must be >= 2')
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
        timeline, layer_events, layer_summary, layer_features = analyze_drum_melody(
            samples, sr, features, runtime.events, beat_times, layer_hop_ms=hop_ms
        )
        write_csv(output_dir / "drum_melody_timeline.csv", timeline,
                  ["time_s", "drum_strength", "melody_strength", "drum_onset",
                   "melody_onset", "gbmc_event", "room_before", "room_after", "reference_id"])
        write_csv(output_dir / "drum_melody_events.csv", layer_events,
                  ["source", "time_s", "nearest_beat_s", "offset_from_beat_ms",
                   "nearest_restart_s", "offset_from_restart_ms"])
        summary["layer_analysis"] = layer_summary
        state_rows, transition_rows, layer_metrics = run_independent_layers(
            layer_features, features, change_threshold=change_threshold,
            transition_threshold=transition_threshold, hop_ms=hop_ms)
        write_csv(output_dir / 'layer_rooms_timeline.csv', state_rows,
                  ['time_s','drum_room','drum_event','drum_reference_id','drum_novelty',
                   'melody_room','melody_event','melody_reference_id','melody_novelty'])
        write_csv(output_dir / 'layer_room_events.csv', transition_rows,
                  ['source','time_s','event','room_before','room_after','reference_id','novelty'])
        pairs, pair_metrics = match_layer_onsets(layer_events, tolerance_ms=pair_tolerance_ms)
        write_csv(output_dir / 'drum_melody_offsets.csv', pairs,
                  ['drum_time_s','melody_time_s','offset_ms','relation'])
        gated_rows,gated_summary=run_gated_layers(
            layer_features,timeline,beat_times,change_threshold=change_threshold,
            transition_threshold=transition_threshold,
            min_transition_ms=min_transition_ms,min_restart_ms=min_restart_ms,
            persistence=pattern_persistence, route_mode=route_mode,
            repeat_limit=repeat_limit)
        write_csv(output_dir/'gated_layer_timeline.csv',gated_rows,
                  ['source','time_s','room_before','room_after','event',
                   'reference_id','novelty','reason'])
        summary['gated_layer_runtimes']=gated_summary
        summary['gated_layer_rules']={
            'min_transition_ms':min_transition_ms,'min_restart_ms':min_restart_ms,
            'pattern_persistence':pattern_persistence,
            'route_mode':route_mode, 'route_hex':ROUTES[route_mode],
            'repeat_limit':repeat_limit, 'repeat_unit':'detected_onset_decisions',
            'note':'Onset-gated; approximate rhythmic position memory; thresholds experimental. '
                   'Legacy counts remain unchanged for comparison.'}
        summary['independent_layer_runtimes'] = layer_metrics
        summary['drum_melody_offset_analysis'] = pair_metrics
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
    ap.add_argument("--pair-tolerance-ms", type=float, default=100.0,
                    help="Max event pairing distance (ms), default 100")
    ap.add_argument('--min-transition-ms',type=float,default=180.)
    ap.add_argument('--min-restart-ms',type=float,default=2000.)
    ap.add_argument('--pattern-persistence',type=int,default=3)
    ap.add_argument('--repeat-limit',type=int,choices=(2,3),default=3,
                    help='Reconsider same Room after 2 or 3 onset-based decisions; never force a transition')
    ap.add_argument('--route',choices=tuple(ROUTES),default='normal',
                    help='Choose normal 16-Room route or bypass 8-Room route for gated drum/melody instances')
    args = ap.parse_args()
    if args.min_transition_ms < 0 or args.min_restart_ms < 0 or args.pattern_persistence < 1:
        ap.error('Minimum times must be >=0 and persistence >=1')
    print(json.dumps(run(args.wav, args.out, hop_ms=args.hop_ms,
                         change_threshold=args.change_threshold,
                         transition_threshold=args.transition_threshold,
                         beat_tolerance_ms=args.beat_tolerance_ms, analyze_beats=not args.no_beats,
                         analyze_layers=not args.no_layers, pair_tolerance_ms=args.pair_tolerance_ms,
                         min_transition_ms=args.min_transition_ms,
                         min_restart_ms=args.min_restart_ms,
                         pattern_persistence=args.pattern_persistence,
                         route_mode=args.route, repeat_limit=args.repeat_limit),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
