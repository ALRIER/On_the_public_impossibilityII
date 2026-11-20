"""N6-1b: distinguish structural payment incompatibility from engine viability.

No-shock 104-sector reference counterfactuals: direct vs two-hop settlement vs
financially unconstrained routing, fixed original technological A and seeds.
This diagnostic does not certify frozen 8 economic anchors or grant Q1 closure.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from runtime.tasks.n5_clearing_engine import run,equilibrium
from runtime.tasks.n5_review_proofs import simple10,baseline6,metrics

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"public_bundle/n5_v1"
def check(ok,msg):
    if not bool(ok):raise AssertionError(msg)
def write(path,rows):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--out-dir",type=Path,default=Path("outputs/n6_viability_falsification"))
    args=pa.parse_args();out=args.out_dir;out.mkdir(parents=True,exist_ok=True)
    a=DATA/"m001.json";b=DATA/"t001.json"
    m=json.loads(a.read_text());t=json.loads(b.read_text())
    A=np.asarray(m["M001"],float);original=A.copy()
    check(A.shape==(104,104),"Original physical A has changed")
    x,f=equilibrium(A)
    bands=np.asarray([r["T"] for r in t["M201"]],float)
    check(bands.shape==(6,3),"Original six Q2 bands changed")
    arms={"inherited":baseline6(A,m["I001"])}
    for idx in (0,31):
      P,D,_,_=simple10(A,m["V002"][idx])
      vals=np.asarray(metrics(P))
      check(np.all(vals>=bands[:,1]) and np.all(vals<=bands[:,2]),
            "Original frozen Q2 admissibility changed")
      check(np.allclose(D.sum(axis=0),A.sum(axis=0),atol=1e-10),
            "Frozen physical direct requirements identity failed")
      arms[f"reconstructed_{idx:02d}"]=P
    configs=(("direct","base","direct"),
             ("two_hop","base","two_hop"),
             ("zero_frictions","zero_frictions","direct"))
    finances=(("tight",.15,.6),("loose",1.2,2.))
    inventory_levels=(.5,1.5)
    rows=[];pathrows=[];max_res=0.
    for buf in inventory_levels:
      for name,credit,pcap in finances:
        placebo_paths=[]
        for routed,mode,hop in configs:
          for arm,P in arms.items():
            kw=dict(seed=961120,periods=18,shock_start=999,shock_length=0,
               shock_source=49,shock_severity=0.,
               inventory_months=buf,credit_fraction=credit,
               payment_capacity_scale=pcap,order_policy="forward_input_coverage",
               shock_channel="delivery",hop_policy=hop,mode=mode,
               full_ledger=True,trace_mechanism=True)
            res=run(A,P,**kw)
            path=res["path"]; led=res["ledger"]
            max_res=max(max_res,max(max(abs(row[key]) for key in
                         ("R001","R002","R003")) for row in path))
            q=np.asarray([l["Q"] for l in led],float)
            ratios=np.sum(q,axis=1)/float(np.sum(x))
            all_pos=A>0
            direct=(P>0)
            reachable=direct | ((direct.astype(np.int32)@direct.astype(np.int32))>0)
            eligible=(np.ones_like(direct,dtype=bool) if mode=="zero_frictions"
                      else reachable if hop=="two_hop" else direct)
            totalmass=float(np.sum(A))
            coverage=float(np.sum(A[eligible])/totalmass)
            source_supported=float(np.sum(all_pos&eligible)/max(int(np.sum(all_pos)),1))
            tr=[l["N6_TRACE"] for l in led]
            def tally(k):return float(sum(v[k] for v in tr))
            result={"inventory":buf,"finance":name,"route_policy":routed,
               "arm":arm,"positive_A_links":int(np.sum(all_pos)),
               "directly_reachable_physical_links":int(np.sum(all_pos&direct)),
               "financially_eligible_fraction_physical_links":source_supported,
               "financially_eligible_fraction_input_mass":coverage,
               "initial_output_ratio":float(ratios[0]),
               "months_2_to_5_mean_output_ratio":float(np.mean(ratios[1:5])),
               "last_6_month_mean_output_ratio":float(np.mean(ratios[-6:])),
               "all_month_mean_output_ratio":float(np.mean(ratios)),
               "final_month_near_zero_sector_count":int(np.sum(q[-1,:]<1e-10)),
               "last_6_month_mean_near_zero_sectors":float(np.mean(np.sum(q[-6:,:]<1e-10,axis=1))),
               "input_limited_sector_months":int(tally("input_limited_sectors")),
               "input_limited_production_gap":tally("input_limited_production_gap"),
               "orders":tally("ordered"),
               "settled":tally("settled_deliveries"),
               "seller_goods_shortfall":tally("seller_goods_shortfall"),
               "route_denied":tally("route_denied"),
               "payment_capacity_shortfall":tally("payment_edge_capacity_shortfall"),
               "cash_shortfall":tally("cash_shortfall"),
               "credit_requested":tally("credit_requested"),
               "credit_granted":tally("credit_granted")}
            rows.append(result)
            pathrows.extend([{"inventory":buf,"finance":name,"route_policy":routed,
                         "arm":arm,"month":i,"output_ratio":float(ratios[i]),
                         "near_zero_sectors":int(np.sum(q[i,:]<1e-10)),
                         "input_limited_sectors":int(tr[i]["input_limited_sectors"]),
                         "settled":float(tr[i]["settled_deliveries"])}
                         for i in range(len(path))])
            if mode=="zero_frictions":
                placebo_paths.append(path)
        check(all(q==placebo_paths[0] for q in placebo_paths[1:]),
              "Financially zero-friction routing still depends on network topology")
    check(np.array_equal(A,original),"Frozen technology modified")
    check(len(rows)==len(inventory_levels)*len(finances)*len(configs)*len(arms),
          "Viability factorial incomplete")
    check(max_res<1e-9,"Viability stage stock-flow identity failure")
    write(out/"viability_all_36_scenarios.csv",rows)
    write(out/"viability_648_monthly_output_paths.csv",pathrows)
    summary={}
    for policy,_,_ in configs:
        r=[v for v in rows if v["route_policy"]==policy]
        summary[policy]={
          "count":len(r),
          "mean_late_output_ratio":float(np.mean([v["last_6_month_mean_output_ratio"] for v in r])),
          "min_late_output_ratio":float(min(v["last_6_month_mean_output_ratio"] for v in r)),
          "max_late_output_ratio":float(max(v["last_6_month_mean_output_ratio"] for v in r)),
          "mean_eligible_input_mass_fraction":float(np.mean([v["financially_eligible_fraction_input_mass"] for v in r])),
          "mean_near_zero_sectors_last_month":float(np.mean([v["final_month_near_zero_sector_count"] for v in r])),
          "total_seller_shortfall":float(sum(v["seller_goods_shortfall"] for v in r)),
          "total_route_denied":float(sum(v["route_denied"] for v in r)),
          "total_payment_capacity_shortfall":float(sum(v["payment_capacity_shortfall"] for v in r))}
    result={
      "schema":"n6_no_shock_104sector_viability_falsification_v1",
      "stage":"N6-1b",
      "original_A_frozen":True,"original_Q2_six_bands_frozen":True,
      "simulated_scenarios":len(rows),"monthly_path_rows":len(pathrows),
      "base_order_policy":"forward_input_coverage",
      "read_only_mechanism_trace":True,
      "no_shock_periods":18,
      "zero_financial_friction_topology_placebo_pass":True,
      "max_conservation_residual":max_res,
      "route_coverage_and_output_by_policy":summary,
      "source_m001_sha256":hashlib.sha256(a.read_bytes()).hexdigest(),
      "source_t001_sha256":hashlib.sha256(b.read_bytes()).hexdigest(),
      "legacy_original_8x10_economic_anchors_applied":False,
      "original_economic_model_certified":False,
      "economic_optimization_authorized":False,
      "note":"If even zero-friction route coverage produces low late output, repair physical stock/replenishment dynamics BEFORE network search; otherwise isolate payment and shipment support as the bottleneck."
    }
    (out/"status.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
