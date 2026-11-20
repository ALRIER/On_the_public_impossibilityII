"""N5 prospective delivery-channel falsification map; engineering only.

Preserves original historical capacity-shock mechanism by opt-in shock_channel.
Uses frozen 104x104 physical A and its original two public financial networks.
Also includes intentionally ineligible artificial support controls, NEVER
classified as admissible reconstructed network designs.
"""
from __future__ import annotations
import csv,hashlib,json
from pathlib import Path
import numpy as np
from runtime.tasks.n5_clearing_engine import run
from runtime.tasks.n5_review_proofs import baseline6,simple10

ROOT=Path(__file__).resolve().parents[2]
OUT=Path("outputs/n5_delivery_channel_pilot")
def demand(ok,msg):
    if not bool(ok):raise AssertionError(msg)
def save(filename,rows):
    with (OUT/filename).open("w",newline="") as handle:
        w=csv.DictWriter(handle,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
def aggregate(path,k):return float(sum(row[k] for row in path))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    src=ROOT/"public_bundle/n5_v1/m001.json"
    m=json.loads(src.read_text()); A=np.asarray(m["M001"],float)
    old=A.copy()
    demand(A.shape==(104,104) and len(m["V002"])==32,"Original numeric data mismatch")
    inherited=baseline6(A,m["I001"])
    reconstructed,_,_,_=simple10(A,m["V002"][0])
    control_full=np.ones_like(A)
    control_block=control_full.copy()
    src_sector,buyer=np.unravel_index(int(np.argmax(A)),A.shape)
    control_block[src_sector,buyer]=0.
    demand(A[src_sector,buyer]>0,"Non-physical diagnostic blocked edge")
    arms={"inherited":inherited,"reconstructed_0":reconstructed,
          "diagnostic_full_payment":control_full,
          "diagnostic_block_one_direct_edge":control_block}
    # Predefined, mechanically justified extremes; no post hoc search.
    specs=[("early",0,.5,.15,.6),("later",3,1.0,1.2,2.0)]
    source=int(src_sector)
    rows=[];contrasts=[]
    for label,start,buffer,credit,capacity in specs:
      for policy in ("legacy_stock_only","forward_input_coverage"):
        outcomes={}
        for name,P in arms.items():
          for severity in (0.,.65):
            p=run(A,P,seed=20261120,periods=14,shock_start=start,
                  shock_length=5,shock_source=source,
                  shock_severity=severity,inventory_months=buffer,
                  credit_fraction=credit,payment_capacity_scale=capacity,
                  order_policy=policy,shock_channel="delivery")["path"]
            demand(max(max(abs(t["R001"]),abs(t["R002"]),abs(t["R003"])) for t in p)<1e-9,
                   "Conservation failed "+label+" "+policy+" "+name)
            outcomes[name,severity]=p
            rows.append({"design":label,"policy":policy,"arm":name,
                    "severity":severity,"shock_source":source,
                    "blocked_physical_seller":int(src_sector),
                    "blocked_physical_buyer":int(buyer),
                    "inventory":buffer,"credit":credit,"payment_capacity":capacity,
                    "value_added":aggregate(p,"Y002"),
                    "output":aggregate(p,"Y001"),
                    "consumption":aggregate(p,"Y004"),
                    "shipments":aggregate(p,"Y009"),
                    "arrears":aggregate(p,"Y006"),
                    "physical_shortage":aggregate(p,"Y007")})
        # strict no-friction topology falsification under real delivery shock
        placebos=[]
        for name in ("inherited","reconstructed_0",
                     "diagnostic_block_one_direct_edge"):
          placebos.append(run(A,arms[name],seed=20261120,periods=14,
                     shock_start=start,shock_length=5,shock_source=source,
                     shock_severity=.65,inventory_months=buffer,
                     credit_fraction=credit,payment_capacity_scale=capacity,
                     order_policy=policy,shock_channel="delivery",
                     mode="zero_frictions")["path"])
        demand(all(x==placebos[0] for x in placebos[1:]),
               "Network topology leaks into no-friction real outcomes")
        for name in list(arms)[1:]:
          d={"design":label,"policy":policy,"arm":name,
             "reference":"inherited",
             "diagnostic_nonadmissible":
                 int(name.startswith("diagnostic"))}
          for metric,k in (("va","Y002"),("output","Y001"),
                           ("consumption","Y004"),("shipments","Y009"),
                           ("arrears","Y006")):
            d["shock_did_"+metric] = (
               aggregate(outcomes[name,.65],k)-aggregate(outcomes[name,0.],k)-
               aggregate(outcomes["inherited",.65],k)+aggregate(outcomes["inherited",0.],k))
            d["shock_level_"+metric] = (
               aggregate(outcomes[name,.65],k)-aggregate(outcomes["inherited",.65],k))
          contrasts.append(d)
    demand(np.array_equal(A,old),"Original physical technology modified")
    save("all_104_sector_economic_paths.csv",rows)
    save("all_104_sector_paired_network_contrasts.csv",contrasts)
    def meaningful(r):
        return any(abs(float(r["shock_did_"+k]))>1e-10
                   for k in ("va","output","consumption"))
    admissible=[r for r in contrasts if not r["diagnostic_nonadmissible"]]
    excluded=[r for r in contrasts if r["diagnostic_nonadmissible"]]
    status={
      "schema":"n5_original_104sector_delivery_shock_pilot_v1",
      "public_input_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
      "original_104_sector_A_unchanged":True,
      "original_historical_capacity_shock_default_unchanged":True,
      "all_periodic_conservation_pass":True,
      "zero_financial_friction_network_placebo_pass":True,
      "designs":len(specs),"tested_order_policies":2,
      "prospective_admissible_original_structure_contrasts":len(admissible),
      "original_structure_nonzero_shock_did_cases":sum(meaningful(r) for r in admissible),
      "out_of_band_diagnostic_nonzero_shock_did_cases":sum(meaningful(r) for r in excluded),
      "out_of_band_controls_not_eligible_for_q2_structural_claims":True,
      "legacy_10_parameter_anchors_mapped":False,
      "independent_original_economic_ABM_parity":False,
      "q1_scientific_certification":False,
      "q4_original_historical_failures_modified":False,
      "large_scale_ml_search_authorized":False
    }
    (OUT/"status.json").write_text(json.dumps(status,indent=2)+"\n")
    print(json.dumps(status,indent=2))
if __name__=="__main__":main()
