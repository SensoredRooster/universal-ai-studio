"""Optional Universal AI Studio tester diagnostics collector.

Run this only on infrastructure you control.

Environment:
  UAS_SUPPORT_COLLECTOR_TOKEN=<long-random-secret>
  UAS_SUPPORT_INBOX=/path/to/support-inbox
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
MAX_BUNDLE_BYTES = 75 * 1024 * 1024
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _token() -> str:
    value = os.getenv("UAS_SUPPORT_COLLECTOR_TOKEN", "").strip()
    if not value:
        raise RuntimeError("UAS_SUPPORT_COLLECTOR_TOKEN is required.")
    return value


def _inbox() -> Path:
    path = Path(os.getenv("UAS_SUPPORT_INBOX", "support-inbox")).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _authorized() -> bool:
    return request.headers.get("Authorization", "") == "Bearer " + _token()


def _safe_name(value: str, fallback: str) -> str:
    clean = _SAFE.sub("-", (value or "").strip()).strip(".-")
    return clean[:140] or fallback


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "uas-support-collector"})


@app.post("/upload")
def upload():
    if not _authorized():
        return jsonify({"error": "Unauthorized"}), 401
    if request.content_length and request.content_length > MAX_BUNDLE_BYTES:
        return jsonify({"error": "Bundle too large"}), 413
    data = request.get_data(cache=False)
    if not data:
        return jsonify({"error": "Empty bundle"}), 400
    if len(data) > MAX_BUNDLE_BYTES:
        return jsonify({"error": "Bundle too large"}), 413
    if not data.startswith(b"PK"):
        return jsonify({"error": "Expected a ZIP support bundle"}), 415

    session = _safe_name(request.headers.get("X-UAS-Session", ""), "unknown-session")
    original = _safe_name(request.headers.get("X-UAS-Filename", ""), "UniversalAIStudio-Support.zip")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"{stamp}-{session}-{original}"
    path = _inbox() / name
    path.write_bytes(data)

    metadata = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session,
        "bundle": name,
        "size_bytes": len(data),
        "client": request.remote_addr,
    }
    path.with_suffix(path.suffix + ".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return jsonify({"ok": True, "bundle": name, "session_id": session})


@app.get("/bundles")
def list_bundles():
    if not _authorized():
        return jsonify({"error": "Unauthorized"}), 401
    items = []
    for path in sorted(_inbox().glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
        meta_path = path.with_suffix(path.suffix + ".json")
        meta = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        items.append({"name": path.name, "size_bytes": path.stat().st_size, **meta})
    return jsonify({"bundles": items})


@app.get("/bundles/<path:name>")
def download_bundle(name):
    if not _authorized():
        return jsonify({"error": "Unauthorized"}), 401
    safe = _safe_name(name, "")
    if safe != name or not safe.endswith(".zip"):
        return jsonify({"error": "Invalid bundle name"}), 400
    path = _inbox() / safe
    if not path.is_file():
        return jsonify({"error": "Not found"}), 404
    return send_file(path, as_attachment=True, download_name=path.name, mimetype="application/zip")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8791)
