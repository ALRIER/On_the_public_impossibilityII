from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import urllib.request
import urllib.parse
import zipfile
from pathlib import Path

import numpy as np

from runtime.tasks.hr1_diag import _load, _sim

PANEL_DEFAULT = "public_bundle/h1_country_panel.csv"
H1_MASTER = 17102027
SEED_STRIDE = 104729
REPS = 512
HR1_RUN_ID = 37687986340

def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))

def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def _panel(path: Path):
    rows=_read_csv(path)
    fresh=[r for r in rows if r["ROLE"]=="R0"]
    refs=[r for r in rows if r["ROLE"]!="R0"]
    X=np.asarray([[float(r[e]) for e in ("E001","E002","E003")] for r in fresh],dtype=float)
    med=np.median(X,axis=0)
    mad=np.median(np.abs(X-med),axis=0)
    scale=1.4826*mad
    for j in range(3):
        if scale[j] <= 1e-12:
            q25,q75=np.quantile(X[:,j],[.25,.75]); scale[j]=(q75-q25)/1.349
        if scale[j] <= 1e-12:
            scale[j]=np.std(X[:,j],ddof=1)
        if scale[j] <= 1e-12:
            raise RuntimeError(f"degenerate H1 scale {j}")
    Z=(X-med)/scale
    cov=np.cov(Z,rowvar=False)
    inv=np.linalg.pinv(cov)
    return rows,fresh,refs,X,Z,med,scale,inv

def _loo_nn(Z: np.ndarray) -> np.ndarray:
    out=np.empty(len(Z),dtype=float)
    for i in range(len(Z)):
        d=np.sqrt(np.sum((Z-Z[i])**2,axis=1)); d[i]=np.inf
        out[i]=float(np.min(d))
    return out

def _rank(model: np.ndarray, panel_path: Path):
    rows,fresh,refs,X,Z,med,scale,inv=_panel(panel_path)
    z=(model-med)/scale
    d=np.sqrt(np.sum((Z-z)**2,axis=1))
    D=Z-z
    md=np.sqrt(np.maximum(np.einsum("ij,jk,ik->i",D,inv,D),0.0))
    idx1=np.argsort(d); idx2=np.argsort(md)
    rank2={int(ix):k+1 for k,ix in enumerate(idx2)}
    out=[]
    for k,ix in enumerate(idx1):
        i=int(ix)
        out.append({
            "C":fresh[i]["C"],
            "PRIMARY_RANK":k+1,
            "PRIMARY_DISTANCE":float(d[i]),
            "SECONDARY_RANK":rank2[i],
            "MAHALANOBIS_DISTANCE":float(md[i]),
        })
    nn=_loo_nn(Z)
    nearest=float(np.min(d))
    pct=float(np.mean(nn <= nearest)*100.0)
    # contextual references, scored in same frozen geometry but excluded from fresh ranking
    ref_rows=[]
    for r in refs:
        x=np.asarray([float(r[e]) for e in ("E001","E002","E003")],dtype=float)
        rz=(x-med)/scale
        rd=float(np.sqrt(np.sum((rz-z)**2)))
        q=rz-z
        rmd=float(math.sqrt(max(float(q@inv@q),0.0)))
        ref_rows.append({"C":r["C"],"ROLE":r["ROLE"],"PRIMARY_DISTANCE":rd,"MAHALANOBIS_DISTANCE":rmd})
    summ={
        "E001":float(model[0]),"E002":float(model[1]),"E003":float(model[2]),
        "NEAREST_C":out[0]["C"],"NEAREST_DISTANCE":nearest,
        "EMPIRICAL_SUPPORT_PERCENTILE":pct,
        "TOP10":";".join(x["C"] for x in out[:10]),
        "FRESH_N":len(fresh),
        "MED_E001":float(med[0]),"MED_E002":float(med[1]),"MED_E003":float(med[2]),
        "SCALE_E001":float(scale[0]),"SCALE_E002":float(scale[1]),"SCALE_E003":float(scale[2]),
    }
    return out,ref_rows,summ

