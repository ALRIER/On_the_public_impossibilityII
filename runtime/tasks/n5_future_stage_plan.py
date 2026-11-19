"""Immutable proposed N5 public computational design and workload preflight.

This is a design enumerator only: it cannot run scientific simulations.
The anchor-to-coupled-engine mapping and independent macro calibration are
not yet certified and must be completed before a production dispatch is built.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/"public_bundle/n5_v1"
ARMS=["M0","M1","M2","M3"] # inherited, reconstructed, density-only and topology control (private decode)
SCREEN_SCENARIOS=["S0","S1","S2","S3"] # frozen no-shock, mild, severe and liquidity regime
CONFIRM_SCENARIOS=["S0","S1","S2","S3","S4","S5"] # plus alternate source and multi-supplier regime
CONFIRM_STRUCTURES=[0,4,8,12,16,20,24,28]
SCREEN_MASTER=26062027
CONFIRM_MASTER=27062027
STRIDE=104729

def need(condition,msg):
    if not condition:raise RuntimeError(msg)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def row_count(structures,anchors,seeds,arms,scenarios):
    return len(structures)*len(anchors)*len(seeds)*len(arms)*len(scenarios)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",type=Path,default=Path("outputs/n5_plan"))
    args=ap.parse_args()
    p=json.loads((BUNDLE/"m001.json").read_text())
    nstruct=len(p["V002"]);na=len(p["V001"])
    need(nstruct==32 and na==8 and len(CONFIRM_STRUCTURES)==8,
         "Frozen original anchor/structure bundle changed")
    need(len(ARMS)==len(set(ARMS)),"Duplicate economic arm")
    need(len(SCREEN_SCENARIOS)==4 and len(CONFIRM_SCENARIOS)==6,
         "Scenario preregistration changed")
    phases={
      "screen":{"structures":list(range(nstruct)),
                "anchors":list(range(na)),
                "seeds":[SCREEN_MASTER+j*STRIDE for j in range(2)],
                "arms":ARMS,"scenarios":SCREEN_SCENARIOS},
      "confirm":{"structures":CONFIRM_STRUCTURES,
                 "anchors":list(range(na)),
                 "seeds":[CONFIRM_MASTER+j*STRIDE for j in range(12)],
                 "arms":ARMS,"scenarios":CONFIRM_SCENARIOS}
    }
    s1=set(phases["screen"]["seeds"])
    s2=set(phases["confirm"]["seeds"])
    need(not s1.intersection(s2),"Screen and confirmation random seeds collide")
    sizes={x:row_count(**v) for x,v in phases.items()}
    need(sizes=={"screen":8192,"confirm":18432},
         "Frozen total experiment envelope changed")
    args.out_dir.mkdir(parents=True,exist_ok=True)
    shards=[]
    for phase,v in phases.items():
        for shard,structure in enumerate(v["structures"]):
            n=na*len(v["seeds"])*len(ARMS)*len(v["scenarios"])
            shards.append({"PHASE":phase,"SHARD":shard,
                           "STRUCTURE_INDEX":structure,
                           "ECONOMIC_ANCHORS":na,
                           "INDEPENDENT_SEEDS":len(v["seeds"]),
                           "NETWORK_ARMS":len(ARMS),
                           "SHOCK_SCENARIOS":len(v["scenarios"]),
                           "EXPECTED_TRAJECTORIES":n,
                           "MASTER_SEED":SCREEN_MASTER if phase=="screen" else CONFIRM_MASTER,
                           "SEED_STRIDE":STRIDE,
                           "FULL_RUNTIME_ALLOWED":0})
    with (args.out_dir/"o601.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,list(shards[0]));w.writeheader();w.writerows(shards)
    report={
      "schema":"n5_public_full_design_prospective_v1",
      "frozen_source_input_sha256":{name:sha(BUNDLE/name) for name in ["m001.json","r001.json","t001.json"]},
      "screen_design":{"structures":32,"anchors":8,"unique_seeds":2,
                       "arms":ARMS,"scenario_codes":SCREEN_SCENARIOS,
                       "trajectories":sizes["screen"],"shards":32},
      "confirm_design":{"structures":CONFIRM_STRUCTURES,"anchors":8,
                        "unique_fresh_seeds":12,
                        "arms":ARMS,"scenario_codes":CONFIRM_SCENARIOS,
                        "trajectories":sizes["confirm"],"shards":8},
      "total_prospective_trajectories":sum(sizes.values()),
      "sum_shard_rows":sum(r["EXPECTED_TRAJECTORIES"] for r in shards),
      "seed_family_overlap":0,
      "maximum_public_parallel_jobs":20,
      "calibration_of_full_legacy_macro_anchor_vectors":"NOT_VERIFIED",
      "full_four_arm_network_implementation":"NOT_FINISHED",
      "independent_confirmation_not_yet_launched":True,
      "economic_significance_bands_and_power_analysis":"NOT_FROZEN",
      "source_data_disclosure_review":"NEEDS_FINAL_SIGN_OFF",
      "cost_estimate":"PENDING_VALIDATED_SHARD_RUNTIME_AND_EVIDENCE_SIZE",
      "scientific_experiment_ready":False,
      "large_scientific_jobs_must_not_auto_start":True
    }
    need(report["sum_shard_rows"]==report["total_prospective_trajectories"],
         "Partially counted design")
    (args.out_dir/"o602.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
