"""N5 Q3 public-only annual-reference window and macro-weight robustness batch.

Uses archived neutral numerical annual observations. Does not invent model
subperiod histories: period-matched model validation stays scientifically blocked.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from runtime.tasks.n5_review_proofs import robust_data,percent,window_stat

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"public_bundle/n5_v1"
WINDOWS=[
    ("W1",range(1995,2005)),
    ("W2",range(2005,2015)),
    ("W3",range(2015,2024)),
    ("W4",range(1995,2009)),
    ("W5",range(2009,2024)),
    ("W6",tuple(y for y in range(1995,2024) if y not in (2020,2021))),
]


def guard(ok,reason):
    if not bool(ok):raise RuntimeError(reason)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(path,rows):
    guard(bool(rows),"Cannot save empty numeric coverage")
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def nearest_descriptive(X):
    _,m,s=robust_data([{"V":x.tolist()} for x in X])
    Z=(X-m[None,:])/s[None,:]
    distance=np.sqrt(np.sum(((Z[:,None,:]-Z[None,:,:])**2)/3,axis=2))
    np.fill_diagonal(distance,np.inf)
    return np.min(distance,axis=1)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out-dir",type=Path,default=Path("outputs/n5_q3_batch"))
    args=parser.parse_args()
    out=args.out_dir
    out.mkdir(parents=True,exist_ok=True)
    r=json.loads((SOURCE/"r001.json").read_text())
    guard(r["revision"]=="n5-r1" and r["years"]==list(range(1995,2024)),
          "Original public annual source changed")
    full=[x for x in r["U001"] if x["R"]=="R0"]
    guard(len(full)==146 and len(r["U002"])==36 and len(r["V001"])==8,
          "The two registered reference universes changed")
    X,med,scale=robust_data(full)
    independent,m2,s2=robust_data(r["U002"])
    d0=percent(r["V002"],X,med,scale)
    d1=percent(r["V003"],independent,m2,s2)
    guard(abs(d0[1]-r["L001"][0])<1e-9 and abs(d1[1]-r["L001"][1])<1e-9,
          "The frozen independent-provider percentiles did not reproduce")
    guard(abs(d0[1]-100*11/146)<1e-9 and abs(d1[1]-100*25/36)<1e-9,
          "Expected 11/146 and 25/36 percentages changed")
    original_nn=nearest_descriptive(X)
    baseline_map={u["G"]:float(original_nn[k]) for k,u in enumerate(full)}
    period_rows=[]
    country_rows=[]
    for label,years in WINDOWS:
        yearset=set(years)
        selected=[]
        for u in full:
            v=window_stat(u["Y"],yearset)
            if v is None:continue
            guard(all(np.isfinite(v)),"Annual reference subperiod contains nonfinite statistics")
            selected.append((u["G"],v))
        guard(len(selected)>=3,"Too few original-reference countries in a window")
        subset=np.asarray([x[1] for x in selected],float)
        nn=nearest_descriptive(subset)
        shared=np.array([baseline_map[code] for code,_ in selected])
        corr=float(spearmanr(shared,nn).statistic) if (np.std(shared)>0 and np.std(nn)>0) else float("nan")
        period_rows.append({
            "W":label,"BEGIN_YEAR":min(yearset),"END_YEAR":max(yearset),
            "EXCLUDED_YEARS":"2020,2021" if label=="W6" else "",
            "REGISTERED_COUNTRY_COUNT":len(full),
            "ELIGIBLE_COUNTRIES":len(selected),
            "INELIGIBLE_COUNTRIES":len(full)-len(selected),
            "YEARS_IN_WINDOW":len(yearset),
            "E001_COUNTRY_MEAN":float(np.mean(subset[:,0])),
            "E002_COUNTRY_MEDIAN":float(np.median(subset[:,1])),
            "E003_COUNTRY_MEDIAN":float(np.median(subset[:,2])),
            "MEDIAN_REFERENCE_NN_DISTANCE":float(np.median(nn)),
            "P10_REFERENCE_NN_DISTANCE":float(np.quantile(nn,.1)),
            "P90_REFERENCE_NN_DISTANCE":float(np.quantile(nn,.9)),
            "ORIGINAL_VS_WINDOW_COUNTRY_NN_SPEARMAN":corr,
            "MODEL_SUBPERIOD_DATA_AVAILABLE":0
        })
        for i,(country,vector) in enumerate(selected):
            country_rows.append({
                "W":label,"G":country,"N_YEARS_REQUESTED":len(yearset),
                "E001_MEAN":float(vector[0]),
                "E002_GROWTH_VOLATILITY":float(vector[1]),
                "E003_MEAN":float(vector[2]),
                "COUNTRY_REFERENCE_NN_DISTANCE":float(nn[i]),
                "MATCHED_MODEL_WINDOW_AVAILABLE":0
            })
    weight_rows=[]
    volatility_changed=0
    for k,anchor in enumerate(r["V001"]):
        base=percent(anchor,X,med,scale,"l2",(1/3,1/3,1/3))
        no=percent(anchor,X,med,scale,"l2",(.5,0,.5))
        high=percent(anchor,X,med,scale,"l2",(.2,.6,.2))
        if abs(base[1]-no[1])>1e-9:volatility_changed+=1
        weight_rows.append({
            "V":k,"FROZEN_THREE_DIMENSION_SUPPORT":base[1],
            "NO_VOLATILITY_SUPPORT":no[1],
            "HIGH_VOLATILITY_SUPPORT":high[1],
            "ZERO_VOLATILITY_SUPPORT_CHANGE":no[1]-base[1],
            "HIGH_VOLATILITY_SUPPORT_CHANGE":high[1]-base[1],
            "SOURCE_MODEL_SUBPERIOD_SERIES_AVAILABLE":0,
            "ORIGINAL_3v5_GROUP":"R1" if k in (0,1,7) else "R2"
        })
    guard(len(period_rows)==6 and len(weight_rows)==8,"Incomplete preregistered Q3 coverage")
    guard(len(country_rows)>=6*3,"No eligible-window country observations")
    emit(out/"q3_reference_window_coverage.csv",period_rows)
    emit(out/"q3_reference_country_window_points.csv",country_rows)
    emit(out/"q3_anchor_volatility_weight_diagnostics.csv",weight_rows)
    summary={
        "schema":"n5_public_q3_annual_reference_window_batch_v1",
        "reference_coverage_origin":"original archived neutral annual observations",
        "full_reference_countries":146,
        "independent_external_reference_countries":36,
        "panel_A_frozen_reference_support_percent":float(d0[1]),
        "panel_A_support_numerator":11,"panel_A_support_denominator":146,
        "panel_B_frozen_reference_support_percent":float(d1[1]),
        "panel_B_support_numerator":25,"panel_B_support_denominator":36,
        "distinct_model_anchors":8,
        "model_anchor_weight_ablation_support_changed":volatility_changed,
        "reference_window_count":6,
        "country_window_descriptive_rows":len(country_rows),
        "model_period_matched_timeseries_available":False,
        "cross_window_country_rank_analysis_is_descriptive_only":True,
        "period_matched_scientific_validation_complete":False,
        "scientific_simulations":0,
        "source_sha256":{"r001.json":digest(SOURCE/"r001.json")}
    }
    (out/"q3_batch_status.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
