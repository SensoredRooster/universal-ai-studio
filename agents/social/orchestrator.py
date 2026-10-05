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
from studio_core.qa import inspect_video_file
from studio_core.runs import ProductionRun


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

    def create_video(self, plan: dict, run_id: str | None = None, progress_callback=None) -> str:
        """Generate frames and compose a vertical video."""
        run_id = run_id or str(uuid.uuid4())
        return video_generator.generate_video(plan, run_id, progress_callback)

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

    def run_once(
        self,
        topics: list[str] | None = None,
        post: bool = False,
        progress_callback=None,
        run_id: str | None = None,
        resume: bool = True,
    ) -> dict:
        """Research, plan, generate, validate, and optionally publish a resumable Short."""
        report = progress_callback or (lambda progress, message: None)
        production = ProductionRun.create(
            "social-short",
            run_id=run_id,
            request=", ".join(topics or []),
            metadata={"post_requested": bool(post)},
        )
        run_id = production.run_id

        try:
            if resume and production.stage_complete("research") and production.artifact_exists("research"):
                report(10, "Resuming: using saved research")
                trends = production.load_artifact("research")
            else:
                production.start_stage("research")
                report(10, "Researching current trends")
                trends = self.research(topics)
                if not trends:
                    raise RuntimeError("No trends found.")
                production.save_artifact("research", trends)
                production.complete_stage("research", count=len(trends))

            if resume and production.stage_complete("plan") and production.artifact_exists("plan"):
                report(20, "Resuming: using saved production plan")
                plan = production.load_artifact("plan")
            else:
                production.start_stage("plan")
                report(20, "Planning the Short")
                plan = self.plan(trends[0])
                production.save_artifact("plan", plan)
                production.complete_stage("plan", title=plan.get("short_title", ""))

            if resume and production.stage_complete("render") and production.artifact_exists("render"):
                render_artifact = production.load_artifact("render")
                video_path = render_artifact.get("video_path")
                if not video_path or not os.path.isfile(video_path):
                    production.emit("checkpoint_invalid", stage="render", reason="saved video is missing")
                    video_path = None
            else:
                video_path = None

            if not video_path:
                production.start_stage("render")
                video_path = self.create_video(plan, run_id, report)
                production.save_artifact("render", {"video_path": video_path})
                production.complete_stage("render", video_path=video_path)

            if resume and production.stage_complete("qa") and production.artifact_exists("qa"):
                report(95, "Resuming: using saved Inspector QA")
                qa_report = production.load_artifact("qa")
            else:
                production.start_stage("qa")
                report(95, "Inspector QA: validating rendered video")
                qa_report = inspect_video_file(video_path, expected_aspect="9:16")
                production.save_artifact("qa", qa_report)
                if not qa_report.get("approved"):
                    error = "Inspector rejected the rendered video: " + "; ".join(
                        qa_report.get("errors") or ["unknown QA failure"]
                    )
                    production.fail_stage("qa", error)
                    raise RuntimeError(error)
                production.complete_stage("qa", approved=True)

            if post:
                if resume and production.stage_complete("publish") and production.artifact_exists("publish"):
                    report(97, "Resuming: publish result already recorded")
                    result = production.load_artifact("publish")
                else:
                    production.start_stage("publish")
                    report(97, "Uploading to YouTube")
                    result = self.post_now(plan, video_path)
                    production.save_artifact("publish", result)
                    production.complete_stage("publish", status=result.get("status"))
            else:
                if resume and production.stage_complete("save") and production.artifact_exists("save"):
                    report(97, "Resuming: validated draft already saved")
                    result = production.load_artifact("save")
                else:
                    production.start_stage("save")
                    report(97, "Saving the validated draft")
                    post_id = database.create_post(plan, video_path)
                    result = {"post_id": post_id, "video_path": video_path, "status": "generated"}
                    production.save_artifact("save", result)
                    production.complete_stage("save", post_id=post_id)

            result["plan"] = plan
            result["qa_report"] = qa_report
            result["run_id"] = run_id
            result["production_run"] = production.snapshot()
            production.mark_complete()
            result["production_run"] = production.snapshot()
            return result
        except Exception as exc:
            state = production.state()
            current_stage = state.get("current_stage")
            if current_stage and state.get("stages", {}).get(current_stage, {}).get("status") == "running":
                production.fail_stage(current_stage, str(exc))
            raise

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
