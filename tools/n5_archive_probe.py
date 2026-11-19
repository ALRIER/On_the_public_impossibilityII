"""Read-only inventory of original public-run N3 source ZIP bytes.

Never modifies the original GitHub Release, never simulates.
"""
from __future__ import annotations
import argparse,csv,io,json,hashlib,tarfile,zipfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument("--tar",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    with a.manifest.open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
    chosen=[r for r in rows if str(r.get("name","")).startswith("network_n3_final_confirmation-shard-")]
    if len(chosen)!=8:raise RuntimeError(f"Expected all eight source N3 shards, found {len(chosen)}")
    indexed={r["filename"]:r for r in chosen}
    results=[]
    with tarfile.open(a.tar) as archive:
        for entry in archive:
            if entry.name not in indexed:continue
            data=archive.extractfile(entry).read()
            m=indexed[entry.name]
            if len(data)!=int(m["bytes"]) or hashlib.sha256(data).hexdigest()!=m["sha256"]:
                raise RuntimeError("Original ZIP SHA256 mismatch "+entry.name)
            with zipfile.ZipFile(io.BytesIO(data)) as archive_zip:
                files=[]
                for member in archive_zip.infolist():
                    if member.is_dir():continue
                    record={"name":member.filename,"bytes":member.file_size}
                    if member.filename.endswith(".csv"):
                        with archive_zip.open(member) as h:
                            txt=h.readline().decode("utf-8-sig",errors="replace").strip()
                            record["first_line"]=txt[:1200]
                    elif member.filename.endswith(".json") and member.file_size<15000:
                        with archive_zip.open(member) as h:
                            txt=h.read().decode("utf-8-sig",errors="replace")
                            try:
                                obj=json.loads(txt)
                                record["keys"]=list(obj)[:40] if isinstance(obj,dict) else []
                            except Exception:pass
                    files.append(record)
                results.append({"original_zip_id":m["artifact_id"],
                                "original_zip_sha256":m["sha256"],
                                "original_run":m.get("workflow_run_id"),
                                "files":files})
    if len(results)!=8:raise RuntimeError(f"Expected 8 hashes, found {len(results)}")
    result={"status":"N3_SOURCE_ARCHIVE_8_ZIPS_SHA256_VERIFIED",
            "source_bundle":"raw_bundle_010.tar","shards":results}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],
                      "source_shards":len(results),
                      "file_headers":[x["files"] for x in results[:2]]},indent=2))

if __name__=="__main__":main()
