#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GBMCCQSD × MediaPipe: unsupervised prototype
--------------------------------------------

Input:
  - one video file, or a directory containing videos
Output:
  - landmarks.csv
  - state_timeseries.csv
  - q_timeseries.csv
  - habit_summary.csv
  - model_summary.json

No teacher labels are required.

This is an operational prototype, not a proof of the theory.
The current implementation uses a 1D latent trajectory and interprets ∇ as
an along-trajectory derivative. It is intentionally simple so that each
mapping can be inspected and replaced later.

Operational mapping
-------------------
G : memory availability / effective neighbor count
B : "margin" / weighted spread of candidate future transitions
M : trial state / latent state x(t)
C1: predicted candidate transition from similar past states
C2: actually observed next transition
Q : responsibility-direction proxy, Q = ∇M - C2
S : next-state prediction = current state + C1
D : self-reference range / weighted radius to similar past states

Full fitted equation
--------------------
g * Db/Dt =
    - alpha_s * grad_m
    + beta_s * d * lap_b
    + alpha_e * DeltaC
    + beta_e * Q
    + gamma_e * DeltaC * Q

where DeltaC = C1 - C2.

Since all terms except the five coefficients are constructed from the
observed sequence, the coefficients can be fitted with linear regression
without teacher labels.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

try:
    import mediapipe as mp
except ImportError as e:
    raise SystemExit(
        "mediapipe is not installed. Run: pip install -r requirements.txt"
    ) from e

from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.neighbors import NearestNeighbors

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}


def list_videos(path: Path):
    if path.is_file():
        return [path]
    return sorted([p for p in path.rglob("*") if p.suffix.lower() in VIDEO_EXTS])


def angle3(a, b, c):
    """Angle ABC in radians."""
    ba = a - b
    bc = c - b
    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)
    if nba < 1e-9 or nbc < 1e-9:
        return np.nan
    cosv = np.dot(ba, bc) / (nba * nbc)
    return float(np.arccos(np.clip(cosv, -1.0, 1.0)))


def extract_video(video_path: Path, pose, min_visibility=0.5):
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not np.isfinite(fps) or fps <= 0:
        fps = 30.0

    rows = []
    frame_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = pose.process(rgb)

        row = {
            "video": video_path.name,
            "frame": frame_idx,
            "time_sec": frame_idx / fps,
            "detected": 0,
        }

        if result.pose_landmarks:
            row["detected"] = 1
            for i, lm in enumerate(result.pose_landmarks.landmark):
                row[f"x{i}"] = lm.x
                row[f"y{i}"] = lm.y
                row[f"z{i}"] = lm.z
                row[f"v{i}"] = lm.visibility
        rows.append(row)
        frame_idx += 1

    cap.release()
    return pd.DataFrame(rows), fps


def normalize_landmarks(df):
    """
    Translation: midpoint of hips -> origin.
    Scale: shoulder width, fallback hip width.
    We keep x,y,z for 33 landmarks.
    """
    coords = np.full((len(df), 33, 3), np.nan, dtype=float)
    vis = np.full((len(df), 33), np.nan, dtype=float)

    for i in range(33):
        for j, ax in enumerate(("x", "y", "z")):
            col = f"{ax}{i}"
            if col in df:
                coords[:, i, j] = df[col].to_numpy(float)
        vcol = f"v{i}"
        if vcol in df:
            vis[:, i] = df[vcol].to_numpy(float)

    # MediaPipe indices: shoulders 11,12; hips 23,24
    hip_center = (coords[:, 23] + coords[:, 24]) / 2.0
    shoulder_w = np.linalg.norm(coords[:, 11] - coords[:, 12], axis=1)
    hip_w = np.linalg.norm(coords[:, 23] - coords[:, 24], axis=1)
    scale = shoulder_w.copy()
    bad = ~np.isfinite(scale) | (scale < 1e-4)
    scale[bad] = hip_w[bad]
    scale[~np.isfinite(scale) | (scale < 1e-4)] = 1.0

    norm = (coords - hip_center[:, None, :]) / scale[:, None, None]
    return norm, vis


def interpolate_1d(a):
    s = pd.Series(a)
    return s.interpolate(limit_direction="both").to_numpy(float)


