"""Trend fetching for content ideation.

This module focuses on sources that do not require API keys:
- RSS feeds from Google News / Reddit (public)
- YouTube trending page scraping (no API key needed)
- Optional: SerpAPI / RapidAPI if keys are provided
"""
import html
import json
import os
import random
import re
from urllib.parse import quote_plus

import requests
import feedparser

from . import config


def _fetch_rss_news(topic: str, max_items: int = 10):
    """Fetch recent news headlines via Google News RSS."""
    url = f"https://news.google.com/rss/search?q={quote_plus(topic)}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:max_items]:
        title = html.unescape(entry.get("title", ""))
        summary = html.unescape(entry.get("summary", ""))
        items.append({"title": title, "summary": summary, "source": entry.get("link", "")})
    return items


def _fetch_reddit_rss(subreddit: str = "technology", max_items: int = 10):
    """Fetch top posts from a subreddit via public RSS."""
    url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=day"
    feed = feedparser.parse(url, request_headers={"User-Agent": "UniversalAISocialAgent/1.0"})
    items = []
    for entry in feed.entries[:max_items]:
        title = html.unescape(entry.get("title", ""))
        items.append({"title": title, "summary": "", "source": entry.get("link", "")})
    return items


def _scrape_youtube_trending(max_items: int = 10):
    """Scrape trending YouTube Shorts titles (best-effort, no API key)."""
    url = "https://www.youtube.com/feed/trending?hl=en"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        text = resp.text
        # Extract video titles from ytInitialData JSON
        match = re.search(r"var ytInitialData = ({.+?});</script>", text)
        if not match:
            return []
        data = json.loads(match.group(1))
        titles = []
        # Navigate the complex JSON structure best-effort
        tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
        for tab in tabs:
            contents = tab.get("tabRenderer", {}).get("content", {}).get("sectionListRenderer", {}).get("contents", [])
            for section in contents:
                items = section.get("itemSectionRenderer", {}).get("contents", [])
                for item in items:
                    video = item.get("videoRenderer", {})
                    title = video.get("title", {}).get("runs", [{}])[0].get("text", "")
                    if title:
                        titles.append({"title": html.unescape(title), "summary": "", "source": "youtube_trending"})
        return titles[:max_items]
    except Exception as exc:
        return [{"title": f"Trending scrape unavailable: {exc}", "summary": "", "source": ""}]


def fetch_trends(topics: list[str] | None = None) -> list[dict]:
    """Gather trending topic candidates from multiple public sources."""
    topics = topics or ["AI", "technology", "gaming", "science", "motivation"]
    results = []
    # Reddit + News per topic
    for topic in topics:
        results.extend(_fetch_rss_news(topic, max_items=5))
    results.extend(_fetch_reddit_rss("technology", max_items=10))
    results.extend(_scrape_youtube_trending(max_items=10))
    # Deduplicate by title
    seen = set()
    unique = []
    for item in results:
        key = item["title"].lower().strip()
        if key and key not in seen and len(key) > 8:
            seen.add(key)
            unique.append(item)
    random.shuffle(unique)
    return unique[:30]
