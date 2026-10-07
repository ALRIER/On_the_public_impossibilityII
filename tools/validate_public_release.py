from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {".md", ".json", ".py", ".yml", ".yaml", ".csv", ".txt"}
FORBIDDEN = (
    "PRIVATE_REPO_TOKEN",
    "On_the_Impossibility_of_Central_Planning",
    "worldbank.org",
    "World Bank",
    "Colombia",
    "PAT007_",
    "PAT008_",
    "PAT009_",
    "P2_",
)


def main() -> int:
    errors = []
    workflow = ROOT / ".github/workflows/compute-bridge-public.yml"
    text = workflow.read_text(encoding="utf-8")
    if "PRIVATE_REPO_TOKEN" in text or "On_the_Impossibility_of_Central_Planning" in text:
        errors.append("independent workflow references private runtime or credentials")
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path == Path(__file__):
            continue
        if path.name == "compute-bridge-holdout-legacy.yml":
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for term in FORBIDDEN:
            if term in content:
                errors.append(f"forbidden semantic/private term {term!r} in {path.relative_to(ROOT)}")
    manifest = json.loads((ROOT / "runtime/manifest.json").read_text(encoding="utf-8"))
    if not manifest.get("tasks"):
        errors.append("runtime manifest has no registered task")
    if errors:
        raise SystemExit("Public release validation failed:\n- " + "\n- ".join(errors))
    print("Public release boundary: PASS")


if __name__ == "__main__":
    main()