def make_pose_features(df, fps):
    coords, vis = normalize_landmarks(df)

    # Interpolate each landmark coordinate independently.
    for i in range(33):
        for j in range(3):
            coords[:, i, j] = interpolate_1d(coords[:, i, j])

    # Selected joints: shoulders, elbows, wrists, hips, knees, ankles + nose.
    idx = [0, 11,12,13,14,15,16,23,24,25,26,27,28]
    flat = coords[:, idx, :].reshape(len(df), -1)

    # Angles (radians)
    angle_specs = {
        "elbow_l": (11,13,15),
        "elbow_r": (12,14,16),
        "shoulder_l": (13,11,23),
        "shoulder_r": (14,12,24),
        "hip_l": (11,23,25),
        "hip_r": (12,24,26),
        "knee_l": (23,25,27),
        "knee_r": (24,26,28),
    }
    angles = []
    angle_names = []
    for name, (a,b,c) in angle_specs.items():
        vals = np.array([angle3(coords[t,a], coords[t,b], coords[t,c]) for t in range(len(df))])
        vals = interpolate_1d(vals)
        angles.append(vals)
        angle_names.append(name)

    angles = np.column_stack(angles)

    # Center-of-body proxy.
    torso_center = (coords[:,11] + coords[:,12] + coords[:,23] + coords[:,24]) / 4.0

    # Velocity features.
    dt = 1.0 / fps
    velocity = np.gradient(flat, dt, axis=0)
    vel_mag = np.linalg.norm(velocity.reshape(len(df), -1), axis=1)

    features = np.column_stack([flat, angles, torso_center, vel_mag])

    names = []
    for i in idx:
        names += [f"lm{i}_x", f"lm{i}_y", f"lm{i}_z"]
    names += angle_names
    names += ["torso_x","torso_y","torso_z","pose_speed"]

    fdf = pd.DataFrame(features, columns=names)
    fdf.insert(0, "time_sec", df["time_sec"].to_numpy())
    fdf.insert(0, "frame", df["frame"].to_numpy())
    fdf.insert(0, "video", df["video"].to_numpy())
    return fdf


def smooth(x, win=7):
    win = max(3, int(win))
    if win % 2 == 0:
        win += 1
    return pd.Series(x).rolling(win, center=True, min_periods=1).mean().to_numpy(float)


def build_lag_embedding(x, lag=2, embed_dim=4):
    n = len(x)
    emb = np.full((n, embed_dim), np.nan, dtype=float)
    for i in range(embed_dim):
        shift = i * lag
        emb[shift:, i] = x[:n-shift]
    return emb


def effective_sample_size(weights):
    s1 = np.sum(weights)
    s2 = np.sum(weights**2)
    if s2 <= 1e-12:
        return 0.0
    return float((s1*s1)/s2)


def local_candidates(x, emb, k=20, exclusion=15):
    """
    For each t, find similar historical states and collect their next transition.
    Search is within the same concatenated series; temporal exclusion prevents
    trivial near-neighbor leakage.
    """
    n = len(x)
    valid_idx = np.where(np.all(np.isfinite(emb), axis=1))[0]
    valid_idx = valid_idx[valid_idx < n-1]
    X = emb[valid_idx]

    nn = NearestNeighbors(n_neighbors=min(max(k*4, k+1), len(valid_idx)))
    nn.fit(X)

    c1 = np.full(n, np.nan)
    b = np.full(n, np.nan)
    d = np.full(n, np.nan)
    g = np.full(n, np.nan)

    for t in valid_idx:
        dists, inds = nn.kneighbors(emb[t:t+1], return_distance=True)
        cand_idx = valid_idx[inds[0]]

        keep = []
        keep_dist = []
        for ci, dist in zip(cand_idx, dists[0]):
            if ci == t or abs(ci - t) <= exclusion:
                continue
            if ci >= n-1:
                continue
            keep.append(ci)
            keep_dist.append(dist)
            if len(keep) >= k:
                break

        if len(keep) < 3:
            continue

        keep = np.asarray(keep, dtype=int)
        keep_dist = np.asarray(keep_dist, dtype=float)
        fut = x[keep+1] - x[keep]

        sigma = np.median(keep_dist) + 1e-9
        w = np.exp(-(keep_dist**2)/(2*sigma*sigma))
        w = w / (w.sum() + 1e-12)

        mu = float(np.sum(w*fut))
        var = float(np.sum(w*(fut-mu)**2))

        c1[t] = mu
        b[t] = math.sqrt(max(var, 0.0))
        d[t] = float(np.sum(w*keep_dist))
        g[t] = effective_sample_size(w) / max(k, 1)

    return c1, b, d, g


