#!/usr/bin/env python3
"""N5 Stage 1: public-only prerequisite diagnostic, NOT model certification.

No private checkout, no semantic anchors, no search/optimization, no claim
that a synthetic engineering fixture calibrates the frozen economic model.
"""
from __future__ import annotations
import ast
import csv
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np

from runtime.tasks.n5_clearing_engine import equilibrium, run

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "n5_stage1_mechanism_gate"


def require(test, description):
    if not bool(test):
        raise AssertionError(description)


def totals(result):
    p = result["path"]
    return {
        "production": float(sum(x["Y001"] for x in p)),
        "real_value_added": float(sum(x["Y002"] for x in p)),
        "consumption": float(sum(x["Y004"] for x in p)),
        "arrears": float(sum(x["Y006"] for x in p)),
        "intermediate_shipments": float(sum(x["Y009"] for x in p)),
        "payment_hhi": float(np.mean([x["Y005"] for x in p])),
        "max_goods_residual": max(abs(x["R001"]) for x in p),
        "max_inputs_residual": max(abs(x["R002"]) for x in p),
        "max_money_residual": max(abs(x["R003"]) for x in p),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # This is an adversarial synthetic engine-level fixture, not a frozen anchor.
    A = np.array([[.15, .07, .12], [.08, .19, .06], [.11, .03, .16]])
    P_full = np.ones((3, 3))
    P_cut = P_full.copy()
    P_cut[0, 1] = 0.
    x, f = equilibrium(A)
    require(np.allclose(x, A @ x + f), "Technology baseline invalid")
    common = dict(seed=4811, periods=36, shock_start=7,
                  shock_length=9, shock_source=0, shock_severity=.65,
                  inventory_months=.25, credit_fraction=.0,
                  payment_capacity_scale=.25)
    cases = {
        "full_shock": run(A, P_full, **common),
        "cut_shock": run(A, P_cut, **common),
        "full_no_shock": run(A, P_full, **{**common, "shock_severity":0.}),
        "cut_no_shock": run(A, P_cut, **{**common, "shock_severity":0.}),
        "full_zero_friction": run(A, P_full, **common, mode="zero_frictions"),
        "cut_zero_friction": run(A, P_cut, **common, mode="zero_frictions"),
    }
    require(cases["full_zero_friction"]["path"] ==
            cases["cut_zero_friction"]["path"],
            "No-friction topology placebo failed")
    duplicate = run(A, P_full, **common)
    require(duplicate == cases["full_shock"],
            "Deterministic same-seed replay failed")
    rows = []
    for name, result in cases.items():
        measures = totals(result)
        require(max(measures[k] for k in
                    ("max_goods_residual", "max_inputs_residual",
                     "max_money_residual")) < 1e-9,
                "Stock-flow conservation failed in "+name)
        rows.append({"arm":name, **measures})
    byname = {x["arm"]:x for x in rows}
    metrics = ("production", "real_value_added", "consumption")
    effects = {
        k:(byname["cut_shock"][k]-byname["cut_no_shock"][k]) -
           (byname["full_shock"][k]-byname["full_no_shock"][k])
        for k in metrics
    }
    # A synthetic fixture must be capable of producing a real-sector response
    # before any ML model is trained to predict network economic advantages.
    economic_signal = any(abs(v) > 1e-10 for v in effects.values())
    # The frozen 10-dimensional economic anchors need an independently
    # certified mapping into the public engine. Inspect the live signature,
    # never infer a mapping from coordinate positions.
    signature = inspect.signature(run)
    explicit_anchor = any(
        p in signature.parameters
        for p in ("economic_anchor", "anchor_parameters", "anchor_index"))
    source_sha = hashlib.sha256(
        (ROOT/"runtime/tasks/n5_clearing_engine.py").read_bytes()).hexdigest()
    with (OUT/"synthetic_case_metrics.csv").open("w",newline="") as handle:
        writer = csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    result = {
      "schema":"n5_stage1_public_mechanism_gate_v1",
      "source_engine_sha256":source_sha,
      "fixture":"synthetic_3_sector_adversarial_not_original_economic_anchors",
      "same_seed_replay_identical":True,
      "financial_zero_friction_placebo_identical":True,
      "all_periodic_accounting_residuals_lt_1e_minus_9":True,
      "synthetic_did_effects":effects,
      "synthetic_real_sector_signal_detected":economic_signal,
      "engine_accepts_explicit_anchor_argument":explicit_anchor,
      "original_eight_anchor_adapter_independently_certified":False,
      "original_8x32_economic_calibration_certified":False,
      "original_historical_period_match_certified":False,
      "fresh_seeds_confirmatory_economics_performed":False,
      "scientific_stage1_certified":False,
      "authorization_for_large_N5_experiments":False,
      "next_gate":"private_parameter_semantic_mapping_and_public_anchor_adapter_parity",
      "methodological_warning":
        "Synthetic structural response tests do not certify economic anchoring or Q1 causality.",
    }
    (OUT/"stage1_status.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    assert not result["scientific_stage1_certified"]
    assert not result["authorization_for_large_N5_experiments"]


if __name__=="__main__":
    main()
