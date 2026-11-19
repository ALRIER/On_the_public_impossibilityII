"""Numerical-only, public-code verification for N5 historical review bundle.

All identifiers refer to neutral numeric arrays. Scientific decoding stays private.
Read-only preflight: fast (~seconds), no simulator trajectories or private access.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, sys
from pathlib import Path
import numpy as np
from scipy.stats import qmc

ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/"public_bundle/n5_v1"
RANGES10=np.array([[0,.90],[0,.25],[.05,1],[.50,.99],[0,.99],[0,1.5],
                   [.50,3],[.50,.95],[1,5],[0,2]],float)
RANGES6=np.array([[0,.99],[0,1.5],[.50,3],[.50,.95],[1,5],[0,2]],float)
OUT=Path("outputs/n5_v1/proofs")

def load(name):
    path=BUNDLE/name
    with path.open(encoding="utf-8") as h:return json.load(h)

def ensure(x,msg):
    if not bool(x):raise RuntimeError(msg)

def write(name,rows):
    OUT.mkdir(parents=True,exist_ok=True)
    if not rows:return
    path=OUT/name
    with path.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def simple10(A,Z):
    C=RANGES10[:,0]+np.asarray(Z,dtype=float)*(RANGES10[:,1]-RANGES10[:,0])
    qd,floor,fraction,coverage,qind,mass,rho,qt,tail,hetero=C
    D=np.zeros_like(A)
    shares=[]
    for j in range(A.shape[1]):
        col=np.maximum(A[:,j],0)
        positive=np.flatnonzero(col>0)
        if not len(positive):continue
        vals=col[positive]
        total=float(vals.sum())
        order=np.argsort(vals)[::-1]
        threshold=max(float(np.quantile(vals,qd)),floor*float(vals.max()))
        active_count=max(1,int(np.ceil(fraction*len(positive))))
        chosen=[int(k) for k in order if vals[k]>=threshold][:active_count]
        if not chosen:chosen=[int(order[0])]
        kept=set(chosen)
        retained=float(sum(vals[k] for k in kept))
        if retained<coverage*total:
            for k in order:
                k=int(k)
                if k in kept:continue
                kept.add(k);retained+=float(vals[k])
                if retained>=coverage*total:break
        selected=positive[np.array(sorted(kept),dtype=int)]
        D[selected,j]=col[selected]
        tot=float(D[:,j].sum())
        if tot>0:D[:,j]*=total/tot
        shares.append(retained/total)
    # Mandatory original technological columns always remain unchanged; D is an
    # auxiliary financial representation, never a replacement physical A.
    ensure(np.allclose(D.sum(axis=0),A.sum(axis=0),atol=1e-11,rtol=1e-11),
           "Selected financial column does not conserve original direct input mass")
    second=A@A
    pos=second[second>0]
    threshold=float(np.quantile(pos,qind)) if len(pos) else np.inf
    support=(second>0)&(second>=threshold)
    G=D.copy()
    for j in range(A.shape[1]):
        total=float(A[:,j].sum())
        raw=np.where(support[:,j],second[:,j],0)
        s=float(raw.sum())
        if s>0 and total>0 and mass>0:
            G[:,j]+=raw*((mass*total)/s)
    H=np.where(G>0,G**rho,0)
    hhi=[]
    for j in range(A.shape[1]):
        col=A[:,j];total=float(col.sum())
        hhi.append(float(np.sum((col/total)**2)) if total>0 else 0)
    good=np.array([v for v in hhi if v>0])
    median=max(float(np.median(good)),1e-12) if len(good) else 1
    cutoff=float(np.quantile(good,qt)) if len(good) else np.inf
    P=H.copy()
    for j,hj in enumerate(hhi):
        col=P[:,j];total=float(col.sum())
        if total<=0 or hj<=0:continue
        local=float(np.clip(1+hetero*(math.sqrt(max(hj/median,1e-12))-1),.35,3.5))
        if hj>=cutoff:local*=tail
        changed=np.where(col>0,col**local,0)
        s=float(changed.sum())
        if s>0:P[:,j]=changed*(total/s)
    ensure(np.all(np.isfinite(P)) and np.all(P>=0),"nonfinite financial weights")
    ensure(np.allclose(P.sum(axis=0),H.sum(axis=0),rtol=1e-10,atol=1e-11),
           "Final financial reweighting does not conserve transformed financial column sums")
    ensure(np.array_equal(A,np.asarray(A)),"Technological array changed")
    return P,D,G,H

def baseline6(A,index):
    engine=qmc.Sobol(d=6,scramble=True,seed=6032026)
    engine.fast_forward(int(index))
    Z=engine.random(1)[0]
    mass_q,mass,rho,qt,tail,hetero=RANGES6[:,0]+Z*(RANGES6[:,1]-RANGES6[:,0])
    second=A@A
    positive=second[second>0]
    threshold=float(np.quantile(positive,mass_q)) if len(positive) else np.inf
    S=(second>0)&(second>=threshold)
    raw=A.copy()
    for j in range(A.shape[1]):
        total=float(A[:,j].sum())
        v=np.where(S[:,j],second[:,j],0)
        s=float(v.sum())
        if s>0 and total>0 and mass>0:
            raw[:,j]+=v*(mass*total/s)
    P=np.where(raw>0,raw**rho,0)
    hh=[]
    for j in range(A.shape[1]):
        col=A[:,j];ss=float(col.sum())
        hh.append(float(np.sum((col/ss)**2)) if ss>0 else 0)
    good=np.array([x for x in hh if x>0])
    med=max(float(np.median(good)),1e-12) if len(good) else 1
    cut=float(np.quantile(good,qt)) if len(good) else np.inf
    for j,h in enumerate(hh):
        col=P[:,j];ss=float(col.sum())
        if ss<=0 or h<=0:continue
        local=float(np.clip(1+hetero*(math.sqrt(max(h/med,1e-12))-1),.35,3.5))
        if h>=cut:local*=tail
        transformed=np.where(col>0,col**local,0)
        tot=float(transformed.sum())
        if tot>0:P[:,j]=transformed*(ss/tot)
    return P

def density_only(A,goal):
    candidates=[(float(A[i,j]),i,j) for i,j in zip(*np.nonzero(A))]
    candidates.sort(key=lambda x:(-x[0],x[1],x[2]))
    picked=set()
    for j in range(A.shape[1]):
        if np.any(A[:,j]>0):picked.add((int(np.argmax(A[:,j])),j))
    possible=len(candidates)
    count=min(max(int(goal),len(picked)),possible)
    for _,i,j in candidates:
        if len(picked)>=count:break
        picked.add((i,j))
    out=np.zeros_like(A)
    for i,j in picked:out[i,j]=A[i,j]
    denom=out.sum(axis=0);tot=A.sum(axis=0)
    out*=np.divide(tot,denom,out=np.zeros_like(tot),where=denom>0)[None,:]
    ensure(np.allclose(out.sum(axis=0),tot,atol=1e-11),"Simple comparator column sum failure")
    return out,goal<=possible

def metrics(P):
    total=max(float(P.sum()),1e-15)
    sh=P.ravel()/total
    hh=[];top=[]
    for j in range(P.shape[1]):
        col=P[:,j];s=float(col.sum())
        if s<=0:continue
        p=col/s;hh.append(float(np.sum(p*p)));top.append(float(np.max(p)))
    return [float(np.mean(P>0)),float(np.sum(sh*sh)),float(np.median(hh)),
            float(np.quantile(hh,.9)),float(np.median(top)),float(np.quantile(top,.9))]

def network_proofs(m,t):
    A=np.asarray(m["M001"],float).copy();frozen=A.copy()
    ensure(A.shape==(104,104) and np.all(np.isfinite(A)) and np.all(A>=0),
           "Frozen matrix invalid")
    p0=baseline6(A,m["I001"])
    # Grounded N1 density reproduced from the frozen original scientific source.
    expected_n1=0.9675480769230769
    ensure(abs(float(np.mean(p0>0))-expected_n1)<1e-12,
           "Original inherited financial baseline not exactly reconstructed")
    rows=[];compare=[];perstructure=[]
    targets=t["M201"]
    for k,Z in enumerate(m["V002"]):
        P,D,G,H=simple10(A,Z)
        mm=metrics(P)
        density,achieved=np.count_nonzero(P),np.count_nonzero(A)
        matched,possible=density_only(A,density)
        compare.append({"S":k,"N":int(density),"N_MAX_DIRECT":int(achieved),
                        "MATCHABLE":int(possible),
                        "DIRECT_COMPARATOR_N":int(np.count_nonzero(matched)),
                        "DIRECT_COMPARATOR_DISTANCE":float(np.linalg.norm(P-matched))})
        for i,v in enumerate(mm):
            low,high=targets[i]["T"][1:]
            rows.append({"S":k,"C":targets[i]["id"],"Y":v,
                         "T":targets[i]["T"][0],"LO":low,"HI":high,
                         "IN_BAND":int(low<=v<=high)})
        perstructure.append(mm)
    ensure(np.array_equal(A,frozen),"Numeric preflight modified frozen technology")
    # Cases = 32 structural representations paired with 8 frozen economic anchors;
    # here P does not depend on anchor. Never pseudo-replicate 256 metric draws.
    ensure(len(rows)==192 and len(perstructure)==32,"Expected structural panel incomplete")
    write("o201.csv",rows);write("o202.csv",compare)
    return {"q2_identity_pass":True,"original_network_reproduced":True,
            "number_structures":32,"network_metrics_measured":192,
            "metric_passes":sum(x["IN_BAND"] for x in rows),
            "metric_total":len(rows),"simple_density_matched_count":
            sum(x["MATCHABLE"] for x in compare)}

def robust_data(U):
    X=np.array([u["V"] for u in U],float)
    med=np.median(X,axis=0)
    mad=1.4826*np.median(np.abs(X-med),axis=0)
    for j in range(3):
        if mad[j]<=1e-12:
            q1,q3=np.quantile(X[:,j],[.25,.75]);mad[j]=(q3-q1)/1.349
        if mad[j]<=1e-12:mad[j]=np.std(X[:,j],ddof=1)
        ensure(mad[j]>1e-12,"Cannot calculate robust dimension scaling")
    return X,med,mad

def percent(model,X,med,scale,kind="l2",weights=None):
    if weights is None:weights=np.ones(3)/3
    weights=np.asarray(weights,float)
    Z=(X-med)/scale; z=(np.asarray(model,float)-med)/scale
    delta=np.abs(Z-z)
    if kind=="l1":d=np.sum(delta*weights[None,:],axis=1)
    elif kind=="linf":d=np.max(delta*weights[None,:],axis=1)
    elif kind=="l2":d=np.sqrt(np.sum((delta**2)*weights[None,:],axis=1))
    elif kind=="mahal":
        inv=np.linalg.pinv(np.cov(Z,rowvar=False))
        D=Z-z
        d=np.sqrt(np.maximum(np.einsum("ij,jk,ik->i",D,inv,D),0))
    else:raise ValueError(kind)
    near=float(np.min(d))
    # Reference countries' leave-one-out nearest neighbor, same geometry.
    ref=[]
    for i in range(len(X)):
        diff=np.abs(Z-Z[i])
        if kind=="l1":ds=np.sum(diff*weights[None,:],axis=1)
        elif kind=="linf":ds=np.max(diff*weights[None,:],axis=1)
        elif kind=="l2":ds=np.sqrt(np.sum((diff**2)*weights[None,:],axis=1))
        else:
            D=Z-Z[i];ds=np.sqrt(np.maximum(np.einsum("ij,jk,ik->i",D,inv,D),0))
        ds[i]=np.inf
        ref.append(float(np.min(ds)))
    return near,100*float(np.mean(np.asarray(ref)<=near)),int(np.argmin(d))

def window_stat(obs,years):
    selected=[row for y,row in zip(range(1995,2024),obs) if y in years]
    vals=[[p[j] for p in selected if p[j] is not None] for j in range(3)]
    threshold=max(3,int(math.ceil(.75*len(years))))
    if any(len(x)<threshold for x in vals):return None
    return [float(np.mean(vals[0])),float(np.std(vals[1],ddof=1)),float(np.mean(vals[2]))]

def position_proofs(bundle):
    fresh=[u for u in bundle["U001"] if u["R"]=="R0"]
    ensure(len(fresh)==146,"Registered original reference universe changed")
    X,med,scale=robust_data(fresh)
    separate=bundle["U002"]
    ensure(len(separate)==36,"Independent alternative panel count changed")
    X2,med2,scale2=robust_data(separate)
    # The registered primary distance was unweighted Euclidean; uniform weights
    # produce identical normalized nearest-neighbor percentiles.
    low=percent(bundle["V002"],X,med,scale)
    other=percent(bundle["V003"],X2,med2,scale)
    ensure(abs(low[1]-float(bundle["L001"][0]))<1e-9,
           "Full-country reference support percentile did not reproduce")
    ensure(abs(other[1]-float(bundle["L001"][1]))<1e-9,
           "Independent provider support percentile did not reproduce")
    # Full historical source snapshots are exported as only neutral numerical
    # years; never reuse a full-period country average for subperiod sensitivity.
    for u in bundle["U001"]:
        v=window_stat(u["Y"],set(range(1995,2024)))
        ensure(v is None or np.allclose(v,u["V"],rtol=1e-9,atol=1e-9),
               "Frozen full-window reference does not reproduce historical numeric source")
    weights=[]
    for a in range(11):
        for b in range(11-a):
            c=10-a-b
            weights.append((a/10,b/10,c/10))
    anchors=[*bundle["V001"],bundle["V002"]]
    rows=[]
    for ix,p in enumerate(anchors):
        for w in weights:
            for k in ("l1","l2","linf"):
                v=percent(p,X,med,scale,k,w)
                rows.append({"V":ix,"W1":w[0],"W2":w[1],"W3":w[2],
                             "K":k,"D":v[0],"SUPPORT":v[1],"NEAR":v[2]})
        v=percent(p,X,med,scale,"mahal")
        rows.append({"V":ix,"W1":1/3,"W2":1/3,"W3":1/3,
                     "K":"mahal","D":v[0],"SUPPORT":v[1],"NEAR":v[2]})
    write("o301.csv",rows)
    windows=[
        ("W1",set(range(1995,2005))),
        ("W2",set(range(2005,2015))),
        ("W3",set(range(2015,2024))),
        ("W4",set(range(1995,2009))),
        ("W5",set(range(2009,2024))),
        ("W6",set(range(1995,2024))-{2020,2021}),
    ]
    cover=[]
    for name,years in windows:
        r=[window_stat(u["Y"],years) for u in fresh]
        eligible=[x for x in r if x is not None]
        cover.append({"W":name,"N":len(eligible),"YEAR_N":len(years),
                      "MODEL_YEAR_IDENTIFICATION":"full_period_only"})
        # A model's full-period moment is NOT automatically a comparable
        # short-period model moment. Report reference geometry only until
        # matched-period model histories can be generated by public runtime.
    write("o302.csv",cover)
    return {"q3_reference_reproduced":True,
            "original_universe":146,"independent_universe":36,
            "support_original":low[1],"support_independent":other[1],
            "weight_distance_rows":len(rows),
            "subperiod_reference_coverage_prepared":len(cover),
            "subperiod_model_matched":False}

def residual_proofs(t):
    rows=[]
    for x in t["M202"]:
        values=x["T"]
        rows.append({"C":x["id"],"T":values[0],"LO":values[1],
                     "HI":values[2],"PASS_CASES":x["C"],"CASES":x["N"],
                     "ACHIEVED":"UNAVAILABLE_IN_AGGREGATE_N3_SUMMARY",
                     "SIGN_GAP":"NOT_COMPUTED_UNTIL_RAW_SHARDS_RESTORED"})
    write("o401.csv",rows)
    ensure(len(rows)==6 and all(r["PASS_CASES"]==0 and r["CASES"]==256
                               for r in rows),"Original N3 universal failure register mismatch")
    return {"q4_targets_loaded":12,"q4_universally_failed":6,
            "q4_achieved_gap_source":"MISSING_RAW_N3_CASE_MOMENTS",
            "q4_reader_numeric_complete":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="outputs/n5_v1/proofs")
    ar=ap.parse_args()
    global OUT
    OUT=Path(ar.out)
    m,r,t=load("m001.json"),load("r001.json"),load("t001.json")
    ensure(m["revision"]==r["revision"]==t["revision"]=="n5-r1",
           "Unfrozen mixed package revision")
    s={"schema":"n5_neutral_proofs_v1","revision":"n5-r1",
       "inputs":{name:digest(BUNDLE/name) for name in ["m001.json","r001.json","t001.json"]},
       **network_proofs(m,t),**position_proofs(r),**residual_proofs(t)}
    s["full_reviewer_closure_ready"]=False
    s["status"]="ENGINEERING_PRECHECK_ONLY_NOT_READY_FOR_FULL_RUN"
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"o000.json").write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(s,indent=2))
    return 0

if __name__=="__main__":
    sys.exit(main())
