"""Flask blueprint for the social agent UI/API."""
import os
import threading
import uuid

from flask import Blueprint, jsonify, request, send_file

from . import analytics
from . import database
from .orchestrator import SocialAgent

database.init_db()

social_bp = Blueprint("social", __name__, url_prefix="/social")
_agent = SocialAgent()
_background_lock = threading.Lock()
_social_jobs = {}


def _set_job_status(job_id, status, result=None, error=None):
    _social_jobs[job_id] = {"status": status, "result": result, "error": error}


def _run_agent_async(job_id, topics, post):
    def _process():
        try:
            _set_job_status(job_id, "running")
            result = _agent.run_once(topics=topics or None, post=post)
            _set_job_status(job_id, "ready", result=result)
        except Exception as exc:
            _set_job_status(job_id, "error", error=str(exc))
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
    payload = request.get_json(silent=True) or {}
    topics = payload.get("topics", [])
    job_id = str(uuid.uuid4())
    _set_job_status(job_id, "pending")
    _run_agent_async(job_id, topics, post=False)
    return jsonify({"job_id": job_id, "status": "pending"})


@social_bp.route("/post", methods=["POST"])
def post_now():
    """Generate and immediately post a video to YouTube Shorts (async)."""
    payload = request.get_json(silent=True) or {}
    topics = payload.get("topics", [])
    job_id = str(uuid.uuid4())
    _set_job_status(job_id, "pending")
    _run_agent_async(job_id, topics, post=True)
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
