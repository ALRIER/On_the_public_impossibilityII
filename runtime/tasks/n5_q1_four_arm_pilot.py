"""N5 Q1 four-arm PUBLIC engineering pilot and topology falsification.

The original ten-parameter economic anchors are not yet mapped/certified into
this new engine. This bounded test MUST NOT be used as scientific confirmation.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from pathlib import Path
import numpy as np

from runtime.tasks.n5_clearing_engine import run
from runtime.tasks.n5_review_proofs import baseline6,density_only,simple10

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"public_bundle/n5_v1"


def assert_pass(ok,message):
    if not bool(ok):raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csvwrite(path,rows):
    with path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def rewire_financial_only(P,seed=20261120,desired=32,proposal_cap=120000):
    """A bounded neutral 2-edge swap, exact degree and buyer-mass preservation.

    Seller-value strengths are only approximately preserved; this is an
    engineering comparator and NOT a certified degree-strength null model.
    """
    P=np.asarray(P,float)
    original=P.copy()
    target=P.copy()
    active=np.argwhere(target>0)
    rng=np.random.default_rng(seed)
    committed=0
    proposed=0
    while committed<desired and proposed<proposal_cap:
        proposed+=1
        a,b=rng.integers(0,len(active),size=2)
        if a==b:continue
        i,j=map(int,active[a]); k,l=map(int,active[b])
        if i==k or j==l or target[i,l]>0 or target[k,j]>0:continue
        v=float(target[i,j]);w=float(target[k,l])
        if v<=0 or w<=0:continue
        if abs(math.log(v/w))>.5:continue
        target[i,j]=0.;target[k,l]=0.
        target[k,j]=v;target[i,l]=w
        active[a]=[k,j];active[b]=[i,l]
        committed+=1
    assert_pass(committed>=1,"No valid degree-preserving financial rewire exists")
    assert_pass(np.count_nonzero(target)==np.count_nonzero(original),
                "Rewire changed network density")
    assert_pass(np.array_equal(np.count_nonzero(target,axis=0),
                               np.count_nonzero(original,axis=0)),
                "Rewire changed buyer active degree")
    assert_pass(np.array_equal(np.count_nonzero(target,axis=1),
                               np.count_nonzero(original,axis=1)),
                "Rewire changed seller active degree")
    assert_pass(np.allclose(target.sum(axis=0),original.sum(axis=0),
                            rtol=1e-12,atol=1e-11),
                "Buyer payment masses were modified by topology control")
    original_seller=original.sum(axis=1)
    diff=np.abs(target.sum(axis=1)-original_seller)
    seller_relative=diff/np.maximum(np.abs(original_seller),1e-12)
    return target,{
        "algorithm":"two_edge_swap_same_buyer_mass_near_weight_pairs",
        "proposals":proposed,"successful_swaps":committed,
        "source_support_count":int(np.count_nonzero(original)),
        "new_support_count":int(np.count_nonzero(target)),
        "buyer_and_seller_degree_exact":True,
        "buyer_value_column_mass_conserved":True,
        "seller_strength_max_absolute_difference":float(diff.max()),
        "seller_strength_max_relative_difference":float(seller_relative.max()),
        "seller_strength_mean_relative_difference":float(seller_relative.mean()),
        "seller_strength_exactly_preserved":bool(np.allclose(original_seller,
                                                          target.sum(axis=1),
                                                          rtol=1e-10,atol=1e-11)),
        "full_degree_and_strength_preserving_control_certified":False
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",type=Path,default=Path("outputs/n5_q1_four_arm_pilot"))
    opts=ap.parse_args()
    out=opts.out_dir
    out.mkdir(parents=True,exist_ok=True)
    data=json.loads((SOURCE/"m001.json").read_text())
    assert_pass(data["revision"]=="n5-r1" and len(data["V001"])==8,
                "Original frozen source changed")
    A=np.asarray(data["M001"],float)
    original=A.copy()
    assert_pass(A.shape==(104,104),"Frozen source input-output matrix not 104 sectors")
    P0=baseline6(A,data["I001"])
    P1,_,_,_=simple10(A,data["V002"][0])
    P2,matched=density_only(A,int(np.count_nonzero(P1)))
    assert_pass(matched,"Direct density comparator not attainable in original fixed pilot")
    P3,rewire=rewire_financial_only(P1)
    networks={"M0":P0,"M1":P1,"M2":P2,"M3":P3}
    source_order=np.argsort(-A.sum(axis=1))
    kwargs={
        "seed":29112027,
        "periods":36,
        "shock_start":13,
        "shock_length":9,
        "shock_source":int(source_order[0]),
        "inventory_months":1.,
        "payment_capacity_scale":5.,
        "credit_fraction":1.2
    }
    scenarios={
        "K0":{"shock_severity":0.},
        "K1":{"shock_severity":.5},
        "K2":{"shock_severity":.35,"shock_source":int(source_order[1])}
    }
    rows=[];statuses=[];paths={}
    for name,P in networks.items():
        for scenario,override in scenarios.items():
            args={**kwargs,**override}
            full=(name in ("M1","M3") and scenario=="K1")
            result=run(A,P,**args,full_ledger=full)
            paths[(name,scenario)]=result["path"]
            for t in result["path"]:
                rows.append({"A":name,"K":scenario,"SEED":kwargs["seed"],**t})
            statuses.append({
                "A":name,"K":scenario,
                "MAX_GOODS_RESIDUAL":max(r["R001"] for r in result["path"]),
                "MAX_INPUT_RESIDUAL":max(r["R002"] for r in result["path"]),
                "MAX_MONEY_RESIDUAL":max(r["R003"] for r in result["path"]),
                "LEDGER_FULL":int(full)
            })
            if full:
                (out/f"q1_original_period_ledgers_{name}_{scenario}.json").write_text(
                    json.dumps(result["ledger"],separators=(",",":"))+"\n")
    assert_pass(len(rows)==12*36 and len(statuses)==12,
                "Four-by-three paired economic engineering pilot incomplete")
    assert_pass(max(v[k] for v in statuses for k in
                    ("MAX_GOODS_RESIDUAL","MAX_INPUT_RESIDUAL","MAX_MONEY_RESIDUAL"))<1e-9,
                "Engineering pilot did not satisfy periodic stock-flow identities")
    z1=run(A,P1,**{**kwargs,"shock_severity":.5},mode="zero_frictions")
    z3=run(A,P3,**{**kwargs,"shock_severity":.5},mode="zero_frictions")
    assert_pass(z1["path"]==z3["path"],
                "Financial-topology placebo affects real outcomes without financial friction")
    assert_pass(np.array_equal(A,original),"Public control altered technology")
    contrast=[]
    for other in ("M1","M2","M3"):
        for shock in ("K1","K2"):
            for outcome in ("Y001","Y002","Y003","Y004","Y005","Y006","Y007","Y008","Y009"):
                value=sum(
                    (a[outcome]-a0[outcome])-(b[outcome]-b0[outcome])
                    for a,a0,b,b0 in zip(paths[(other,shock)],paths[(other,"K0")],
                                         paths[("M0",shock)],paths[("M0","K0")])
                )
                contrast.append({
                    "COMPARATOR_ARM":other,
                    "SHOCK":shock,
                    "OUTCOME":outcome,
                    "CUMULATIVE_MATCHED_DID_ENGINEERING_ONLY":float(value),
                    "SCIENTIFIC_INFERENCE_ALLOWED":0,
                    "ECONOMIC_ANCHOR_ID":"UNMAPPED"
                })
    assert_pass(len(contrast)==3*2*9,"Missing matched economic engineering contrasts")
    csvwrite(out/"q1_four_arm_period_path.csv",rows)
    csvwrite(out/"q1_four_arm_matched_differences.csv",contrast)
    csvwrite(out/"q1_four_arm_ledger_residuals.csv",statuses)
    (out/"q1_rewire_engineering_diagnostics.json").write_text(json.dumps(rewire,indent=2)+"\n")
    state={
        "schema":"n5_public_q1_four_arm_engineering_batch_v1",
        "status":"SMALL_ENGINEERING_PILOT_ONLY",
        "source_frozen":"n5-r1",
        "original_economic_anchor_count":8,
        "original_economic_anchors_applied":0,
        "scenario_count":3,"network_arms":list(networks),
        "matched_reference_seed":kwargs["seed"],
        "frozen_network_structure_index":0,
        "paid_stockflow_trajectories":12,
        "zero_friction_placebo_trajectories":2,
        "confirmation_trajectories":0,
        "periods":36,"matched_comparisons":len(contrast),
        "full_period_source_ledgers_written":2,
        "all_accounting_residuals_less_than_1e9_negative":True,
        "physical_input_matrix_unchanged":True,
        "zero_friction_topology_placebo_identical":True,
        "degree_and_buyer_mass_preserving_rewire_pass":True,
        "seller_strength_preserving_rewire_certified":False,
        "eight_anchor_calibration_certified":False,
        "genuine_period_matched_macro_validation_complete":False,
        "economic_effects_independently_confirmed":False,
        "science_reviewer_question_one_complete":False,
        "large_scale_screen_permitted":False,
        "source_sha256":{"m001.json":digest(SOURCE/"m001.json")}
    }
    (out/"q1_batch_status.json").write_text(json.dumps(state,indent=2)+"\n")
    print(json.dumps(state,indent=2))


if __name__=="__main__":
    main()
