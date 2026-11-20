"""Encode ORIGINAL public N5 release byte assets as reversible text chunks.

An intermediary public-only byte export used for direct GitHub API private
backup (not private GitHub Actions). Asset SHA256 is checked before packaging.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import tarfile
from pathlib import Path

REPO="ALRIER/On_the_public_impossibilityII"
TAGS=[
 "n5-public-q1-four-arm-pilot-44745711109-a1",
 "n5-public-q2-batch-r1-44745247621-a1",
 "n5-public-q3-batch-r1-44745247621-a1",
 "n5-public-q4-batch-r1-44745247621-a1",
 "n5-public-ml-guided-pilot-44748984557-a1",
 "n5-public-q1-tuning-44749701109-a1",
 "n5-public-q2-tuning-44749701109-a1",
]
TASKS=[
 "runtime/tasks/n5_q1_four_arm_pilot.py",
 "runtime/tasks/n5_q2_batch.py",
 "runtime/tasks/n5_q3_batch.py",
 "runtime/tasks/n5_q4_batch.py",
 "runtime/tasks/n5_ml_guided_pilot.py",
 "runtime/tasks/n5_q1_mechanism_exposure.py",
 "runtime/tasks/n5_q2_local_tuning.py",
 ".github/workflows/n5-q1-four-arm-pilot.yml",
 ".github/workflows/n5-q2-q3-q4-batch.yml",
 ".github/workflows/n5-ml-guided-pilot.yml",
 ".github/workflows/n5-mechanism-and-network-tuning.yml",
]
PART_BYTES=384*1024


def run(*parts):
    return subprocess.run(parts,check=True,capture_output=True,text=True).stdout


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    folder=Path("n5_original_bytes")
    exported=Path("n5_evidence_byte_export")
    folder.mkdir(exist_ok=True)
    exported.mkdir(exist_ok=True)
    manifests=[]
    for tag in TAGS:
        target=folder/tag
        target.mkdir(parents=True,exist_ok=True)
        run("gh","release","download",tag,"--repo",REPO,"--dir",str(target))
        response=run("gh","api","repos/"+REPO+"/releases/tags/"+tag)
        metadata=json.loads(response)
        files=[]
        for asset in metadata["assets"]:
            path=target/asset["name"]
            content=path.read_bytes()
            actual=sha(content)
            expected=asset["digest"]
            if not expected or actual!="".join(expected.split(":")[1:]):
                raise RuntimeError("Original public asset SHA256 mismatch: "+tag+"/"+asset["name"])
            if len(content)!=asset["size"]:
                raise RuntimeError("Original public asset size mismatch")
            files.append({"name":asset["name"],"bytes":len(content),
                          "sha256":actual,"release_asset_id":asset["id"]})
        if len(files)!=len(list(target.iterdir())):
            raise RuntimeError("Original release asset collection incomplete")
        manifests.append({"tag":tag,"public_url":metadata["html_url"],"assets":files})
    for item in TASKS:
        if not Path(item).is_file():
            raise RuntimeError("Original public analysis code source missing: "+item)
    source_sha={item:sha(Path(item).read_bytes()) for item in TASKS}
    meta={
        "schema":"n5_public_exact_release_asset_byte_export_r1",
        "original_public_repository":REPO,
        "releases":manifests,
        "original_public_analysis_source_sha256":source_sha,
        "all_original_release_assets_sha256_checked":True,
        "all_original_release_asset_sizes_checked":True,
        "negative_or_inconclusive_evidence_included":True,
        "private_gitHub_actions_triggered":False,
        "total_release_assets":sum(len(x["assets"]) for x in manifests),
        "total_original_release_asset_bytes":sum(
            a["bytes"] for x in manifests for a in x["assets"])
    }
    (folder/"source_provenance.json").write_text(
        json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    archive=exported/"original_n5_release_assets_and_scripts.tar.gz"
    with tarfile.open(archive,"w:gz",format=tarfile.PAX_FORMAT) as tar:
        for p in sorted(folder.rglob("*")):
            if not p.is_file():continue
            info=tar.gettarinfo(str(p),arcname=str(p))
            info.uid=0;info.gid=0;info.uname="";info.gname="";info.mtime=0
            with p.open("rb") as fh:tar.addfile(info,fh)
        for pstr in TASKS:
            p=Path(pstr)
            info=tar.gettarinfo(str(p),arcname="public_source_snapshot/"+pstr)
            info.uid=0;info.gid=0;info.uname="";info.gname="";info.mtime=0
            with p.open("rb") as fh:tar.addfile(info,fh)
    contents=archive.read_bytes()
    parts=[]
    for offset in range(0,len(contents),PART_BYTES):
        sample=contents[offset:offset+PART_BYTES]
        name="part_"+str(len(parts)).zfill(3)+".b64"
        # A UTF-8, base64-encoded text chunk; decoded private GitHub Git blob
        # preserves the original binary bytes without using private Actions.
        (exported/name).write_text(base64.b64encode(sample).decode("ascii"),
                                   encoding="ascii")
        parts.append({"name":name,"size_bytes":len(sample),
                      "part_sha256":sha(sample)})
    archive.unlink()  # never store the large binary on a source branch
    export_manifest={
        **meta,
        "original_archive_sha256":sha(contents),
        "original_archive_size_bytes":len(contents),
        "original_archive_filename":
            "original_n5_release_assets_and_scripts.tar.gz",
        "encoded_part_bytes":PART_BYTES,
        "decoded_parts":parts,
        "private_backup_requires_byte_copy":True,
        "private_backup_verified_at_public_export_time":False
    }
    (exported/"manifest.json").write_text(
        json.dumps(export_manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":"ORIGINAL_PUBLIC_ASSETS_HASH_VERIFIED_AND_EXPORTED",
        "release_count":len(TAGS),
        "asset_count":meta["total_release_assets"],
        "original_asset_bytes":meta["total_original_release_asset_bytes"],
        "compressed_archive_bytes":len(contents),
        "binary_chunks":len(parts),
        "original_archive_sha256":sha(contents)
    },indent=2))


if __name__=="__main__":main()
