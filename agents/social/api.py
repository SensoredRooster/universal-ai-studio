"""Flask blueprint for the social agent UI/API."""
import os
import threading

from flask import Blueprint, jsonify, request, send_file

from . import analytics
from . import database
from .orchestrator import SocialAgent

social_bp = Blueprint("social", __name__, url_prefix="/social")
_agent = SocialAgent()
_background_lock = threading.Lock()


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
    """Generate a video draft without posting."""
    payload = request.get_json(silent=True) or {}
    topics = payload.get("topics", [])
    try:
        result = _agent.run_once(topics=topics or None, post=False)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@social_bp.route("/post", methods=["POST"])
def post_now():
    """Generate and immediately post a video to YouTube Shorts."""
    payload = request.get_json(silent=True) or {}
    topics = payload.get("topics", [])
    try:
        result = _agent.run_once(topics=topics or None, post=True)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@social_bp.route("/videos/<path:filename>", methods=["GET"])
def serve_video(filename):
    from . import config
    safe = os.path.basename(filename)
    return send_file(os.path.join(config.VIDEO_DIR, safe))
