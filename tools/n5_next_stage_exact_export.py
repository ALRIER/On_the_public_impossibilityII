"""Public-only exact-byte export of completed N5 exploratory evidence.

Uses GitHub Release asset SHA256 attestations; no private access or Actions.
"""
import base64,hashlib,json,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"staging/n5_next_stage_20261120"
TAG="n5-public-next-stage-heterogeneity-44763687139-a1"
REPO="ALRIER/On_the_public_impossibilityII"
SNAPSHOT=["runtime/tasks/n5_next_stage_network_heterogeneity.py",
          ".github/workflows/n5-next-stage-heterogeneity.yml",
          "runtime/tasks/n5_clearing_engine.py"]
def output(*cmd):return subprocess.check_output(cmd,text=True)
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
    DEST.mkdir(parents=True,exist_ok=True)
    assetdir=DEST/"original_release_files";assetdir.mkdir(exist_ok=True)
    meta=json.loads(output("gh","api",f"repos/{REPO}/releases/tags/{TAG}"))
    output("gh","release","download",TAG,"--repo",REPO,"--dir",str(assetdir))
    rows=[]; files=[]
    for a in sorted(meta["assets"],key=lambda x:x["name"]):
        p=assetdir/a["name"]; data=p.read_bytes()
        assert digest(data)==a["digest"].removeprefix("sha256:") and len(data)==a["size"]
        rows.append({"filename":a["name"],"bytes":len(data),"sha256":digest(data)})
        files.append((p,"original_release_assets/"+a["name"]))
    source={}
    for rel in SNAPSHOT:
        p=ROOT/rel;source[rel]=digest(p.read_bytes())
        files.append((p,"source_snapshot/"+rel))
    tarpath=DEST/"n5_next_stage_original_assets.tar.gz"
    with tarfile.open(tarpath,"w:gz") as tar:
        for path,name in files:tar.add(path,arcname=name,recursive=False)
    data=tarpath.read_bytes()
    m={"schema":"n5_original_network_heterogeneity_exact_public_export_v1",
       "repository":REPO,"tag":TAG,"assets":rows,"source_snapshots":source,
       "archive_file":tarpath.name,"archive_bytes":len(data),"archive_sha256":digest(data),
       "source_commit":output("git","rev-parse","HEAD").strip(),
       "private_actions_executed":False}
    (DEST/"manifest.json").write_text(json.dumps(m,indent=2)+"\n")
    (DEST/"archive_bytes.b64").write_text(base64.b64encode(data).decode()+"\n")
    print(json.dumps({"assets":len(rows),"archive_size":len(data),"sha256":digest(data)}))
if __name__=="__main__":main()
