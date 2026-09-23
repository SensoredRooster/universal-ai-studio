"""Flask blueprint for the social agent UI/API."""
import os
import threading
import uuid
import logging

from flask import Blueprint, jsonify, request, send_file

from . import analytics
from . import database
from .orchestrator import SocialAgent
from telemetry import log_event

database.init_db()

social_bp = Blueprint("social", __name__, url_prefix="/social")
_agent = SocialAgent()
_background_lock = threading.Lock()
_social_jobs = {}


def _set_job_status(job_id, status, result=None, error=None, progress=None, message=None):
    job = _social_jobs.setdefault(job_id, {})
    previous = job.get("status")
    job.update({"status": status, "result": result, "error": error})
    if previous != status:
        log_event("social_job_status", "Social job status changed", job_id=job_id, status=status, error=error or "")
    if progress is not None:
        job["progress"] = max(0, min(100, int(progress)))
    if message is not None:
        job["message"] = message


def _run_agent_async(job_id, topics, post):
    def _process():
        try:
            _set_job_status(job_id, "running", progress=5, message="Researching current trends")
            log_event("social_job_started", "Social generation job started", job_id=job_id, post=post, topic_count=len(topics or []))

            def report(progress, message):
                _set_job_status(job_id, "running", progress=progress, message=message)

            with _background_lock:
                result = _agent.run_once(
                    topics=topics or None,
                    post=post,
                    progress_callback=report,
                )
            _set_job_status(job_id, "ready", result=result, progress=100, message="Complete")
            log_event("social_job_complete", "Social generation job completed", job_id=job_id, post=post)
        except Exception as exc:
            _set_job_status(job_id, "error", error=str(exc), message="Generation failed")
            log_event("social_job_failed", "Social generation job failed", level=logging.ERROR, job_id=job_id, error=str(exc))
    threading.Thread(target=_process, daemon=True).start()


@social_bp.route("/status", methods=["GET"])
def status():
    """Return current agent status, analytics, and recent posts."""
    posts = database.list_posts(limit=20)
    summary = analytics.get_summary()
    return jsonify({"ok": True, "summary": summary, "recent_posts": posts})


@social_bp.route("/trends", methods=["GET"])
def trends():
    """Fetch ranked trends."""
    topics = request.args.getlist("topic")
    try:
        trends = _agent.research(topics or None)
        return jsonify({"trends": trends})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@social_bp.route("/generate", methods=["POST"])
def generate():
    """Generate a video draft without posting (async)."""
    if _background_lock.locked():
        return jsonify({"error": "A social video job is already running. Please wait for it to finish before starting another."}), 409
    payload = request.get_json(silent=True) or {}
    topics = payload.get("topics", [])
    job_id = str(uuid.uuid4())
    _set_job_status(job_id, "pending", progress=0, message="Queued")
    _run_agent_async(job_id, topics, post=False)
    return jsonify({"job_id": job_id, "status": "pending"})


@social_bp.route("/post", methods=["POST"])
def post_now():
    """Generate and immediately post a video to YouTube Shorts (async)."""
    if _background_lock.locked():
        return jsonify({"error": "A social video job is already running. Please wait for it to finish before starting another."}), 409
    payload = request.get_json(silent=True) or {}
    topics = payload.get("topics", [])
    job_id = str(uuid.uuid4())
    _set_job_status(job_id, "pending", progress=0, message="Queued")
    _run_agent_async(job_id, topics, post=True)
    return jsonify({"job_id": job_id, "status": "pending"})


@social_bp.route("/compose", methods=["POST"])
def compose():
    """Render user-uploaded clips into a captioned Short (async)."""
    from . import config
    from . import video_generator

    files = request.files.getlist("clips")
    if not files:
        return jsonify({"error": "No clips uploaded."}), 400
    allowed = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
    job_id = str(uuid.uuid4())
    upload_dir = os.path.join(config.SOCIAL_DIR, "uploads", job_id)
    os.makedirs(upload_dir, exist_ok=True)
    clip_paths = []
    for i, f in enumerate(files):
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in allowed:
            return jsonify({"error": f"Unsupported file type: {ext or 'unknown'}"}), 400
        path = os.path.join(upload_dir, f"clip_{i}{ext}")
        f.save(path)
        clip_paths.append(path)

    title = (request.form.get("title") or "").strip() or "My Short"
    captions = [c.strip() for c in (request.form.get("captions") or "").splitlines() if c.strip()]

    _set_job_status(job_id, "pending", progress=0, message="Queued")

    def _process():
        try:
            _set_job_status(job_id, "running", progress=10, message="Preparing clips")

            def report(progress, message):
                _set_job_status(job_id, "running", progress=progress, message=message)

            video_path = video_generator.compose_user_clips(clip_paths, title, captions, job_id, report)
            result = {"video_path": video_path, "status": "generated"}
            _set_job_status(job_id, "ready", result=result, progress=100, message="Complete")
            log_event("social_compose_complete", "User clip composition completed", job_id=job_id, clip_count=len(clip_paths))
        except Exception as exc:
            _set_job_status(job_id, "error", error=str(exc), message="Render failed")
            log_event("social_compose_failed", "User clip composition failed", level=logging.ERROR, job_id=job_id, error=str(exc))

    threading.Thread(target=_process, daemon=True).start()
    return jsonify({"job_id": job_id, "status": "pending"})


@social_bp.route("/job-status/<job_id>", methods=["GET"])
def job_status(job_id):
    """Poll status of an async social agent job."""
    return jsonify(_social_jobs.get(job_id, {"status": "unknown"}))


@social_bp.route("/videos/<path:filename>", methods=["GET"])
def serve_video(filename):
    from . import config
    safe = os.path.basename(filename)
    return send_file(os.path.join(config.VIDEO_DIR, safe))
