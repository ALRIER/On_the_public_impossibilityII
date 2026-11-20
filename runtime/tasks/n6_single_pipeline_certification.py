"""N6-2 single-run scientific YES/NO adjudicator for NEW Test3 coupling.

Runs only in the PUBLIC numerical repository, and explicitly cannot import
private original Test3 code. Its verdict is NO whenever actual eight-anchor
*paired* parity evidence from the certified source model is unavailable.
A successful code execution is never misrepresented as a scientific pass.

The upstream no-shock engineering test is invoked in the same workflow,
in the same checkout, with independently enumerated frozen anchor hashes.
Historical failures and acceptance bands cannot be adjusted.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np

from runtime.tasks.n5_clearing_engine import run
from runtime.tasks.n5_review_proofs import baseline6, metrics, simple10

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"public_bundle"/"n5_v1"
EXPECT={
 "m001.json":"880f565e47b3b4e7b8f36060109fe2359f84f6412010f05598234bd9ca2e88e0",
 "t001.json":"f29f8af23198df44b57851c0815ac254a978817eb4eb2af9aae3312ed56a1289",
 "r001.json":"27ebb7e2f70a06419aa047c494835c8ce87bd6bc52c37775d7223088d0373137",
}
def shab(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()
def validate(ok,msg):
    if not bool(ok): raise AssertionError(msg)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",type=Path,default=Path("outputs/n6_one_pipeline_certification"))
    ap.add_argument("--compatibility-dir",type=Path,
                    default=Path("outputs/n6_one_pipeline_certification/compatibility"))
    args=ap.parse_args()
    args.out_dir.mkdir(parents=True,exist_ok=True)
    source_hashes={}
    for name,required in EXPECT.items():
        p=DATA/name
        digest=shab(p.read_bytes())
        validate(digest==required,f"Frozen public input SHA256 mismatch: {name}")
        source_hashes[name]=digest
    m=json.loads((DATA/"m001.json").read_text())
    t=json.loads((DATA/"t001.json").read_text())
    r=json.loads((DATA/"r001.json").read_text())
    A=np.asarray(m["M001"],float)
    Z=np.asarray(m["V002"],float)
    anchors=np.asarray(m["V001"],float)
    targets=np.asarray(r["V001"],float)
    bounds=np.asarray([row["T"] for row in t["M201"]],float)
    validate(A.shape==(104,104) and Z.shape==(32,10)
             and anchors.shape==(8,10) and targets.shape==(8,3),
             "Frozen 104/32/8/10/3 model inputs changed")
    validate(bounds.shape==(6,3),"Original Q2 bands missing")
    validate(len(r["years"])==29 and r["years"][0]==1995
             and r["years"][-1]==2023,"Original empirical periods changed")
    validate(np.all(np.isfinite(A)) and np.all(A>=0),
             "Physical technology invalid")
    for z in Z:
        P,D,_,_=simple10(A,z)
        value=np.asarray(metrics(P),float)
        validate(np.all(value>=bounds[:,1]) and
                 np.all(value<=bounds[:,2]),"Original Q2 band failure")
        validate(np.allclose(D.sum(axis=0),A.sum(axis=0),atol=1e-10),
                 "Direct technology column-total conservation failure")
    legacy=baseline6(A,m["I001"])
    validate(legacy.shape==A.shape,"Frozen inherited payment network changed")
    register=[]
    for index,(v,ref) in enumerate(zip(m["V001"],r["V001"])):
        register.append({
            "id":f"A{index:02d}",
            "original_10_parameter_vector_sha256":shab(
                json.dumps(v,separators=(",",":")).encode("utf-8")),
            "macro_reference_dimensions":len(ref),
            "new_engine_consumed_original_parameter_vector":False,
            "new_vs_original_pairwise_moments_verified":False,
        })
    validate(len({a["original_10_parameter_vector_sha256"] for a in register})==8,
             "Original anchors collapsed")

    f=args.compatibility_dir/"status.json"
    validate(f.exists(),"The single-run compatibility study did not complete")
    c=json.loads(f.read_text())
    validate(c["schema"]=="n6_new_coupling_vs_old_test3_compatibility_preflight_v1",
             "Unexpected public compatibility result")
    validate(c["old_test3_validation_preserved"] is True,
             "Historical old Test3 reference would be modified")
    validate(c["8_original_frozen_anchors_present"]==8,
             "Missing original numeric anchor fingerprints")
    validate(c["no_shock_public_engineering_cases"]==72
             and c["monthly_output_paths"]==1296
             and c["route_static_cases"]==36,"Incomplete no-shock study")
    validate(c["max_goods_inputs_money_residual"]<1e-9,
             "Original physical-money conservation failed")
    validate(c["no_frictions_placebo_pairs_checked"]==8,
             "Original topology placebos missing")
    validate(c["original_Q2_six_acceptance_bands_unchanged"],
             "Original Q2 acceptance band changed")
    validate(c["original_Q4_historical_failures_changed"] is False,
             "Original Q4 history was overwritten")

    # These four MUST be independently demonstrated from the original
    # validated Test3 code and paired no-shock economic state, not guessed
    # from neutral parameter coordinates, source metadata, or one healthy run.
    new_interface=any(x in inspect.signature(run).parameters
                       for x in ("economic_anchor","anchor_parameters"))
    authentic_source_mechanism_executed=bool(
        c.get("genuine_original_moments_simulated_in_this_public_run",0)==8
        and c.get("8_anchor_legacy_transition_compatibility_confirmed",False)
        and c.get("new_coupling_explicit_legacy_anchor_adapter_detected",False)
        and new_interface)
    traceable_pairwise_eight=bool(
        authentic_source_mechanism_executed
        and c.get("new_coupling_compatible_with_old_test3",False))
    # The comparison above cannot be true for the compact public kernel.
    # A future unified source-faithful runner must replace this gate with a
    # genuine paired Test3 execution and independently frozen source receipts.
    no_shock_feasibility=bool(
        c["engineering_reference_output_below_90pct_cases"]==0)
    # The 90% reference is a diagnostic ONLY, not a scientific target.
    # It is a necessary safe-operating check, never a sufficient proof.
    conservation=bool(
        c["max_goods_inputs_money_residual"]<1e-9
        and c["no_frictions_placebo_pairs_checked"]==8)
    evidence=[
      {"id":"C1","name":"Frozen public A, 8 anchors, 32 original structures and six Q2 bands",
       "passed":True,"scientific_scope":"input provenance only"},
      {"id":"C2","name":"Double-entry cash and goods, and no-friction topology placebo",
       "passed":conservation,"scientific_scope":"engineering only"},
      {"id":"C3","name":"No-shock baseline sustainable under predeclared routed regimes",
       "passed":no_shock_feasibility,
       "observed_failing_cases":c["engineering_reference_output_below_90pct_cases"],
       "cases":c["no_shock_public_engineering_cases"],
       "scientific_scope":"90% illustrative engineering indicator, not original target"},
      {"id":"C4","name":"New coupling actually executes original ten economic state transitions",
       "passed":authentic_source_mechanism_executed,
       "scientific_scope":"requires original certified Test3 source integration"},
      {"id":"C5","name":"All eight Test3 anchors pass genuine paired economic-moment parity",
       "passed":traceable_pairwise_eight,
       "verified_original_anchors":0,
       "scientific_scope":"not the eight numeric hashes or frozen reference vectors"},
      {"id":"C6","name":"Independent confirmation with unchanged history and fresh economic seeds",
       "passed":False,
       "scientific_scope":"not run: new coupling has no source-faithful paired model"}
    ]
    science_pass=all(item["passed"] for item in evidence)
    decision="YES" if science_pass else "NO"
    blockers=[x["id"]+": "+x["name"] for x in evidence if not x["passed"]]
    verdict={
      "schema":"n6_test3_single_pipeline_scientific_certification_v1",
      "scientific_decision":decision,
      "certified":science_pass,
      "original_test3_certification_preserved":True,
      "new_coupling_is_the_only_thing_under_review":True,
      "source_commit_required":True,
      "public_input_sha256":source_hashes,
      "old_test3_8_anchor_original_vectors_frozen":True,
      "old_test3_recertification_performed":False,
      "new_coupling_8_anchor_scientific_pairwise_pass_count":0,
      "new_coupling_no_shock_simulations":c["no_shock_public_engineering_cases"],
      "new_coupling_no_shock_below_illustrative_90pct":
          c["engineering_reference_output_below_90pct_cases"],
      "preserved_Q2_six_bands":True,
      "preserved_original_Q4_failures":True,
      "mechanical_accounting_passed":conservation,
      "checks":evidence,
      "blocking_conditions":blockers,
      "full_economic_ML_optimization_authorized":science_pass,
      "n6_3_scientific_confirmation_authorized":science_pass,
      "no_automatic_historical_acceptance_rewriting":True,
      "next_exact_action":(
        "Insert an opt-in financially funded bilateral payment/delivery module "
        "inside the existing certified Test3 N4 integration seam, preserve "
        "all ten old economic state equations and historical calibration, "
        "run eight paired original-vs-coupled anchors in a trusted independent "
        "environment, and require feasible no-shock production with fresh seeds. "
        "The private source/data must never be published in this public worker."),
      "interpretation":"An NO is an actual negative certification decision for the NEW kernel, not a failure of old Test3.",
    }
    (args.out_dir/"anchor_vector_inventory.json").write_text(
        json.dumps(register,indent=2)+"\n")
    (args.out_dir/"CERTIFICATION_VERDICT.json").write_text(
        json.dumps(verdict,indent=2)+"\n")
    lines=[
      "# Test3 N6-2 — Single-run NEW coupling certification decision",
      "",
      f"## Decision: **{decision}**",
      "",
      "The original certified Test3 economy remains unchanged. This decision",
      "evaluates only the NEW public compact payment-and-delivery kernel.",
      "A green compilation or accounting check is not a source-equivalence proof.",
      "",
      "| Gate | Description | Scientific result |",
      "|---|---|---|"]
    for check in evidence:
        lines.append(f"| {check['id']} | {check['name']} | "+
                     ("PASS" if check["passed"] else "BLOCKED") + " |")
    lines.extend([
      "",
      "### What happened",
      "",
      f"- No-shock public engineering runs: {c['no_shock_public_engineering_cases']}.",
      f"- Below the illustrative 90% planned-output diagnostic: {c['engineering_reference_output_below_90pct_cases']}.",
      f"- Maximum material/cash conservation residual: {c['max_goods_inputs_money_residual']:.3e}.",
      "- The exact original eight parameter vectors and three reference-moment slots",
      "  are verified as frozen; the new engine does **not** execute those state",
      "  transitions. This is a material unclosed compatibility requirement.",
      "- No false original-model recertification, no modified historical Q2/Q4 targets.",
      "",
      "### Required next technical work",
      "",
      verdict["next_exact_action"],
      "",
      "The 90% output criterion is a failure-detection engineering diagnostic,",
      "not an original Test3 scientific acceptance threshold.",
      "",
    ])
    (args.out_dir/"CERTIFICATION_REPORT.md").write_text("\n".join(lines))
    print(json.dumps({
      "CERTIFICATION":decision,
      "OLD_TEST3_CERTIFICATION":"PRESERVED",
      "new_coupling_scientific":science_pass,
      "no_shock_failures":c["engineering_reference_output_below_90pct_cases"],
      "blockers":blockers
    },indent=2))
if __name__=="__main__":
    main()
