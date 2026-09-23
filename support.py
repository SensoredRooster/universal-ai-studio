"""Support center and diagnostics routes for Universal AI Studio."""

from __future__ import annotations

import os
import shutil
import socket
import urllib.request
from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, jsonify, redirect, render_template_string, request, send_file

from telemetry import (
    ISSUES_URL,
    REPO_URL,
    create_support_bundle,
    open_in_file_browser,
    telemetry_info,
)

support_bp = Blueprint("support", __name__, url_prefix="/support")
_DEFAULT_UPLOAD_URL = "https://universal-ai-studio-support.sensoredrooster-com.workers.dev/upload"


def _port_open(host: str, port: int, timeout: float = 0.15) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def health_snapshot() -> dict:
    root = Path(__file__).resolve().parent
    workspace = root / "workspace"
    try:
        disk = shutil.disk_usage(workspace if workspace.exists() else root)
        disk_info = {
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "total_gb": round(disk.total / (1024 ** 3), 2),
        }
    except OSError:
        disk_info = {}
    return {
        "ollama_ready": _port_open("127.0.0.1", 11434),
        "comfyui_ready": _port_open("127.0.0.1", 8188),
        "studio_ready": True,
        "ffmpeg_available": bool(shutil.which("ffmpeg")),
        "disk": disk_info,
        "workspace": str(workspace),
    }


