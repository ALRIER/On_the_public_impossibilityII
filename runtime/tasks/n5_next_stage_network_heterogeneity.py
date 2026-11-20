"""N5 post-repair prospective public exploratory replication, NOT 8-anchor parity.

Frozen physical A, original Q2 six bands, predetermined subset of the
32 original structures, two new seeds and two shock source sectors.
Reports all paired effects (including negative/zero) and no-friction controls.
No discovery of best economic candidate, no training/validation leakage.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from runtime.tasks.n5_clearing_engine import run
from runtime.tasks.n5_review_proofs import baseline6,simple10,metrics

ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/"public_bundle"/"n5_v1"
INDICES=(0,10,20,31)
SEEDS=(930011,930017)
SOURCES_N=2
POLICIES=("legacy_stock_only","forward_input_coverage")
REGIMES=(("binding",.5,.15,.6),("moderate",1.0,1.2,2.0))
OUTCOMES=("Y001","Y002","Y003","Y004","Y006","Y007","Y009")
def need(ok,msg):
    if not bool(ok):raise AssertionError(msg)
def save(path,rows):
    if not rows:return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
def sum_p(path,key):
    return float(sum(t[key] for t in path))
def trace_stats(path):
    return {k:sum_p(path,k) for k in OUTCOMES}
def effect(case,base,key):
    return case[key]-base[key]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",type=Path,default=Path("outputs/n5_next_stage_heterogeneity"))
    out=ap.parse_args().out_dir;out.mkdir(parents=True,exist_ok=True)
    mpath=BUNDLE/"m001.json";tpath=BUNDLE/"t001.json"
    m=json.loads(mpath.read_text());t=json.loads(tpath.read_text())
    A=np.asarray(m["M001"],float); frozen=A.copy()
    Z=np.asarray(m["V002"],float)
    need(A.shape==(104,104) and Z.shape==(32,10),"Original physical/source shape changed")
    bounds=np.asarray([x["T"] for x in t["M201"]],float)
    need(bounds.shape==(6,3),"Six original source bands changed")
    target,lo,hi=bounds.T
    arms={"inherited":baseline6(A,m["I001"])}
    structural=[]
    for i in INDICES:
        P,D,_,_=simple10(A,Z[i])
        mm=np.asarray(metrics(P),float)
        valid=bool(np.all((lo<=mm)&(mm<=hi)))
        need(valid,"Frozen original structure no longer passes original six bands")
        need(np.allclose(D.sum(axis=0),A.sum(axis=0),atol=1e-10),
             "Selected direct mass identity violation")
        arms[f"original_{i:02d}"]=P
        structural.append({"structure":i,"all_six_original_bands_pass":int(valid),
            "frozen_target_distance":float(np.sum(((mm-target)/np.maximum((hi-lo)/2,1e-12))**2)),
            "payment_positive_edges":int(np.count_nonzero(P)),
            **{f"moment_{j+1}":float(val) for j,val in enumerate(mm)}})
    # Predetermined physical source ranking from the frozen A only, never from
    # outcome simulation or shock gains. Top 2 by physical row requirement.
    order=np.argsort(-A.sum(axis=1),kind="stable")
    sources=[int(x) for x in order[:SOURCES_N]]
    rows=[];paired=[];placebo_tests=0;maximum_residual=0.
    count=0
    for seed in SEEDS:
      for source in sources:
        for policy in POLICIES:
          for label,inventory,credit,pcap in REGIMES:
            observed={}
            for arm,P in arms.items():
              for severity in (0.,.65):
                outpath=run(A,P,seed=seed,periods=14,shock_start=3,
                  shock_length=5,shock_source=source,shock_severity=severity,
                  inventory_months=inventory,credit_fraction=credit,
                  payment_capacity_scale=pcap,order_policy=policy,
                  shock_channel="delivery")["path"]
                res=max(max(abs(v[k]) for k in ("R001","R002","R003")) for v in outpath)
                maximum_residual=max(maximum_residual,res)
                need(res<1e-9,"Ledger identity failed")
                observed[(arm,severity)]=trace_stats(outpath)
                rows.append({"seed":seed,"source":source,"policy":policy,
                   "regime":label,"arm":arm,"shock_severity":severity,
                   **observed[(arm,severity)]})
                count+=1
            for arm in list(arms)[1:]:
              r={"seed":seed,"source":source,"policy":policy,"regime":label,
                  "arm":arm,"reference":"inherited"}
              for k in OUTCOMES:
                # Shock interaction, not post-hoc relative gain claim.
                r["shock_did_"+k]=(
                    observed[(arm,.65)][k]-observed[(arm,0.)][k]-
                    observed[("inherited",.65)][k]+observed[("inherited",0.)][k])
                r["shock_level_"+k]=observed[(arm,.65)][k]-observed[("inherited",.65)][k]
                r["no_shock_level_"+k]=observed[(arm,0.)][k]-observed[("inherited",0.)][k]
              paired.append(r)
            # Explicit no-friction falsification on alternative original topologies
            # for a prespecified subset; avoids unnecessary placebo repetitions.
            if seed==SEEDS[0] and source==sources[0]:
                first=run(A,arms["inherited"],seed=seed,periods=14,
                    shock_start=3,shock_length=5,shock_source=source,
                    shock_severity=.65,inventory_months=inventory,
                    credit_fraction=credit,payment_capacity_scale=pcap,
                    order_policy=policy,shock_channel="delivery",
                    mode="zero_frictions")["path"]
                other=run(A,arms["original_31"],seed=seed,periods=14,
                    shock_start=3,shock_length=5,shock_source=source,
                    shock_severity=.65,inventory_months=inventory,
                    credit_fraction=credit,payment_capacity_scale=pcap,
                    order_policy=policy,shock_channel="delivery",
                    mode="zero_frictions")["path"]
                need(first==other,"No-friction placebo differs across topology")
                placebo_tests+=1
    need(np.array_equal(A,frozen),"Original technology mutated")
    need(count==len(SEEDS)*len(sources)*len(POLICIES)*len(REGIMES)*len(arms)*2,
         "Missing trajectory")
    need(len(paired)==len(SEEDS)*len(sources)*len(POLICIES)*len(REGIMES)*(len(arms)-1),
         "Missing paired contrast")
    save(out/"frozen_original_network_q2.csv",structural)
    save(out/"all_trajectories_aggregate.csv",rows)
    save(out/"all_paired_shock_and_levels.csv",paired)
    def summarize(key):
        vals=np.array([r[key] for r in paired],float)
        return {"count":len(vals),"mean":float(vals.mean()),
                "median":float(np.median(vals)),
                "minimum":float(vals.min()),"maximum":float(vals.max()),
                "positive":int(np.sum(vals>1e-10)),
                "negative":int(np.sum(vals<-1e-10)),
                "near_zero":int(np.sum(np.abs(vals)<=1e-10)),
                "per_seed_means":{str(seed):float(np.mean([r[key] for r in paired if r["seed"]==seed])) for seed in SEEDS}}
    summary={
        "schema":"n5_original_network_heterogeneity_exploratory_v1",
        "original_104_sector_technology_unchanged":True,
        "original_six_network_bands_unchanged":True,
        "original_frozen_networks_admissible":len(INDICES),
        "source_indices_frozen_physical_row_sum_rank":sources,
        "seeds":list(SEEDS),"policies":list(POLICIES),
        "regimes":[x[0] for x in REGIMES],
        "network_arms":list(arms),
        "trajectory_count":count,"paired_contrast_count":len(paired),
        "max_conservation_residual":maximum_residual,
        "no_friction_placebo_pairs_checked":placebo_tests,
        "va_shock_did":summarize("shock_did_Y002"),
        "production_shock_did":summarize("shock_did_Y001"),
        "consumption_shock_did":summarize("shock_did_Y004"),
        "value_added_shocked_levels":summarize("shock_level_Y002"),
        "public_m001_sha256":hashlib.sha256(mpath.read_bytes()).hexdigest(),
        "public_t001_sha256":hashlib.sha256(tpath.read_bytes()).hexdigest(),
        "legacy_ten_parameter_anchor_adapter_certified":False,
        "original_eight_economic_anchors_applied":0,
        "original_1995_2023_model_period_match_certified":False,
        "independent_scientific_confirmation":False,
        "large_scale_ml_economic_surrogate_training_authorized":False,
        "original_n3_q4_failures_unchanged":True,
        "interpretation":"Exploratory engineering two-seed mechanism study; neither uncertainty calibration nor economic generalization warranted."
    }
    (out/"status.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
