from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import qmc

BUNDLE = "public_bundle/hr1_bundle.json"

def _load(root: Path) -> dict:
    return json.loads((root / BUNDLE).read_text(encoding="utf-8"))

def _exp(y_p, w, target, unc, y, p1, p5, p2):
    u = p1 * y_p + p5 * (w - target) - p2 * unc
    return min(max(u, 0.0), w + y)

def _sim(b: dict, p: list[float], seed: int, mech: tuple[str,float] | None = None) -> tuple[float,float,float,bool]:
    periods=int(b["periods"]); warm=int(b["warmup"])
    rng=np.random.default_rng(seed)
    h=np.asarray(b["h"],dtype=float)
    block=int(b["settings"]["s7"])
    pieces=[]
    while sum(len(x) for x in pieces)<periods:
        st=int(rng.integers(0,max(len(h)-block+1,1)))
        pieces.append(h[st:st+block])
    sampled=np.vstack(pieces)[:periods].copy()

    d=b["direct"]; s=b["settings"]
    scale0=1.0; scale1=1.0; hazard_scale=1.0; sep_scale=1.0; e_shift=0.0
    if mech:
        mid,lv=mech
        if mid=="M00": scale0=lv
        elif mid=="M01": scale1=lv
        elif mid=="M04": hazard_scale=lv
        elif mid=="M05": sep_scale=lv
        elif mid=="M06": e_shift=lv
        # M02/M03 are deliberately orthogonal to E001-E003 in the canonical path.

    base0=h[:,0]; raw0=sampled[:,0]
    z0=(raw0-float(np.mean(base0)))/max(float(np.std(base0,ddof=1)),1e-12)
    inn0=z0*float(d["d8"])*scale1
    st0=np.zeros(periods)
    for t in range(1,periods): st0[t]=float(d["d7"])*st0[t-1]+inn0[t]

    base1=h[:,1]; raw1=sampled[:,1]
    z1=(raw1-float(np.mean(base1)))/max(float(np.std(base1,ddof=1)),1e-12)
    inn1=z1*float(d["d10"])
    st1=np.zeros(periods)
    for t in range(1,periods): st1[t]=float(d["d9"])*st1[t-1]+inn1[t]

    # Preserve canonical RNG consumption before the stochastic state loop.
    nprod=len(range(0,periods,3))
    rng.choice(np.arange(max(int(b["rng_padding"]["p"]),1)),size=nprod,replace=True)
    rng.choice(np.arange(max(int(b["rng_padding"]["b"]),1)),size=periods,replace=True)
    rng.choice(np.arange(max(int(b["rng_padding"]["d"]),1)),size=periods,replace=True)

    g=10
    wealth0=np.asarray(b["wealth"],dtype=float)
    wealth=np.interp(np.linspace(.1,.9,g),np.linspace(.1,.9,len(wealth0)),wealth0)
    wealth=wealth/max(float(np.median(wealth)),1.0)
    perm=np.linspace(.65,1.45,g)
    unc=np.full(g,max(float(d["d0"]),1e-9))
    fw=float(b["capacity"]["w"])
    cap=np.where(np.arange(g)<round(fw*g),float(b["capacity"]["a"]),float(b["capacity"]["b"]))

    workers=max(float(s["s0"]),100.0); mass=workers/g
    e0=float(np.clip(float(s["s1"])+e_shift,0.0,1.0))
    er=np.full(g,e0); wpg=max(int(round(workers/g)),1)
    ec=np.rint(er*wpg).astype(int)
    low=np.zeros(g,dtype=bool)
    cshare=[]; ylev=[]; ur=[]

    for t in range(periods):
        um=(1.0-er)*mass; U=max(float(np.sum(um)),1e-9)
        tight=max(1.0+st1[t]/100.0,float(s["s2"]))
        V=max((U/max(float(d["d3"]),1e-9))*tight,1e-9)
        anchor=float(d["d4"])
        haz=min(max(anchor*(tight**max(1.0-float(d["d2"]),0.0))*hazard_scale,0.0),1.0)
        ss=anchor*max(1.0-e0,0.0)/max(e0,1e-9)
        sep=min(max((ss/max(tight,1e-9))*sep_scale,0.0),float(s["s3"]))
        hires=rng.binomial(np.maximum(wpg-ec,0),haz)
        seps=rng.binomial(np.maximum(ec,0),sep)
        ec=np.clip(ec+hires-seps,0,wpg); er=ec.astype(float)/float(wpg)
        ur.append(float(np.mean(1.0-er))*100.0)

        inc=np.maximum((float(s["s4"])*er+float(s["s5"]))*(1.0+st0[t]/100.0)*cap,0.0)
        if t%12==0:
            prev=low.copy()
            enter=(~prev)&(rng.random(g)<float(d["d5"]))
            leave=prev&(rng.random(g)<min(max(float(p[3]),0.0),1.0))
            low=(prev|enter)&(~leave)
        inc=np.where(low,inc*float(s["s6"]),inc)

        prevp=perm.copy()
        for i in range(g):
            perm[i]=p[0]*inc[i]+(1-p[0])*max(prevp[i],0.0)
            var=(1-p[3])*max(unc[i],0.0)**2+p[3]*(inc[i]-max(prevp[i],0.0))**2
            unc[i]=math.sqrt(max(var,0.0))
        spend=np.zeros(g)
        for i in range(g):
            target=(p[4]/12.0)*perm[i]
            spend[i]=_exp(perm[i],wealth[i],target,unc[i],inc[i],p[1],p[5],p[2])
        wealth=np.maximum(wealth+inc-spend,0.0)
        ti=max(float(np.sum(inc)),1e-9); ts=float(np.sum(spend))
        nh=max(float(d["d6"])*scale0*ti,0.0)
        yy=max(ts+nh,1e-9)
        cshare.append(ts/yy); ylev.append(yy)

    e1=float(np.mean(np.asarray(cshare)[warm:]))
    yy=np.asarray(ylev,dtype=float)
    gg=100.0*np.diff(np.log(np.maximum(yy[::12],1e-9)))
    e2=float(np.std(gg,ddof=1)) if len(gg)>1 else 0.0
    e3=float(np.mean(np.asarray(ur)[warm:]))
    vals=np.asarray([e1,e2,e3],dtype=float)
    return e1,e2,e3,bool(np.all(np.isfinite(vals)))