def fit_unsupervised_equation(ts, ridge=1e-6):
    """
    Fit:
      g*DbDt =
      -alpha_s*grad_m + beta_s*d*lap_b
      +alpha_e*DeltaC + beta_e*Q + gamma_e*DeltaC*Q

    Here the coefficients are fitted from the sequence itself. No class labels.
    """
    required = ["g","DbDt","grad_m","d","lap_b","DeltaC","Q"]
    valid = np.ones(len(ts), dtype=bool)
    for c in required:
        valid &= np.isfinite(ts[c].to_numpy(float))

    sub = ts.loc[valid].copy()
    if len(sub) < 30:
        raise ValueError("Not enough valid frames to fit the model (need >= 30).")

    y = (sub["g"] * sub["DbDt"]).to_numpy(float)

    # design columns correspond directly to coefficients
    X = np.column_stack([
        -sub["grad_m"].to_numpy(float),
        sub["d"].to_numpy(float) * sub["lap_b"].to_numpy(float),
        sub["DeltaC"].to_numpy(float),
        sub["Q"].to_numpy(float),
        sub["DeltaC"].to_numpy(float) * sub["Q"].to_numpy(float),
    ])

    # chronological 70/30 split
    cut = max(20, int(len(sub)*0.70))
    Xtr, Xte = X[:cut], X[cut:]
    ytr, yte = y[:cut], y[cut:]

    model = Ridge(alpha=ridge, fit_intercept=False)
    model.fit(Xtr, ytr)

    pred_tr = model.predict(Xtr)
    pred_te = model.predict(Xte) if len(Xte) else np.array([])

    coef = model.coef_
    summary = {
        "alpha_s": float(coef[0]),
        "beta_s": float(coef[1]),
        "alpha_e": float(coef[2]),
        "beta_e": float(coef[3]),
        "gamma_e": float(coef[4]),
        "train_n": int(len(Xtr)),
        "test_n": int(len(Xte)),
        "train_r2": float(r2_score(ytr, pred_tr)) if len(Xtr) > 1 else None,
        "train_rmse": float(np.sqrt(mean_squared_error(ytr, pred_tr))),
        "test_r2": float(r2_score(yte, pred_te)) if len(Xte) > 1 else None,
        "test_rmse": float(np.sqrt(mean_squared_error(yte, pred_te))) if len(Xte) else None,
    }

    full_pred = np.full(len(ts), np.nan)
    full_pred[np.where(valid)[0]] = model.predict(X)
    ts = ts.copy()
    ts["lhs_g_DbDt"] = ts["g"] * ts["DbDt"]
    ts["rhs_fitted"] = full_pred
    ts["equation_residual"] = ts["lhs_g_DbDt"] - ts["rhs_fitted"]
    return ts, summary


