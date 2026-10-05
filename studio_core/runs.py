"""Persistent production runs, artifacts, checkpoints, and event history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "workspace" / "runs"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _safe_id(value: str) -> str:
    safe = "".join(ch for ch in value if ch.isalnum() or ch in "-_")
    if not safe:
        raise ValueError("run_id is invalid")
    return safe


@dataclass
class ProductionRun:
    run_id: str
    root: Path

    @classmethod
    def create(
        cls,
        pipeline_id: str,
        *,
        run_id: str | None = None,
        request: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ProductionRun":
        run_id = _safe_id(run_id or str(uuid.uuid4()))
        root = RUNS_DIR / run_id
        root.mkdir(parents=True, exist_ok=True)
        (root / "artifacts").mkdir(exist_ok=True)
        instance = cls(run_id=run_id, root=root)
        if not instance.state_path.exists():
            instance._write_state(
                {
                    "run_id": run_id,
                    "pipeline_id": pipeline_id,
                    "status": "created",
                    "current_stage": None,
                    "created_at": _utc_now(),
                    "updated_at": _utc_now(),
                    "request": request,
                    "metadata": metadata or {},
                    "stages": {},
                    "artifacts": {},
                    "last_error": None,
                }
            )
            instance.emit("run_created", pipeline_id=pipeline_id)
        return instance

    @classmethod
    def open(cls, run_id: str) -> "ProductionRun":
        safe = _safe_id(run_id)
        root = RUNS_DIR / safe
        if not (root / "run.json").is_file():
            raise FileNotFoundError(f"Unknown production run: {safe}")
        return cls(run_id=safe, root=root)

    @property
    def state_path(self) -> Path:
        return self.root / "run.json"

    @property
    def events_path(self) -> Path:
        return self.root / "events.jsonl"

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

    def state(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: dict[str, Any]) -> None:
        state["updated_at"] = _utc_now()
        temp = self.state_path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        temp.replace(self.state_path)

    def emit(self, event: str, **fields: Any) -> None:
        payload = {"ts": _utc_now(), "event": event, "run_id": self.run_id, **fields}
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str) + "\n")

    def start_stage(self, stage: str) -> None:
        state = self.state()
        record = state["stages"].setdefault(stage, {})
        record.update({"status": "running", "started_at": _utc_now(), "error": None})
        state["status"] = "running"
        state["current_stage"] = stage
        state["last_error"] = None
        self._write_state(state)
        self.emit("stage_started", stage=stage)

    def complete_stage(self, stage: str, **details: Any) -> None:
        state = self.state()
        record = state["stages"].setdefault(stage, {})
        record.update({"status": "complete", "completed_at": _utc_now(), "error": None, **details})
        state["current_stage"] = None
        self._write_state(state)
        self.emit("stage_completed", stage=stage, **details)

    def fail_stage(self, stage: str, error: str) -> None:
        state = self.state()
        record = state["stages"].setdefault(stage, {})
        record.update({"status": "failed", "failed_at": _utc_now(), "error": error})
        state["status"] = "failed"
        state["current_stage"] = stage
        state["last_error"] = error
        self._write_state(state)
        self.emit("stage_failed", stage=stage, error=error)

    def mark_complete(self) -> None:
        state = self.state()
        state["status"] = "complete"
        state["current_stage"] = None
        state["last_error"] = None
        state["completed_at"] = _utc_now()
        self._write_state(state)
        self.emit("run_completed")

    def stage_complete(self, stage: str) -> bool:
        return self.state().get("stages", {}).get(stage, {}).get("status") == "complete"

    def save_artifact(self, name: str, value: Any) -> Path:
        safe = _safe_id(name)
        path = self.artifacts_dir / f"{safe}.json"
        path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")
        state = self.state()
        state["artifacts"][safe] = {
            "path": str(path.relative_to(self.root)),
            "updated_at": _utc_now(),
        }
        self._write_state(state)
        self.emit("artifact_saved", artifact=safe, path=str(path))
        return path

    def load_artifact(self, name: str) -> Any:
        safe = _safe_id(name)
        path = self.artifacts_dir / f"{safe}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Artifact not found: {safe}")
        return json.loads(path.read_text(encoding="utf-8"))

    def artifact_exists(self, name: str) -> bool:
        safe = _safe_id(name)
        return (self.artifacts_dir / f"{safe}.json").is_file()

    def snapshot(self) -> dict[str, Any]:
        state = self.state()
        state["run_dir"] = str(self.root)
        state["resumable"] = state.get("status") in {"created", "running", "failed"}
        return state


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    if not RUNS_DIR.exists():
        return []
    runs: list[dict[str, Any]] = []
    for state_path in RUNS_DIR.glob("*/run.json"):
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            data["run_dir"] = str(state_path.parent)
            runs.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    runs.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return runs[: max(1, min(int(limit), 200))]
