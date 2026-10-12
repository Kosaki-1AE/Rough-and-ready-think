#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, math, re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

DATE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")

def date_key(path):
    m = DATE_RE.search(path.stem)
    if not m:
        return 99999999
    yymmdd = m.group(1)
    return (2000+int(yymmdd[:2]))*10000 + int(yymmdd[2:4])*100 + int(yymmdd[4:6])

def clean_md(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"!\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"^[#>*\-]+\s*", "", text, flags=re.M)
    text = text.replace("**","").replace("__","").replace("`","")
    return re.sub(r"\s+", " ", text).strip()

def split_chunks(text, min_chars=40, max_chars=1200):
    out=[]
    for b in re.split(r"\n\s*\n+", text):
        b=clean_md(b)
        if len(b)<min_chars: 
            continue
        if len(b)<=max_chars:
            out.append(b)
        else:
            sents=re.split(r"(?<=[。！？!?])\s*", b)
            buf=""
            for s in sents:
                if len(buf)+len(s)+1>max_chars and len(buf)>=min_chars:
                    out.append(buf.strip()); buf=s
                else:
                    buf=(buf+" "+s).strip()
            if len(buf)>=min_chars:
                out.append(buf)
    return out

def load_chunks(root, include_regex=None, exclude_regex=None, min_chars=40, max_chars=1200):
    root=Path(root)
    files=sorted(root.rglob("*.md")) if root.is_dir() else [root]
    inc=re.compile(include_regex) if include_regex else None
    exc=re.compile(exclude_regex) if exclude_regex else None
    rows=[]
    for p in files:
        rel=str(p.relative_to(root)) if root.is_dir() else p.name
        if inc and not inc.search(rel): 
            continue
        if exc and exc.search(rel):
            continue
        try:
            txt=p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i,ch in enumerate(split_chunks(txt,min_chars,max_chars)):
            rows.append((date_key(p),rel,p.name,i,ch))
    rows.sort(key=lambda x:(x[0],x[1],x[3]))
    return rows

def delay_embed(x, lag=2, dim=4):
    n=len(x)
    e=np.full((n,dim),np.nan)
    for j in range(dim):
        s=j*lag
        e[s:,j]=x[:n-s]
    return e

def effective_n(w):
    return float((w.sum()**2)/(np.sum(w*w)+1e-12))

def hist_candidates(m, emb, k=20, exclusion=4):
    n=len(m)
    c1=np.full(n,np.nan); b=np.full(n,np.nan); d=np.full(n,np.nan); g=np.full(n,np.nan)
    valid=np.where(np.all(np.isfinite(emb),axis=1))[0]
    for t in valid:
        hist=valid[(valid<t-exclusion)&(valid<n-1)]
        if len(hist)<3: 
            continue
        dist=np.linalg.norm(emb[hist]-emb[t],axis=1)
        order=np.argsort(dist)[:k]
        idx=hist[order]; dist=dist[order]
        fut=m[idx+1]-m[idx]
        sigma=np.median(dist)+1e-9
        w=np.exp(-(dist**2)/(2*sigma*sigma)); w=w/(w.sum()+1e-12)
        mu=float(np.sum(w*fut))
        var=float(np.sum(w*(fut-mu)**2))
        c1[t]=mu
        b[t]=math.sqrt(max(var,0.0))
        d[t]=float(np.sum(w*dist))
        g[t]=effective_n(w)/max(k,1)
    return c1,b,d,g

def interp(x):
    return pd.Series(x).interpolate(limit_direction="both").to_numpy(float)

def smooth(x,win=7):
    win=max(3,int(win))
    if win%2==0: win+=1
    return pd.Series(x).rolling(win,center=True,min_periods=1).mean().to_numpy(float)

def fit_equation(df,ridge=1e-6):
    req=["g","DbDt","grad_m","d","lap_b","DeltaC","Q"]
    valid=np.ones(len(df),dtype=bool)
    for c in req:
        valid &= np.isfinite(df[c].to_numpy(float))
    sub=df.loc[valid].copy()
    if len(sub)<30:
        raise ValueError("Not enough valid states to fit equation (need >=30).")
    y=(sub["g"]*sub["DbDt"]).to_numpy(float)
    X=np.column_stack([
        -sub["grad_m"].to_numpy(float),
        sub["d"].to_numpy(float)*sub["lap_b"].to_numpy(float),
        sub["DeltaC"].to_numpy(float),
        sub["Q"].to_numpy(float),
        sub["DeltaC"].to_numpy(float)*sub["Q"].to_numpy(float),
    ])
    cut=max(20,int(len(sub)*0.7))
    model=Ridge(alpha=ridge,fit_intercept=False).fit(X[:cut],y[:cut])
    pred_all=model.predict(X)
    pred_tr=model.predict(X[:cut]); pred_te=model.predict(X[cut:]) if len(X[cut:]) else np.array([])
    coef=model.coef_
    summ={
        "alpha_s":float(coef[0]),"beta_s":float(coef[1]),
        "alpha_e":float(coef[2]),"beta_e":float(coef[3]),"gamma_e":float(coef[4]),
        "train_n":int(cut),"test_n":int(len(X)-cut),
        "train_r2":float(r2_score(y[:cut],pred_tr)) if cut>1 else None,
        "train_rmse":float(np.sqrt(mean_squared_error(y[:cut],pred_tr))),
        "test_r2":float(r2_score(y[cut:],pred_te)) if len(pred_te)>1 else None,
        "test_rmse":float(np.sqrt(mean_squared_error(y[cut:],pred_te))) if len(pred_te) else None,
    }
    out=df.copy()
    out["lhs_g_DbDt"]=out["g"]*out["DbDt"]
    out["rhs_fitted"]=np.nan
    out.loc[np.where(valid)[0],"rhs_fitted"]=pred_all
    out["equation_residual"]=out["lhs_g_DbDt"]-out["rhs_fitted"]
    return out,summ

def decompose_habit(df,context_k=8):
    feat=[c for c in ["z0","z1","z2","z3","C1","B","D"] if c in df.columns]
    valid=np.isfinite(df["Q"].to_numpy(float))
    for c in feat:
        valid &= np.isfinite(df[c].to_numpy(float))
    sub=df.loc[valid].copy()
    if len(sub)<max(30,context_k*5):
        raise ValueError("Not enough valid states for habit/context decomposition.")
    X=StandardScaler().fit_transform(sub[feat].to_numpy(float))
    k=min(context_k,max(2,len(sub)//10))
    labels=KMeans(n_clusters=k,n_init=20,random_state=42).fit_predict(X)
    q=sub["Q"].to_numpy(float)
    habit=float(np.median(q))
    qctx=np.zeros(len(q)); effects={}
    for c in range(k):
        mask=labels==c
        eff=float(np.mean(q[mask])-habit)
        effects[int(c)]=eff
        qctx[mask]=eff
    eps=q-habit-qctx
    out=df.copy()
    out["context_cluster"]=np.nan; out["Q_habit"]=np.nan; out["Q_context"]=np.nan; out["epsilon"]=np.nan
    idx=np.where(valid)[0]
    out.loc[idx,"context_cluster"]=labels
    out.loc[idx,"Q_habit"]=habit
    out.loc[idx,"Q_context"]=qctx
    out.loc[idx,"epsilon"]=eps
    return out,{
        "Q_habit":habit,
        "Q_std":float(np.std(q)),
        "epsilon_std":float(np.std(eps)),
        "n_valid":int(len(q)),
        "context_clusters":int(k),
        "context_effects":effects
    }

def write_examples(df,path,top_n=30):
    v=df[np.isfinite(df["Q"].to_numpy(float))].copy()
    if v.empty:
        Path(path).write_text("# Habit examples\n\nNo valid Q.\n",encoding="utf-8"); return
    habit=float(v["Q_habit"].dropna().iloc[0]) if v["Q_habit"].notna().any() else float(np.median(v["Q"]))
    v["score"]=np.abs(v["Q"]-habit)+np.abs(v["epsilon"].fillna(0))
    best=v.nsmallest(top_n,"score")
    lines=["# Q_habit representative examples","",f"- Estimated Q_habit: `{habit:.6f}`",""]
    for rank,(_,r) in enumerate(best.iterrows(),1):
        lines += [f"## {rank}. {r['relpath']} / chunk {int(r['chunk_idx'])}",
                  "",f"- Q: `{r['Q']:.6f}`","",str(r["text"]),""] 
    Path(path).write_text("\n".join(lines),encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--output",default="text_gbmccqsd_out")
    ap.add_argument("--include-regex",default=None)
    ap.add_argument("--exclude-regex",default=r"(^|/)(tools|Resources|\.obsidian)(/|$)")
    ap.add_argument("--min-chars",type=int,default=40)
    ap.add_argument("--max-chars",type=int,default=1200)
    ap.add_argument("--max-features",type=int,default=30000)
    ap.add_argument("--svd-dim",type=int,default=32)
    ap.add_argument("--lag",type=int,default=2)
    ap.add_argument("--embed-dim",type=int,default=4)
    ap.add_argument("--neighbors",type=int,default=20)
    ap.add_argument("--exclusion",type=int,default=4)
    ap.add_argument("--smooth",type=int,default=7)
    ap.add_argument("--context-k",type=int,default=8)
    ap.add_argument("--ridge",type=float,default=1e-6)
    args=ap.parse_args()

    rows=load_chunks(args.input,args.include_regex,args.exclude_regex,args.min_chars,args.max_chars)
    if len(rows)<50:
        raise SystemExit(f"Too few chunks: {len(rows)}")

    texts=[r[4] for r in rows]
    vec=TfidfVectorizer(analyzer="char",ngram_range=(2,5),min_df=2,max_df=0.98,
                        max_features=args.max_features,sublinear_tf=True,norm="l2")
    X=vec.fit_transform(texts)
    dim=min(args.svd_dim,max(1,X.shape[0]-1),max(1,X.shape[1]-1))
    svd=TruncatedSVD(n_components=dim,random_state=42)
    Z=StandardScaler().fit_transform(svd.fit_transform(X))
    m=Z[:,0]

    meta=pd.DataFrame({
        "date_key":[r[0] for r in rows],
        "relpath":[r[1] for r in rows],
        "file":[r[2] for r in rows],
        "chunk_idx":[r[3] for r in rows],
        "text":[r[4] for r in rows],
        "M":m
    })

    emb=delay_embed(m,args.lag,args.embed_dim)
    c1,b,d,g=hist_candidates(m,emb,args.neighbors,args.exclusion)
    c2=np.full(len(m),np.nan); c2[:-1]=m[1:]-m[:-1]
    grad_m=np.gradient(m)
    q=grad_m-c2
    s=m+np.nan_to_num(c1,nan=0.0)
    bfill=smooth(interp(b),args.smooth)
    dbdt=np.gradient(bfill); lap_b=np.gradient(dbdt)

    df=meta.copy()
    df["G"]=g; df["B"]=bfill; df["C1"]=c1; df["C2"]=c2; df["Q"]=q; df["S"]=s; df["D"]=d
    df["g"]=g; df["b"]=bfill; df["m"]=m; df["c1"]=c1; df["c2"]=c2; df["d"]=d
    df["grad_m"]=grad_m; df["DbDt"]=dbdt; df["lap_b"]=lap_b; df["DeltaC"]=c1-c2
    for j in range(min(4,Z.shape[1])):
        df[f"z{j}"]=Z[:,j]

    df,eq=fit_equation(df,args.ridge)
    df,habit=decompose_habit(df,args.context_k)

    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    df.to_csv(out/"q_timeseries.csv",index=False)
    pd.DataFrame([{
        "Q_habit":habit["Q_habit"],"Q_std":habit["Q_std"],"epsilon_std":habit["epsilon_std"],
        "n_valid":habit["n_valid"],"context_clusters":habit["context_clusters"],
        "context_effects":json.dumps(habit["context_effects"],ensure_ascii=False)
    }]).to_csv(out/"habit_summary.csv",index=False)
    summary={
        "n_chunks":len(df),
        "tfidf_features":int(X.shape[1]),
        "svd_dim":int(dim),
        "svd_explained_variance_sum":float(np.sum(svd.explained_variance_ratio_)),
        "equation":eq,
        "habit":habit,
        "definitions":{
            "G":"effective historical analogue count",
            "B":"spread of candidate next transitions",
            "M":"current latent text state",
            "C1":"predicted next transition from historical analogues",
            "C2":"observed next transition",
            "Q":"grad(M)-C2 transition-bias proxy",
            "S":"M+C1 predicted next state",
            "D":"historical reference radius"
        }
    }
    (out/"model_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    write_examples(df,out/"habit_examples.md")
    report=f"""# GBMCCQSD Text Report

- chunks: {len(df)}
- test R2: {eq['test_r2']}
- test RMSE: {eq['test_rmse']}
- Q_habit: {habit['Q_habit']:.6f}
- Q std: {habit['Q_std']:.6f}
- epsilon std: {habit['epsilon_std']:.6f}

Interpretation:
- test R2 > 0: current equation/definitions retain some predictive structure on later chronological data.
- test R2 <= 0: current equation and/or operational definitions do not generalize well.
- Q_habit is a habit candidate, not yet proof of a person-specific habit.
"""
    (out/"REPORT.md").write_text(report,encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print(f"Saved to {out.resolve()}")

if __name__=="__main__":
    main()
