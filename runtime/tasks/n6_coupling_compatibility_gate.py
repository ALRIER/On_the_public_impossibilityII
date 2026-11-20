"""Test3/N6-2: audit NEW financial/material coupling against a frozen reference.

The OLD Test3 model was previously validated. This new public-only preflight
checks whether the distinct N5/N6 coupling is safe to compare with that model.
It does NOT revalidate original Test3 or relabel existing experimental knobs
as any of the eight legacy economic anchor parameters.

Pass criteria for executing diagnostics are conservation and provenance, not
a desired economic effect or a fabricated eight-anchor compatibility claim.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import inspect
import json
from pathlib import Path
import numpy as np

from runtime.tasks.n5_clearing_engine import run, equilibrium
from runtime.tasks.n5_review_proofs import baseline6, metrics, simple10

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "public_bundle" / "n5_v1"
SEEDS = (961120, 961121)
BUFFERS = (0.5, 1.5)
FINANCE = (("tight", 0.15, 0.6), ("loose", 1.2, 2.0))
ROUTES = (("direct", "base", "direct"),
          ("two_hop", "base", "two_hop"),
          ("unrestricted_payment_placebo", "zero_frictions", "direct"))
NUMERIC_ARMS = ("inherited", "reconstructed_00", "reconstructed_31")

def require(ok: bool, why: str):
    if not bool(ok):
        raise AssertionError(why)

def write_rows(path: Path, rows: list[dict]):
    require(bool(rows), "Cannot serialize empty evidence")
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def preflight(A: np.ndarray, P: np.ndarray, x: np.ndarray,
              payment_capacity: float, mode: str, hops: str) -> dict:
    """Pure read-only necessary input-support/capacity bounds.

    These are NECESSARY, not sufficient, conditions for steady-state finance.
    They do not assume payment-network weights are the physical IO matrix.
    """
    positive = A > 0
    required = A * x[np.newaxis, :]
    directly_allowed = P > 0
    if mode == "zero_frictions":
        allowed = np.ones_like(positive, dtype=bool)
    elif hops == "two_hop":
        allowed = directly_allowed | (
            (directly_allowed.astype(np.int32) @
             directly_allowed.astype(np.int32)) > 0)
    else:
        allowed = directly_allowed.copy()
    missing = positive & ~allowed
    # The engine applies proportional per-buyer payment-edge throughput only
    # to DIRECT P-positive links, not to two-hop fallback transfers.
    colsum = np.maximum(np.sum(P, axis=0), 1e-12)
    direct_cap = payment_capacity * x[np.newaxis, :] * (P / colsum)
    cap = np.full_like(A, np.inf) if mode == "zero_frictions" else direct_cap.copy()
    if mode != "zero_frictions" and hops == "two_hop":
        cap[allowed & ~directly_allowed] = np.inf
    cap[missing] = 0.
    bounded = positive & directly_allowed & (mode != "zero_frictions")
    cap_short = np.maximum(required - cap, 0.0)
    cap_short[~positive] = 0.
    bottleneck_buyer = np.zeros(len(x), dtype=bool)
    no_route_buyer = np.any(missing, axis=0)
    strict_short = positive & (cap + 1e-12 < required)
    bottleneck_buyer |= np.any(strict_short, axis=0)
    weak = np.divide(cap, required, out=np.full_like(A, np.inf),
                     where=positive)
    weak[~positive] = np.inf
    critical = []
    for j in range(len(x)):
        ids = np.flatnonzero(positive[:, j])
        if len(ids) == 0:
            continue
        i = int(ids[np.argmin(weak[ids, j])])
        if not np.isfinite(weak[i, j]) or weak[i, j] >= 1.0:
            continue
        critical.append({
            "buyer":j, "seller":i, "technical_coefficient":float(A[i, j]),
            "baseline_required_units":float(required[i, j]),
            "has_financial_payment_route":int(allowed[i, j]),
            "direct_link_present":int(directly_allowed[i, j]),
            "max_payment_units":float(cap[i, j]),
            "capacity_to_required_ratio":float(weak[i, j])
        })
    return {
        "technology_positive_input_edges":int(np.sum(positive)),
        "financial_route_missing_technology_edges":int(np.sum(missing)),
        "financial_route_missing_technology_mass":float(np.sum(A[missing])),
        "technology_mass_fraction_route_eligible":
            float(np.sum(A[positive & allowed]) / np.sum(A[positive])),
        "buyer_sectors_with_missing_required_route":int(np.sum(no_route_buyer)),
        "buyer_sectors_with_any_exante_undersupplied_required_input":
            int(np.sum(bottleneck_buyer)),
        "direct_edges_throttled_below_one_period_requirement":
            int(np.sum(bounded & strict_short)),
        "positive_required_mass_failing_monthly_payment_capacity":
            float(np.sum(cap_short)),
        "total_positive_baseline_monthly_required_units":
            float(np.sum(required[positive])),
        "exante_critical_buyer_supplier_examples":
            sorted(critical,
                   key=lambda d:(d["capacity_to_required_ratio"], d["buyer"]))[:12]
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path,
        default=Path("outputs/n6_coupling_compatibility"))
    out = parser.parse_args().out_dir
    out.mkdir(parents=True, exist_ok=True)
    mp, tp, rp = (DATA / p for p in ("m001.json", "t001.json", "r001.json"))
    m = json.loads(mp.read_text())
    t = json.loads(tp.read_text())
    r = json.loads(rp.read_text())
    A = np.array(m["M001"], dtype=float)
    A0 = A.copy()
    x, final_demand = equilibrium(A)
    anchors = m["V001"]
    targets = r["V001"]
    require(A.shape == (104,104), "Wrong physical technology shape")
    require(len(anchors)==8 and len(targets)==8 and
            all(len(z)==10 for z in anchors) and
            all(len(z)==3 for z in targets), "Original public anchor/ref shape mismatch")
    require(len(r["years"])==29 and r["years"][0]==1995 and
            r["years"][-1]==2023, "Original historical series window changed")
    bands = np.array([v["T"] for v in t["M201"]], dtype=float)
    require(bands.shape==(6,3), "Original Q2 target bands changed")
    net = {"inherited":baseline6(A,m["I001"])}
    for idx in (0,31):
        P,D,_,_ = simple10(A,m["V002"][idx])
        moments = np.asarray(metrics(P), dtype=float)
        require(np.all(moments>=bands[:,1]) and
                np.all(moments<=bands[:,2]), "Original network Q2 band failed")
        require(np.allclose(D.sum(axis=0),A.sum(axis=0),atol=1e-10),
                "Frozen technology column conservation failed")
        net[f"reconstructed_{idx:02d}"] = P
    require(tuple(net)==NUMERIC_ARMS, "Unregistered network arm")

    signature = inspect.signature(run)
    # No inference from merely owning numeric 8x10 vectors: this NEW engine
    # must explicitly consume them and reproduce old Test3 state transitions.
    has_anchor_bridge = any(k in signature.parameters for k in
                             ("economic_anchor", "anchor_parameters"))
    frozen = []
    for idx, (v, reference) in enumerate(zip(anchors, targets)):
        vbytes = json.dumps(v, separators=(",", ":")).encode()
        frozen.append({
           "anchor":"A%02d"%idx,
           "parameters_sha256":hashlib.sha256(vbytes).hexdigest(),
           "parameter_count":len(v),
           "reference_moment_count":len(reference),
           "old_test3_certification_preserved":1,
           "new_coupling_receives_anchor_vector":int(has_anchor_bridge),
           "new_coupling_state_equivalence_certified":0,
           "new_coupling_historical_period_match_certified":0
        })
    require(len({z["parameters_sha256"] for z in frozen})==8,
            "Frozen original anchors were modified or duplicated")
    write_rows(out/"eight_existing_anchor_compatibility_registry.csv", frozen)

    static = []
    cases = []
    paths = []
    max_residual = 0.
    pair_placebos = 0
    for buffer in BUFFERS:
      for label,credit,capacity in FINANCE:
        for route,mode,hops in ROUTES:
          for arm,P in net.items():
            profile = preflight(A,P,x,capacity,mode,hops)
            static.append({
              "inventory_initial_months":buffer,
              "finance":label,"route":route,"arm":arm,
              **{k:v for k,v in profile.items()
                 if k!="exante_critical_buyer_supplier_examples"}
            })
            for seed in SEEDS:
              settings=dict(seed=seed,periods=18,shock_start=1000,
                  shock_length=0,shock_severity=0.,shock_source=49,
                  mode=mode,hop_policy=hops,
                  inventory_months=buffer,credit_fraction=credit,
                  payment_capacity_scale=capacity,
                  order_policy="forward_input_coverage",
                  shock_channel="delivery",full_ledger=True,
                  trace_mechanism=True)
              sim=run(A,P,**settings)
              history=sim["path"]
              ledger=sim["ledger"]
              max_residual=max(max_residual,max(max(
                  float(pt[k]) for k in ("R001","R002","R003"))
                  for pt in history))
              output_fractions=[pt["Y001"]/float(np.sum(x)) for pt in history]
              last=float(np.mean(output_fractions[-6:]))
              traces=[l["N6_TRACE"] for l in ledger]
              cases.append({
                 "inventory_initial_months":buffer,
                 "finance":label,"route":route,"arm":arm,"seed":seed,
                 "mean_late_output_fraction":last,
                 "mean_initial_output_fraction":float(np.mean(output_fractions[:3])),
                 "last_near_zero_sector_count":int(
                      np.sum(np.array(ledger[-1]["Q"])<1e-10)),
                 "total_settled_units":float(sum(t["settled_deliveries"] for t in traces)),
                 "total_ordered_units":float(sum(t["ordered"] for t in traces)),
                 "total_route_denied_units":float(sum(t["route_denied"] for t in traces)),
                 "total_capacity_shortfall_units":float(
                      sum(t["payment_edge_capacity_shortfall"] for t in traces)),
                 "total_supplier_shortfall_units":float(
                      sum(t["seller_goods_shortfall"] for t in traces)),
                 "total_input_limited_gap":float(
                      sum(t["input_limited_production_gap"] for t in traces)),
                 "illustrative_90_percent_reference_output_pass":
                     int(last >= 0.9),
                 "source_model_equivalence_certified":0
              })
              paths.extend([{
                  "inventory_initial_months":buffer,
                  "finance":label,"route":route,"arm":arm,"seed":seed,
                  "month":pt["M"],"output_fraction":output_fractions[i],
                  "sector_count_near_zero":int(
                      np.sum(np.array(ledger[i]["Q"])<1e-10)),
                  "settled":traces[i]["settled_deliveries"],
                  "ordered":traces[i]["ordered"],
                  "input_limited_gap":traces[i]["input_limited_production_gap"]
              } for i,pt in enumerate(history)])
          if mode == "zero_frictions":
            # Identical financial-free output for the same reference A, stocks
            # and seed must not depend on payment topology.
            for seed in SEEDS:
              selected=[p for p in cases if
                  p["inventory_initial_months"]==buffer and
                  p["finance"]==label and p["route"]==route and
                  p["seed"]==seed]
              require(len(selected)==3,
                      "Missing zero financial friction comparison arms")
              near=[z["mean_late_output_fraction"] for z in selected]
              require(max(near)-min(near)<1e-12,
                      "Network structure changes frictionless production")
              pair_placebos+=1
    require(len(static)==36 and len(cases)==72 and len(paths)==1296,
            "Incomplete coupling-compatibility test matrix")
    require(np.array_equal(A,A0),"Original physical technology was modified")
    require(max_residual<1e-9, "Material/monetary conservation failed")
    write_rows(out/"financial_route_technical_compatibility_36.csv",static)
    write_rows(out/"all_72_no_shock_compatibility_cases.csv",cases)
    write_rows(out/"all_1296_monthly_compatibility_paths.csv",paths)

    by_route={}
    for name,_,_ in ROUTES:
        subset=[row for row in cases if row["route"]==name]
        by_route[name]={
          "cases":len(subset),
          "output_fraction_late_mean":float(np.mean([
              row["mean_late_output_fraction"] for row in subset])),
          "output_fraction_late_min":float(min(
              row["mean_late_output_fraction"] for row in subset)),
          "output_fraction_late_max":float(max(
              row["mean_late_output_fraction"] for row in subset)),
          "engineering_reference_90pct_cases":int(sum(
              row["illustrative_90_percent_reference_output_pass"]
              for row in subset))
        }
    broken=[row for row in cases if
             row["mean_late_output_fraction"]<0.9]
    bank_or_cash=[row for row in cases if
                  row["total_capacity_shortfall_units"]>1e-10]
    summary={
      "schema":"n6_new_coupling_vs_old_test3_compatibility_preflight_v1",
      "old_test3_validation_preserved":True,
      "old_test3_recognition":"Already validated, no old model calibration run",
      "only_new_coupling_is_under_test":True,
      "8_original_frozen_anchors_present":len(frozen),
      "new_coupling_explicit_legacy_anchor_adapter_detected":has_anchor_bridge,
      "8_anchor_legacy_transition_compatibility_confirmed":False,
      "genuine_original_moments_simulated_in_this_public_run":0,
      "original_1995_2023_year_reference_unchanged":True,
      "original_104sector_technological_A_unchanged":True,
      "original_Q2_six_acceptance_bands_unchanged":True,
      "original_Q4_historical_failures_changed":False,
      "no_shock_public_engineering_cases":len(cases),
      "monthly_output_paths":len(paths),
      "route_static_cases":len(static),
      "no_frictions_placebo_pairs_checked":pair_placebos,
      "max_goods_inputs_money_residual":max_residual,
      "capacity_limited_dynamic_cases":len(bank_or_cash),
      "engineering_reference_output_below_90pct_cases":len(broken),
      "by_route":by_route,
      "new_coupling_compatible_with_old_test3":False,
      "scientific_certification_succeeded":False,
      "authorization_for_economic_ml_search":False,
      "next_development_action":
        "First implement a source-faithful Test3-to-new-ledger adapter, and a financially feasible no-shock input settlement baseline; do NOT tune Q2 bands or old original calibration.",
      "evidence_input_sha256":{p.name:sha(p) for p in (mp,tp,rp)},
      "note":"No-shock 90% output is an engineering diagnostic, NOT a new scientific calibration target or an old Test3 acceptance rule."
    }
    (out/"status.json").write_text(
        json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print(json.dumps(summary,indent=2))
if __name__=="__main__":
    main()
