"""Reconstruct six non-passing numerical outcomes from eight original public N3 ZIPs.

The analysis is PUBLIC ONLY and never changes/reruns the original simulations.
Only neutral target identifiers and numerical output fields are persisted.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,re,statistics,tarfile,zipfile
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
FROZEN=json.loads((ROOT/"public_bundle/n5_v1/t001.json").read_text())
TARGETS={r["L"]:r for r in FROZEN["M202"]}
SIX=set(TARGETS)

def check(value,message):
    if not value:raise RuntimeError(message)

def dumpcsv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--tar",type=Path,required=True)
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    with args.manifest.open(encoding="utf-8",newline="") as fh:
        mf=list(csv.DictReader(fh))
    chosen=[r for r in mf if r["name"].startswith("network_n3_final_confirmation-shard-")]
    check(len(chosen)==8,"Expected eight N3 original source ZIPs")
    byfile={r["filename"]:r for r in chosen}
    original=[];rows=[];case_index={}
    with tarfile.open(args.tar) as archive:
        for member in archive:
            if member.name not in byfile:continue
            b=archive.extractfile(member).read()
            m=byfile[member.name]
            check(len(b)==int(m["bytes"]) and
                  hashlib.sha256(b).hexdigest()==m["sha256"],
                  "Original source ZIP not identical "+member.name)
            seen=[]
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                candidates=[x for x in z.namelist()
                            if re.search(r"n3_validation_anchor_\d+\.csv$",x)]
                check(len(candidates)==1, "Unexpected count of N3 validation source files")
                fname=candidates[0]
                match=re.search(r"anchor_(\d+)",fname)
                check(match is not None,"Original anchor index absent")
                anchor=int(match.group(1))
                check(0<=anchor<8,"Unknown source anchor")
                with z.open(fname) as fh:
                    val=list(csv.DictReader(io.TextIOWrapper(fh,encoding="utf-8-sig")))
                for v in val:
                    t=v["target_id"]
                    if t not in SIX:continue
                    check(t.startswith("T") and t[1:].isdigit(),
                          "Original public target not anonymous")
                    check(v["status"] in ("PASS","FAIL","pass","fail","True","False"),
                          "Unexpected validation status")
                    case=v["N3_CASE_ID"]
                    # Recode unknown source case IDs into neutral within-anchor slots.
                    by_anchor=case_index.setdefault(anchor,{})
                    if case not in by_anchor:by_anchor[case]=len(by_anchor)
                    k=by_anchor[case]
                    ref=TARGETS[t]
                    point=float(v["model_value"])
                    lo=float(v["model_interval_lower"])
                    hi=float(v["model_interval_upper"])
                    e=float(v["empirical_value"])
                    lower=float(v["tolerance_lower"])
                    upper=float(v["tolerance_upper"])
                    check(np.all(np.isfinite([point,lo,hi,e,lower,upper])),
                          "Nonfinite original numeric verification")
                    check(np.allclose([e,lower,upper],ref["T"],rtol=1e-9,atol=1e-9),
                          "Original frozen target numerical mismatch "+t)
                    # Both point-to-band and model-interval-to-band gaps:
                    gap=(point-upper if point>upper else point-lower if point<lower else 0)
                    interval_gap=(lo-upper if lo>upper else hi-lower if hi<lower else 0)
                    width=max((upper-lower)/2,1e-12)
                    rows.append({"Q":ref["id"],"A":anchor,"S":k,
                                 "Y":point,"YLO":lo,"YHI":hi,
                                 "T":e,"TLO":lower,"THI":upper,
                                 "POINT_SIGNED_OUTSIDE":gap,
                                 "INTERVAL_SIGNED_OUTSIDE":interval_gap,
                                 "NORMALIZED_POINT_GAP":gap/width,
                                 "NORMALIZED_INTERVAL_GAP":interval_gap/width,
                                 "PASS":int(v["status"] in ("PASS","pass","True")),
                                 "N":int(v["model_replicates"])})
                seen.append(fname)
            original.append({"artifact_id":str(m["artifact_id"]),"bytes":len(b),
                             "sha256":m["sha256"],"anchor":anchor,
                             "validation":seen})
    check(len(original)==8 and len({x["anchor"] for x in original})==8,
          "Incomplete N3 independent source archives")
    check(len(rows)==6*256, f"Expected 1536 original failed-target rows, got {len(rows)}")
    detailed=sorted(rows,key=lambda r:(r["Q"],r["A"],r["S"]))
    # Verify exactly 8*32 cells for each target, no duplicate case/target pairs.
    summary=[]
    for original_idx,ref in enumerate(FROZEN["M202"]):
        rs=[r for r in detailed if r["Q"]==ref["id"]]
        check(len(rs)==256, "Expected 256 rows per original numeric target")
        check(len({(r["A"],r["S"]) for r in rs})==256,
              "Duplicate original N3 target-case row")
        check(sum(r["PASS"] for r in rs)==0,
              "Frozen 0/256 result contradicted by restored raw ZIPs")
        vals=np.array([r["Y"] for r in rs],float)
        gap=np.array([r["NORMALIZED_POINT_GAP"] for r in rs],float)
        igap=np.array([r["NORMALIZED_INTERVAL_GAP"] for r in rs],float)
        # Keep exactly eight anchors as clusters; 32 repeats do NOT manufacture
        # 256 independent structural learning observations.
        per_anchor=np.array([np.median([r["Y"] for r in rs if r["A"]==a])
                             for a in range(8)],float)
        # Optional variation across structures only when values genuinely differ.
        summary.append({"Q":ref["id"],"T":ref["T"][0],"LO":ref["T"][1],
                        "HI":ref["T"][2],"N_CASES":256,"N_DISTINCT_ANCHORS":8,
                        "N_TOTAL_REPS_REFERENCED":sum(r["N"] for r in rs),
                        "PASS_CASES":0,"ACHIEVED_MEAN":float(np.mean(vals)),
                        "ACHIEVED_MEDIAN":float(np.median(vals)),
                        "ACHIEVED_P25":float(np.quantile(vals,.25)),
                        "ACHIEVED_P75":float(np.quantile(vals,.75)),
                        "ACHIEVED_MIN":float(np.min(vals)),
                        "ACHIEVED_MAX":float(np.max(vals)),
                        "ANCHOR_MEDIAN_MIN":float(np.min(per_anchor)),
                        "ANCHOR_MEDIAN_MAX":float(np.max(per_anchor)),
                        "N_UNIQUE_ACHIEVED_FLOATS":len(set(vals.tolist())),
                        "MEAN_NORM_SIGNED_GAP":float(np.mean(gap)),
                        "MEDIAN_NORM_ABS_GAP":float(np.median(np.abs(gap))),
                        "MEAN_NORM_INTERVAL_SIGNED_GAP":float(np.mean(igap)),
                        "MODE":"ORIGINAL_VALIDATION_INTERVALS_NOT_INDEPENDENT_STRUCTURES"})
    args.out.mkdir(parents=True,exist_ok=True)
    dumpcsv(args.out/"o402.csv",summary)
    dumpcsv(args.out/"o403.csv",detailed)
    manifest={
       "schema":"n5_neutral_original_n3_recovery_v1",
       "status":"ORIGINAL_EIGHT_N3_ZIPS_SHA256_PASS",
       "source_zip_count":len(original),
       "source_original_zip_bytes":sum(r["bytes"] for r in original),
       "recovered_target_rows":len(rows),"failed_targets":len(summary),
       "all_six_target_pass_counts_zero":True,
       "anchor_clusters":8,"structural_combinations_per_anchor":32,
       "full_q4_evidence_available":True,
       "provenance":original
    }
    (args.out/"o404.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":manifest["status"],"source_zip_count":8,
                      "rows":len(rows),"numeric_summary":summary},indent=2))

if __name__=="__main__":main()
