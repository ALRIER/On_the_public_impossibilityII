"""Versioned engineering pilot only; no scientific confirmation or historical retuning.

All scientific semantics and adjudication stay in the private repository.
No automatic full-screen launch is supported by this module.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
import numpy as np
from runtime.tasks.n5_review_proofs import baseline6,simple10,density_only
from runtime.tasks.n5_clearing_engine import run

ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/"public_bundle/n5_v1"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_csv(path,rows):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--seed",type=int,default=29112027)
    args=ap.parse_args()
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    base=json.loads((BUNDLE/"m001.json").read_text())
    A=np.asarray(base["M001"],float)
    P0=baseline6(A,base["I001"])
    P1,_,_,_=simple10(A,base["V002"][0])
    Pd,matched=density_only(A,int(np.count_nonzero(P1)))
    if not matched:raise RuntimeError("Insufficient directly eligible edges for density comparator")
    networks={"M0":P0,"M1":P1,"M2":Pd}
    source=int(np.argmax(A.sum(axis=1)))
    cases={}
    timeseries=[]
    checks=[]
    seed=int(args.seed)
    baseline_inputs={"seed":seed,"periods":36,"shock_start":13,
                     "shock_length":9,"shock_source":source,
                     "inventory_months":1.0,
                     "payment_capacity_scale":5.0,
                     "credit_fraction":1.2}
    for arm,P in networks.items():
        for scenario,severity in (("none",0.),("stress",.5),("alternative",.35)):
            kw={**baseline_inputs,"shock_severity":severity}
            if scenario=="alternative":
                kw["shock_source"]=int(np.argsort(-A.sum(axis=1))[1])
            trace=run(A,P,**kw,full_ledger=(arm in ("M0","M1") and scenario=="stress"))
            cases[(arm,scenario)]=trace
            for row in trace["path"]:
                timeseries.append({"A":arm,"K":scenario,"SEED":seed,**row})
            if trace["ledger"]:
                path=out/f"n5_ledger_{arm}_{scenario}.json"
                path.write_text(json.dumps(trace["ledger"],separators=(",",":"))+"\n")
            checks.append({"A":arm,"K":scenario,
                           "MAX_GOODS_RESIDUAL":max(r["R001"] for r in trace["path"]),
                           "MAX_INPUT_RESIDUAL":max(r["R002"] for r in trace["path"]),
                           "MAX_MONEY_RESIDUAL":max(r["R003"] for r in trace["path"])})
    comps=[]
    for arm in ("M1","M2"):
        for variable in ("Y001","Y002","Y003","Y004","Y005","Y006","Y007"):
            contrasted=sum(
                (u[variable]-v[variable])-(x[variable]-y[variable])
                for u,v,x,y in zip(cases[(arm,"stress")]["path"],
                                   cases[(arm,"none")]["path"],
                                   cases[("M0","stress")]["path"],
                                   cases[("M0","none")]["path"]))
            comps.append({"A":arm,"Y":variable,"DID_CUM":float(contrasted)})
    # Engineering falsification is mandatory: changing the payment matrix
    # cannot change physical outcomes when settlement friction is removed.
    invariant0=run(A,P0,**{**baseline_inputs,"shock_severity":.5},
                   mode="zero_frictions")
    invariant1=run(A,P1,**{**baseline_inputs,"shock_severity":.5},
                   mode="zero_frictions")
    if invariant0["path"]!=invariant1["path"]:
        raise RuntimeError("Counterfactual changes economy despite no financial friction")
    if any(max(float(row[x]) for x in ("MAX_GOODS_RESIDUAL","MAX_INPUT_RESIDUAL",
                                      "MAX_MONEY_RESIDUAL"))>=1e-9 for row in checks):
        raise RuntimeError("Pilot violates a stock/financial identity")
    write_csv(out/"o501.csv",timeseries)
    write_csv(out/"o502.csv",comps)
    write_csv(out/"o503.csv",checks)
    summary={
       "schema":"n5_neutral_clearing_pilot_v1","status":"ENGINEERING_PILOT_ONLY",
       "model_identity":"prospective_coupled_variant",
       "economic_anchor_calibration_gate":"NOT_YET_VERIFIED",
       "matched_independent_confirmation":"NOT_RUN",
       "complete_reviewer_question1":"NOT_ESTABLISHED",
       "input_hashes":{name:sha(BUNDLE/name) for name in
                       ("m001.json","r001.json","t001.json")},
       "source_git_commit":"__GIT_COMMIT_IN_WORKFLOW_RECEIPT__",
       "seed":seed,"time_periods":36,
       "network_arms":list(networks),"scenarios":["none","stress","alternative"],
       "simulation_count":9,"ledger_full_cases":2,
       "all_ledgers_balanced":True,
       "zero_financial_friction_invariant":True,
       "output_files_sha256":{}
    }
    for path in sorted(out.iterdir()):
        if path.is_file():summary["output_files_sha256"][path.name]=sha(path)
    (out/"o504.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="output_files_sha256"},indent=2))

if __name__=="__main__":main()
