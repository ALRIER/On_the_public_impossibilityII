from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


def _digest(rows: list[dict]) -> str:
    clean = [{k: v for k, v in row.items() if k != "PACKAGE_SHA256"} for row in rows]
    payload = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def run(control: dict, shard: int, output: Path, root: Path) -> None:
    package = root / control["package"]
    with package.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError("Public package is empty")
    if any(set(row) - {"TARGET", "VALUE", "LOWER", "UPPER", "N_OBS", "PACKAGE_SHA256"} for row in rows):
        raise RuntimeError("Public package contains fields outside the neutral contract")
    declared = {row.get("PACKAGE_SHA256", "") for row in rows}
    if len(declared) != 1 or next(iter(declared)) != _digest(rows):
        raise RuntimeError("Public package digest mismatch")
    (output / "validation.json").write_text(json.dumps({"package": str(package.relative_to(root)), "rows": len(rows), "package_sha256": next(iter(declared)), "neutral_contract": "PASS"}, indent=2) + "\n", encoding="utf-8")
