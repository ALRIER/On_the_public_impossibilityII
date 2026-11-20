"""Export exact bytes of two N6 public releases plus verified reader-friendly diagnostics.

This PUBLIC action does not access or trigger the private repo. All scientific
numbers are read from immutable GitHub Releases and source SHA256 is checked.
"""
from __future__ import annotations
import base64,csv,hashlib,io,json,subprocess,tarfile
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"staging/n6_20261120"
REPO="ALRIER/On_the_public_impossibilityII"
TAGS=("n6-public-mechanism-trace-44809258583-a1",
      "n6-public-viability-44809509073-a1")
SOURCE_FILES=(
    "runtime/tasks/n5_clearing_engine.py",
    "runtime/tasks/n6_transmission_diagnostic.py",
    "runtime/tasks/n6_viability_falsification.py",
    ".github/workflows/n6-transmission-gate.yml",
    ".github/workflows/n6-viability-falsification.yml",
)
def sh(*args):return subprocess.check_output(args,text=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    files=[]; releases=[]
    for tag in TAGS:
        directory=OUT/"source"/tag
        directory.mkdir(parents=True,exist_ok=True)
        meta=json.loads(sh("gh","api",f"repos/{REPO}/releases/tags/{tag}"))
        sh("gh","release","download",tag,"--repo",REPO,"--dir",str(directory))
        assets=[]
        for item in sorted(meta["assets"],key=lambda x:x["name"]):
            p=directory/item["name"];b=p.read_bytes()
            assert len(b)==item["size"] and "sha256:"+sha(b)==item["digest"],tag+"/"+p.name
            assets.append({"name":p.name,"size":len(b),"sha256":sha(b)})
            files.append((p,"original_release_assets/"+tag+"/"+p.name))
        releases.append({"tag":tag,"assets":assets})
    snapshots={}
    for name in SOURCE_FILES:
        p=ROOT/name
        snapshots[name]=sha(p.read_bytes())
        files.append((p,"public_source_snapshot/"+name))
    archive=OUT/"n6_two_original_public_releases.tar.gz"
    with tarfile.open(archive,"w:gz") as a:
        for p,name in files:a.add(p,arcname=name,recursive=False)
    data=archive.read_bytes()
    manifest={
       "schema":"n6_exact_original_public_source_archives_v1",
       "original_repository":REPO,"releases":releases,
       "source_snapshots":snapshots,
       "archive_filename":archive.name,
       "archive_bytes":len(data),"archive_sha256":sha(data),
       "source_commit":sh("git","rev-parse","HEAD").strip(),
       "no_private_GitHub_actions_invoked":True
    }
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (OUT/"archive_bytes.b64").write_text(base64.b64encode(data).decode()+"\n")
    # Build and verify a human and machine readable summary from ORIGINAL assets,
    # without repeating experimental runs.
    first=OUT/"source"/TAGS[0]/"n6_mechanism_trace.tar.gz"
    second=OUT/"source"/TAGS[1]/"n6_viability_falsification.tar.gz"
    with tarfile.open(first,"r:gz") as t:
        f=t.extractfile("./n6_mechanism_trace/n6_stage1_status.json")
        first_status=json.loads(f.read())
    with tarfile.open(second,"r:gz") as t:
        status=json.loads(t.extractfile("./n6_viability_falsification/status.json").read())
        rows=list(csv.DictReader(io.TextIOWrapper(
            t.extractfile("./n6_viability_falsification/viability_all_36_scenarios.csv"),
            encoding="utf-8")))
    assert len(rows)==36
    grouped=defaultdict(list)
    for r in rows:grouped[(r["inventory"],r["route_policy"])].append(r)
    table=[]
    for inv in ("0.5","1.5"):
        for policy in ("direct","two_hop","zero_frictions"):
            rr=grouped[(inv,policy)]
            assert len(rr)==6,(inv,policy,len(rr))
            table.append({
              "inventory_months":float(inv),"routing":policy,
              "late_output_ratio_mean":sum(float(x["last_6_month_mean_output_ratio"]) for x in rr)/6,
              "final_near_zero_sector_count_mean":sum(float(x["final_month_near_zero_sector_count"]) for x in rr)/6,
              "eligible_technology_mass_mean":sum(float(x["financially_eligible_fraction_input_mass"]) for x in rr)/6
            })
    lines=[
       "# N6 first-stage trace and viable baseline: verified-public-evidence report",
       "",
       "**Status:** completed public engineering diagnostics, original 8 × 10 economic anchors not mapped; none of five N6 reviewer questions closed.",
       "",
       f"- [Original trace release](https://github.com/{REPO}/releases/tag/{TAGS[0]})",
       f"- [Original no-shock viability release](https://github.com/{REPO}/releases/tag/{TAGS[1]})",
       "- The original Release files are byte-for-byte preserved in the N6 private canonical archive.",
       "",
       "## Mechanism trace",
       "",
       f"- {first_status['original_full_ledger_trajectories']} trajectories, {first_status['original_monthly_trace_rows']} period ledgers, {first_status['matched_network_shock_contrasts']} matched inherited/reconstructed shock contrasts.",
       f"- Conservation maximum residual {first_status['maximum_goods_and_money_conservation_residual']:.3e}; opt-in trace unchanged legacy outcomes and no-friction placebo passed.",
       f"- Nonzero value-added shock DID contrasts: {first_status['value_added_shock_DID']['nonzero']}/{first_status['value_added_shock_DID']['n']}; nonzero consumption shock DID: {first_status['consumption_shock_DID']['nonzero']}/{first_status['consumption_shock_DID']['n']} (negative {first_status['consumption_shock_DID']['negative']}).",
       "- Source-level shortages and input-limited production dominate many tested states. Cash shortfall is zero, but payment edge capacity limits some transactions; the decomposition exactly reconciles total unfulfilled orders.",
       "",
       "## No-shock structural versus physical viability experiment",
       "",
       "Same original 104-sector technology, unchanged six Q2 bands; two inventory initializations, two financial parameter settings and three route modes, original inherited and two reconstructed networks. Measurements are model ratios relative to the reference equilibrium plan, NOT historical calibration.",
       "",
       "| Initial inventory (months) | Route | Late actual/planned output | Final near-zero sectors /104 | Eligible technological-input mass |",
       "|---|---|---:|---:|---:|"
    ]
    for r in table:
        lines.append(f"| {r['inventory_months']:.1f} | {r['routing']} | {100*r['late_output_ratio_mean']:.2f}% | {r['final_near_zero_sector_count_mean']:.1f} | {100*r['eligible_technology_mass_mean']:.4f}% |")
    lines.extend([
       "",
       "## Source-preserving N6 engineering decision",
       "",
       "1. **Stage N6-1 bottleneck diagnosed, not reviewer-closed:** baseline physical availability and financial settlement interaction creates a discontinuous production-viability region. High eligible financial link mass alone is insufficient when every positive technological input enters a Leontief minimum. Avoid inferring that adding links alone improves the economy.",
       "2. **Next actual code change:** implement a versioned *baseline steady-state reachability preflight* with original ledger, checking that zero-shock planned output, input stocks, settled production, wages and household purchases survive the burn-in under the original calibrated 8×10 anchor settings. Distinguish monthly input purchase timing from inventory safety buffers, without changing historical A or assuming low-mass inputs can be omitted. Reject nonviable baseline regimes; DO NOT select hyperparameters to maximize apparent effects.",
       "3. **N6-2 remains essential:** faithfully carry each original economic control to its original household/firms/labor/expectations equations, and independently verify all eight frozen anchors. Engineer material procurement and payment routing jointly with explicit legal credit and budget identities.",
       "4. Only after parity and baseline viability, predeclare critical supplier/edge ablation (N6-3), six-band constrained multiobjective redesign (N6-4), and fresh-seed macro/historical/Q4 independent confirmation (N6-5).",
       "5. **Scientific scope:** baseline positive control and a recoverable zero-friction high-inventory regime establish conditional engineering viability, not economic superiority of any reconstructed topology; do not change Q4 original failures.",
       "",
       "## Test 3 and parent-program transfer receipt",
       "",
       f"- Public run identities: 44809258583 and 44809509073; original Release tags: `{TAGS[0]}`, `{TAGS[1]}`.",
       f"- Exact public original-release archive SHA256: `{manifest['archive_sha256']}`, original archive {manifest['archive_bytes']} bytes.",
       "- SHA256 of each original asset and each public analysis code snapshot appears in the accompanying manifest. This is the reproducible chain for subsequent Test 3 tables, future manuscript updates, and later parent-study import.",
       ""
    ])
    (OUT/"N6_VERIFIED_BOTTLENECK_REPORT.md").write_text("\n".join(lines))
    (OUT/"N6_VERIFIED_EVIDENCE_SUMMARY.json").write_text(json.dumps({
       "schema":"n6_verified_readonly_source_report_v1",
       "run_ids":[44809258583,44809509073],
       "original_public_release_archive_sha256":manifest["archive_sha256"],
       "viability_by_inventory_and_route":table,
       "n6_first_trace":first_status,
       "n6_viability":status,
       "scientific_8_anchor_model_certified":False,
       "reviewer_n6_R1_through_R5_closed":False
    },indent=2)+"\n")
    print(json.dumps({"exact_archived_original_asset_count":sum(len(x["assets"]) for x in releases),
        "archive_bytes":len(data),"sha256":sha(data),
        "route_buffer_table":table},indent=2))
if __name__=="__main__":main()
