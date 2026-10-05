"""Deterministic media QA used by The Inspector."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any


def inspect_video_file(
    path: str | Path,
    *,
    expected_aspect: str | None = None,
    min_duration_seconds: float = 0.5,
) -> dict[str, Any]:
    video_path = Path(path)
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})
        if not ok:
            errors.append(f"{name}: {detail}")

    check("file_exists", video_path.is_file(), str(video_path))
    if not video_path.is_file():
        return {
            "approved": False,
            "errors": errors,
            "warnings": warnings,
            "checks": checks,
            "media": {},
        }

    size = video_path.stat().st_size
    check("file_nonempty", size > 0, f"{size} bytes")
    if shutil.which("ffprobe") is None:
        check("ffprobe_available", False, "ffprobe is not on PATH")
        return {
            "approved": False,
            "errors": errors,
            "warnings": warnings,
            "checks": checks,
            "media": {"size_bytes": size},
        }

    cmd = [
        "ffprobe", "-v", "error",
        "-show_streams", "-show_format",
        "-of", "json", str(video_path),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, check=True,
        )
        payload = json.loads(result.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        check("ffprobe_readable", False, str(exc))
        return {
            "approved": False,
            "errors": errors,
            "warnings": warnings,
            "checks": checks,
            "media": {"size_bytes": size},
        }

    check("ffprobe_readable", True, "media metadata loaded")
    streams = payload.get("streams") or []
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    check("video_stream", bool(video_streams), f"{len(video_streams)} video stream(s)")

    media: dict[str, Any] = {
        "size_bytes": size,
        "video_streams": len(video_streams),
        "audio_streams": len(audio_streams),
    }
    if video_streams:
        stream = video_streams[0]
        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
        media.update({
            "width": width,
            "height": height,
            "codec": stream.get("codec_name"),
            "pix_fmt": stream.get("pix_fmt"),
        })
        check("dimensions", width > 0 and height > 0, f"{width}x{height}")
        if expected_aspect == "9:16" and width and height:
            ratio = width / height
            target = 9 / 16
            aspect_ok = abs(ratio - target) <= 0.02
            check("aspect_ratio_9_16", aspect_ok, f"{width}x{height} ratio={ratio:.4f}")

    duration_raw = (payload.get("format") or {}).get("duration")
    try:
        duration = float(duration_raw)
    except (TypeError, ValueError):
        duration = 0.0
    media["duration_seconds"] = duration
    check(
        "duration",
        duration >= min_duration_seconds,
        f"{duration:.2f}s (minimum {min_duration_seconds:.2f}s)",
    )

    if not audio_streams:
        warnings.append("No audio stream detected. This may be intentional, but review before publishing.")

    return {
        "approved": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "media": media,
    }
