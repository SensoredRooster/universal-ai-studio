"""Local bridge from Universal AI Studio production runs to SubScript."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .runs import ProductionRun


CONTRACT = "open-production-job"
CONTRACT_VERSION = "1.0"
DEFAULT_SUBSCRIPT_URL = os.getenv("SUBSCRIPT_URL", "http://127.0.0.1:8787").rstrip("/")


def _validated_local_base(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("SubScript bridge URL must use http or https.")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("SubScript bridge is local-only by default.")
    return url.rstrip("/")


def build_subscript_job(
    run: ProductionRun,
    *,
    source_path: str,
    start_seconds: float | None = None,
    duration_seconds: float | None = None,
    auto_highlight: bool = False,
) -> dict[str, Any]:
    source = Path(source_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"Source video not found: {source}")

    state = run.state()
    request_text = state.get("request") or ""
    return {
        "contract": CONTRACT,
        "version": CONTRACT_VERSION,
        "job_id": run.run_id,
        "origin": "universal-ai-studio",
        "intent": "highlight" if auto_highlight else "clip",
        "source": {"path": str(source.resolve()), "kind": "video"},
        "edit": {
            "start_seconds": start_seconds,
            "duration_seconds": duration_seconds,
            "auto_highlight": bool(auto_highlight),
        },
        "delivery": {
            "review_required": True,
            "formats": ["16:9", "9:16"],
        },
        "metadata": {
            "request": request_text,
            "parent_pipeline": state.get("pipeline_id"),
            "uas_run_id": run.run_id,
        },
    }


def submit_to_subscript(
    run: ProductionRun,
    job: dict[str, Any],
    *,
    base_url: str = DEFAULT_SUBSCRIPT_URL,
    timeout: float = 10.0,
) -> dict[str, Any]:
    base = _validated_local_base(base_url)
    response = requests.post(f"{base}/api/production-jobs", json=job, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    status_url = payload.get("status_url") or f"/api/production-jobs/{run.run_id}"
    if status_url.startswith("/"):
        status_url = base + status_url
    run.save_artifact("subscript_job", job)
    run.update_metadata(
        subscript_base_url=base,
        subscript_status_url=status_url,
        subscript_review_url=payload.get("review_url"),
    )
    return payload


def sync_subscript_run(
    run: ProductionRun,
    *,
    timeout: float = 5.0,
) -> dict[str, Any] | None:
    state = run.state()
    url = (state.get("metadata") or {}).get("subscript_status_url")
    if not url:
        return None
    _validated_local_base(url.rsplit("/api/", 1)[0])
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    snapshot = response.json()
    run.mirror_external("subscript", snapshot)
    return snapshot
