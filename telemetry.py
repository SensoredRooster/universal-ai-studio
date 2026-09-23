"""Universal AI Studio local-first telemetry and support bundle helpers."""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import shutil
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO_URL = "https://github.com/SensoredRooster/universal-ai-studio"
ISSUES_URL = REPO_URL + "/issues"

_SECRET_KEY_RE = re.compile(r"(secret|token|password|passwd|api[_-]?key|authorization|cookie|credential)", re.I)
_BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+\-/]+=*")
_QUERY_SECRET_RE = re.compile(r"(?i)([?&](?:code|token|access_token|refresh_token|client_secret|state|password)=)[^&\s]+")
_LONG_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_-]{32,}(?![A-Za-z0-9])")

_state_lock = threading.Lock()
_state: dict[str, Any] = {
    "session_id": None,
    "started_at": None,
    "log_dir": None,
    "heartbeat_stop": None,
    "heartbeat_thread": None,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def redact_text(value: Any) -> str:
    text = str(value)
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    text = _QUERY_SECRET_RE.sub(lambda m: m.group(1) + "[REDACTED]", text)
    text = _LONG_TOKEN_RE.sub("[REDACTED]", text)
    return text


def redact_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if _SECRET_KEY_RE.search(str(key)):
                out[key] = "[REDACTED]"
            else:
                out[key] = redact_mapping(item)
        return out
    if isinstance(value, (list, tuple)):
        return [redact_mapping(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": utc_now(),
            "level": record.levelname,
            "logger": record.name,
            "thread": record.threadName,
            "message": redact_text(record.getMessage()),
            "session_id": _state.get("session_id"),
        }
        extra = getattr(record, "telemetry", None)
        if isinstance(extra, dict):
            payload.update(redact_mapping(extra))
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def default_log_dir() -> Path:
    base = os.getenv("LOCALAPPDATA")
    if base:
        return Path(base) / "UniversalAIStudio" / "logs"
    return ROOT / "workspace" / "logs"


def configure_telemetry(log_dir: Path | None = None) -> Path:
    with _state_lock:
        if _state.get("log_dir"):
            return Path(_state["log_dir"])

        directory = Path(log_dir or default_log_dir())
        directory.mkdir(parents=True, exist_ok=True)
        _state["session_id"] = uuid.uuid4().hex[:12]
        _state["started_at"] = utc_now()
        _state["log_dir"] = str(directory)

        logger = logging.getLogger("uas")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        handler = RotatingFileHandler(directory / "universal-ai-studio.jsonl", maxBytes=10*1024*1024, backupCount=8, encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(JsonLineFormatter())
        logger.addHandler(handler)

        errors = RotatingFileHandler(directory / "errors.jsonl", maxBytes=5*1024*1024, backupCount=5, encoding="utf-8")
        errors.setLevel(logging.ERROR)
        errors.setFormatter(JsonLineFormatter())
        logger.addHandler(errors)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(handler)
        root_logger.addHandler(errors)

        original = sys.excepthook
        def _sys_hook(exc_type, exc_value, exc_tb):
            logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb), extra={"telemetry":{"event":"uncaught_exception"}})
            original(exc_type, exc_value, exc_tb)
        sys.excepthook = _sys_hook

        original_thread = getattr(threading, "excepthook", None)
        if original_thread:
            def _thread_hook(args):
                logger.error("Uncaught thread exception", exc_info=(args.exc_type,args.exc_value,args.exc_traceback), extra={"telemetry":{"event":"uncaught_thread_exception","thread_name":getattr(args.thread,"name","")}})
                original_thread(args)
            threading.excepthook = _thread_hook

        logger.info("Telemetry started", extra={"telemetry":{
            "event":"app_start",
            "python":sys.version.split()[0],
            "platform":platform.platform(),
            "pid":os.getpid(),
        }})
        return directory


def log_event(event: str, message: str, *, level: int = logging.INFO, **fields: Any) -> None:
    configure_telemetry()
    logging.getLogger("uas").log(level, message, extra={"telemetry":{"event":event, **redact_mapping(fields)}})


def start_heartbeat(status_provider=None, interval: float = 1.0) -> None:
    configure_telemetry()
    with _state_lock:
        current = _state.get("heartbeat_thread")
        if current and current.is_alive():
            return
        stop = threading.Event()
        _state["heartbeat_stop"] = stop
        started = time.monotonic()

        def _run():
            while not stop.wait(max(.5, float(interval))):
                fields={"uptime_seconds":round(time.monotonic()-started,3)}
                if status_provider:
                    try:
                        value=status_provider()
                        if isinstance(value,dict):
                            fields.update(redact_mapping(value))
                    except Exception as exc:
                        fields["status_error"]=str(exc)
                log_event("heartbeat","App heartbeat",level=logging.DEBUG,**fields)

        thread=threading.Thread(target=_run,name="uas-telemetry",daemon=True)
        _state["heartbeat_thread"]=thread
        thread.start()


def telemetry_info() -> dict[str, Any]:
    return {
        "session_id": _state.get("session_id"),
        "started_at": _state.get("started_at"),
        "log_dir": str(configure_telemetry()),
    }


def runtime_health(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    workspace=ROOT/"workspace"
    try:
        usage=shutil.disk_usage(workspace if workspace.exists() else ROOT)
        disk={"free_gb":round(usage.free/(1024**3),2),"total_gb":round(usage.total/(1024**3),2)}
    except OSError:
        disk={}
    return {
        "python":sys.version,
        "platform":platform.platform(),
        "machine":platform.machine(),
        "processor":platform.processor(),
        "pid":os.getpid(),
        "workspace":str(workspace),
        "disk":disk,
        **(extra or {}),
    }


def create_support_bundle(extra_status: dict[str, Any] | None = None) -> Path:
    log_dir=configure_telemetry()
    out=log_dir.parent/"support-bundles"
    out.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    sid=str(_state.get("session_id") or "session")
    bundle=out/f"UniversalAIStudio-Support-{stamp}-{sid}.zip"

    env_safe={}
    for key,value in os.environ.items():
        if key.startswith(("OLLAMA_","COMFYUI_","PLANNER_","CAPTION_","SOCIAL_","WAN_","YT_","YOUTUBE_","SUBSCRIPT_","UAS_")):
            env_safe[key]="[REDACTED]" if _SECRET_KEY_RE.search(key) else redact_text(value)

    manifest={
        "created_at":utc_now(),
        "session_id":sid,
        "health":runtime_health(extra_status),
        "environment":env_safe,
        "repository":REPO_URL,
    }
    with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("diagnostics/manifest.json",json.dumps(redact_mapping(manifest),indent=2,default=str))
        zf.writestr("README.txt",
            "Universal AI Studio support bundle\n"
            "Generated locally. Known credentials/tokens are redacted where detectable.\n"
            "Review before sharing if filenames or paths are sensitive.\n"
            f"Repository: {REPO_URL}\nIssues: {ISSUES_URL}\n")
        for path in sorted(log_dir.glob("*.jsonl*")):
            if path.is_file():
                zf.write(path,arcname=f"logs/{path.name}")
        for path in sorted(log_dir.glob("*.log")):
            if path.is_file():
                try:
                    sanitized = "\n".join(redact_text(line) for line in path.read_text(encoding="utf-8", errors="replace").splitlines())
                    zf.writestr(f"logs/{path.name}", sanitized)
                except OSError:
                    pass
    log_event("support_bundle_created","Support bundle created",bundle_name=bundle.name)
    return bundle


def open_in_file_browser(path: Path) -> None:
    path=Path(path)
    if os.name=="nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform=="darwin":
        import subprocess; subprocess.Popen(["open",str(path)])
    else:
        import subprocess; subprocess.Popen(["xdg-open",str(path)])
