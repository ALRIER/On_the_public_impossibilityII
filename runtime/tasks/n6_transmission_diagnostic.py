"""N6 engineering gate 1: trace complete payment/physical bottleneck chain.

This is a *mechanism identification preflight*, not certification of the eight
original economic anchors or reviewer closure. Uses no private source.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from collections import defaultdict
from pathlib import Path
import numpy as np
from runtime.tasks.n5_clearing_engine import run
from runtime.tasks.n5_review_proofs import simple10,baseline6,metrics

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"public_bundle/n5_v1"
SEED=961120
POLICIES=("legacy_stock_only","forward_input_coverage")
FINANCE={"tight":(.15,.6),"loose":(1.2,2.0)}
CHANNELS=("capacity","delivery")
KEYS=("Y001","Y002","Y003","Y004","Y006","Y007","Y009")
TRACE_KEYS=("ordered","available_before_shock","seller_goods_shortfall",
            "shock_withheld","route_denied","credit_requested",
            "credit_granted","cash_shortfall","payment_edge_capacity_shortfall",
            "settled_deliveries","settlement_gap","explained_gap",
            "input_limited_sectors","input_limited_production_gap",
            "orders_count","disallowed_routes_count")
def need(b,msg):
    if not bool(b):raise AssertionError(msg)
def emit(path,rows):
    if not rows:return
    with path.open("w",newline="",encoding="utf-8") as handle:
        w=csv.DictWriter(handle,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
def summarize(case):
    path=case["path"]
    ledger=case["ledger"]
    need(len(path)==len(ledger),"Period ledger missing")
    total=defaultdict(float); per=[]
    for y,l in zip(path,ledger):
        d=l["N6_TRACE"]
        need(abs(d["settlement_gap"]-d["explained_gap"])<1e-8,
             "Channel decomposition violation")
        need(abs(d["settled_deliveries"]-y["Y009"])<1e-9,
             "N6 shipments and N5 aggregate do not match")
        for k in TRACE_KEYS:total[k]+=float(d[k])
        for k in KEYS:total[k]+=float(y[k])
        per.append({"period":int(y["M"]),**{k:float(d[k]) for k in TRACE_KEYS},
                    **{k:float(y[k]) for k in KEYS}})
    return dict(total),per
def original_structures(A,m,t):
    bounds=np.asarray([x["T"] for x in t["M201"]],float)
    need(bounds.shape==(6,3),"Original Q2 bands changed")
    centers,low,high=bounds.T
    arms={"inherited":baseline6(A,m["I001"])}
    for idx in (0,31):
        P,D,_,_=simple10(A,m["V002"][idx])
        achieved=np.asarray(metrics(P))
        need(bool(np.all(achieved>=low)&np.all(achieved<=high)),
             "Frozen original Q2 structural eligibility failed")
        need(np.allclose(D.sum(axis=0),A.sum(axis=0),atol=1e-10),
             "Technological mass failed")
        arms[f"reconstructed_{idx:02d}"]=P
    return arms
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out-dir",type=Path,default=Path("outputs/n6_mechanism_trace"))
    args=p.parse_args();out=args.out_dir;out.mkdir(parents=True,exist_ok=True)
    mp=DATA/"m001.json";tp=DATA/"t001.json"
    m=json.loads(mp.read_text());t=json.loads(tp.read_text())
    A=np.asarray(m["M001"],float);A0=A.copy()
    need(A.shape==(104,104) and len(m["V001"])==8 and len(m["V002"])==32,
         "Original 104 sector / 8 economic anchors / 32 network structure input mismatch")
    arms=original_structures(A,m,t)
    # Preselect distinct physical sources before any outcomes: most important
    # direct physical edge's seller; and highest row-sum requirements.
    critical=int(np.unravel_index(int(np.argmax(A)),A.shape)[0])
    aggregate=int(np.argsort(-A.sum(axis=1),kind="stable")[0])
    sources=list(dict.fromkeys([critical,aggregate]))
    need(len(sources)==2,"Predeclared physical sources unexpectedly coincide")
    experiments=[];periods=[];effects=[]
    worst_residual=0.
    silent_trace_equal=None;zero_frictions=True
    for source in sources:
      for policy in POLICIES:
        for regime,(credit,pcap) in FINANCE.items():
          for channel in CHANNELS:
            arm_cases={}
            for arm,P in arms.items():
              for severity in (0.,.65):
                kwargs=dict(seed=SEED,periods=12,shock_start=1,shock_length=5,
                    shock_source=source,shock_severity=severity,
                    inventory_months=.5,credit_fraction=credit,
                    payment_capacity_scale=pcap,order_policy=policy,
                    shock_channel=channel)
                case=run(A,P,**kwargs,full_ledger=True,trace_mechanism=True)
                outcome,pr=summarize(case)
                worst_residual=max(worst_residual,max(
                    max(float(row[k]) for k in ("R001","R002","R003"))
                    for row in case["path"]))
                arm_cases[arm,severity]=outcome
                base={"source":source,"policy":policy,"finance":regime,
                      "channel":channel,"arm":arm,"severity":severity}
                experiments.append({**base,**outcome})
                periods.extend([{**base,**row} for row in pr])
                if silent_trace_equal is None:
                    without=run(A,P,**kwargs,full_ledger=True)
                    silent_trace_equal=(case["path"]==without["path"] and
                      all({k:v for k,v in l.items() if k!="N6_TRACE"}==l0
                          for l,l0 in zip(case["ledger"],without["ledger"])))
                    need(silent_trace_equal,"Tracing changed original model outputs")
            for arm in ("reconstructed_00","reconstructed_31"):
              row={"source":source,"policy":policy,"finance":regime,
                   "channel":channel,"arm":arm,"reference":"inherited"}
              for key in KEYS+TRACE_KEYS:
                a=arm_cases[arm,.65][key]
                a0=arm_cases[arm,0.][key]
                b=arm_cases["inherited",.65][key]
                b0=arm_cases["inherited",0.][key]
                row["shock_did_"+key]=(a-a0)-(b-b0)
                row["shocked_level_"+key]=a-b
              effects.append(row)
            # Cheap zero-friction placebo for one fixed source/policy/finance
            # pair per channel, not inferred from model outcomes.
            if source==sources[0] and policy==POLICIES[0] and regime=="tight":
                kw=dict(seed=SEED,periods=12,shock_start=1,shock_length=5,
                     shock_source=source,shock_severity=.65,
                     inventory_months=.5,credit_fraction=credit,
                     payment_capacity_scale=pcap,order_policy=policy,
                     shock_channel=channel,mode="zero_frictions")
                r0=run(A,arms["inherited"],**kw)["path"]
                r1=run(A,arms["reconstructed_00"],**kw)["path"]
                need(r0==r1,"Topology leaks into no-friction placebo")
    need(np.array_equal(A,A0),"Technology changed")
    need(worst_residual<1e-9,"Main stock flow conservation failed")
    need(len(experiments)==len(sources)*len(POLICIES)*len(FINANCE)*len(CHANNELS)*len(arms)*2,
         "Incomplete original mechanism factorial")
    need(len(effects)==len(sources)*len(POLICIES)*len(FINANCE)*len(CHANNELS)*2,
         "Missing matched network contrasts")
    # A small, separate known-binding synthetic positive control: physically
    # blocked direct supplier path, not eligible as an original Q2 network.
    tiny=np.array([[.15,.07,.12],[.08,.19,.06],[.11,.03,.16]])
    full=np.ones((3,3)); blocked=full.copy();blocked[0,1]=0.
    k=dict(seed=4811,periods=16,shock_start=2,shock_length=5,
           shock_source=0,shock_severity=.65,inventory_months=.25,
           credit_fraction=.15,payment_capacity_scale=.6,
           order_policy="forward_input_coverage",shock_channel="delivery",
           full_ledger=True,trace_mechanism=True)
    positive={}
    for arm,P in (("all_direct",full),("one_blocked",blocked)):
        for shock in (0.,.65):
            case=run(tiny,P,**{**k,"shock_severity":shock})
            positive[arm,shock]=summarize(case)[0]
    pos_did=(positive["one_blocked",.65]["Y002"]-
             positive["one_blocked",0.]["Y002"]-
             positive["all_direct",.65]["Y002"]+
             positive["all_direct",0.]["Y002"])
    # Known physical cut should display at least one real-sector difference,
    # but result sign is not used as an economic success gate.
    need(abs(pos_did)>1e-10,"Synthetic mechanism positive control is nonresponsive")
    emit(out/"all_96_original_trajectories.csv",experiments)
    emit(out/"all_1152_monthly_trace_rows.csv",periods)
    emit(out/"all_32_network_matched_contrasts.csv",effects)
    channels=("seller_goods_shortfall","shock_withheld","route_denied",
              "cash_shortfall","payment_edge_capacity_shortfall")
    diag={}
    for name in arms:
        r=[x for x in experiments if x["arm"]==name and x["severity"]==.65]
        channel_sum={k:float(sum(float(q[k]) for q in r)) for k in channels}
        diag[name]={"channel_totals":channel_sum,
                    "input_limited_month_sector_events":int(sum(x["input_limited_sectors"] for x in r)),
                    "input_limited_output_gap":float(sum(x["input_limited_production_gap"] for x in r)),
                    "ordered_total":float(sum(x["ordered"] for x in r)),
                    "settled_total":float(sum(x["settled_deliveries"] for x in r)),
                    "unsettled_total":float(sum(x["settlement_gap"] for x in r))}
    def distribution(key):
        v=np.array([row[key] for row in effects],float)
        return {"n":len(v),"nonzero":int(np.sum(np.abs(v)>1e-10)),
                "positive":int(np.sum(v>1e-10)),
                "negative":int(np.sum(v<-1e-10)),
                "mean":float(np.mean(v)),
                "minimum":float(np.min(v)),
                "maximum":float(np.max(v))}
    stats={
      "schema":"n6_mechanism_trace_public_engineering_gate_v1",
      "original_104x104_A_unchanged":True,
      "original_q2_six_bands_unchanged":True,
      "original_eight_economic_anchors_present_but_not_applied":True,
      "original_10_parameter_8_anchor_parity_certified":False,
      "original_empirical_Q3_Q4_closure":False,
      "original_input_sha256":hashlib.sha256(mp.read_bytes()).hexdigest(),
      "original_target_sha256":hashlib.sha256(tp.read_bytes()).hexdigest(),
      "experimental_source_sectors":sources,
      "networks":list(arms),"seed":SEED,
      "policies":list(POLICIES),"finance_regimes":list(FINANCE),
      "shock_channels":list(CHANNELS),
      "original_full_ledger_trajectories":len(experiments),
      "original_monthly_trace_rows":len(periods),
      "matched_network_shock_contrasts":len(effects),
      "maximum_goods_and_money_conservation_residual":worst_residual,
      "read_only_trace_does_not_modify_outputs":silent_trace_equal,
      "no_friction_placebo_pass":zero_frictions,
      "synthetic_control_real_VA_shock_did":float(pos_did),
      "network_channel_exposures":diag,
      "value_added_shock_DID":distribution("shock_did_Y002"),
      "consumption_shock_DID":distribution("shock_did_Y004"),
      "shocked_value_added_levels":distribution("shocked_level_Y002"),
      "network_reconstructed_marginal_input_limit_did":distribution("shock_did_input_limited_production_gap"),
      "large_scale_ML_ABM_optimization_authorized":False,
      "manuscript_economic_improvement_confirmed":False,
      "diagnostic_only":"N6 stage 1: conditional physical-financial mechanism, not original economic equivalence."
    }
    (out/"n6_stage1_status.json").write_text(json.dumps(stats,indent=2)+"\n")
    print(json.dumps(stats,indent=2))
if __name__=="__main__":main()
