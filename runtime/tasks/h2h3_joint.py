from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

import numpy as np
from scipy.stats import qmc

from runtime.tasks.hr1_diag import _load, _sim
from runtime.tasks.h1_position import fetch_hr1_global, _read_csv, _write, _rank

H2_MASTER = 21102027
H3_MASTER = 23102027
STRIDE = 104729
IQR = {
    "E001": (0.5419317280016975, 0.7485472630587153),
    "E002": (2.528433657227799, 4.67855725674577),
    "E003": (3.9928275862068965, 10.077293103448277),
}
P1090 = {
    "E001": (0.4063748573417162, 0.8212320709979283),
    "E002": (2.0262639021463675, 7.432423405683753),
    "E003": (2.8140862068965515, 14.938517241379309),
}

def _inside(x, band):
    return band[0] <= x <= band[1]

def _metrics(model, panel):
    _,_,s = _rank(np.asarray(model,dtype=float), panel)
    vals = dict(zip(("E001","E002","E003"), map(float,model)))
    iq = {e:_inside(vals[e],IQR[e]) for e in vals}
    p = {e:_inside(vals[e],P1090[e]) for e in vals}
    iqhits = sum(iq.values())
    gate = iq["E002"] and (iq["E001"] or iq["E003"]) and all(p.values()) and s["EMPIRICAL_SUPPORT_PERCENTILE"] <= 75.0
    return {
        **vals,
        "IQR_HITS":iqhits,
        "E001_IQR":iq["E001"],"E002_IQR":iq["E002"],"E003_IQR":iq["E003"],
        "ALL_P10_P90":all(p.values()),
        "SUPPORT_PERCENTILE":float(s["EMPIRICAL_SUPPORT_PERCENTILE"]),
        "NEAREST_C":s["NEAREST_C"],
        "NEAREST_DISTANCE":float(s["NEAREST_DISTANCE"]),
        "REALISM_GATE":bool(gate),
        "TOP10":s["TOP10"],
    }

def _normalized(p,bounds):
    b=np.asarray(bounds,dtype=float)
    return (np.asarray(p,dtype=float)-b[:,0])/(b[:,1]-b[:,0])

def _moderate_distance(p,b):
    x=_normalized(p,b["bounds"])
    refs=[_normalized(a["p"],b["bounds"]) for a in (b["anchors"][0],b["anchors"][1],b["anchors"][7])]
    return float(min(np.linalg.norm(x-r) for r in refs))

def _select_diverse(rows,bounds,n=32):
    ordered=sorted(rows,key=lambda r:(-int(r["IQR_HITS"]),float(r["SUPPORT_PERCENTILE"]),float(r["NEAREST_DISTANCE"]),int(r["IDX"])))
    for sep in (0.12,0.08,0.04,0.0):
        sel=[]
        for r in ordered:
            p=np.array([float(r[f"P{i:02d}"]) for i in range(10)])
            z=_normalized(p,bounds)
            if all(np.linalg.norm(z-_normalized(np.array([float(s[f"P{i:02d}"]) for i in range(10)]),bounds))>=sep for s in sel):
                sel.append(r)
            if len(sel)>=n: break
        if len(sel)>=min(16,n) or sep==0.0:
            return sel[:n],sep
    return ordered[:n],0.0

def _summ(vals):
    A=np.asarray([[v[0],v[1],v[2]] for v in vals],dtype=float)
    return np.mean(A,axis=0), np.quantile(A,[.025,.975],axis=0)

