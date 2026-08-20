"""Simple scheduling utilities for social media posts."""
import datetime
import random

from . import config


def next_post_times(count: int = config.POSTS_PER_DAY, base_date: datetime.date | None = None) -> list[datetime.datetime]:
    """Generate upcoming post datetimes spread across the day."""
    base = base_date or datetime.date.today()
    hh, mm = map(int, config.DEFAULT_POST_TIME.split(":"))
    base_dt = datetime.datetime.combine(base, datetime.time(hh, mm))
    slots = []
    for i in range(count):
        # Space posts roughly evenly with small random jitter
        jitter_minutes = random.randint(-15, 15)
        delta = datetime.timedelta(hours=(24 // count) * i, minutes=jitter_minutes)
        slots.append(base_dt + delta)
    return slots


def seconds_until(dt: datetime.datetime) -> float:
    """Return seconds until a given datetime."""
    return max(0.0, (dt - datetime.datetime.now()).total_seconds())
