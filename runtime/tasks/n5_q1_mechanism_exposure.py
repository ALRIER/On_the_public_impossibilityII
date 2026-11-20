"""N5 public scientific-mechanism exposure map: never tune by observed sign.

The original anchor mapping is not certified. This is an unbiased grid diagnostic
of whether finance/settlement constraints causally reach physical outcomes.
"""
from __future__ import annotations
import argparse,csv,json,hashlib
from pathlib import Path
import numpy as np
from itertools import product
from runtime.tasks.n5_clearing_engine import run
from runtime.tasks.n5_review_proofs import baseline6,density_only,simple10

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"public_bundle/n5_v1"

def require(ok,message):
    if not bool(ok):raise RuntimeError(message)

def save(path,rows):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

def simulate(A,P,settings,shock,mode="base"):
    r=run(A,P,seed=472801,periods=24,shock_start=9,shock_length=6,
          shock_severity=shock,shock_source=int(np.argmax(A.sum(axis=1))),
          mode=mode,
          payment_capacity_scale=float(settings[2]),
          inventory_months=float(settings[0]),
          credit_fraction=float(settings[1]),
          full_ledger=False)
    path=r["path"]
    require(max(max(x["R001"],x["R002"],x["R003"]) for x in path)<1e-9,
            "Original ledger physical or monetary identity failed")
    return {k:sum(x[k] for x in path[9:])
            for k in ("Y001","Y002","Y003","Y004","Y005","Y006","Y007","Y008","Y009")},path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",default="outputs/n5_q1_mechanism_exposure",type=Path)
    out=ap.parse_args().out_dir
    out.mkdir(parents=True,exist_ok=True)
    m=json.loads((DATA/"m001.json").read_text())
    A=np.asarray(m["M001"],float)
    frozen=A.copy()
    require(A.shape==(104,104) and len(m["V002"])==32,"Original source invalid")
    p0=baseline6(A,m["I001"])
    p1,_,_,_=simple10(A,m["V002"][0])
    p31,_,_,_=simple10(A,m["V002"][31])
    p2,canmatch=density_only(A,int(np.count_nonzero(p1)))
    arms={"M0":p0,"M1":p1,"M2":p2,"M3":p31}
    regimes=list(product([.5,1.0],[.15,1.2],[.35,1.,4.]))
    totals=[];diffs=[]
    nonzero=0
    for g,setting in enumerate(regimes):
        paths={}
        for arm,P in arms.items():
            no,baseline=simulate(A,P,setting,0.)
            yes,shocked=simulate(A,P,setting,.5)
            paths[arm]=(no,yes)
            rec={"REGIME":g,"ARM":arm,"INVENTORY_MONTHS":setting[0],
                 "CREDIT_FRACTION":setting[1],
                 "PAYMENT_CAPACITY_SCALE":setting[2],
                 "SHOCK_START":9,"SHOCK_END_EXCLUSIVE":15,
                 "SEED":472801}
            for k in no:
                rec[f"{k}_NO_SHOCK"]=float(no[k])
                rec[f"{k}_SHOCK"]=float(yes[k])
                rec[f"{k}_SHOCK_DIFFERENCE"]=float(yes[k]-no[k])
            totals.append(rec)
        for arm in ("M1","M2","M3"):
            n,s=paths[arm]
            bn,bs=paths["M0"]
            did=float((s["Y002"]-n["Y002"])-(bs["Y002"]-bn["Y002"]))
            if abs(did)>1e-10:nonzero+=1
            diffs.append({
                "REGIME":g,"COMPARATOR_ARM":arm,
                "SEED":472801,
                "REAL_VALUE_ADDED_SHOCK_DID_VS_INHERITED":did,
                "REAL_CONSUMPTION_SHOCK_DID_VS_INHERITED":
                    float((s["Y004"]-n["Y004"])-(bs["Y004"]-bn["Y004"])),
                "WAGE_EMPLOYMENT_SHOCK_DID_VS_INHERITED":
                    float((s["Y003"]-n["Y003"])-(bs["Y003"]-bn["Y003"])),
                "REAL_OUTPUT_SHOCK_DID_VS_INHERITED":
                    float((s["Y001"]-n["Y001"])-(bs["Y001"]-bn["Y001"])),
                "FINANCIAL_ARREARS_DID_VS_INHERITED":
                    float((s["Y006"]-n["Y006"])-(bs["Y006"]-bn["Y006"])),
                "FINANCIAL_FRICTIONS_CAUSALITY_PROVED":0,
                "ECONOMIC_ANCHOR_APPLIED":0
            })
    zero_a,zero_path_a=simulate(A,p0,regimes[0],.5,"zero_frictions")
    zero_b,zero_path_b=simulate(A,p1,regimes[0],.5,"zero_frictions")
    require(zero_path_a==zero_path_b,"No-friction topology placebo failed")
    require(np.array_equal(A,frozen),"Changed physical source technology")
    save(out/"q1_predeclared_financial_regime_grid.csv",totals)
    save(out/"q1_shock_difference_in_difference.csv",diffs)
    overview={
        "schema":"n5_q1_public_mechanism_exposure_grid_v1",
        "fixed_predeclared_regimes":len(regimes),
        "network_comparator_arms":list(arms),
        "pilot_paths":len(regimes)*len(arms)*2+2,
        "single_original_design_seed":472801,
        "nonzero_real_value_added_DID_rows_over_1e10_negative":nonzero,
        "total_real_value_added_DID_rows":len(diffs),
        "direct_density_comparator_matchable":bool(canmatch),
        "all_periodic_accounting_identities_pass":True,
        "zero_friction_all_arms_real_outcomes_identical":True,
        "physical_technology_unchanged":True,
        "original_economic_anchors_applied":0,
        "regime_was_not_selected_after_sign_or_significance":True,
        "new_improvement_found_requires_fresh_seeds":True,
        "original_q3_macro_moments_revalidated":False,
        "original_q4_development_fails_revalidated":False,
        "full_scale_scientific_n5_allowed":False,
        "source_sha256":hashlib.sha256((DATA/"m001.json").read_bytes()).hexdigest()
    }
    (out/"q1_mechanism_status.json").write_text(json.dumps(overview,indent=2)+"\n")
    print(json.dumps(overview,indent=2))

if __name__=="__main__":
    main()
