"""N5 Q2 direct supplier selection and density comparator independent numerical audit.

This is an original-public numerical analysis, not a verification of private
source identity. Private source and manuscript remain outside the public repo.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from runtime.tasks.n5_review_proofs import (
    RANGES10, density_only, metrics, simple10
)

ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/"public_bundle/n5_v1"


def guard(test,why):
    if not bool(test):
        raise RuntimeError(why)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_csv(path,rows):
    with path.open("w",encoding="utf-8",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def selected_by_equations(A,z):
    """Independent, explicit Q2 columnwise direct-link mathematical comparator."""
    controls=RANGES10[:,0]+np.asarray(z,float)*(RANGES10[:,1]-RANGES10[:,0])
    qd,relative,max_fraction,minimum_mass=controls[:4]
    result=np.zeros_like(A)
    for j in range(A.shape[1]):
        candidates=np.flatnonzero(A[:,j]>0)
        if len(candidates)==0:continue
        weights=A[candidates,j]
        mass=float(weights.sum())
        rank=np.argsort(weights)[::-1]  # frozen equal-value tie policy
        threshold=max(float(np.quantile(weights,qd)),
                      relative*float(weights.max()))
        eligible=[int(x) for x in rank if weights[x]>=threshold]
        selected=set(eligible[:max(1,int(np.ceil(max_fraction*len(candidates))))])
        if not selected:
            selected.add(int(rank[0]))
        retained=float(sum(weights[k] for k in selected))
        for k in rank:
            if retained>=minimum_mass*mass:break
            k=int(k)
            if k not in selected:
                selected.add(k)
                retained+=float(weights[k])
        global_idx=candidates[np.asarray(sorted(selected),dtype=int)]
        result[global_idx,j]=A[global_idx,j]
        result[:,j]*=mass/result[:,j].sum()
    return result


def synthetic_cases():
    gen=np.random.default_rng(20261120)
    cases=[
        np.zeros((5,5)),
        np.diag([.14,.21,.16,.12,.18]),
        np.full((5,5),.035),
        np.tril(np.full((5,5),.07)),
    ]
    z=np.zeros((5,5))
    z[:4,0]=[.2,.16,.12,.08]
    z[:4,3]=[.1,.2,.1,.3]
    cases.append(z)  # buyer 2 has zero technological requirements
    for k in range(20):
        density=[.03,.15,.45,.95][k%4]
        A=gen.uniform(.002,.18,size=(8,8))
        A[gen.random((8,8))>density]=0.
        cases.append(A)
    return cases


def identities(A,Z):
    original=A.copy()
    P,D,G,H=simple10(A,Z)
    reference=selected_by_equations(A,Z)
    a=A.sum(axis=0)
    assert P.shape==A.shape==D.shape
    guard(np.array_equal(A,original),"Frozen physical technology mutated")
    guard(np.isfinite(P).all() and (P>=0).all(),"Invalid financial weights")
    guard(np.allclose(D.sum(axis=0),a,rtol=1e-11,atol=1e-11),
          "Direct supplier mass not conserved")
    guard(np.allclose(P.sum(axis=0),H.sum(axis=0),rtol=1e-10,atol=1e-11),
          "Final transformed payment mass not conserved")
    guard(not np.any((D>0)&(A==0)),"Phantom physical direct supplier")
    missing=np.where(a==0)[0]
    guard((D[:,missing]==0).all() and (G[:,missing]==0).all()
          and (P[:,missing]==0).all(),"Empty input column manufactured activity")
    positive=np.where(P.sum(axis=0)>0)[0]
    if len(positive):
        W=P[:,positive]/P[:,positive].sum(axis=0)[None,:]
        guard(np.allclose(W.sum(axis=0),1,rtol=1e-10,atol=1e-11),
              "Buyer payment shares do not sum to unity")
    distance=float(np.max(np.abs(D-reference)))
    guard(np.allclose(D,reference,rtol=1e-11,atol=1e-11),
          "Standalone mathematical supplier-selection comparator disagrees")
    indirect=float((RANGES10[:,0]+np.asarray(Z,float)*
                  (RANGES10[:,1]-RANGES10[:,0]))[5])
    B=A@A
    qind=float((RANGES10[:,0]+np.asarray(Z,float)*
                 (RANGES10[:,1]-RANGES10[:,0]))[4])
    p=B[B>0]
    threshold=float(np.quantile(p,qind)) if len(p) else np.inf
    mask=(B>0)&(B>=threshold)
    nonempty=(a>0)&(np.sum(B*mask,axis=0)>0)
    expected=a.copy()
    expected[nonempty]+=a[nonempty]*indirect
    guard(np.allclose(G.sum(axis=0),expected,rtol=1e-10,atol=1e-11),
          "Indirect financial extension has incorrect column mass")
    return P,D,distance


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",type=Path,default=Path("outputs/n5_q2_batch"))
    args=ap.parse_args()
    out=args.out_dir
    out.mkdir(parents=True,exist_ok=True)
    m=json.loads((BUNDLE/"m001.json").read_text())
    t=json.loads((BUNDLE/"t001.json").read_text())
    guard(m["revision"]==t["revision"]=="n5-r1","Mixed frozen source revisions")
    A=np.asarray(m["M001"],float)
    original=A.copy()
    guard(A.shape==(104,104),"Source technology shape changed")
    guard(len(m["V002"])==32 and len(t["M201"])==6,"Original registry changed")
    structure_rows=[]
    metric_rows=[]
    max_d=0.
    original_support=int(np.count_nonzero(A))
    attainable=0
    for i,Z in enumerate(m["V002"]):
        P,D,d=identities(A,Z)
        max_d=max(max_d,d)
        size=int(np.count_nonzero(P))
        Pd,matched=density_only(A,size)
        got=int(np.count_nonzero(Pd))
        guard(np.array_equal(A,original),"Network comparison modified technological A")
        guard(np.allclose(Pd.sum(axis=0),A.sum(axis=0),atol=1e-10),
              "Density comparator fails direct column conservation")
        guard(not np.any((Pd>0)&(A==0)),"Density comparator fabricated physical arc")
        guard(bool(matched)==(size<=original_support),
              "Density-only attainability flag incorrect")
        if matched:guard(got==size,"Achievable density comparator did not match edge count")
        else:guard(got==original_support,"Infeasible density comparator not saturated")
        attainable+=int(matched)
        structure_rows.append({
            "S":i,"TECH_DIRECT_LINKS":original_support,"SELECTED_DIRECT_LINKS":int(np.count_nonzero(D)),
            "RECONSTRUCTED_PAYMENT_LINKS":size,"DENSITY_COMPARATOR_LINKS":got,
            "DIRECT_DENSITY_MATCH_ATTAINABLE":int(matched),
            "PAYMENT_LINKS_ABOVE_TECH_SUPPORT":max(size-original_support,0),
            "DISTANCE_TO_DIRECT_DENSITY":float(np.linalg.norm(P-Pd)),
            "SELECTED_DIRECT_MAX_ABS_DISAGREEMENT":d
        })
        achieved=metrics(P)
        density_vals=metrics(Pd)
        for k,(v,dc,source) in enumerate(zip(achieved,density_vals,t["M201"])):
            target,lower,upper=source["T"]
            metric_rows.append({
                "S":i,"C":source["id"],"RECONSTRUCTED":v,"DENSITY_ONLY":dc,
                "FROZEN_TARGET":target,"LOWER":lower,"UPPER":upper,
                "RECONSTRUCTED_WITHIN_BAND":int(lower<=v<=upper),
                "DENSITY_ONLY_WITHIN_BAND":int(lower<=dc<=upper),
                "DENSITY_COMPARISON_VALID":int(matched)
            })
    guard(len(metric_rows)==192,"Not all 32 x 6 moment observations generated")
    guard(sum(x["RECONSTRUCTED_WITHIN_BAND"] for x in metric_rows)==192,
          "Frozen structural reconstruction no longer reproduces reference intervals")

    cases=synthetic_cases()
    check_rows=[]
    zsets=[np.zeros(10),np.ones(10),np.full(10,.5)]
    for k,B in enumerate(cases):
        for l,z in enumerate(zsets):
            P,D,d=identities(B,z)
            check_rows.append({"CASE":k,"Z":l,"SIZE":B.shape[0],
                               "PHYSICAL_POSITIVE_LINKS":int(np.count_nonzero(B)),
                               "FINANCIAL_POSITIVE_LINKS":int(np.count_nonzero(P)),
                               "SELECTED_POSITIVE_LINKS":int(np.count_nonzero(D)),
                               "EQUATION_COMPARATOR_MAX_ABS_DISAGREEMENT":d})
            max_d=max(d,max_d)
    guard(len(check_rows)==len(cases)*len(zsets),"Edge case coverage incomplete")
    save_csv(out/"q2_structure_comparators.csv",structure_rows)
    save_csv(out/"q2_six_moment_recomputations.csv",metric_rows)
    save_csv(out/"q2_pathological_identity_tests.csv",check_rows)
    status={
        "schema":"n5_public_q2_comparator_batch_v1",
        "source_revision":"n5-r1",
        "original_technology_unchanged":bool(np.array_equal(A,original)),
        "network_structures":32,
        "structural_diagnostic_rows":192,
        "structural_diagnostics_in_frozen_bands":192,
        "direct_density_attainable_count":attainable,
        "direct_density_unattainable_count":32-attainable,
        "standalone_direct_equation_parity_max_abs":max_d,
        "independent_synthetic_matrix_count":len(cases),
        "synthetic_control_grid_total":len(check_rows),
        "source_code_line_by_line_independently_certified":False,
        "full_q2_reviewer_closure":False,
        "scientific_simulations":0,
        "frozen_source_sha256":{name:file_hash(BUNDLE/name)
                               for name in ("m001.json","t001.json")}
    }
    (out/"q2_batch_status.json").write_text(json.dumps(status,indent=2)+"\n")
    print(json.dumps(status,indent=2))


if __name__=="__main__":
    main()
