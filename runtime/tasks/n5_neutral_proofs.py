"""Registered standalone numerical proof task for the n5-r1 public bundle."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

def run(control:dict, shard:int, output:Path, root:Path)->None:
    if shard!=0 or control.get("revision")!="n5-r1":
        raise RuntimeError("Invalid frozen N5 public proof task")
    subprocess.run([sys.executable,str(root/"runtime/tasks/n5_review_proofs.py"),
                    "--out",str(output)],cwd=root,check=True)
