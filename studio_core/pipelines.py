"""Declarative production-pipeline loading for Universal AI Studio."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIR = ROOT / "pipeline_defs"


def load_pipeline_manifest(name: str) -> dict[str, Any]:
    safe_name = Path(name).stem
    path = PIPELINE_DIR / f"{safe_name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown pipeline: {safe_name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("id") != safe_name:
        raise ValueError(f"Pipeline id mismatch in {path.name}")
    if not isinstance(data.get("stages"), list) or not data["stages"]:
        raise ValueError(f"Pipeline {safe_name} has no stages")
    return data


def load_pipeline_catalog() -> list[dict[str, Any]]:
    if not PIPELINE_DIR.exists():
        return []
    catalog: list[dict[str, Any]] = []
    for path in sorted(PIPELINE_DIR.glob("*.json")):
        data = load_pipeline_manifest(path.stem)
        catalog.append(
            {
                "id": data["id"],
                "name": data.get("name", data["id"]),
                "description": data.get("description", ""),
                "required_capabilities": data.get("required_capabilities", []),
                "optional_capabilities": data.get("optional_capabilities", []),
                "stage_count": len(data["stages"]),
            }
        )
    return catalog
