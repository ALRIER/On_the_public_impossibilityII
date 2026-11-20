"""N5 Q1/Q3 frozen-anchor linkage audit: no scientific experiment is executed.

Reads only existing neutral, public numerical inputs. A green audit attests that
gates are measured and blockers disclosed, not that scientific gates pass.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import inspect
import json
import math
from pathlib import Path

from runtime.tasks.n5_clearing_engine import run

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "public_bundle" / "n5_v1"


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_number(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def write_csv(path: Path, rows: list[dict]) -> None:
    require(bool(rows), "Cannot write empty audit")
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/n5_anchor_gate"))
    args = parser.parse_args()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    m = json.loads((SOURCE / "m001.json").read_text(encoding="utf-8"))
    r = json.loads((SOURCE / "r001.json").read_text(encoding="utf-8"))
    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    plan_path = Path("outputs/n5_plan/o602.json")
    require(plan_path.exists(), "Missing independently generated future-stage design")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    require(m["revision"] == r["revision"] == manifest["bundle_revision"] == "n5-r1",
            "Frozen source revisions differ")
    dims = m["dims"]
    require(dims == {"n": 104, "k": 10, "structures": 32, "anchors": 8},
            "Frozen N5 dimensions changed")
    require(len(m["M001"]) == 104 and all(len(row) == 104 for row in m["M001"]),
            "Original technology array changed dimensions")
    require(all(frozen_number(x) and x >= 0 for row in m["M001"] for x in row),
            "Physical input array has invalid coefficients")
    require(len(m["V001"]) == len(r["V001"]) == 8, "Expected eight frozen anchor entries")
    require(len(m["V002"]) == 32 and all(len(v) == 10 for v in m["V002"]),
            "Original network configuration registry changed")
    require(len(r["U001"]) == 148 and r["r0_n"] == 146 and len(r["U002"]) == 36,
            "Independent reference universe counts changed")
    years = r["years"]
    require(years == list(range(1995, 2024)), "Archived reference years changed")
    require(plan["screen_design"]["trajectories"] == 8192 and
            plan["confirm_design"]["trajectories"] == 18432 and
            plan["seed_family_overlap"] == 0 and
            not plan["scientific_experiment_ready"],
            "Historical prelaunch design or preregistered safety guard changed")

    rows: list[dict] = []
    parameter_hashes: list[str] = []
    for index, (parameter_vector, target_vector) in enumerate(zip(m["V001"], r["V001"])):
        require(len(parameter_vector) == 10 and len(target_vector) == 3,
                "Missing original anchor or macro-reference dimensions")
        require(all(frozen_number(x) for x in parameter_vector + target_vector),
                "Original anchor contains a nonfinite value")
        parameter_digest = hashlib.sha256(
            json.dumps(parameter_vector, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        parameter_hashes.append(parameter_digest)
        rows.append({
            "ANCHOR": f"A{index:02d}",
            "FROZEN_PARAMETER_VECTOR_SHA256": parameter_digest,
            "FROZEN_PARAMETER_COUNT": len(parameter_vector),
            "REFERENCE_1": float(target_vector[0]),
            "REFERENCE_2": float(target_vector[1]),
            "REFERENCE_3": float(target_vector[2]),
            "ENGINE_ANCHOR_MAPPING_CERTIFIED": 0,
            "PERIOD_MATCHED_MODEL_OUTPUT_CERTIFIED": 0,
        })
    require(len(set(parameter_hashes)) == 8, "Original eight independent anchors collapsed")
    write_csv(out / "anchor_reference_inventory.csv", rows)

    # A certified adapter must be a separately validated bridge from each
    # ten-component frozen anchor to the coupled engine. No position-wise
    # mapping is invented: these inputs are not interchangeable.
    engine_parameters = list(inspect.signature(run).parameters)
    has_explicit_anchor_argument = any(
        x in engine_parameters for x in ("economic_anchor", "anchor_parameters", "anchor_index")
    )
    certified_anchor_bridge = False
    temporal_model_validation = False
    fourth_network_arm_implemented = False
    significance_and_power_frozen = False
    fresh_independent_confirmation = False

    gates = [
        ("neutral_bundle_frozen", "PASS", "8 x 10 input vectors, 32 structures, source revision and reference panels checked"),
        ("public_preflight_independent", "PASS", "Executed separately in this workflow before this audit"),
        ("accounting_falsification_tests", "PASS", "Executed separately in this workflow before this audit"),
        ("anchor_to_engine_scientific_bridge", "BLOCKED", "No independently certified translation of original anchor parameters to coupled engine"),
        ("three_reference_moments_calibration", "BLOCKED", "Original eight macro reference targets exist but new coupled engine is not calibrated"),
        ("period_matched_model_series", "BLOCKED", "29 archived annual observations exist; model output has no corresponding independently validated series"),
        ("four_arm_economic_runner", "BLOCKED", "Only three distinct network arms were used by the engineering pilot"),
        ("equivalence_power_and_runtime_signoff", "BLOCKED", "Pre-registered effect bands, pilot runtime and resource budget not frozen"),
        ("fresh_confirmatory_execution", "BLOCKED", "Independent confirmatory trajectories must not start at this stage"),
    ]
    write_csv(out / "gate_matrix.csv", [
        {"GATE": gate, "STATUS": status, "EVIDENCE": evidence}
        for gate, status, evidence in gates
    ])

    target_spread = {}
    for j in range(3):
        values = [float(row[j]) for row in r["V001"]]
        target_spread[f"REFERENCE_{j + 1}"] = {
            "minimum": min(values), "maximum": max(values),
            "unique_values": len(set(values)),
        }
    status = {
        "schema": "n5_anchor_mapping_audit_v1",
        "phase": "source_linkage_and_macro_calibration_readiness",
        "source_only_public": True,
        "scientific_simulation_count": 0,
        "original_anchors": 8,
        "economic_dimensions_per_anchor": 10,
        "network_structure_count": 32,
        "reference_annual_periods": len(years),
        "reference_first_year": years[0],
        "reference_last_year": years[-1],
        "original_fresh_reference_economies": 146,
        "separate_independent_provider_economies": 36,
        "target_spread": target_spread,
        "existing_coupled_run_argument_names": engine_parameters,
        "existing_coupled_run_has_explicit_anchor_argument": has_explicit_anchor_argument,
        "eight_anchor_bridge_independently_certified": certified_anchor_bridge,
        "macro_reference_calibration_certified": False,
        "period_matched_model_time_series_certified": temporal_model_validation,
        "four_arm_economic_runner_certified": fourth_network_arm_implemented,
        "effect_equivalence_and_power_frozen": significance_and_power_frozen,
        "fresh_confirmation_completed": fresh_independent_confirmation,
        "proposed_screen_trajectories": 8192,
        "proposed_confirm_trajectories": 18432,
        "full_scientific_execution_allowed": False,
        "n5_scientifically_complete": False,
        "next_required_stage": "certify_legacy_economic_anchor_adapter_and_period_aware_macro_calibration_before_full_screen",
        "neutral_source_sha256": {
            name: sha256(SOURCE / name)
            for name in ("m001.json", "r001.json", "t001.json", "manifest.json")
        },
        "design_receipt_sha256": sha256(plan_path),
        "gate_matrix": {row[0]: row[1] for row in gates},
    }
    require(sum(v == "BLOCKED" for v in status["gate_matrix"].values()) == 6,
            "The audit cannot silently promote missing scientific certification")
    require(not status["full_scientific_execution_allowed"] and
            not status["n5_scientifically_complete"], "False N5 scientific closure claim")
    (out / "anchor_gate_status.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "audit": "PASS", "anchors": 8,
        "passed_checkpoints": 3, "blocked_scientific_checkpoints": 6,
        "scientific_simulations": 0, "full_execution_allowed": False,
        "status_file": str(out / "anchor_gate_status.json")
    }, indent=2))


if __name__ == "__main__":
    main()
