"""Standalone neutral stock-flow coupled economy kernel, experimental variant.

Public source only. Physical matrix A and financial eligibility P are distinct.
No direct topology coefficient is allowed in the production or employment
equations. Real changes arise from shipments, inventory and settled invoices.
This is a NEW coupled-economy variant, not a retrospective result for older runs.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import numpy as np

TOL=1e-9

def check(condition,message):
    if not bool(condition):raise RuntimeError(message)

@dataclass
class State:
    goods:np.ndarray
    inputs:np.ndarray
    firm_cash:np.ndarray
    household_cash:float
    bank_cash:float
    firm_loan:np.ndarray
    workforce:np.ndarray
    previous_output:np.ndarray

def init_state(A,reference,inventory_months=2.0):
    A=np.asarray(A,float)
    n=A.shape[0]
    check(A.shape==(n,n) and np.all(np.isfinite(A)) and np.all(A>=0),
          "Invalid physical input data")
    x=np.asarray(reference,float)
    check(x.shape==(n,) and np.all(x>0),"Invalid endogenous baseline output")
    goods=x*.5
    inputs=A*x[None,:]*float(inventory_months)
    cash=np.maximum(x*3,1e-6)
    household=float(np.sum(x)*2)
    bank=-float(np.sum(cash))-household
    return State(goods,inputs,cash,household,bank,np.zeros(n),np.ones(n),x.copy())

def equilibrium(A):
    A=np.asarray(A,float)
    n=len(A)
    demand=np.ones(n)/n
    production=np.linalg.solve(np.eye(n)-A,demand)
    check(np.all(np.isfinite(production)) and np.all(production>0),
          "Frozen input-output system not viable for positive demand")
    check(np.max(np.abs(production-A@production-demand))<1e-11,
          "Technology/consumption steady-state mismatch")
    return production,demand

def allowed(P,i,j,mode,hop_policy="direct"):
    if mode=="zero_frictions":return True,0.0
    if P[i,j]>0:return True,0.0
    if hop_policy=="two_hop" and np.any((P[i,:]>0)&(P[:,j]>0)):
        return True,0.01
    return False,0.0

def transfer(state,origin,dest,value):
    if value<=0:return
    if origin=="household":state.household_cash-=value
    elif origin=="bank":state.bank_cash-=value
    else:state.firm_cash[int(origin)]-=value
    if dest=="household":state.household_cash+=value
    elif dest=="bank":state.bank_cash+=value
    else:state.firm_cash[int(dest)]+=value

def borrow(state,j,need,maximum,friction):
    if need<=0:return 0.0
    if friction=="zero_frictions":
        grant=need
    else:
        credit_left=max(float(maximum)-float(state.firm_loan[j]),0.0)
        grant=min(need,credit_left)
    if grant:
        transfer(state,"bank",j,grant)
        state.firm_loan[j]+=grant
    return grant

def run(A,P,*,seed,periods=48,shock_start=12,shock_length=6,
        shock_severity=.4,shock_source=0,mode="base",
        hop_policy="direct",payment_capacity_scale=2.0,
        inventory_months=2.0,credit_fraction=1.2,
        wage_fraction=.22,investment_fraction=0.0,
        labor_speed=.25,full_ledger=False,
        order_policy="legacy_stock_only",shock_channel="capacity"):
    A=np.asarray(A,float)
    P=np.asarray(P,float)
    n=len(A)
    check(A.shape==P.shape==(n,n) and np.isfinite(P).all() and np.all(P>=0),
          "Nonconforming financial matrix")
    check(mode in ("base","zero_frictions"),"Unknown immutable financial regime")
    check(hop_policy in ("direct","two_hop"),"Unknown route policy")
    check(shock_channel in ("capacity","delivery"),"Unknown shock channel")
    check(order_policy in ("legacy_stock_only","forward_input_coverage"),
          "Unknown input ordering policy")
    check(0<=shock_severity<=1 and 0<=shock_source<n and periods>0,"Invalid shock")
    x,f=equilibrium(A)
    s=init_state(A,x,inventory_months)
    initial_money=float(np.sum(s.firm_cash)+s.household_cash+s.bank_cash)
    previous_total_goods=np.zeros(n)
    rng=np.random.default_rng(seed)
    path=[];ledgers=[]
    for t in range(periods):
        opening_goods=s.goods.copy()
        opening_inputs=s.inputs.copy()
        opening_money=float(np.sum(s.firm_cash)+s.household_cash+s.bank_cash)
        planned=x.copy()
        # Common exogenous (not network-specific) productivity perturbation:
        noise=rng.normal(0,.005,n)
        capacity=x*np.clip(1+noise,.8,1.2)
        if shock_channel=="capacity" and shock_start<=t<shock_start+shock_length:
            capacity[shock_source]*=1.0-shock_severity
        # Material requirements are non-substitutable in the primary model.
        # A buyer needs every positive physical input to produce a unit.
        feasible=np.divide(s.inputs,A,out=np.full_like(A,np.inf),where=A>0)
        material_bound=np.min(feasible,axis=0)
        q=np.minimum.reduce([planned,capacity,material_bound])
        check(np.all(q>=0),"Negative production")
        consumed=A*q[None,:]
        s.inputs-=consumed
        check(np.min(s.inputs)>=-1e-12,"Physical input inventories negative")
        s.inputs=np.maximum(s.inputs,0)
        s.goods+=q
        bill=np.zeros((n,n),float);shipments=np.zeros((n,n),float)
        unpaid=0.0;unfilled_physical=0.0
        # Frozen buyer loop and seller order avoid randomness in settlement order.
        # Purchases replenish input stock for the next monthly production.
        # Existing N5 runs retain the exact legacy ordering rule by default.
        # The new prospective forward-coverage alternative orders the next
        # period's technological requirements PLUS a separate desired safety
        # buffer. This is physical base-stock planning, not a direct payment-
        # topology coefficient; any constraints arise from actual shipment
        # availability, routing permission, and cash/credit settlement.
        desired_months = (inventory_months if order_policy=="legacy_stock_only"
                          else 1.0+inventory_months)
        requests=np.maximum(A*(x[None,:]*desired_months)-s.inputs,0)
        for i in range(n):
            for j in range(n):
                order=float(requests[i,j])
                if order<=0:continue
                quantity=min(order,max(float(s.goods[i]),0))
                if quantity<order:unfilled_physical+=order-quantity
                # Prospective delivery-interruption shock: the seller retains
                # any undelivered real goods. Nothing is created or destroyed.
                # Unlike the legacy productivity shock, this acts on actual
                # shipment eligibility and has no direct q/topology coefficient.
                if (shock_channel=="delivery" and i==shock_source
                        and shock_start<=t<shock_start+shock_length):
                    withheld=quantity*shock_severity
                    quantity-=withheld
                    unfilled_physical+=withheld
                if quantity<=0:continue
                permit,fee=allowed(P,i,j,mode,hop_policy)
                if not permit:
                    unpaid+=quantity
                    continue
                # Credit/payment access affects **settled shipments**, not
                # technological A, output q or labor directly.
                budget=float(s.firm_cash[j])
                if budget<quantity*(1+fee):
                    borrow(s,j,quantity*(1+fee)-budget,
                           max(float(x[j])*credit_fraction,0),mode)
                settled=min(quantity,max(float(s.firm_cash[j]),0)/(1+fee))
                if mode!="zero_frictions" and payment_capacity_scale<np.inf:
                    # Payment-routing capacity depends on a fixed *ex ante*
                    # financial edge, never on the output. No physical unit is
                    # minted by an indirect financial arc.
                    limit=(payment_capacity_scale*max(x[j],1e-12)*
                           float(P[i,j]/max(np.sum(P[:,j]),1e-12)))
                    if P[i,j]>0:settled=min(settled,limit)
                if settled<=0:
                    unpaid+=quantity
                    continue
                transfer(s,j,i,settled)
                if fee>0:transfer(s,j,"bank",settled*fee)
                s.goods[i]-=settled
                s.inputs[i,j]+=settled
                bill[i,j]+=settled
                shipments[i,j]+=settled
                unpaid+=max(quantity-settled,0)
        # Wage transfer is financed by actual output, with explicitly booked
        # bank credit as the only source for unfunded payroll.
        wage_paid=0.0
        employment=np.clip(q/np.maximum(x,1e-12),0,1)
        s.workforce=(1-labor_speed)*s.workforce+labor_speed*employment
        for j in range(n):
            wage=min(float(wage_fraction*q[j]),max(float(s.firm_cash[j]),0))
            req=float(wage_fraction*q[j])
            if wage<req:
                borrow(s,j,req-wage,max(float(x[j])*credit_fraction,0),mode)
                wage=min(req,max(float(s.firm_cash[j]),0))
            transfer(s,j,"household",wage)
            wage_paid+=wage
        # Household demand from real goods availability; unfulfilled spending
        # remains in household cash, not double-counted as final sales.
        household_requested=np.maximum(f,0)
        spending_budget=max(float(s.household_cash),0)
        scaling=min(1,spending_budget/max(float(np.sum(household_requested)),1e-12))
        actual=np.minimum(s.goods,household_requested*scaling)
        for i,amount in enumerate(actual):
            transfer(s,"household",i,float(amount))
        s.goods-=actual
        # Strict physical and internal payment identities hold every period.
        residual_goods=opening_goods+q-s.goods-np.sum(shipments,axis=1)-actual
        residual_input=opening_inputs+shipments-consumed-s.inputs
        money=float(np.sum(s.firm_cash)+s.household_cash+s.bank_cash)
        check(np.max(np.abs(residual_goods))<TOL,"Stock-flow identity fails")
        check(np.max(np.abs(residual_input))<TOL,"Intermediate-input identity fails")
        check(abs(money-opening_money)<TOL,"Monetary transfers fail double-entry check")
        check(abs(money-initial_money)<TOL,"Money created/destroyed without ledger")
        check(np.min(s.goods)>=-1e-9 and np.min(s.inputs)>=-1e-9,
              "Negative goods or intermediate inventory")
        # Real value added calculated from quantities actually produced/used.
        value_added=float(np.sum(q)-np.sum(consumed))
        share=bill.ravel()/max(float(np.sum(bill)),1e-12)
        HHI=float(np.sum(share**2))
        y={
          "M":t,
          "Y001":float(np.sum(q)),
          "Y002":value_added,
          "Y003":float(np.mean(s.workforce)),
          "Y004":float(np.sum(actual)),
          "Y005":HHI,
          "Y006":float(unpaid),
          "Y007":float(unfilled_physical),
          "Y008":float(np.sum(s.firm_loan)),
          "Y009":float(np.sum(shipments)),
          "Y010":float(np.sum(household_requested)),
          "Y011":float(np.sum(s.goods)),
          "Y012":float(s.household_cash),
          "R001":float(np.max(np.abs(residual_goods))),
          "R002":float(np.max(np.abs(residual_input))),
          "R003":float(abs(money-opening_money)),
          "R004":float(wage_paid)
        }
        check(all(np.isfinite(float(v)) for v in y.values()),"Nonfinite outcomes")
        path.append(y)
        if full_ledger:
            ledgers.append({
                "M":t,
                "Q":q.tolist(),
                "C":consumed.tolist(),
                "X":shipments.tolist(),
                "B":bill.tolist(),
                "F":actual.tolist(),
                "STOCK":s.goods.tolist(),
                "INPUT_STOCK":s.inputs.tolist(),
                "FIRM_CASH":s.firm_cash.tolist(),
                "HOUSEHOLD_CASH":s.household_cash,
                "BANK_CASH":s.bank_cash,
                "BANK_LOANS":s.firm_loan.tolist(),
                "LABOR":s.workforce.tolist()
            })
    return {"path":path,"ledger":ledgers}

def diff_in_diff(paths):
    """Two-way paired shock-versus-unshocked contrast between network arms."""
    a=paths["reconstructed_shock"]["path"]
    b=paths["reconstructed_none"]["path"]
    c=paths["mandatory_shock"]["path"]
    d=paths["mandatory_none"]["path"]
    check(len(a)==len(b)==len(c)==len(d),"Nonmatching paired horizon")
    out={}
    for k in ("Y001","Y002","Y003","Y004","Y005","Y006","Y007"):
        out[k]=sum((x[k]-y[k])-(u[k]-v[k]) for x,y,u,v in zip(a,b,c,d))
    return out
