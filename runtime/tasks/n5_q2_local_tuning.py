"""N5 Q2 prospective LOCAL network-design study, retains original target bands.

Perturbations around all 32 frozen acceptable controls with predeclared radii.
No economic outcome labels are used to choose controls; no historical results edited.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from runtime.tasks.n5_review_proofs import metrics,simple10

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"public_bundle/n5_v1"

def check(ok,why):
    if not bool(ok):raise RuntimeError(why)

def emit(path,rows):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

def values(A,z,orig,half,lo,hi):
    P,D,_,_=simple10(A,z)
    achieved=np.asarray(metrics(P),float)
    check(np.allclose(D.sum(axis=0),A.sum(axis=0),atol=1e-10),
          "Direct supplier mass not preserved")
    check(np.all(P>=0) and np.isfinite(P).all(),
          "Payment topology invalid")
    score=float(np.sum(((achieved-orig)/half)**2))
    passall=bool(np.all(achieved>=lo)&np.all(achieved<=hi))
    return score,passall,achieved,int(np.count_nonzero(P))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",default="outputs/n5_q2_local_tuning",type=Path)
    out=ap.parse_args().out_dir
    out.mkdir(parents=True,exist_ok=True)
    m=json.loads((DATA/"m001.json").read_text())
    t=json.loads((DATA/"t001.json").read_text())
    A=np.asarray(m["M001"],float)
    frozen=A.copy()
    Z=np.asarray(m["V002"],float)
    check(A.shape==(104,104) and Z.shape==(32,10) and len(t["M201"])==6,
          "Original public source shape changed")
    original=np.array([x["T"][0] for x in t["M201"]])
    lo=np.array([x["T"][1] for x in t["M201"]])
    hi=np.array([x["T"][2] for x in t["M201"]])
    half=np.maximum((hi-lo)/2,1e-12)
    base=[]
    for j,z in enumerate(Z):
        score,valid,achieved,links=values(A,z,original,half,lo,hi)
        check(valid,"Original frozen six target tests changed")
        base.append({"SOURCE":j,"IS_FROZEN":1,"RADIUS":0.,
                     "DRAW":0,"SCORE":score,
                     "ALL_SIX_ORIGINAL_BANDS_PASS":1,
                     "ACTIVE_PAYMENT_LINKS":links,
                     "CONTROLS":json.dumps(z.tolist())})
    rng=np.random.default_rng(34532)
    rows=[]
    radii=(.00025,.0025,.02,.10)
    for k,z in enumerate(Z):
        for radius in radii:
            for draw in range(2):
                perturb=np.clip(z+rng.normal(0,radius,size=10),0.,1.)
                score,valid,achieved,links=values(
                    A,perturb,original,half,lo,hi)
                rows.append({
                    "SOURCE":k,"IS_FROZEN":0,"RADIUS":radius,
                    "DRAW":draw,"SCORE":score,
                    "ALL_SIX_ORIGINAL_BANDS_PASS":int(valid),
                    "ACTIVE_PAYMENT_LINKS":links,
                    "CONTROLS":json.dumps(perturb.tolist())})
    check(len(rows)==32*len(radii)*2,"Local perturbation protocol incomplete")
    eligible=[r for r in rows if r["ALL_SIX_ORIGINAL_BANDS_PASS"]]
    best_original=min(float(x["SCORE"]) for x in base)
    better=[x for x in eligible if float(x["SCORE"])<best_original-1e-9]
    compare=[]
    for radius in radii:
        subset=[r for r in rows if r["RADIUS"]==radius]
        viable=[r for r in subset if r["ALL_SIX_ORIGINAL_BANDS_PASS"]]
        compare.append({
            "RADIUS":radius,"PROPOSED":len(subset),
            "ALL_SIX_BANDS_PASS":len(viable),
            "BEST_SCORE_WITHIN_BANDS":
                min((x["SCORE"] for x in viable),default="NONE"),
            "BETTER_THAN_BEST_ORIGINAL":
                sum(x["SCORE"]<best_original-1e-9 for x in viable),
            "ORIGINAL_BEST_FROZEN_SCORE":best_original})
    check(np.array_equal(A,frozen),"Original technology changed")
    emit(out/"q2_frozen_32_originals.csv",base)
    emit(out/"q2_local_256_candidates.csv",rows)
    emit(out/"q2_radius_feasibility_and_improvement.csv",compare)
    summary={
        "schema":"n5_q2_public_local_design_tuning_v1",
        "original_frozen_valid_structures":32,
        "prospective_structural_candidates":len(rows),
        "radius_grid":list(radii),
        "candidate_all_six_original_bands_passes":len(eligible),
        "valid_candidates_better_than_best_original_center_distance":len(better),
        "best_original_center_distance":best_original,
        "best_prospective_valid_center_distance":
            min((x["SCORE"] for x in eligible),default=None),
        "objective":"preregistered six frozen network-moment center-distance",
        "original_reference_targets_changed":False,
        "original_eight_economic_anchors_linked":False,
        "direct_mass_identical_and_physical_A_untouched":True,
        "causal_economic_outcome_improved_by_structural_fidelity":False,
        "q1_q3_q4_scientific_improvements_claimed":False,
        "public_original_m001_sha256":
            hashlib.sha256((DATA/"m001.json").read_bytes()).hexdigest(),
        "public_original_t001_sha256":
            hashlib.sha256((DATA/"t001.json").read_bytes()).hexdigest()
    }
    (out/"q2_local_tuning_status.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
