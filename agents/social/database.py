"""Lightweight SQLite persistence for the social agent."""
import datetime
import json
import os
import sqlite3
import uuid

from . import config


def _connect():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                scheduled_for TEXT,
                posted_at TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                platform TEXT NOT NULL DEFAULT 'youtube',
                video_path TEXT,
                title TEXT,
                description TEXT,
                tags TEXT,
                plan_json TEXT,
                youtube_video_id TEXT,
                error_message TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status)"
        )


def create_post(
    plan: dict,
    video_path: str,
    scheduled_for: datetime.datetime | None = None,
) -> str:
    post_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO posts (id, created_at, scheduled_for, status, platform, video_path,
                               title, description, tags, plan_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post_id,
                datetime.datetime.now().isoformat(),
                scheduled_for.isoformat() if scheduled_for else None,
                "scheduled" if scheduled_for else "pending",
                "youtube",
                video_path,
                plan.get("short_title", ""),
                plan.get("description", ""),
                json.dumps(plan.get("hashtags", [])),
                json.dumps(plan),
            ),
        )
    return post_id


def mark_posted(post_id: str, youtube_video_id: str):
    with _connect() as conn:
        conn.execute(
            "UPDATE posts SET status = 'posted', posted_at = ?, youtube_video_id = ? WHERE id = ?",
            (datetime.datetime.now().isoformat(), youtube_video_id, post_id),
        )


def mark_error(post_id: str, error: str):
    with _connect() as conn:
        conn.execute(
            "UPDATE posts SET status = 'error', error_message = ? WHERE id = ?",
            (str(error), post_id),
        )


def list_posts(limit: int = 50):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM posts ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]
