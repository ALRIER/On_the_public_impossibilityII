"""Export exact original N6-2 public release evidence; source-derived audit.

Runs in PUBLIC GitHub Actions only. No private repo, token, Actions or
parameter semantics are touched.
"""
from __future__ import annotations
import base64,csv,hashlib,io,json,subprocess,tarfile
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"staging/n6_coupling_20261120"
REPO="ALRIER/On_the_public_impossibilityII"
TAG="n6-public-coupling-compatibility-44821050420-a1"
FILES=("runtime/tasks/n5_clearing_engine.py",
       "runtime/tasks/n6_coupling_compatibility_gate.py",
       ".github/workflows/n6-new-coupling-compatibility.yml")
def call(*a):return subprocess.check_output(a,text=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    d=OUT/"original_release_assets";d.mkdir(exist_ok=True)
    meta=json.loads(call("gh","api",f"repos/{REPO}/releases/tags/{TAG}"))
    call("gh","release","download",TAG,"--repo",REPO,"--dir",str(d))
    originals=[];paths=[]
    for x in sorted(meta["assets"],key=lambda a:a["name"]):
        p=d/x["name"];body=p.read_bytes()
        assert len(body)==x["size"]
        assert x["digest"]=="sha256:"+sha(body)
        originals.append({"name":p.name,"size":len(body),"sha256":sha(body)})
        paths.append((p,"original_assets/"+p.name))
    snapshots={}
    for name in FILES:
        f=ROOT/name;snapshots[name]=sha(f.read_bytes())
        paths.append((f,"public_source_snapshot/"+name))
    packed=OUT/"n6_original_coupling_compatibility_release.tar.gz"
    with tarfile.open(packed,"w:gz") as tf:
        for file,arcname in paths:tf.add(file,arcname=arcname,recursive=False)
    data=packed.read_bytes()
    manifest={
      "schema":"n6_original_coupling_compatibility_evidence_v1",
      "original_repository":REPO,"original_tag":TAG,
      "original_assets":originals,"source_snapshots":snapshots,
      "archive_file":packed.name,"archive_bytes":len(data),
      "archive_sha256":sha(data),
      "source_commit":call("git","rev-parse","HEAD").strip(),
      "no_private_actions_executed":True}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (OUT/"archive_bytes.b64").write_text(base64.b64encode(data).decode()+"\n")
    with tarfile.open(d/"n6_coupling_compatibility.tar.gz","r:gz") as tf:
        def read(n):return tf.extractfile("./n6_coupling_compatibility/"+n).read()
        summary=json.loads(read("status.json"))
        values=list(csv.DictReader(io.StringIO(
            read("financial_route_technical_compatibility_36.csv").decode())))
    assert len(values)==36
    representative=[r for r in values if
       r["inventory_initial_months"]=="0.5" and r["finance"]=="tight"]
    assert len(representative)==9
    rows=[]
    for r in representative:
      rows.append({
         "route":r["route"],"arm":r["arm"],
         "missing_technology_edges":int(r["financial_route_missing_technology_edges"]),
         "buyers_with_missing_route":int(r["buyer_sectors_with_missing_required_route"]),
         "buyers_with_undersupplied_input":int(r["buyer_sectors_with_any_exante_undersupplied_required_input"]),
         "direct_capacity_shortfall_edges":int(r["direct_edges_throttled_below_one_period_requirement"]),
         "eligible_technology_mass_fraction":float(r["technology_mass_fraction_route_eligible"])
      })
    report=[
       "# N6-2 new payment coupling compatibility — source-verified results",
       "",
       "**Scope:** only the new N5/N6 payment/material coupling. The already certified original Test 3 model has NOT been recertified or modified.",
       f"Public [N6-2 workflow](https://github.com/{REPO}/actions/runs/44821050420) and [immutable Release](https://github.com/{REPO}/releases/tag/{TAG}).",
       "",
       "## Tested baseline behavior",
       "",
       f"- {summary['no_shock_public_engineering_cases']} no-shock 104-sector trajectories, {summary['monthly_output_paths']} monthly records, {summary['route_static_cases']} static payment-technology compatibility checks; two seeds.",
       f"- Engineering-only reference ratio below 90% in **{summary['engineering_reference_output_below_90pct_cases']}/72** cases (90% is not a Test 3 scientific threshold).",
       f"- Financial edge-capacity shortfalls occurred in **{summary['capacity_limited_dynamic_cases']}/72** cases.",
       f"- Max physical/cash accounting residual: **{summary['max_goods_inputs_money_residual']:.3e}**; no-friction topology placebos: **{summary['no_frictions_placebo_pairs_checked']}**.",
       "- The original eight parameter vectors and corresponding macro targets remain intact, but the new public engine does not accept or implement these validated Test 3 state controls; **8/8 new coupling parity is not certified**.",
       "",
       "## Output by payment mode",
       "",
       "| Payment mode | No-shock cases | Late realized/planned output (mean) | Illustrative reference >= 90% |",
       "|---|---:|---:|---:|"]
    for k,v in summary["by_route"].items():
        report.append(f"| {k} | {v['cases']} | {v['output_fraction_late_mean']:.2%} | {v['engineering_reference_90pct_cases']}/{v['cases']} |")
    report.extend([
       "",
       "## Strict necessary supplier-payment support and throughput test",
       "",
       "For each positive technological input requirement, the current coupled kernel requires an eligible payment route, plus enough financed monthly settlement. With a hard non-substitutable Leontief minimum, even a very small unsupported input can stop a buyer sector. The following table is a **pre-shock necessary-condition audit**, not evidence that caps alone explain every dynamic outcome.",
       "",
       "| Mode | Frozen payment arm | Missing technological payment edges | Buyers missing an essential route | Buyers below ex ante input requirement | Direct capacity-short edges | Eligible technological mass |",
       "|---|---|---:|---:|---:|---:|---:|"]
    )
    for z in rows:
        report.append("| "+ " | ".join([
           z["route"],z["arm"],str(z["missing_technology_edges"]),
           str(z["buyers_with_missing_route"]),
           str(z["buyers_with_undersupplied_input"]),
           str(z["direct_capacity_shortfall_edges"]),
           f"{z['eligible_technology_mass_fraction']:.6%}"])+" |")
    report.extend([
       "",
       "## N6-2 compatibility decision and next code change",
       "",
       "**Public engineering diagnostics ran successfully. The new coupling FAILS the compatibility-readiness gate** because its no-shock economy collapses under direct/two-hop payment routing, and the eight authentic legacy economic anchors are not wired into the new state transitions. This does NOT revisit or invalidate the original Test3 economy.",
       "",
       "**Next implementation:** reuse the existing opt-in original Test3 `n4_coupling` integration seam for a source-faithful baseline. Keep original ten parameter/state equations intact. Introduce a *separate* bilateral purchase/settlement layer with bank routing, funded credit and explicit edge-capacity constraints, preserving full technological input requirements and goods/money identities. Test no-shock baseline before shock sensitivity; do not optimize any engineering knobs to manufacture beneficial shock differences. Repeat reference comparison across eight anchors, independently.",
       "",
       "Q2 original six bands, Q3 historical reference window and Q4 original failed targets remain untouched. No new economic benefit or reviewer closure certified.",
       "",
       f"Original source Release archive SHA256: `{manifest['archive_sha256']}`; archive {manifest['archive_bytes']} bytes, 4 original Release assets, 3 source/workflow snapshots.",
       ""
    ])
    (OUT/"N6_COUPLING_COMPATIBILITY_VERIFIED_REPORT.md").write_text("\n".join(report))
    (OUT/"N6_COUPLING_COMPATIBILITY_VERIFIED_SUMMARY.json").write_text(
        json.dumps({"schema":"n6_coupling_source_verified_report_v1",
            "source_tag":TAG,"original_release_archive_sha256":manifest["archive_sha256"],
            "status":summary,"predeclared_static_support_table":rows,
            "new_coupling_parity_certified":False},indent=2)+"\n")
    print(json.dumps({
        "original_asset_count":len(originals),
        "archive_sha256":manifest["archive_sha256"],
        "archive_bytes":manifest["archive_bytes"],
        "support_by_original_structure":rows,
        "late_output_by_route":summary["by_route"],
        "scientific_certification":False},indent=2))
if __name__=="__main__":main()