def run_anchor(shard:int, output:Path, root:Path, panel_path:Path) -> None:
    b=_load(root)
    if not 0 <= shard <= 7:
        raise RuntimeError("anchor shard must be 0..7")
    p=np.asarray(b["anchors"][shard]["p"],dtype=float)
    vals=[_sim(b,p,H1_MASTER+r*SEED_STRIDE) for r in range(REPS)]
    A=np.asarray([[x[0],x[1],x[2]] for x in vals],dtype=float)
    if not np.all(np.isfinite(A)):
        raise RuntimeError("nonfinite H1 anchor output")
    model=np.mean(A,axis=0)
    dist,refs,summ=_rank(model,panel_path)
    summ.update({
        "A":f"A{shard:02d}","REPLICATES":REPS,
        "E001_LO":float(np.quantile(A[:,0],.025)),"E001_HI":float(np.quantile(A[:,0],.975)),
        "E002_LO":float(np.quantile(A[:,1],.025)),"E002_HI":float(np.quantile(A[:,1],.975)),
        "E003_LO":float(np.quantile(A[:,2],.025)),"E003_HI":float(np.quantile(A[:,2],.975)),
    })
    _write(output/f"h1_anchor_{shard:02d}_distances.csv",[{"A":f"A{shard:02d}",**r} for r in dist])
    _write(output/f"h1_anchor_{shard:02d}_references.csv",[{"A":f"A{shard:02d}",**r} for r in refs])
    _write(output/f"h1_anchor_{shard:02d}_summary.csv",[summ])

def _api_json(url:str):
    req=urllib.request.Request(url,headers={
        "Authorization":f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"h1-position"
    })
    with urllib.request.urlopen(req,timeout=120) as r:
        return json.loads(r.read().decode())

class _StripAuthOnCrossHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None:
            old_host = urllib.parse.urlparse(req.full_url).netloc
            new_host = urllib.parse.urlparse(newurl).netloc
            if old_host != new_host:
                new_req.remove_header("Authorization")
                new_req.remove_header("X-GitHub-Api-Version")
                new_req.remove_header("Accept")
        return new_req

def _download(url:str)->bytes:
    req=urllib.request.Request(url,headers={
        "Authorization":f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"h1-position"
    })
    opener=urllib.request.build_opener(_StripAuthOnCrossHostRedirect())
    with opener.open(req,timeout=120) as r:
        return r.read()

def fetch_hr1_global(repo:str, output:Path) -> Path:
    meta=_api_json(f"https://api.github.com/repos/{repo}/actions/runs/{HR1_RUN_ID}/artifacts?per_page=100")
    arts=meta["artifacts"]
    rows=[]
    for a in arts:
        name=a["name"]
        try: shard=int(name.split("-")[-1])
        except Exception: continue
        if not 8 <= shard <= 71: continue
        raw=_download(a["archive_download_url"])
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=[n for n in z.namelist() if n.endswith("global.csv")]
            if len(names)!=1: raise RuntimeError(f"{name}: expected one global.csv")
            txt=z.read(names[0]).decode("utf-8")
            rows.extend(csv.DictReader(io.StringIO(txt)))
    if len(rows)!=4096*3:
        raise RuntimeError(f"expected 12288 HR1 global rows, got {len(rows)}")
    # pivot target rows to one vector per Sobol point
    by={}
    for r in rows:
        idx=r["IDX"]
        ent=by.setdefault(idx,{"IDX":idx,**{f"P{i:02d}":r[f"P{i:02d}"] for i in range(10)}})
        ent[r["E"]]=r["MEAN"]
    points=list(by.values())
    if len(points)!=4096: raise RuntimeError(f"expected 4096 points, got {len(points)}")
    p=output/"hr1_global_point_means.csv"; _write(p,points); return p

def project_global(repo:str, output:Path, panel_path:Path) -> None:
    src=fetch_hr1_global(repo,output)
    rows=_read_csv(src)
    out=[]
    for r in rows:
        model=np.asarray([float(r["E001"]),float(r["E002"]),float(r["E003"])],dtype=float)
        dist,refs,summ=_rank(model,panel_path)
        out.append({
            "IDX":r["IDX"],
            **{f"P{i:02d}":r[f"P{i:02d}"] for i in range(10)},
            "NEAREST_C":summ["NEAREST_C"],
            "NEAREST_DISTANCE":summ["NEAREST_DISTANCE"],
            "EMPIRICAL_SUPPORT_PERCENTILE":summ["EMPIRICAL_SUPPORT_PERCENTILE"],
            "TOP10":summ["TOP10"],
        })
    _write(output/"h1_hr1_parameter_condition_map.csv",out)

def run(control:dict, shard:int, output:Path, root:Path) -> None:
    panel=root/PANEL_DEFAULT
    if 0 <= shard <= 7:
        run_anchor(shard,output,root,panel)
    elif shard == 8:
        repo=os.environ.get("GITHUB_REPOSITORY","ALRIER/On_the_public_impossibilityII")
        project_global(repo,output,panel)
    else:
        raise RuntimeError("H1 shard must be 0..8")