def decompose_habit(ts, context_k=6, random_state=42):
    """
    Unsupervised decomposition:
      Q_t = Q_habit + Q_context(cluster_t) + epsilon_t

    Q_habit: global robust center (median)
    Q_context: context-cluster mean deviation from global center
    context: KMeans on [latent_x, C1, B, D]
    """
    valid = (
        np.isfinite(ts["Q"].to_numpy(float)) &
        np.isfinite(ts["latent_x"].to_numpy(float)) &
        np.isfinite(ts["C1"].to_numpy(float)) &
        np.isfinite(ts["B"].to_numpy(float)) &
        np.isfinite(ts["D"].to_numpy(float))
    )

    sub = ts.loc[valid].copy()
    if len(sub) < max(30, context_k*5):
        raise ValueError("Not enough valid points for habit/context decomposition.")

    X = sub[["latent_x","C1","B","D"]].to_numpy(float)
    X = StandardScaler().fit_transform(X)
    k = min(context_k, max(2, len(sub)//10))
    km = KMeans(n_clusters=k, n_init=20, random_state=random_state)
    labels = km.fit_predict(X)

    q = sub["Q"].to_numpy(float)
    q_habit = float(np.median(q))

    ctx_effect = {}
    q_context = np.empty(len(sub), dtype=float)
    for c in range(k):
        mask = labels == c
        effect = float(np.mean(q[mask]) - q_habit)
        ctx_effect[int(c)] = effect
        q_context[mask] = effect

    eps = q - q_habit - q_context

    out = ts.copy()
    out["context_cluster"] = np.nan
    out["Q_habit"] = np.nan
    out["Q_context"] = np.nan
    out["epsilon"] = np.nan
    idx = np.where(valid)[0]
    out.loc[idx, "context_cluster"] = labels
    out.loc[idx, "Q_habit"] = q_habit
    out.loc[idx, "Q_context"] = q_context
    out.loc[idx, "epsilon"] = eps

    summary = pd.DataFrame([{
        "Q_habit": q_habit,
        "Q_std": float(np.std(q)),
        "epsilon_std": float(np.std(eps)),
        "n_valid": int(len(q)),
        "context_clusters": int(k),
        "context_effects": json.dumps(ctx_effect, ensure_ascii=False),
    }])
    return out, summary


def process_series(feature_df, fps, args):
    # Standardize pose features, PCA -> one-dimensional latent state.
    meta = ["video","frame","time_sec"]
    X = feature_df.drop(columns=meta).to_numpy(float)
    X = StandardScaler().fit_transform(X)
    pca = PCA(n_components=1, random_state=42)
    latent = pca.fit_transform(X)[:,0]
    latent = smooth(latent, args.smooth)

    dt = 1.0 / fps
    # M is the trial state in the reduced 1D model.
    m = latent.copy()
    grad_m = np.gradient(m, dt)

    emb = build_lag_embedding(latent, lag=args.lag, embed_dim=args.embed_dim)
    c1, b, d, g = local_candidates(
        latent, emb, k=args.neighbors, exclusion=args.exclusion
    )

    c2 = np.full(len(latent), np.nan)
    c2[:-1] = (latent[1:] - latent[:-1]) / dt

    # Q = ∇M - C2 (operational 1D version)
    q = grad_m - c2

    b_sm = smooth(interpolate_1d(b), args.smooth)
    dbdt = np.gradient(b_sm, dt)
    lap_b = np.gradient(dbdt, dt)

    delta_c = c1 - c2
    s_pred = latent + np.nan_to_num(c1, nan=0.0) * dt

    ts = pd.DataFrame({
        "video": feature_df["video"].to_numpy(),
        "frame": feature_df["frame"].to_numpy(),
        "time_sec": feature_df["time_sec"].to_numpy(),
        "latent_x": latent,
        "G": g,
        "B": b_sm,
        "M": m,
        "C1": c1,
        "C2": c2,
        "Q": q,
        "S": s_pred,
        "D": d,
        "g": g,
        "b": b_sm,
        "m": m,
        "c1": c1,
        "c2": c2,
        "d": d,
        "grad_m": grad_m,
        "DbDt": dbdt,
        "lap_b": lap_b,
        "DeltaC": delta_c,
    })

    ts, model_summary = fit_unsupervised_equation(ts, ridge=args.ridge)
    ts, habit_summary = decompose_habit(ts, context_k=args.context_k)

    model_summary["pca_explained_variance_ratio"] = float(
        pca.explained_variance_ratio_[0]
    )
    return ts, habit_summary, model_summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", help="video file or directory")
    p.add_argument("--output", default="gbmccqsd_output")
    p.add_argument("--model-complexity", type=int, default=2, choices=[0,1,2])
    p.add_argument("--min-detection-confidence", type=float, default=0.5)
    p.add_argument("--min-tracking-confidence", type=float, default=0.5)
    p.add_argument("--neighbors", type=int, default=20)
    p.add_argument("--exclusion", type=int, default=15)
    p.add_argument("--lag", type=int, default=2)
    p.add_argument("--embed-dim", type=int, default=4)
    p.add_argument("--smooth", type=int, default=7)
    p.add_argument("--context-k", type=int, default=6)
    p.add_argument("--ridge", type=float, default=1e-6)
    args = p.parse_args()

    inp = Path(args.input)
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    videos = list_videos(inp)
    if not videos:
        raise SystemExit("No video files found.")

    mp_pose = mp.solutions.pose
    landmark_parts = []
    feature_parts = []
    fps_values = []

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=args.model_complexity,
        enable_segmentation=False,
        min_detection_confidence=args.min_detection_confidence,
        min_tracking_confidence=args.min_tracking_confidence,
    ) as pose:
        for video in videos:
            print(f"[MediaPipe] {video}")
            ldf, fps = extract_video(video, pose)
            if len(ldf) < 10:
                print(f"  skipped: too short ({len(ldf)} frames)")
                continue
            fdf = make_pose_features(ldf, fps)
            landmark_parts.append(ldf)
            feature_parts.append(fdf)
            fps_values.append(fps)

    if not feature_parts:
        raise SystemExit("No usable video was extracted.")

    # For the first prototype we concatenate sessions.
    # If FPS differs, use median FPS for derivatives.
    landmarks = pd.concat(landmark_parts, ignore_index=True)
    features = pd.concat(feature_parts, ignore_index=True)
    fps = float(np.median(fps_values))

    landmarks.to_csv(outdir/"landmarks.csv", index=False)
    features.to_csv(outdir/"pose_features.csv", index=False)

    ts, habit_summary, model_summary = process_series(features, fps, args)

    ts.to_csv(outdir/"q_timeseries.csv", index=False)
    habit_summary.to_csv(outdir/"habit_summary.csv", index=False)
    (outdir/"model_summary.json").write_text(
        json.dumps(model_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n=== fitted equation ===")
    print(json.dumps(model_summary, ensure_ascii=False, indent=2))
    print("\n=== habit summary ===")
    print(habit_summary.to_string(index=False))
    print(f"\nSaved to: {outdir.resolve()}")


if __name__ == "__main__":
    main()
