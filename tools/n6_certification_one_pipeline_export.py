"""Keep exact original public YES/NO certification release bytes on a staging branch.

Runs within the SAME public certification GitHub Actions job; no second
pipeline and no access to or computation inside private GitHub Actions.
"""
from __future__ import annotations
import base64,hashlib,json,os,subprocess,tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO="ALRIER/On_the_public_impossibilityII"
SRC=("runtime/tasks/n6_single_pipeline_certification.py",
     "runtime/tasks/n6_coupling_compatibility_gate.py",
     "runtime/tasks/n5_clearing_engine.py",
     ".github/workflows/n6-one-pipeline-scientific-certification.yml")
OUT=ROOT/"staging"/"n6_one_pipeline_certification_20261120"
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(args,text=True).strip()
def main():
    runid=os.environ.get("GITHUB_RUN_ID")
    attempt=os.environ.get("GITHUB_RUN_ATTEMPT","1")
    assert runid and runid.isdigit(),"Must run in public GitHub Actions"
    tag=f"n6-public-one-pipeline-certification-{runid}-a{attempt}"
    OUT.mkdir(parents=True,exist_ok=True)
    source=OUT/"release_assets"
    source.mkdir(exist_ok=True)
    desc=json.loads(git("gh","api",f"repos/{REPO}/releases/tags/{tag}"))
    git("gh","release","download",tag,"--repo",REPO,"--dir",str(source))
    records=[];files=[]
    for a in sorted(desc["assets"],key=lambda v:v["name"]):
        p=source/a["name"];b=p.read_bytes()
        assert len(b)==a["size"]
        assert a["digest"]=="sha256:"+sha(b)
        records.append({"name":a["name"],"bytes":len(b),"sha256":sha(b)})
        files.append((p,"original_release_assets/"+a["name"]))
    original_code={}
    for p in SRC:
        f=ROOT/p;original_code[p]=sha(f.read_bytes())
        files.append((f,"public_source_snapshot/"+p))
    archive=OUT/"n6_one_pipeline_original_release_and_sources.tar.gz"
    with tarfile.open(archive,"w:gz") as tar:
        for p,arc in files:tar.add(p,arcname=arc,recursive=False)
    data=archive.read_bytes()
    verdict=json.loads((ROOT/"outputs/n6_one_pipeline_certification/CERTIFICATION_VERDICT.json").read_text())
    assert verdict["scientific_decision"] in ("YES","NO")
    status={
        "schema":"n6_one_pipeline_original_evidence_exact_bytes_v1",
        "original_repository":REPO,"original_tag":tag,"original_workflow_run":int(runid),
        "original_assets":records,"source_snapshots":original_code,
        "archive_name":archive.name,"archive_sha256":sha(data),
        "archive_bytes":len(data),
        "scientific_certification_decision":verdict["scientific_decision"],
        "public_commit":git("git","rev-parse","HEAD"),
        "no_private_actions_run":True,
    }
    (OUT/"manifest.json").write_text(json.dumps(status,indent=2)+"\n")
    (OUT/"archive_bytes.b64").write_text(base64.b64encode(data).decode()+"\n")
    (OUT/"CERTIFICATION_VERDICT.json").write_text(json.dumps(verdict,indent=2)+"\n")
    print(json.dumps({
        "run":int(runid),"tag":tag,"decision":verdict["scientific_decision"],
        "assets":len(records),"archive_sha256":sha(data),"bytes":len(data)},indent=2))
if __name__=="__main__":
    main()
