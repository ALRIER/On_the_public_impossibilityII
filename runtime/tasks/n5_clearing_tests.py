"""Fast, deterministic, neutral N5 physical/financial conservation smoke tests."""
import json
import numpy as np
from runtime.tasks.n5_clearing_engine import run,diff_in_diff,equilibrium

def need(x,msg):
    if not bool(x):raise RuntimeError(msg)

def main():
    A=np.array([[.15,.07,.12],[.08,.19,.06],[.11,.03,.16]],float)
    P=np.ones((3,3),float)
    Q=np.array([[1.,0.,1.],[1.,1.,0.],[0.,1.,1.]])
    x,f=equilibrium(A)
    need(np.allclose(x,A@x+f),"Baseline requirements equilibrium wrong")
    args={"seed":4811,"periods":24,"shock_start":5,
          "shock_length":5,"shock_source":0,"shock_severity":.65,
          "inventory_months":1.0}
    a=run(A,P,**args,full_ledger=True)
    b=run(A,P,**args,full_ledger=True)
    need(a==b,"Repeated same seed not identical")
    no=run(A,P,**{**args,"shock_severity":0})
    need(sum(t["Y001"] for t in a["path"]) <
         sum(t["Y001"] for t in no["path"])-1e-10,
         "Physical supply loss did not reduce realized production")
    for v in (a,no):
        need(max(t["R001"] for t in v["path"])<1e-9,
             "Goods conservation violated")
        need(max(t["R002"] for t in v["path"])<1e-9,
             "Bilateral input conservation violated")
        need(max(t["R003"] for t in v["path"])<1e-9,
             "Payment conservation violated")
        need(min(t["Y003"] for t in v["path"])>=0,"Negative labor")
    # No direct topology-to-outcome path under zero friction:
    z1=run(A,P,**args,mode="zero_frictions")
    z2=run(A,Q,**args,mode="zero_frictions")
    need(z1["path"]==z2["path"],"Zero financial friction network placebo failed")
    # Decouple labor without removing a real physical shortage.
    x1=run(A,P,**args,labor_speed=0)
    x2=run(A,P,**{**args,"shock_severity":0},labor_speed=0)
    need(sum(t["Y001"] for t in x1["path"]) <
         sum(t["Y001"] for t in x2["path"])-1e-10,
         "Direct goods shock vanished when labor feedback removed")
    # Same physical technology and financial routing, different credit access.
    low=run(A,P,**args,credit_fraction=0.0)
    need(all(np.isfinite(v) for row in low["path"] for v in row.values()),
         "Credit stress creates nonfinite economic states")
    bundle=json.loads(open("public_bundle/n5_v1/m001.json").read())
    frozen=np.asarray(bundle["M001"],float)
    # two-period 104-node smoke test only; not a full data-generating run.
    R=run(frozen,np.ones_like(frozen),seed=4811,periods=2,
          shock_start=999,shock_length=0)
    need(len(R["path"])==2,"Frozen matrix smoke test incomplete")
    result={"status":"N5_LEDGER_SAFETY_GATE_PASS",
            "synthetic_replays_identical":True,
            "actual_supply_shock_reduces_output":True,
            "zero_frictions_topology_invariant":True,
            "physical_effect_persists_without_labor_feedback":True,
            "strict_mass_and_money_accounting":True,
            "104_node_frozen_numeric_smoke":True,
            "scientific_conclusion":"NOT_TESTED"}
    print(json.dumps(result,indent=2))
    return result

if __name__=="__main__":main()
