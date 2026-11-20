"""N5 ML-ABM public GitHub release exact-byte export, no private repo access."""
import base64,hashlib,json,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"staging/n5_ml_abm_discovery_20261120"
TAG="n5-public-ml-abm-discovery-44771571783-a1"
REPO="ALRIER/On_the_public_impossibilityII"
SCRIPTS=["runtime/tasks/n5_ml_abm_discovery_wave.py",
         ".github/workflows/n5-ml-abm-discovery-wave.yml",
         "runtime/tasks/n5_clearing_engine.py",
         "runtime/tasks/n5_review_proofs.py"]
def run(*args):return subprocess.check_output(args,text=True)
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
  DEST.mkdir(parents=True,exist_ok=True)
  location=DEST/"original";location.mkdir(exist_ok=True)
  m=json.loads(run("gh","api",f"repos/{REPO}/releases/tags/{TAG}"))
  run("gh","release","download",TAG,"--repo",REPO,"--dir",str(location))
  sources=[];files=[];assets=[]
  for a in sorted(m["assets"],key=lambda v:v["name"]):
    p=location/a["name"];b=p.read_bytes()
    assert len(b)==a["size"] and "sha256:"+sha(b)==a["digest"]
    assets.append({"name":a["name"],"size":len(b),"sha256":sha(b)})
    files.append((p,"original_assets/"+a["name"]))
  for rel in SCRIPTS:
    p=ROOT/rel;digest=sha(p.read_bytes())
    sources.append({"path":rel,"sha256":digest})
    files.append((p,"source_snapshot/"+rel))
  archive=DEST/"n5_ml_abm_original_release_and_source.tar.gz"
  with tarfile.open(archive,"w:gz") as t:
    for p,name in files:t.add(p,arcname=name,recursive=False)
  b=archive.read_bytes()
  manifest={"schema":"n5_ml_abm_original_release_exact_bytes_v1",
     "original_tag":TAG,"public_repo":REPO,"original_assets":assets,
     "source_snapshots":sources,"archive_file":archive.name,
     "archive_bytes":len(b),"archive_sha256":sha(b),
     "source_commit":run("git","rev-parse","HEAD").strip(),
     "no_private_actions":True}
  (DEST/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
  (DEST/"archive_bytes.b64").write_text(base64.b64encode(b).decode()+"\n")
  print(json.dumps({"original_asset_count":len(assets),"archive_bytes":len(b),
                    "sha256":sha(b)}))
if __name__=="__main__":main()
