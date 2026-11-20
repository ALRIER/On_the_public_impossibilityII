"""Prospective N5 controlled ordering-mechanism comparison (public only).

Tests legacy inventory targeting vs next-period physical-input coverage.
No fitted parameter adapters, no ML outcome optimization, no retrospective
Q1/Q4 validation claim. Both null and unfavorable cases are preserved.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from runtime.tasks.n5_clearing_engine import run
from runtime.tasks.n5_review_proofs import baseline6,simple10

ROOT=Path(__file__).resolve().parents[2]
POLICIES=("legacy_stock_only","forward_input_coverage")
METRICS={"output":"Y001","value_added":"Y002","consumption":"Y004",
         "employment":"Y003","arrears":"Y006","shipments":"Y009",
         "unfilled":"Y007","payment_hhi":"Y005"}
def ensure(ok,msg):
    if not bool(ok):raise AssertionError(msg)
def csvout(path,rows):
    if not rows:return
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def total(path,key):return float(sum(float(t[key]) for t in path))
def analyse(A,networks,context,periods,shock_start,shock_source,inventory,credit,paycap):
    results={}; rows=[]; diffs=[]
    initial_A=A.copy()
    for policy in POLICIES:
      for arm,P in networks.items():
        for shock in (0.,.65):
          result=run(A,P,seed=20261120,periods=periods,shock_start=shock_start,
                     shock_length=5,shock_source=shock_source,
                     shock_severity=shock,inventory_months=inventory,
                     credit_fraction=credit,payment_capacity_scale=paycap,
                     order_policy=policy,full_ledger=False)
          path=result["path"]
          ensure(max(max(abs(x["R001"]),abs(x["R002"]),abs(x["R003"])) for x in path)<1e-9,
                 context+" conservation failed "+policy+"/"+arm)
          results[policy,arm,shock]=path
          rows.append({"context":context,"order_policy":policy,"arm":arm,
                       "shock":shock,"periods":periods,"inventory_months":inventory,
                       "credit_fraction":credit,"payment_capacity_scale":paycap,
                       **{k:total(path,v) for k,v in METRICS.items()}})
      reference=list(networks)[0]
      for arm in list(networks)[1:]:
        x=results[policy,arm,.65];xn=results[policy,arm,0.]
        y=results[policy,reference,.65];yn=results[policy,reference,0.]
        effects={k:total(x,v)-total(y,v) for k,v in METRICS.items()}
        did={k:(total(x,v)-total(xn,v))-(total(y,v)-total(yn,v))
             for k,v in METRICS.items()}
        diffs.append({"context":context,"order_policy":policy,
                      "comparator":arm,"reference":reference,
                      **{"level_"+k:v for k,v in effects.items()},
                      **{"shock_did_"+k:v for k,v in did.items()}})
      placebo=run(A,networks[reference],seed=20261120,
                  periods=periods,shock_start=shock_start,shock_length=5,
                  shock_source=shock_source,shock_severity=.65,
                  inventory_months=inventory,credit_fraction=credit,
                  payment_capacity_scale=paycap,order_policy=policy,
                  mode="zero_frictions")["path"]
      other=list(networks)[-1]
      placebo_other=run(A,networks[other],seed=20261120,
                  periods=periods,shock_start=shock_start,shock_length=5,
                  shock_source=shock_source,shock_severity=.65,
                  inventory_months=inventory,credit_fraction=credit,
                  payment_capacity_scale=paycap,order_policy=policy,
                  mode="zero_frictions")["path"]
      ensure(placebo==placebo_other,context+" zero-friction network placebo failed")
    ensure(np.array_equal(A,initial_A),"Frozen physical technology modified")
    return rows,diffs

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out-dir",type=Path,default=Path("outputs/n5_forward_coverage_pilot"))
    args=p.parse_args();args.out_dir.mkdir(parents=True,exist_ok=True)
    A=np.array([[.15,.07,.12],[.08,.19,.06],[.11,.03,.16]],float)
    full=np.ones_like(A); cut=full.copy();cut[0,1]=0.
    # Predetermined positive-control route obstruction: not optimized
    # using economic outcomes.
    rows,diffs=analyse(A,{"full_direct":full,"one_direct_edge_blocked":cut},
                      "synthetic_3sector_positive_control",
                      16,2,0,.25,.15,.6)
    m=json.loads((ROOT/"public_bundle/n5_v1/m001.json").read_text())
    frozen=np.asarray(m["M001"],float);before=frozen.copy()
    ensure(frozen.shape==(104,104) and len(m["V002"])==32,"Frozen inputs changed")
    P0=baseline6(frozen,m["I001"])
    P1,_,_,_=simple10(frozen,m["V002"][0])
    rows104,diffs104=analyse(frozen,{"original_inherited":P0,"original_reconstructed_0":P1},
                            "original_104sector_technology_not_frozen_anchor",
                            14,3,int(np.argmax(frozen.sum(axis=1))),.5,.15,.6)
    rows+=rows104;diffs+=diffs104
    ensure(np.array_equal(before,frozen),"Frozen original technology modified")
    csvout(args.out_dir/"physical_and_financial_paths.csv",rows)
    csvout(args.out_dir/"topology_levels_and_paired_did.csv",diffs)
    bypolicy={policy:{"synthetic":{},"original_structure":{}}
              for policy in POLICIES}
    for row in diffs:
        name="synthetic" if row["context"].startswith("synthetic") else "original_structure"
        bypolicy[row["order_policy"]][name]={
            k:row[k] for k in row if k.startswith("level_") or k.startswith("shock_did_")}
    status={
        "schema":"n5_forward_input_coverage_experimental_pilot_v1",
        "order_policies_compared":list(POLICIES),
        "original_engine_default_preserved":True,
        "technology_invariant":True,
        "ledger_residual_limit":1e-9,
        "synthetic_positive_control_did_nonzero":
            any(abs(float(x["shock_did_"+k]))>1e-10 for x in diffs
                if x["context"].startswith("synthetic") and
                x["order_policy"]=="forward_input_coverage"
                for k in ("output","value_added","consumption")),
        "original_structure_real_effect_did_nonzero":
            any(abs(float(x["shock_did_"+k]))>1e-10 for x in diffs
                if x["context"].startswith("original") and
                x["order_policy"]=="forward_input_coverage"
                for k in ("output","value_added","consumption")),
        "differences":bypolicy,
        "original_economic_anchors_mapped":False,
        "original_10_param_legacy_ABM_equivalence_certified":False,
        "q1_scientific_result_confirmed":False,
        "q4_historical_target_failures_unchanged":True,
        "large_scale_screen_authorized":False,
        "note":"Engineering mechanism sensitivity only; real economic model parity and external validation remain mandatory."
    }
    (args.out_dir/"status.json").write_text(json.dumps(status,indent=2)+"\n")
    print(json.dumps(status,indent=2))
if __name__=="__main__":main()
