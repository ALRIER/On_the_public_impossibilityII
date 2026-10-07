from __future__ import annotations

import argparse
import importlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    control_path = args.control.resolve()
    control = load_json(control_path)
    manifest_path = control_path.parent.parent / "runtime" / "manifest.json"
    manifest = load_json(manifest_path)
    task_id = control.get("task_id")
    spec = manifest.get("tasks", {}).get(task_id)
    if not spec:
        raise SystemExit(f"Unregistered public task: {task_id!r}")
    allowed = spec.get("shards", [])
    if args.shard not in allowed:
        raise SystemExit(f"Shard {args.shard} is not registered for {task_id}")

    module = importlib.import_module(spec["module"])
    if not hasattr(module, "run"):
        raise SystemExit(f"Task adapter has no run(): {spec['module']}")
    output = args.output_root / task_id / f"shard_{args.shard:04d}"
    output.mkdir(parents=True, exist_ok=True)
    module.run(control, args.shard, output, control_path.parent.parent)
    receipt = {
        "schema": "public_task_receipt_v1",
        "task_id": task_id,
        "shard": args.shard,
        "control": str(control_path.relative_to(control_path.parent.parent)),
        "runtime_manifest": str(manifest_path.relative_to(control_path.parent.parent)),
        "public_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=control_path.parent.parent, text=True).strip(),
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (output / "task_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
