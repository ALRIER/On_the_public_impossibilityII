"""N5 Q4 independent public re-analysis of original recovered N3 numerical cases.

Reads the original *public* N3 source-recovery Release, never private files.
No historical simulation is re-run or retroactively declared successful.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
TARGETS=json.loads((ROOT/"public_bundle/n5_v1/t001.json").read_text())["M202"]


def check(test,description):
    if not bool(test):raise RuntimeError(description)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(path,rows):
    with path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-dir",required=True,type=Path)
    ap.add_argument("--out-dir",type=Path,default=Path("outputs/n5_q4_batch"))
    args=ap.parse_args()
    out=args.out_dir
    out.mkdir(parents=True,exist_ok=True)
    source=args.source_dir
    files=[source/x for x in ("o402.csv","o403.csv","o404.json")]
    check(all(x.is_file() for x in files),"Missing original public numerical data")
    detail=read(files[1])
    original=read(files[0])
    meta=json.loads(files[2].read_text(encoding="utf-8"))
    check(meta["schema"]=="n5_neutral_original_n3_recovery_v1",
          "Original archived numerical N3 schema changed")
    check(meta["source_zip_count"]==8 and meta["recovered_target_rows"]==1536 and
          meta["failed_targets"]==6 and meta["all_six_target_pass_counts_zero"],
          "Original N3 recovered archive is not complete")
    check(meta["source_registry_band_mismatch_count"]==3,
          "Material original/current band differences changed")
    check(len(meta["provenance"])==8 and len({x["anchor"] for x in meta["provenance"]})==8,
          "Original eight archive provenance entries missing")
    check(len(detail)==1536 and len(original)==6,"Expected 1536 case records and six diagnostics")
    byid=defaultdict(list)
    for row in detail:
        byid[row["Q"]].append(row)
    index={r["Q"]:r for r in original}
    check(set(byid)==set(index)=={x["id"] for x in TARGETS},
          "Original six neutral target identities changed")
    variance=[]
    bands=[]
    for target in TARGETS:
        code=target["id"]
        rec=byid[code]
        s=index[code]
        check(len(rec)==256,"Original N3 target does not contain 256 cases")
        keys={(int(x["A"]),int(x["S"])) for x in rec}
        check(keys=={(a,k) for a in range(8) for k in range(32)},
              "Original N3 not a balanced 8-anchor x 32-structure design")
        check(sum(int(x["PASS"]) for x in rec)==0,"Historical N3 failure was revised")
        check(int(s["PASS_CASES"])==0 and int(s["N_CASES"])==256,
              "Original recovered N3 summary contradicts per-case data")
        check(sum(int(x["CURRENT_PASS"]) for x in rec)==int(s["CURRENT_BAND_PASS_CASES"]),
              "Retrospective reference-band pass count inconsistent")
        a=np.empty((8,32),float)
        for x in rec:
            a[int(x["A"]),int(x["S"])]=float(x["Y"])
        check(np.isfinite(a).all(),"Recovered original scientific values invalid")
        grand=float(a.mean())
        amean=a.mean(axis=1)
        smean=a.mean(axis=0)
        total=float(np.sum((a-grand)**2))
        between_anchor=float(32*np.sum((amean-grand)**2))
        between_structure=float(8*np.sum((smean-grand)**2))
        remainder=float(np.sum((a-amean[:,None]-smean[None,:]+grand)**2))
        check(abs(total-(between_anchor+between_structure+remainder))<
              1e-7*max(1.,total),"Two-way descriptive sum-of-squares does not add up")
        variance.append({
            "Q":code,"N_ORIGINAL_CASES":256,"N_ANCHORS":8,"N_STRUCTURES":32,
            "N_UNIQUE_SOURCE_VALUES":len(set(a.ravel().tolist())),
            "SOURCE_VARIANCE":float(np.var(a,ddof=0)),
            "ANCHOR_SS":between_anchor,"STRUCTURE_SS":between_structure,
            "INTERACTION_UNRESOLVED_SS":remainder,"TOTAL_SS":total,
            "ANCHOR_DESCRIPTIVE_FRACTION":between_anchor/total if total>1e-16 else 0.,
            "STRUCTURE_DESCRIPTIVE_FRACTION":between_structure/total if total>1e-16 else 0.,
            "UNIDENTIFIED_FRACTION":remainder/total if total>1e-16 else 0.,
            "CASE_SEED_INDEPENDENCE_CLAIMED":0,
            "INFERENTIAL_VARIANCE_IDENTIFIED":0
        })
        bands.append({
            "Q":code,"SOURCE_ACHIEVED_MEAN":grand,
            "SOURCE_ACHIEVED_MEDIAN":float(np.median(a)),
            "ANCHOR_MEAN_MIN":float(np.min(amean)),
            "ANCHOR_MEAN_MAX":float(np.max(amean)),
            "HISTORICAL_TARGET":float(s["SOURCE_T"]),
            "HISTORICAL_LO":float(s["SOURCE_LO"]),
            "HISTORICAL_HI":float(s["SOURCE_HI"]),
            "LATER_TARGET":float(s["CURRENT_T"]),
            "LATER_LO":float(s["CURRENT_LO"]),
            "LATER_HI":float(s["CURRENT_HI"]),
            "HISTORICAL_ACCEPTANCE_COUNT":0,
            "RETROSPECTIVE_ACCEPTANCE_COUNT":int(s["CURRENT_BAND_PASS_CASES"]),
            "BANDS_IDENTICAL":int(s["BANDS_AGREE"]),
            "HISTORICAL_MEAN_NORMALIZED_SIGNED_GAP":float(s["MEAN_NORM_SIGNED_GAP"]),
            "SOURCE_REGISTRY_CHRONOLOGY_EXPLANATION_PROVEN":0
        })
    check(sum(b["BANDS_IDENTICAL"]==0 for b in bands)==3,
          "Original/current tolerance divergence no longer matches audited source")
    check(sorted(x["RETROSPECTIVE_ACCEPTANCE_COUNT"] for x in bands)
          ==[0,0,0,256,256,256],"Re-adjudication is not the historical six-failure result")
    write(out/"q4_original_vs_later_six_targets.csv",bands)
    write(out/"q4_anchor_structure_variance_descriptive.csv",variance)
    report={
        "schema":"n5_q4_original_n3_independent_numeric_batch_v1",
        "public_source_release":"n5-n3-public-source-probe-r1-44627702757-a1",
        "original_source_archives_referenced":8,
        "original_case_target_rows":1536,
        "original_n3_cases_per_target":256,
        "original_failed_targets":6,
        "all_six_original_0_of_256":True,
        "material_target_band_changes":3,
        "later_target_retro_pass_counts":{x["Q"]:x["RETROSPECTIVE_ACCEPTANCE_COUNT"] for x in bands},
        "historical_acceptance_never_retroactively_changed":True,
        "variance_components_descriptive_only":True,
        "no_independent_inference_from_256_reused_cases":True,
        "source_registry_chronology_reason_independently_proven":False,
        "full_q4_reviewer_closure":False,
        "scientific_simulations":0,
        "public_recovered_source_asset_sha256":{x.name:sha(x) for x in files},
        "frozen_current_registry_sha256":sha(ROOT/"public_bundle/n5_v1/t001.json")
    }
    (out/"q4_batch_status.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
