"""Summarize immutable public N5 research release archives without rerunning.

Run from a public checkout with verified archives extracted to staging.
No private source, hidden targets, new simulation, or outcome selection.
"""
from __future__ import annotations
import csv,json
from pathlib import Path

STAGE=Path("staging_n5")
OUT=Path("reports/n5")
def load_csv(path):
    with path.open(newline="") as f:return list(csv.DictReader(f))
def fmt(v):
    return f"{float(v):+.8f}"
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    f=STAGE/"forward"/"n5_forward_coverage_pilot"
    d=STAGE/"delivery"/"n5_delivery_channel_pilot"
    forward=json.loads((f/"status.json").read_text())
    delivery=json.loads((d/"status.json").read_text())
    fw=load_csv(f/"topology_levels_and_paired_did.csv")
    dc=load_csv(d/"all_104_sector_paired_network_contrasts.csv")
    lines=[
      "# N5 controlled financial-shock mechanism diagnostic (Nov 20, 2026)",
      "",
      "These observations are from engineering-only coupled simulations with the frozen public 104-sector physical technology, **not** from eight certified legacy economic anchors.",
      "Sources: [forward-input-coverage release](https://github.com/ALRIER/On_the_public_impossibilityII/releases/tag/n5-public-forward-coverage-44758150356-a1) and [delivery-shock release](https://github.com/ALRIER/On_the_public_impossibilityII/releases/tag/n5-public-delivery-channel-44758591721-a1).",
      "All case rows, including null and adverse outcomes, remain in the original immutable release archives.",
      "",
      "## Original 104-sector economic differences: legacy capacity shock",
      "",
      "| Ordering rule | Shock output DID | Shock real-value-added DID | Shock consumption DID | Value-added level difference |",
      "|---|---:|---:|---:|---:|",
    ]
    for r in fw:
      if not r["context"].startswith("original"):continue
      lines.append("| "+r["order_policy"]+" | "+
          " | ".join(fmt(r["shock_did_"+x]) for x in ("output","value_added","consumption"))+
          " | "+fmt(r["level_value_added"])+" |")
    lines.extend(["","## Original 104-sector paired delivery-shock contrasts","",
        "All contrasts are reconstructed (or explicitly nonadmissible diagnostic) minus inherited. Positive/negative DID signs are not evidence of overall network superiority.",
        "",
        "| Design | Policy | Arm | Admissible original structure? | Output DID | Value added DID | Consumption DID | Value added shocked level difference |",
        "|---|---|---|---|---:|---:|---:|---:|"])
    for r in dc:
      admissible="No — diagnostic control" if int(r["diagnostic_nonadmissible"]) else "Yes — original"
      lines.append("| "+" | ".join([r["design"],r["policy"],r["arm"],admissible,
                fmt(r["shock_did_output"]),fmt(r["shock_did_va"]),
                fmt(r["shock_did_consumption"]),fmt(r["shock_level_va"])])+" |")
    lines.extend([
        "",
        "## Audit and limitations",
        "",
        f"- Synthetic forward-coverage positive-control nonzero shock contrast: **{forward['synthetic_positive_control_did_nonzero']}**.",
        f"- Original 104-sector delivery-shock contrasts with nonzero output/VA/consumption DID: **{delivery['original_structure_nonzero_shock_did_cases']} / {delivery['prospective_admissible_original_structure_contrasts']}**.",
        f"- Nonadmissible topology diagnostic nonzero contrasts: **{delivery['out_of_band_diagnostic_nonzero_shock_did_cases']}** (not candidates for Q2).",
        "- Frozen A unchanged; periodic stock, goods and monetary accounting residuals below 1e-9; zero-financial-friction placebo passed.",
        "- Sample sizes are small and deterministic; no independent seed-based economic intervals or external empirical calibration.",
        "- Both new options are opt-in. The historical order policy and capacity shock are still the defaults.",
        "- Ten legacy parameters and eight economic anchors have NOT been mapped and validated.",
        "- Q1–Q4 original decisions and targets remain unchanged, Q5 deferred, and full ML/ABM confirmation blocked.",
        "",
        "## Required scientific gate",
        "",
        "Verify the original legacy-model parameter-to-state transition mapping for all eight anchors; independently certify no-shock macro parity, calibration, shock timing and 1995–2023 period semantics; then preregister structurally admissible network comparisons with fresh seeds. This report is not evidence of journal-ready scientific closure.",
        ""
    ])
    (OUT/"N5_ENGINEERING_REPAIR_VERIFIED_2026-11-20.md").write_text("\n".join(lines))
    (OUT/"N5_ENGINEERING_REPAIR_SUMMARY_2026-11-20.json").write_text(json.dumps({
      "schema":"n5_public_engineering_repair_summary_v1",
      "verified_inputs":["44758150356","44758591721"],
      "source_release_tags":["n5-public-forward-coverage-44758150356-a1",
                             "n5-public-delivery-channel-44758591721-a1"],
      "original_structure_nonzero_delivery_did":
        delivery["original_structure_nonzero_shock_did_cases"],
      "original_structure_total_delivery_did":
        delivery["prospective_admissible_original_structure_contrasts"],
      "unmapped_original_economic_anchors":8,
      "full_scientific_certification":False
      },indent=2)+"\n")
    print("Published all original 104-sector comparisons, including null and unfavorable findings.")
if __name__=="__main__":main()
