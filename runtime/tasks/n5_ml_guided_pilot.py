"""Public N5 surrogate-guided structural discovery + fresh coupled-engine test.

Exploratory study only. Model predictions are accepted only when held-out
structure prediction beats a training-mean baseline. New seed validation is
separate. Frozen old N3 outcomes and historical reference targets never change.
The eight original economic anchors are NOT linked to this engineering kernel.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import qmc
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from runtime.tasks.n5_clearing_engine import run
from runtime.tasks.n5_review_proofs import baseline6, metrics, simple10

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"public_bundle/n5_v1"


def require(value,why):
    if not bool(value):raise RuntimeError(why)


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def writecsv(path,rows):
    require(bool(rows),"empty output: "+str(path))
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def exposure(A,P,seed,shock_severity):
    return run(A,P,seed=int(seed),periods=24,shock_start=9,
               shock_length=6,shock_severity=shock_severity,
               shock_source=int(np.argmax(A.sum(axis=1))),
               payment_capacity_scale=5.,inventory_months=1.,
               credit_fraction=1.2,full_ledger=False)


def stockflow_ok(result):
    path=result["path"]
    require(len(path)==24,"unexpected paired horizon")
    require(all(max(x["R001"],x["R002"],x["R003"])<1e-9
                for x in path),"production/payment conservation failure")


def shock_loss(A,P,seed):
    base=exposure(A,P,seed,0.)
    shock=exposure(A,P,seed,.5)
    stockflow_ok(base)
    stockflow_ok(shock)
    post=range(9,24)
    base_va=sum(base["path"][t]["Y002"] for t in post)
    loss=sum(base["path"][t]["Y002"]-shock["path"][t]["Y002"] for t in post)
    return float(loss),float(base_va),{
        "base":base,"shock":shock
    }


def format_network(A,Z):
    P,_,_,_=simple10(A,Z)
    require(P.shape==A.shape and np.all(np.isfinite(P)) and np.min(P)>=0,
            "invalid candidate financial network")
    return P


def moments(A,P,targets):
    M=np.asarray(metrics(P),float)
    e=np.asarray([x["T"][0] for x in targets],float)
    lo=np.asarray([x["T"][1] for x in targets],float)
    hi=np.asarray([x["T"][2] for x in targets],float)
    half=np.maximum((hi-lo)/2.,1e-12)
    err=(M-e)/half
    passband=bool(np.all((lo<=M)&(M<=hi)))
    return M,float(np.sum(err**2)),passband


def candidate_rows(A,Zs,targets,label):
    res=[]
    for i,z in enumerate(Zs):
        P=format_network(A,z)
        M,distance,passes=moments(A,P,targets)
        res.append({"K":label+str(i).zfill(3),
                    "S":i,
                    "SCORE_STRUCTURAL":distance,
                    "SIX_MOMENTS_WITHIN_ORIGINAL_BANDS":int(passes),
                    "N_ACTIVE_PAYMENT_LINKS":int(np.count_nonzero(P)),
                    "C1":float(M[0]),"C2":float(M[1]),
                    "C3":float(M[2]),"C4":float(M[3]),
                    "C5":float(M[4]),"C6":float(M[5])})
    return res


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",type=Path,
                    default=Path("outputs/n5_ml_surrogate_pilot"))
    args=ap.parse_args()
    output=args.out_dir
    output.mkdir(parents=True,exist_ok=True)
    m=json.loads((DATA/"m001.json").read_text())
    t=json.loads((DATA/"t001.json").read_text())
    require(m["revision"]==t["revision"]=="n5-r1","mixed source revisions")
    A=np.asarray(m["M001"],float)
    frozen=A.copy()
    train_grid=np.asarray(m["V002"],float)
    require(A.shape==(104,104) and train_grid.shape==(32,10),
            "frozen original design changed")
    require(np.all((train_grid>=0)&(train_grid<=1)),
            "unit-frozen original controls invalid")
    requires=[x for x in t["M201"]]
    require(len(requires)==6,"original six moment registry changed")
    P0=baseline6(A,m["I001"])
    train_seed=46017
    inherited_loss,inherited_va,_=shock_loss(A,P0,train_seed)
    historical=candidate_rows(A,train_grid,requires,"O")
    labels=[]
    for k,z in enumerate(train_grid):
        p=format_network(A,z)
        l,va,_=shock_loss(A,p,train_seed)
        labels.append(inherited_loss-l)
        historical[k]["ENGINEERING_GAIN_SINGLE_TRAIN_SEED"]=float(labels[-1])
    labels=np.array(labels,float)

    # Seal eight original structures as out-of-sample ML prediction tests.
    rng=np.random.default_rng(7321)
    perm=rng.permutation(32)
    fit=perm[:24]
    held=perm[24:]
    require(len(set(fit)&set(held))==0,"ML fit/holdout leakage")
    surrogate=RandomForestRegressor(
        n_estimators=120,min_samples_leaf=2,max_features=.7,
        random_state=321,n_jobs=1)
    surrogate.fit(train_grid[fit],labels[fit])
    forecast=surrogate.predict(train_grid[held])
    naive=np.full(8,float(np.mean(labels[fit])))
    mae=float(mean_absolute_error(labels[held],forecast))
    naive_mae=float(mean_absolute_error(labels[held],naive))
    predictiveness=bool(mae<naive_mae)
    holdout=[{
        "ORIGINAL_STRUCTURE_INDEX":int(i),
        "TRUE_ABM_ENGINEERING_GAIN":float(labels[i]),
        "ML_PREDICTED_GAIN":float(pred),
        "NAIVE_TRAIN_MEAN_PREDICTION":float(avg),
        "TRAINED_ON_THIS_STRUCTURE":0,
    } for i,pred,avg in zip(held,forecast,naive)]

    # Candidates are generated independently of the eight held-out economic
    # labels; no selection uses the held-out target.
    Z=qmc.Sobol(d=10,scramble=True,seed=8802).random_base2(m=7)
    candidates=candidate_rows(A,Z,requires,"C")
    predicted=surrogate.predict(Z)
    for rec,pred in zip(candidates,predicted):
        rec["PREDICTED_GAIN_UNCERTIFIED"]=float(pred)
    feasible=[j for j,r in enumerate(candidates)
              if r["SIX_MOMENTS_WITHIN_ORIGINAL_BANDS"]]
    # Always hold fidelity to preregistered targets above the model objective.
    pool=feasible if len(feasible)>=4 else list(range(len(Z)))
    if predictiveness:
        preferred=sorted(pool,key=lambda i:
            (-float(predicted[i]),candidates[i]["SCORE_STRUCTURAL"],i))[:4]
        selection_mode="validated_ml_score_with_six_moment_feasibility"
    else:
        preferred=sorted(pool,key=lambda i:
            (candidates[i]["SCORE_STRUCTURAL"],i))[:4]
        selection_mode="ml_failed_holdout_fallback_to_structural_design"
    require(len(preferred)==4,"fewer than four original selected candidates")
    reserved=[i for i in pool if i not in preferred]
    require(len(reserved)>=4,"no independent random comparator pool")
    random_choices=list(np.random.default_rng(45091).choice(
        reserved,size=4,replace=False).astype(int))
    selected=[("TARGETED",int(i)) for i in preferred]
    selected +=[("RANDOM_CONTROL",int(i)) for i in random_choices]

    # NEW random seeds never used to fit the surrogate; paired shocks and
    # own unshocked controls for every selected financial network.
    fresh_seeds=(920011,920017)
    tests=[]
    for seed in fresh_seeds:
        inherited,ref_va,_=shock_loss(A,P0,seed)
        for group,j in selected:
            P=format_network(A,Z[j])
            loss,noshock_va,_=shock_loss(A,P,seed)
            tests.append({
                "NEW_CONFIRMATION_SEED":seed,
                "K":candidates[j]["K"],
                "GROUP":group,
                "ML_SELECTION_MODE":selection_mode,
                "ALL_SIX_MOMENTS_IN_BAND":
                    candidates[j]["SIX_MOMENTS_WITHIN_ORIGINAL_BANDS"],
                "MODEL_PREDICTION":float(predicted[j]),
                "INHERITED_SHOCK_LOSS":float(inherited),
                "CANDIDATE_SHOCK_LOSS":float(loss),
                "ENGINEERING_GAIN_VS_INHERITED":float(inherited-loss),
                "PCT_GAIN_RELATIVE_INHERITED_UNSHOCKED_VA":
                    float(100*(inherited-loss)/max(abs(ref_va),1e-12)),
                "UNSHOCKED_CANDIDATE_VA":float(noshock_va),
                "PERIOD_MATCHED_TO_HISTORICAL_DATA":0,
                "ORIGINAL_ECONOMIC_ANCHOR_APPLIED":0
            })
    require(len(tests)==16,"two-fresh-seed experiment incomplete")
    require(np.array_equal(A,frozen),"immutable physical technology changed")
    require(all(len([x for x in tests if x["NEW_CONFIRMATION_SEED"]==seed])==8
                for seed in fresh_seeds),"paired confirmation incomplete")

    train=[{"S":i,
            "Z":json.dumps(train_grid[i].tolist()),
            "SUBSET":"FIT" if i in fit else "SEALED_TEST",
            "ENGINEERING_GAIN_ON_SINGLE_SEED":float(labels[i]),
            "Q2_TARGET_DISTANCE":historical[i]["SCORE_STRUCTURAL"],
            "SIX_MOMENTS_IN_BAND":
                historical[i]["SIX_MOMENTS_WITHIN_ORIGINAL_BANDS"]}
           for i in range(32)]
    selection=[{
        "K":candidates[j]["K"],"GROUP":group,
        "PREDICTED_GAIN":float(predicted[j]),
        "Q2_STRUCTURAL_SCORE":candidates[j]["SCORE_STRUCTURAL"],
        "SIX_MOMENTS_IN_BAND":
            candidates[j]["SIX_MOMENTS_WITHIN_ORIGINAL_BANDS"],
        "Z_UNIT_CONTROLS":json.dumps(Z[j].tolist())}
        for group,j in selected]
    writecsv(output/"ml_original_32_training_and_sealed_test.csv",train)
    writecsv(output/"ml_sealed_prediction_holdout.csv",holdout)
    writecsv(output/"ml_128_candidate_structural_scores.csv",candidates)
    writecsv(output/"ml_candidate_selection_and_controls.csv",selection)
    writecsv(output/"ml_fresh_seed_abm_validation.csv",tests)

    targeted=np.array([x["ENGINEERING_GAIN_VS_INHERITED"]
                       for x in tests if x["GROUP"]=="TARGETED"])
    control=np.array([x["ENGINEERING_GAIN_VS_INHERITED"]
                      for x in tests if x["GROUP"]=="RANDOM_CONTROL"])
    all_pass=sum(x["ALL_SIX_MOMENTS_IN_BAND"] for x in tests)
    report={
        "schema":"n5_public_ml_guided_engineering_pilot_v1",
        "purpose":"exploratory surrogate discovery, new-seed coupled-engine test",
        "original_network_training_structures":24,
        "sealed_original_heldout_structures":8,
        "candidate_design_sobol_count":128,
        "candidate_original_moment_fidelity_count":len(feasible),
        "selection_mode":selection_mode,
        "ml_holdout_mae":mae,
        "naive_training_mean_holdout_mae":naive_mae,
        "ml_holdout_r2":float(r2_score(labels[held],forecast)),
        "ml_predicts_better_than_naive_on_sealed_holdout":predictiveness,
        "tested_new_network_candidates":8,
        "fresh_unseen_seeds":list(fresh_seeds),
        "fresh_seed_candidate_comparisons":16,
        "targeted_mean_gain":float(targeted.mean()),
        "random_control_mean_gain":float(control.mean()),
        "targeted_minus_random_engineering_gain":float(targeted.mean()-control.mean()),
        "validation_case_six_moment_band_passes":int(all_pass),
        "outcome_metric":"cumulative decrease in real-value-added shock loss; positive is better",
        "original_frozen_technology_unchanged":True,
        "original_development_target_thresholds_altered":False,
        "original_n3_historical_case_results_edited":False,
        "original_economic_anchor_count":8,
        "original_economic_anchors_applied":0,
        "model_is_not_historical_period_matched":True,
        "statistical_significance_test_predeclared":False,
        "small_seeds_not_independent_scientific_confirmation":True,
        "n5_q1_scientific_closure":False,
        "n5_q2_frozen_code_parity_certified":False,
        "n5_q3_macro_model_validation_complete":False,
        "n5_q4_development_targets_improved_in_original_model":False,
        "full_n5_simulation_unlocked":False,
        "source_sha256":{p:checksum(DATA/p) for p in ("m001.json","t001.json")}
    }
    (output/"ml_pilot_status.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
