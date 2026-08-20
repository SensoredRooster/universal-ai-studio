"""Plan video topics and generate prompts/captions via local Ollama LLMs."""
import json
import random
import re

import requests

from . import config


def _ollama_generate(model: str, prompt: str, system: str = "", temperature: float = 0.8) -> str:
    """Call the local Ollama generate endpoint."""
    try:
        resp = requests.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as exc:
        return f"Error: {exc}"


def pick_trend(trends: list[dict], count: int = 1) -> list[dict]:
    """Select the most promising trends for short-form video content."""
    scored = []
    for item in trends:
        title = item.get("title", "")
        # Simple heuristic: prefer concise, concrete, visualizable topics
        score = 0
        if 20 <= len(title) <= 80:
            score += 2
        if any(word in title.lower() for word in ["ai", "robot", "space", "future", "new", "revealed", "vs"]):
            score += 1
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:count]]


def generate_video_plan(trend: dict) -> dict:
    """Produce a complete plan: title, description, hashtags, image prompts, voiceover script."""
    title = trend["title"]
    system = (
        "You are a social media content strategist for YouTube Shorts. "
        "Output only valid JSON with no markdown."
    )
    prompt = (
        f"Create a YouTube Shorts plan for this trending topic:\n{title}\n\n"
        "Return JSON with keys: short_title (string under 60 chars), "
        "description (string under 300 chars), hashtags (list of 5 strings), "
        "visual_prompts (list of 3 vivid English image-generation prompts, each under 100 words, "
        "optimized for photorealistic or cinematic digital art), "
        "voiceover_script (list of 3 short sentences, each under 12 words, punchy and engaging)."
    )
    raw = _ollama_generate(config.PLANNER_MODEL, prompt, system=system)
    # Strip markdown code fences if the model added them
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    try:
        plan = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback structure
        plan = {
            "short_title": title[:60],
            "description": title[:120],
            "hashtags": ["#shorts", "#viral", "#ai", "#trending", "#tech"],
            "visual_prompts": [f"Cinematic scene of {title}", f"Futuristic visualization of {title}", f"Close-up artistic render of {title}"],
            "voiceover_script": [title, "Here's what you need to know.", "Like and follow for more."],
        }
    plan["source_trend"] = title
    return plan


def generate_caption(plan: dict) -> str:
    """Generate a final posting caption from a video plan."""
    hashtags = " ".join(plan.get("hashtags", []))
    return f"{plan.get('short_title', '')}\n\n{plan.get('description', '')}\n\n{hashtags} #shorts"
