"""Simple analytics / monitoring for posted videos.

In a full deployment this would call the YouTube Analytics API.
For now it records metadata at post time and computes basic engagement
scores when metrics are provided manually or via a future API integration.
"""
import datetime
import json

from . import database


def record_metrics(video_id: str, views: int = 0, likes: int = 0, comments: int = 0):
    """Store or update performance metrics for a posted video."""
    with database._connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics (
                video_id TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                score REAL DEFAULT 0.0
            )
            """
        )
        score = _engagement_score(views, likes, comments)
        conn.execute(
            """
            INSERT INTO analytics (video_id, updated_at, views, likes, comments, score)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                updated_at=excluded.updated_at,
                views=excluded.views,
                likes=excluded.likes,
                comments=excluded.comments,
                score=excluded.score
            """,
            (video_id, datetime.datetime.now().isoformat(), views, likes, comments, score),
        )


def _engagement_score(views: int, likes: int, comments: int) -> float:
    """Compute a simple engagement score for ranking past performance."""
    if views <= 0:
        return 0.0
    return round((likes * 2 + comments * 4) / views * 100, 2)


def top_performers(limit: int = 10) -> list[dict]:
    """Return best-performing posts by engagement score."""
    with database._connect() as conn:
        rows = conn.execute(
            """
            SELECT p.title, p.youtube_video_id, a.views, a.likes, a.comments, a.score
            FROM posts p
            LEFT JOIN analytics a ON p.youtube_video_id = a.video_id
            WHERE p.status = 'posted'
            ORDER BY COALESCE(a.score, 0) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_summary() -> dict:
    """Return high-level stats for the dashboard."""
    with database._connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        posted = conn.execute("SELECT COUNT(*) FROM posts WHERE status = 'posted'").fetchone()[0]
        errors = conn.execute("SELECT COUNT(*) FROM posts WHERE status = 'error'").fetchone()[0]
        scheduled = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE status = 'scheduled'"
        ).fetchone()[0]
    return {
        "total_posts": total,
        "posted": posted,
        "scheduled": scheduled,
        "errors": errors,
        "top_performers": top_performers(5),
    }