SUPPORT_HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Universal AI Studio — Support</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:linear-gradient(135deg,#111827,#312e81);min-height:100vh;color:#eef5ff}
main{max-width:980px;margin:0 auto;padding:36px 20px}.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.top a{color:#dbeafe;text-decoration:none}
.card{margin-top:20px;padding:24px;border-radius:20px;background:rgba(15,23,42,.94);border:1px solid rgba(148,163,184,.2);box-shadow:0 18px 50px rgba(0,0,0,.25)}
h1{margin:.25rem 0 .5rem;font-size:clamp(1.7rem,4vw,2.5rem)}.lede{color:#cbd5e1;line-height:1.6}.eyebrow{text-transform:uppercase;letter-spacing:.14em;color:#93c5fd;font-size:.75rem;font-weight:800}
.facts,.health{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:18px 0}.fact,.chip{border:1px solid rgba(148,163,184,.2);background:rgba(30,41,59,.7);border-radius:12px;padding:12px}.fact strong{display:block;margin-bottom:5px}.fact code,.fact span{font-size:.8rem;color:#cbd5e1;word-break:break-word}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}.actions a,.actions button{border:0;border-radius:10px;padding:11px 15px;font-weight:800;cursor:pointer;text-decoration:none}.primary{background:#3b82f6;color:white}.secondary{background:#1e293b;color:#e2e8f0;border:1px solid rgba(148,163,184,.25)!important}
.note{border-left:3px solid #60a5fa;padding:12px 14px;background:rgba(59,130,246,.08);border-radius:8px;margin-top:12px;color:#cbd5e1;line-height:1.5}.status{color:#bfdbfe;font-size:.85rem}
@media(max-width:760px){.facts,.health{grid-template-columns:1fr}.actions>*{width:100%;text-align:center}}
</style>
</head>
<body>
<main>
<div class="top"><a href="/">← Back to Studio</a><a href="/support/repository" target="_blank">Main repository ↗</a></div>
<section class="card">
<p class="eyebrow">Support & diagnostics</p>
<h1>One place for tester evidence.</h1>
<p class="lede">Universal AI Studio keeps rotating diagnostics locally while it runs. Export one support bundle when something breaks, or send it directly to your configured support collector.</p>
<div class="facts">
<div class="fact"><strong>Session</strong><code>{{ session_id }}</code></div>
<div class="fact"><strong>Started</strong><span>{{ started_at }}</span></div>
<div class="fact"><strong>Logs</strong><code>{{ log_dir }}</code></div>
</div>
<div class="health" id="support-health"><div class="chip">Checking Ollama…</div><div class="chip">Checking ComfyUI…</div><div class="chip">Checking system…</div></div>
<div class="actions">
<a class="primary" href="/support/bundle">Download Support Bundle</a>
<button class="secondary" id="open-logs">Open Logs Folder</button>
{{ upload_control|safe }}
<a class="secondary" href="/support/report" target="_blank">Report Issue on GitHub</a>
</div>
<p class="status" id="support-status">Nothing is uploaded automatically.</p>
<div class="note"><strong>Privacy:</strong> passwords, tokens, bearer credentials and common OAuth secret values are redacted where detectable. Filenames and local paths may remain because they are useful for diagnosing model, media, and installation problems. Review the ZIP before sharing if those names are sensitive.</div>
</section>
</main>
<script>
const statusEl=document.getElementById('support-status');
fetch('/support/status').then(r=>r.json()).then(d=>{
 const chips=[
  d.ollama_ready?'Ollama ready':'Ollama unavailable',
  d.comfyui_ready?'ComfyUI ready':'ComfyUI unavailable',
  (d.ffmpeg_available?'FFmpeg ready':'FFmpeg missing')+(d.disk&&d.disk.free_gb!==undefined?' · '+d.disk.free_gb+' GB free':'')
 ];
 const box=document.getElementById('support-health'); box.innerHTML='';
 chips.forEach(t=>{const s=document.createElement('div');s.className='chip';s.textContent=t;box.appendChild(s);});
});
document.getElementById('open-logs').onclick=async()=>{
 const r=await fetch('/support/open-logs',{method:'POST'});const d=await r.json();
 statusEl.textContent=r.ok?'Opened telemetry folder.':(d.error||'Could not open logs.');
};
const upload=document.getElementById('send-diagnostics');
if(upload) upload.onclick=async()=>{
 if(!confirm('Send a freshly generated support bundle to the configured Universal AI Studio support collector?')) return;
 upload.disabled=true;upload.textContent='Sending diagnostics…';
 try{const r=await fetch('/support/upload',{method:'POST'});const d=await r.json();statusEl.textContent=r.ok?(d.message||'Diagnostics sent.'):(d.error||'Upload failed.');}
 finally{upload.disabled=false;upload.textContent='Send Diagnostics to Developer';}
};
</script>
</body>
</html>
"""


@support_bp.get("")
def support_home():
    info = telemetry_info()
    upload_url = (os.getenv("UAS_SUPPORT_UPLOAD_URL", "").strip() or _DEFAULT_UPLOAD_URL)
    upload_control = (
        '<button class="secondary" id="send-diagnostics">Send Diagnostics to Developer</button>'
        if upload_url else
        '<span class="status">Remote diagnostics upload is not configured on this build.</span>'
    )
    return render_template_string(SUPPORT_HTML, **info, upload_control=upload_control)


@support_bp.get("/status")
def support_status():
    return jsonify({**telemetry_info(), **health_snapshot()})


@support_bp.get("/bundle")
def support_bundle():
    bundle = create_support_bundle(health_snapshot())
    return send_file(bundle, as_attachment=True, download_name=bundle.name, mimetype="application/zip")


@support_bp.post("/open-logs")
def open_logs():
    path = Path(telemetry_info()["log_dir"])
    try:
        open_in_file_browser(path)
        return jsonify({"ok": True, "folder": str(path)})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@support_bp.get("/repository")
def repository():
    return redirect(REPO_URL, code=302)


@support_bp.get("/report")
def report_issue():
    info = telemetry_info()
    body = (
        "## What happened?\n\n"
        "Describe what you were doing and what you expected.\n\n"
        "## What actually happened?\n\n"
        "Describe the failure.\n\n"
        "## Diagnostics\n"
        f"- Universal AI Studio session: {info.get('session_id')}\n"
        f"- Started: {info.get('started_at')}\n\n"
        "Please attach the Support Bundle from Universal AI Studio > Support.\n"
    )
    return redirect(ISSUES_URL + "/new?title=" + quote("Tester report: ") + "&body=" + quote(body), code=302)


@support_bp.post("/upload")
def upload_bundle():
    upload_url = (os.getenv("UAS_SUPPORT_UPLOAD_URL", "").strip() or _DEFAULT_UPLOAD_URL)
    if not upload_url:
        return jsonify({"error": "Remote diagnostics upload is not configured."}), 409
    bundle = create_support_bundle(health_snapshot())
    headers = {
        "Content-Type": "application/zip",
        "X-UAS-Session": str(telemetry_info().get("session_id") or ""),
        "X-UAS-Filename": bundle.name,
    }
    token = os.getenv("UAS_SUPPORT_UPLOAD_TOKEN", "").strip()
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(upload_url, data=bundle.read_bytes(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if not 200 <= getattr(response, "status", 200) < 300:
                raise RuntimeError(f"Support server returned HTTP {response.status}.")
        return jsonify({"ok": True, "message": "Diagnostics sent to developer.", "filename": bundle.name})
    except Exception as exc:
        return jsonify({"error": f"Could not send diagnostics: {exc}"}), 502
