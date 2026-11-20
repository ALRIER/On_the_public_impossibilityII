"""N5 ML -> structural active search -> matched ABM engineering pilot.

Prospective exploratory wave, NOT legacy economic anchor certification.
32 frozen Q2 network parent groups; group-disjoint 24 train / 8 lockbox.
Models: RF, XGBoost, CatBoost; explicit mean benchmark on sealed groups.
Candidate acquisition uses structural predictions ONLY, never ABM outcomes.
Candidates must pass all six original Q2 bands and exact frozen technology.
All unfavorable, rejected and non-improving trials are reported.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error,r2_score
from xgboost import XGBRegressor
from catboost import CatBoostRegressor
from runtime.tasks.n5_review_proofs import simple10,metrics,baseline6
from runtime.tasks.n5_clearing_engine import run

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"public_bundle"/"n5_v1"
TRAIN_GROUPS=tuple(range(24))
SEALED_GROUPS=tuple(range(24,32))
RADII=(0.00025,0.0025,0.02,0.10)
ABM_SEEDS=(940011,940017)
def require(ok,msg):
    if not bool(ok):raise AssertionError(msg)
def csvwrite(path,rows):
    if not rows:return
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
def network(A,z,center,lo,hi):
    P,D,_,_=simple10(A,z)
    m=np.asarray(metrics(P),float)
    require(np.allclose(D.sum(axis=0),A.sum(axis=0),atol=1e-10),
            "Direct technological input mass mismatch")
    require(np.isfinite(P).all() and (P>=0).all(),"Payment weights not viable")
    score=float(np.sum(((m-center)/np.maximum((hi-lo)/2,1e-12))**2))
    valid=bool(np.all(m>=lo) and np.all(m<=hi))
    return P,score,valid,m
def models():
    return {
      "random_forest":RandomForestRegressor(n_estimators=110,min_samples_leaf=2,
                max_features=.9,random_state=20261120,n_jobs=2),
      "xgboost":XGBRegressor(n_estimators=115,max_depth=3,learning_rate=.065,
                subsample=.85,colsample_bytree=.9,reg_lambda=3.0,
                objective="reg:squarederror",random_state=20261120,n_jobs=2),
      "catboost":CatBoostRegressor(iterations=160,depth=4,learning_rate=.06,
                l2_leaf_reg=5.0,loss_function="RMSE",verbose=False,
                thread_count=2,random_seed=20261120)
    }
def totals(path):return {k:float(sum(row[k] for row in path))
                     for k in ("Y001","Y002","Y003","Y004","Y006","Y007","Y009")}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out-dir",type=Path,default=Path("outputs/n5_ml_abm_discovery_wave"))
    args=parser.parse_args();out=args.out_dir;out.mkdir(parents=True,exist_ok=True)
    mpath=SOURCE/"m001.json";tpath=SOURCE/"t001.json"
    m=json.loads(mpath.read_text());t=json.loads(tpath.read_text())
    A=np.asarray(m["M001"],float); A0=A.copy()
    Z=np.asarray(m["V002"],float)
    T=np.asarray([v["T"] for v in t["M201"]],float)
    require(A.shape==(104,104) and Z.shape==(32,10) and T.shape==(6,3),
            "Frozen scientific input arrays unexpected")
    center,lo,hi=T.T
    best_original=np.inf; frozen=[]
    for parent,z in enumerate(Z):
        _,score,valid,moments=network(A,z,center,lo,hi)
        require(valid,"One frozen original network violates original Q2 acceptance")
        frozen.append({"parent":parent,"score":score,"valid":int(valid)})
        best_original=min(best_original,score)
    # Draw 8 perturbations for each original parent from frozen seeded generator.
    rng=np.random.default_rng(34532)
    records=[]
    for parent,z in enumerate(Z):
        for radius in RADII:
            for draw in range(2):
                dz=np.clip(z+rng.normal(0,radius,size=10),0.,1.)
                _,score,valid,mm=network(A,dz,center,lo,hi)
                records.append({"parent":parent,"radius":radius,"draw":draw,
                    "z":dz,"score":score,"valid":valid,
                    "moments":mm})
    train=[r for r in records if r["parent"] in TRAIN_GROUPS]
    hold=[r for r in records if r["parent"] in SEALED_GROUPS]
    require(len(train)==192 and len(hold)==64,"Group-disjoint split invalid")
    X=np.array([r["z"] for r in train]); y=np.array([r["score"] for r in train])
    Xh=np.array([r["z"] for r in hold]); yh=np.array([r["score"] for r in hold])
    train_parents=set(r["parent"] for r in train)
    hold_parents=set(r["parent"] for r in hold)
    require(not train_parents.intersection(hold_parents),"Parent-group holdout contamination")
    baseline=float(y.mean()); base_mae=float(mean_absolute_error(yh,np.full(len(yh),baseline)))
    model_results=[];fitted={}
    predictions={}
    for name,estimator in models().items():
        estimator.fit(X,y); fitted[name]=estimator
        pred=np.asarray(estimator.predict(Xh),float)
        require(np.isfinite(pred).all(),"Nonfinite surrogate predictions")
        mae=float(mean_absolute_error(yh,pred))
        model_results.append({"model":name,"holdout_mae":mae,
              "holdout_r2":float(r2_score(yh,pred)),
              "training_mean_holdout_mae":base_mae,
              "beats_naive_train_mean":int(mae<base_mae-1e-12),
              "training_parent_groups":24,"sealed_parent_groups":8})
        predictions[name]=pred
    # Original train+holdout candidate rows are preserved with no predictions
    # incorporated into scoring or network eligibility.
    csvwrite(out/"candidate_fit_and_sealed_256.csv",[
      {"parent":r["parent"],"partition":"train" if r["parent"] in TRAIN_GROUPS else "sealed",
       "radius":r["radius"],"draw":r["draw"],"score":r["score"],"valid":int(r["valid"]),
       "controls":json.dumps(r["z"].tolist())} for r in records])
    csvwrite(out/"three_model_sealed_group_benchmark.csv",model_results)
    # New prospective proposals from *training* parents, generated independently.
    # No economic response or sealed-parent label is used in this acquisition.
    acquire_rng=np.random.default_rng(20261121)
    candidates=[]
    for j in range(160):
        parent=int(TRAIN_GROUPS[j%len(TRAIN_GROUPS)])
        radius=float(RADII[(j//len(TRAIN_GROUPS))%len(RADII)])
        z=np.clip(Z[parent]+acquire_rng.normal(0,radius,10),0.,1.)
        yp=np.array([float(est.predict(z.reshape(1,-1))[0]) for est in fitted.values()])
        candidates.append({"candidate":j,"parent":parent,"radius":radius,"z":z,
               "predicted_score":float(yp.mean()),"disagreement":float(yp.std())})
    # Fixed 40 surrogate + 8 disagreement + 8 random acquisition policy.
    ranked=sorted(candidates,key=lambda r:(r["predicted_score"],r["candidate"]))
    picked=ranked[:40]
    remainder=[r for r in candidates if r["candidate"] not in {x["candidate"] for x in picked}]
    picked+=sorted(remainder,key=lambda r:(-r["disagreement"],r["candidate"]))[:8]
    remainder=[r for r in candidates if r["candidate"] not in {x["candidate"] for x in picked}]
    sampled_idx=acquire_rng.choice(len(remainder),size=8,replace=False)
    picked += [remainder[int(i)] for i in sampled_idx]
    require(len({r["candidate"] for r in picked})==56,"Duplicate acquisition candidate")
    acquired=[]
    for idx,r in enumerate(picked):
        _,score,valid,mm=network(A,r["z"],center,lo,hi)
        acquired.append({**r,"acquisition":"predicted_top40" if idx<40 else "model_disagreement8" if idx<48 else "random8",
             "true_score":score,"valid":valid,"moments":mm})
    acquired_csv=[]
    for r in acquired:
        acquired_csv.append({k:v for k,v in r.items() if k not in ("z","moments")} |
                            {"controls":json.dumps(r["z"].tolist()),
                             **{f"moment_{k+1}":float(v) for k,v in enumerate(r["moments"])}})
    csvwrite(out/"active_acquisition_all_56.csv",acquired_csv)
    eligible=[r for r in acquired if r["valid"]]
    better=[r for r in eligible if r["true_score"]<best_original-1e-9]
    # ABM arms were determined on STRUCTURAL grounds before any economic run.
    # Favor best valid structurally, plus a second network with a different
    # parent when feasible. Frozen reference arm 0 is an unchanged control.
    winners=sorted(eligible,key=lambda r:(r["true_score"],r["candidate"]))
    chosen=[]; parents=set()
    for r in winners:
        if r["parent"] not in parents:
            chosen.append(r);parents.add(r["parent"])
        if len(chosen)>=2:break
    if len(chosen)<2:
        chosen=winners[:2]
    require(len(chosen)==2,"Insufficient Q2-admissible finalists; stop")
    arms={"inherited":baseline6(A,m["I001"])}
    p_frozen,_s,_v,_mm=network(A,Z[0],center,lo,hi)
    arms["frozen_00"]=p_frozen
    for j,r in enumerate(chosen):
        P,score,valid,_=network(A,r["z"],center,lo,hi)
        require(valid and score==r["true_score"],"Selected candidate score mismatch")
        arms[f"structural_candidate_{j}"]=P
    # Two predeclared physical sources; existing responsive source is retained,
    # plus independent largest-row physical-technology source. No ABM optimization.
    source_early=int(np.unravel_index(int(np.argmax(A)),A.shape)[0])
    source_rank=int(np.argsort(-A.sum(axis=1),kind="stable")[0])
    sources=tuple(dict.fromkeys((source_early,source_rank)))
    economic_rows=[];pairing=[];maxres=0.
    for source in sources:
      for seed in ABM_SEEDS:
        paths={}
        for arm,P in arms.items():
          for shock in (0.,.65):
            p=run(A,P,seed=seed,periods=14,shock_start=0,
               shock_length=5,shock_severity=shock,shock_source=source,
               inventory_months=.5,credit_fraction=.15,payment_capacity_scale=.6,
               order_policy="forward_input_coverage",
               shock_channel="delivery")["path"]
            res=max(max(abs(x[k]) for k in ("R001","R002","R003")) for x in p)
            maxres=max(maxres,res)
            require(res<1e-9,"Engineering physical/financial ledger failed")
            val=totals(p);paths[arm,shock]=val
            economic_rows.append({"source":source,"seed":seed,"arm":arm,
                "shock":shock,**val})
        for arm in list(arms)[1:]:
          row={"source":source,"seed":seed,"arm":arm,"baseline":"inherited"}
          for k in ("Y001","Y002","Y003","Y004","Y006","Y007","Y009"):
            row["level_"+k]=paths[arm,.65][k]-paths["inherited",.65][k]
            row["did_"+k]=(paths[arm,.65][k]-paths[arm,0.][k]-
                paths["inherited",.65][k]+paths["inherited",0.][k])
          pairing.append(row)
    # Two no-friction topology controls on original and candidate.
    for source in sources:
      base=run(A,arms["inherited"],seed=ABM_SEEDS[0],periods=14,
         shock_start=0,shock_length=5,shock_severity=.65,shock_source=source,
         order_policy="forward_input_coverage",shock_channel="delivery",
         inventory_months=.5,credit_fraction=.15,payment_capacity_scale=.6,
         mode="zero_frictions")["path"]
      compare=run(A,arms["structural_candidate_0"],seed=ABM_SEEDS[0],periods=14,
         shock_start=0,shock_length=5,shock_severity=.65,shock_source=source,
         order_policy="forward_input_coverage",shock_channel="delivery",
         inventory_months=.5,credit_fraction=.15,payment_capacity_scale=.6,
         mode="zero_frictions")["path"]
      require(base==compare,"Financially zero-friction placebo violated")
    csvwrite(out/"ABM_all_32_matched_trajectories.csv",economic_rows)
    csvwrite(out/"ABM_all_12_paired_contrasts.csv",pairing)
    require(np.array_equal(A,A0),"Frozen original technology altered")
    require(len(economic_rows)==len(sources)*len(ABM_SEEDS)*len(arms)*2,"ABM trajectory count incomplete")
    def counts(metric):
        vals=np.array([r[metric] for r in pairing])
        return {"n":len(vals),"positive":int(np.sum(vals>1e-10)),
                "negative":int(np.sum(vals<-1e-10)),
                "near_zero":int(np.sum(np.abs(vals)<=1e-10)),
                "mean":float(np.mean(vals)),
                "min":float(np.min(vals)),"max":float(np.max(vals))}
    result={
       "schema":"n5_ml_to_structural_network_to_abm_exploratory_v1",
       "public_original_matrix_sha256":hashlib.sha256(mpath.read_bytes()).hexdigest(),
       "public_original_target_sha256":hashlib.sha256(tpath.read_bytes()).hexdigest(),
       "original_physical_104x104_A_unchanged":True,
       "original_Q2_six_target_bands_unchanged":True,
       "original_frozen_32_all_q2_bands_pass":True,
       "original_best_frozen_center_score":best_original,
       "training_parent_groups":24,"sealed_parent_groups":8,
       "sealed_group_holdout_candidates":len(hold),"training_candidates":len(train),
       "surrogate_models":model_results,
       "acquisition_pool_size":len(candidates),
       "new_prospectively_ABM_blind_acquired":len(acquired),
       "new_acquired_passing_all_six_original_bands":len(eligible),
       "new_acquired_better_than_best_frozen_score":len(better),
       "best_acquired_valid_score":float(winners[0]["true_score"]),
       "selected_structural_candidate_ids":[int(x["candidate"]) for x in chosen],
       "ABM_arms":list(arms),"ABM_seeds":list(ABM_SEEDS),
       "ABM_predeclared_physical_sources":list(sources),
       "ABM_matched_trajectories":len(economic_rows),
       "ABM_paired_contrasts":len(pairing),
       "ABM_value_added_shock_DID":counts("did_Y002"),
       "ABM_consumption_shock_DID":counts("did_Y004"),
       "ABM_value_added_shock_levels":counts("level_Y002"),
       "ABM_max_conservation_residual":maxres,
       "ABM_no_financial_friction_placebo_pass":True,
       "selected_by_economic_outcome":False,
       "original_eight_legacy_anchor_adapter_certified":False,
       "independent_external_economic_confirmation":False,
       "Q1_beneficial_economic_claim_supported":False,
       "Q4_historical_development_failure_changed":False,
       "large_scale_economic_ML_training_authorized":False,
       "interpretation":"Structural ML and finite engineering ABM pilot; original 10-parameter 8-anchor model is NOT mapped."
    }
    (out/"status.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
