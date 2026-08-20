"""Main orchestrator for the social media agent."""
import datetime
import os
import uuid

from . import config
from . import content_planner
from . import database
from . import scheduler
from . import trend_fetcher
from . import video_generator
from . import youtube_uploader


class SocialAgent:
    """End-to-end agent: research -> plan -> generate -> schedule/post."""

    def __init__(self):
        database.init_db()
        os.makedirs(config.SOCIAL_DIR, exist_ok=True)
        os.makedirs(config.FRAME_DIR, exist_ok=True)
        os.makedirs(config.VIDEO_DIR, exist_ok=True)
        os.makedirs(config.LOG_DIR, exist_ok=True)

    def research(self, topics: list[str] | None = None) -> list[dict]:
        """Fetch and rank trending topics."""
        trends = trend_fetcher.fetch_trends(topics)
        return content_planner.pick_trend(trends, count=config.POSTS_PER_DAY)

    def plan(self, trend: dict) -> dict:
        """Generate a full video plan from a trend."""
        return content_planner.generate_video_plan(trend)

    def create_video(self, plan: dict, run_id: str | None = None) -> str:
        """Generate frames and compose a vertical video."""
        run_id = run_id or str(uuid.uuid4())
        return video_generator.generate_video(plan, run_id)

    def schedule_post(self, plan: dict, video_path: str, when: datetime.datetime | None = None) -> str:
        """Persist a post and optionally schedule it for a future time."""
        if when is None:
            slots = scheduler.next_post_times(count=1)
            when = slots[0]
        return database.create_post(plan, video_path, scheduled_for=when)

    def post_now(self, plan: dict, video_path: str) -> dict:
        """Upload immediately to YouTube Shorts."""
        post_id = database.create_post(plan, video_path)
        title = plan.get("short_title", "Short")
        description = content_planner.generate_caption(plan)
        tags = [t.lstrip("#") for t in plan.get("hashtags", [])]
        try:
            result = youtube_uploader.upload_short(video_path, title, description, tags)
            video_id = result.get("id")
            database.mark_posted(post_id, video_id)
            return {"post_id": post_id, "video_id": video_id, "status": "posted"}
        except Exception as exc:
            database.mark_error(post_id, str(exc))
            raise

    def run_once(self, topics: list[str] | None = None, post: bool = False) -> dict:
        """Research, plan, generate, and optionally post one Short."""
        trends = self.research(topics)
        if not trends:
            raise RuntimeError("No trends found.")
        plan = self.plan(trends[0])
        run_id = str(uuid.uuid4())
        video_path = self.create_video(plan, run_id)
        if post:
            result = self.post_now(plan, video_path)
        else:
            post_id = self.schedule_post(plan, video_path)
            result = {"post_id": post_id, "video_path": video_path, "status": "scheduled"}
        result["plan"] = plan
        return result

    def run_scheduler(self, topics: list[str] | None = None):
        """Blocking loop that creates and posts content at scheduled times."""
        while True:
            slots = scheduler.next_post_times()
            for slot in slots:
                wait = scheduler.seconds_until(slot)
                if wait > 0:
                    # In a real deployment, sleep here. For now, just generate and schedule.
                    pass
                try:
                    self.run_once(topics, post=True)
                except Exception as exc:
                    # Log and continue
                    print(f"Scheduled post failed: {exc}")
            # Daily regeneration of schedule
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            next_run = datetime.datetime.combine(tomorrow, datetime.time(0, 1))
            import time
            time.sleep(max(1, (next_run - datetime.datetime.now()).total_seconds()))
