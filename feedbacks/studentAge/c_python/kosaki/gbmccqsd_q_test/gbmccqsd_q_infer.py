#!/usr/bin/env python3
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

EPS = 1e-12

def infer_q(df, alpha_s, beta_s, alpha_e, beta_e, gamma_e):
    d = df["d"].to_numpy(float)
    lap_b = df["lap_b"].to_numpy(float)
    rself = df["R_self"].to_numpy(float)
    c1 = df["c1"].to_numpy(float)
    renv = df["R_env"].to_numpy(float)

    A0 = (beta_s*d*lap_b - rself) / alpha_s
    H = A0 - c1

    q = np.full(len(df), np.nan)
    root1 = np.full(len(df), np.nan)
    root2 = np.full(len(df), np.nan)
    disc_out = np.full(len(df), np.nan)

    if abs(gamma_e) < EPS:
        den = alpha_e + beta_e
        if abs(den) < EPS:
            raise ValueError("alpha_e + beta_e must be non-zero")
        q = (alpha_e*H + renv) / den
        root1 = q.copy()
    else:
        a = gamma_e
        b = alpha_e + beta_e - gamma_e*H
        c = -(alpha_e*H + renv)
        disc = b*b - 4*a*c
        disc_out = disc.copy()

        prev = None
        for i in range(len(df)):
            if disc[i] < 0:
                continue
            s = np.sqrt(disc[i])
            r1 = (-b[i] + s)/(2*a)
            r2 = (-b[i] - s)/(2*a)
            root1[i], root2[i] = r1, r2
            if prev is None or not np.isfinite(prev):
                chosen = r1 if abs(r1) <= abs(r2) else r2
            else:
                chosen = r1 if abs(r1-prev) <= abs(r2-prev) else r2
            q[i] = chosen
            prev = chosen

    out = df.copy()
    out["A0"] = A0
    out["H"] = H
    out["q_root1"] = root1
    out["q_root2"] = root2
    out["q_discriminant"] = disc_out
    out["Q_inferred"] = q

    den = alpha_e + gamma_e*q
    rhs = H + (renv - beta_e*q)/den
    out["fixed_point_residual"] = q-rhs
    return out

def decompose_q(df, context_cols):
    valid = np.isfinite(df["Q_inferred"].to_numpy(float))
    q = df.loc[valid, "Q_inferred"].to_numpy(float)

    X_parts = [np.ones((len(q), 1))]
    for col in context_cols:
        X_parts.append(df.loc[valid, col].to_numpy(float).reshape(-1,1))
    X = np.hstack(X_parts)

    coef, *_ = np.linalg.lstsq(X, q, rcond=None)
    fit = X @ coef
    resid = q-fit

    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((q-q.mean())**2))
    r2 = 1-ss_res/ss_tot if ss_tot > EPS else float("nan")

    out = df.copy()
    out["Q_hat_habit_context"] = np.nan
    out["epsilon_hat"] = np.nan
    out.loc[valid, "Q_hat_habit_context"] = fit
    out.loc[valid, "epsilon_hat"] = resid

    summary = {
        "Q_habit": float(coef[0]),
        "context_coefficients": {
            context_cols[i]: float(coef[i+1]) for i in range(len(context_cols))
        },
        "rmse": float(np.sqrt(np.mean(resid**2))),
        "r2": r2,
        "mean_abs_fixed_point_residual": float(
            np.nanmean(np.abs(out["fixed_point_residual"].to_numpy(float)))
        )
    }
    return out, summary

def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--alpha-s", type=float, required=True)
    p.add_argument("--beta-s", type=float, required=True)
    p.add_argument("--alpha-e", type=float, required=True)
    p.add_argument("--beta-e", type=float, required=True)
    p.add_argument("--gamma-e", type=float, required=True)
    p.add_argument("--context-cols", default="")
    p.add_argument("--out-prefix", default="q_result")
    a = p.parse_args()

    df = pd.read_csv(a.csv)
    cols = [s.strip() for s in a.context_cols.split(",") if s.strip()]

    inferred = infer_q(df, a.alpha_s, a.beta_s, a.alpha_e, a.beta_e, a.gamma_e)
    out, summary = decompose_q(inferred, cols)

    out.to_csv(a.out_prefix + ".csv", index=False)
    Path(a.out_prefix + ".json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