def _summ(vals: list[tuple[float,float,float,bool]]) -> list[dict]:
    a=np.asarray([[x[0],x[1],x[2]] for x in vals],dtype=float)
    out=[]
    for j,e in enumerate(["E001","E002","E003"]):
        out.append({"E":e,"N":len(vals),"MEAN":float(np.mean(a[:,j])),
                    "LO":float(np.quantile(a[:,j],.025)),"HI":float(np.quantile(a[:,j],.975)),
                    "FINITE":bool(all(x[3] for x in vals))})
    return out

def _write(path: Path, rows: list[dict]) -> None:
    if not rows: return
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def _replay(b: dict, aidx: int) -> list[dict]:
    p=b["anchors"][aidx]["p"]
    vals=[_sim(b,p,12062027+r*104729) for r in range(512)]
    got={r["E"]:r for r in _summ(vals)}
    exp={r["e"]:r for r in b["h0"] if r["a"]==f"A{aidx:02d}"}
    rows=[]
    for e in ["E001","E002","E003"]:
        g=got[e]; x=exp[e]
        err=max(abs(g["MEAN"]-x["m"]),abs(g["LO"]-x["lo"]),abs(g["HI"]-x["hi"]))
        rows.append({"A":f"A{aidx:02d}","E":e,"MEAN":g["MEAN"],"LO":g["LO"],"HI":g["HI"],
                     "REF_MEAN":x["m"],"REF_LO":x["lo"],"REF_HI":x["hi"],"MAX_ABS_ERR":err,
                     "PASS":err<=1e-10})
    return rows

def run(control: dict, shard: int, output: Path, root: Path) -> None:
    b=_load(root); master=int(b["master"])
    if 0 <= shard <= 7:
        replay=_replay(b,shard)
        _write(output/"replay.csv",replay)
        if not all(r["PASS"] for r in replay):
            raise RuntimeError("equivalence replay failed")
        base=np.asarray(b["anchors"][shard]["p"],dtype=float)
        bounds=np.asarray(b["bounds"],dtype=float)
        cells=[("BASE",-1,0.0,base.copy())]
        for j in range(10):
            for off in (-.10,-.025,.025,.10):
                q=base.copy(); q[j]=np.clip(q[j]+off*(bounds[j,1]-bounds[j,0]),bounds[j,0],bounds[j,1])
                cells.append((f"P{j:02d}",j,off,q))
        rows=[]
        seeds=[master+shard*1000000+r*104729 for r in range(16)]
        for cid,j,off,p in cells:
            sm=_summ([_sim(b,p,int(seed)) for seed in seeds])
            for z in sm: rows.append({"A":f"A{shard:02d}","CELL":cid,"J":j,"OFF":off,**z})
        _write(output/"local.csv",rows)
        return

    if 8 <= shard <= 71:
        sob=qmc.Sobol(d=10,scramble=True,seed=master)
        u=sob.random_base2(m=12)
        bounds=np.asarray(b["bounds"],dtype=float)
        X=qmc.scale(u,bounds[:,0],bounds[:,1])
        k=shard-8; lo=k*64; hi=lo+64
        seeds=[master+50000000+r*104729 for r in range(8)]
        rows=[]
        for idx in range(lo,hi):
            sm=_summ([_sim(b,X[idx],int(seed)) for seed in seeds])
            for z in sm: rows.append({"IDX":idx,**{f"P{j:02d}":float(X[idx,j]) for j in range(10)},**z})
        _write(output/"global.csv",rows)
        return

    if 72 <= shard <= 79:
        aidx=shard-72; p=np.asarray(b["anchors"][aidx]["p"],dtype=float)
        rows=[]; seeds=[master+90000000+aidx*1000000+r*104729 for r in range(16)]
        for mi in range(7):
            mid=f"M{mi:02d}"
            levels=(-0.05,0.0,0.05) if mid=="M06" else (0.75,1.0,1.25)
            for lv in levels:
                sm=_summ([_sim(b,p,int(seed),(mid,float(lv))) for seed in seeds])
                for z in sm: rows.append({"A":f"A{aidx:02d}","M":mid,"LEVEL":lv,**z})
        _write(output/"probes.csv",rows)
        return
    raise RuntimeError(f"invalid shard {shard}")