def run(control:dict, shard:int, output:Path, root:Path)->None:
    if shard != 0:
        raise RuntimeError("joint H2-H3 uses shard 0 only")
    panel=root/"public_bundle/h1_country_panel.csv"
    b=_load(root)
    repo=os.environ.get("GITHUB_REPOSITORY","ALRIER/On_the_public_impossibilityII")

    # Immutable HR1 screen.
    src=fetch_hr1_global(repo,output)
    pts=_read_csv(src)
    by={}
    for r in pts:
        if "E001" in r and "E002" in r and "E003" in r:
            by[r["IDX"]]=r
    if len(by)!=4096:
        raise RuntimeError(f"expected 4096 HR1 points, got {len(by)}")

    screened=[]
    for r in by.values():
        model=[float(r["E001"]),float(r["E002"]),float(r["E003"])]
        m=_metrics(model,panel)
        row={"IDX":r["IDX"],**{f"P{i:02d}":r[f"P{i:02d}"] for i in range(10)},**m}
        if m["REALISM_GATE"]:
            screened.append(row)
    if not screened:
        raise RuntimeError("H2 screening found no points satisfying frozen realism gate")

    seeds,sep=_select_diverse(screened,b["bounds"],32)
    _write(output/"h2_seed_screen.csv",screened)
    _write(output/"h2_selected_seeds.csv",[{**r,"DIVERSITY_SEP":sep} for r in seeds])

    # 64 local Sobol perturbations around each selected seed.
    local=[]
    bounds=np.asarray(b["bounds"],dtype=float)
    crn=[H2_MASTER+i*STRIDE for i in range(16)]
    for si,s in enumerate(seeds):
        center=np.array([float(s[f"P{i:02d}"]) for i in range(10)])
        engine=qmc.Sobol(d=10,scramble=True,seed=H2_MASTER+si)
        U=engine.random_base2(m=6)
        delta=(U-.5)*.10*(bounds[:,1]-bounds[:,0])
        X=np.clip(center+delta,bounds[:,0],bounds[:,1])
        for li,p in enumerate(X):
            mean,qq=_summ([_sim(b,p,int(sd)) for sd in crn])
            m=_metrics(mean,panel)
            local.append({
                "SEED_IDX":s["IDX"],"LOCAL_IDX":li,
                **{f"P{i:02d}":float(p[i]) for i in range(10)},
                **m,
                "E001_LO":float(qq[0,0]),"E001_HI":float(qq[1,0]),
                "E002_LO":float(qq[0,1]),"E002_HI":float(qq[1,1]),
                "E003_LO":float(qq[0,2]),"E003_HI":float(qq[1,2]),
                "MODERATE_DISTANCE":_moderate_distance(p,b),
            })
    _write(output/"h2_local_cells.csv",local)

    eligible=[r for r in local if r["REALISM_GATE"]]
    if not eligible:
        raise RuntimeError("H2 local search produced no finalist")
    eligible=sorted(eligible,key=lambda r:(-int(r["IQR_HITS"]),float(r["SUPPORT_PERCENTILE"]),float(r["NEAREST_DISTANCE"]),float(r["MODERATE_DISTANCE"]),int(r["SEED_IDX"]),int(r["LOCAL_IDX"])))
    finalists=[]
    for r in eligible:
        z=_normalized(np.array([float(r[f"P{i:02d}"]) for i in range(10)]),b["bounds"])
        if all(np.linalg.norm(z-_normalized(np.array([float(s[f"P{i:02d}"]) for i in range(10)]),b["bounds"]))>=0.04 for s in finalists):
            finalists.append(r)
        if len(finalists)>=8: break
    if not finalists:
        finalists=[eligible[0]]
    _write(output/"h2_finalists.csv",finalists)

    # H3: sealed finalists, fresh seed family.
    h3=[]
    seeds3=[H3_MASTER+i*STRIDE for i in range(512)]
    for fi,r in enumerate(finalists):
        p=np.array([float(r[f"P{i:02d}"]) for i in range(10)])
        mean,qq=_summ([_sim(b,p,int(sd)) for sd in seeds3])
        m=_metrics(mean,panel)
        h3.append({
            "FINALIST":fi,
            **{f"P{i:02d}":float(p[i]) for i in range(10)},
            **m,
            "E001_LO":float(qq[0,0]),"E001_HI":float(qq[1,0]),
            "E002_LO":float(qq[0,1]),"E002_HI":float(qq[1,1]),
            "E003_LO":float(qq[0,2]),"E003_HI":float(qq[1,2]),
            "MODERATE_DISTANCE":_moderate_distance(p,b),
            "H3_CERTIFIED":bool(m["REALISM_GATE"]),
        })
    _write(output/"h3_confirmed.csv",h3)

    survivors=[r for r in h3 if r["H3_CERTIFIED"]]
    survivors=sorted(survivors,key=lambda r:(-int(r["IQR_HITS"]),float(r["SUPPORT_PERCENTILE"]),float(r["NEAREST_DISTANCE"]),float(r["MODERATE_DISTANCE"]),int(r["FINALIST"])))
    decision={
        "schema":"h2h3_joint_decision_v1",
        "h2_screen_pass_count":len(screened),
        "h2_seed_count":len(seeds),
        "h2_local_cells":len(local),
        "h2_local_gate_count":len(eligible),
        "h3_finalists":len(h3),
        "h3_certified_count":len(survivors),
        "baseline_selected":bool(survivors),
        "baseline_finalist":int(survivors[0]["FINALIST"]) if survivors else None,
        "baseline_support_percentile":float(survivors[0]["SUPPORT_PERCENTILE"]) if survivors else None,
        "requires_private_internal_recertification":True,
        "test3_terminal":False,
    }
    (output/"h2h3_decision.json").write_text(json.dumps(decision,indent=2)+"\n",encoding="utf-8")
