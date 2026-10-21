#!/usr/bin/env python3
"""Exploratory ART-inspired + BAM-inspired + predictive-coding-inspired hybrid.
Not an implementation of the original algorithms or a validation of GBMC/CQSD.
Standard library only. No history arrays used in decisions; traces are output only.
"""
import argparse, csv, math
from pathlib import Path

def clip(x, lo=-1., hi=1.): return max(lo,min(hi,x))
def tanh(x): return math.tanh(x)
def mismatch(g,c): return abs(g-c)/2.0  # [0,1] for states in [-1,1]

def simulate(seed, target, drive, coupling, eta, vigilance, steps, mode, tol):
    g,c=seed,0.0
    records=[]; status='max_steps'; resets=0; streak=0
    for t in range(steps):
        error=mismatch(g,c)
        # ART-inspired: mismatch-triggered reset (no historical candidate list)
        reset=mode=='hybrid' and error>vigilance
        if reset:
            # target-conditioned reset of top-down expectation; current inputs only
            c=tanh(target)
            resets+=1
        # Predictive coding inspired: correction proportional to current discrepancy
        correction=eta*(c-g) if mode=='hybrid' else 0.0
        # BAM inspired: bidirectional recurrent coupling, but no energy guarantee
        if mode=='bottom_only':
            gn=tanh(drive*g+target); cn=0.0
        elif mode=='top_only':
            gn=g; cn=tanh(drive*c+target)
        else:
            gn=tanh(drive*g+coupling*c+target+correction)
            cn=tanh(drive*c+coupling*g+target-correction)
        delta=max(abs(gn-g),abs(cn-c))
        g,c=gn,cn
        e=mismatch(g,c)
        records.append((mode,seed,target,t,g,c,e,delta,int(reset)))
        # reset must not be happening and agreement must hold
        streak=streak+1 if delta<tol and e<=vigilance and not reset else 0
        if streak>=5:
            status='stable_candidate'; break
    return {'mode':mode,'seed':seed,'target':target,'status':status,'steps':len(records),'g':g,'c':c,'error':mismatch(g,c),'resets':resets},records

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--steps',type=int,default=250)
    p.add_argument('--drive',type=float,default=0.35)
    p.add_argument('--coupling',type=float,default=0.45)
    p.add_argument('--eta',type=float,default=0.12)
    p.add_argument('--vigilance',type=float,default=0.22)
    p.add_argument('--tol',type=float,default=1e-7)
    p.add_argument('--out',default='hybrid_output')
    args=p.parse_args()
    if args.steps<1 or not 0<=args.vigilance<=1 or args.tol<=0: p.error('invalid steps/vigilance/tol')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    summary=[];traces=[]
    for mode in ('bottom_only','top_only','bidirectional','hybrid'):
        for target in (-0.6,0.6):
            for seed in (-0.9,-0.2,0.2,0.9):
                row,trace=simulate(seed,target,args.drive,args.coupling,args.eta,args.vigilance,args.steps,mode,args.tol)
                summary.append(row);traces.extend(trace)
    with (out/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=summary[0].keys());w.writeheader();w.writerows(summary)
    with (out/'traces.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['mode','seed','target','step','gbmc','cqsd','match_error','step_delta','reset']);w.writerows(traces)
    print('mode             stable/total   avg_error    avg_resets')
    for mode in ('bottom_only','top_only','bidirectional','hybrid'):
        a=[r for r in summary if r['mode']==mode]
        print(f"{mode:17s}{sum(r['status']=='stable_candidate' for r in a):2d}/{len(a):<10d}{sum(r['error'] for r in a)/len(a):.5f}      {sum(r['resets'] for r in a)/len(a):.2f}")
    print('Output:',out/'summary.csv',out/'traces.csv')
    print('WARNING: stable_candidate is a finite-step numerical heuristic, not an attractor proof.')
    print('WARNING: this hybrid is inspired by ART/BAM/predictive coding, not an exact reproduction.')
if __name__=='__main__': main()
