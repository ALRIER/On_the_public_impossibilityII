"""Archive exact bytes of three immutable original N5 public releases.

Public-only source export; private copy is performed separately by a user-
authorized Git connector. No private checkout, token or private Actions.
"""
from __future__ import annotations
import base64,hashlib,json,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"staging"/"n5_stage1_20261120"
REPO="ALRIER/On_the_public_impossibilityII"
TAGS=(
    "n5-public-stage1-mechanism-gate-44756238527-a1",
    "n5-public-forward-coverage-44758150356-a1",
    "n5-public-delivery-channel-44758591721-a1",
)
SOURCES=[
    "tools/n5_stage1_mechanism_gate.py",
    "runtime/tasks/n5_clearing_engine.py",
    "runtime/tasks/n5_forward_coverage_pilot.py",
    "runtime/tasks/n5_delivery_channel_pilot.py",
    "tools/n5_verified_diagnostic_report.py",
    ".github/workflows/n5-stage1-mechanism-gate.yml",
    ".github/workflows/n5-forward-coverage-pilot.yml",
    ".github/workflows/n5-delivery-channel-pilot.yml",
]
def call(*argv):return subprocess.check_output(argv,text=True)
def checksum(data):return hashlib.sha256(data).hexdigest()
def main():
    DEST.mkdir(parents=True,exist_ok=True)
    cache=DEST/"original";cache.mkdir(exist_ok=True)
    manifest={"schema":"n5_stage1_three_release_exact_bytes_v1",
              "source_repository":REPO,"releases":[],
              "source_scripts":{},
              "source_code_commit":call("git","rev-parse","HEAD").strip(),
              "no_private_actions_invoked":True}
    files=[]
    for tag in TAGS:
        meta=json.loads(call("gh","api",f"repos/{REPO}/releases/tags/{tag}"))
        target=cache/tag
        target.mkdir(exist_ok=True)
        call("gh","release","download",tag,"--repo",REPO,"--dir",str(target))
        release={"tag":tag,"assets":[]}
        for record in sorted(meta["assets"],key=lambda x:x["name"]):
            name=record["name"]
            data=(target/name).read_bytes()
            sha=checksum(data)
            expected=record.get("digest")
            assert expected and expected=="sha256:"+sha,tag+"/"+name+" SHA mismatch"
            assert len(data)==record["size"]
            files.append((target/name, "n5_original_releases/"+tag+"/"+name))
            release["assets"].append({"name":name,"bytes":len(data),"sha256":sha})
        manifest["releases"].append(release)
    for relative in SOURCES:
        path=ROOT/relative
        data=path.read_bytes()
        manifest["source_scripts"][relative]=checksum(data)
        files.append((path,"n5_public_source_snapshot/"+relative))
    archive=DEST/"n5_three_original_releases_and_source.tar.gz"
    with tarfile.open(archive,"w:gz") as tar:
        for source,name in files:
            tar.add(source,arcname=name,recursive=False)
    archive_data=archive.read_bytes()
    manifest["archive_filename"]=archive.name
    manifest["archive_bytes"]=len(archive_data)
    manifest["archive_sha256"]=checksum(archive_data)
    manifest["asset_count"]=sum(len(r["assets"]) for r in manifest["releases"])
    manifest["original_asset_bytes"]=sum(a["bytes"] for r in manifest["releases"] for a in r["assets"])
    (DEST/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (DEST/"archive_bytes.b64").write_text(base64.b64encode(archive_data).decode("ascii")+"\n")
    print(json.dumps({"source_releases":len(TAGS),"assets":manifest["asset_count"],
                      "raw_asset_bytes":manifest["original_asset_bytes"],
                      "archive_bytes":manifest["archive_bytes"],
                      "archive_sha256":manifest["archive_sha256"]},indent=2))
if __name__=="__main__":main()
