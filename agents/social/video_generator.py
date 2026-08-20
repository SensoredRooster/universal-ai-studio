"""Generate short videos from ComfyUI image frames using ffmpeg."""
import json
import os
import random
import shutil
import subprocess
import time
import uuid

import requests

from . import config


def _find_checkpoint() -> str | None:
    if not os.path.isdir(config.CHECKPOINT_DIR):
        return None
    for name in os.listdir(config.CHECKPOINT_DIR):
        lower = name.lower()
        if lower.endswith(".safetensors") or lower.endswith(".ckpt") or lower.endswith(".pt"):
            return name
    return None


def _queue_prompt(workflow: dict) -> str:
    data = {"prompt": workflow, "client_id": str(uuid.uuid4())}
    resp = requests.post(f"{config.COMFYUI_URL}/prompt", json=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def _wait_for_image(prompt_id: str, timeout: int = 600) -> bytes | None:
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{config.COMFYUI_URL}/history/{prompt_id}", timeout=30)
        resp.raise_for_status()
        history = resp.json()
        if prompt_id not in history:
            time.sleep(1)
            continue
        entry = history[prompt_id]
        status = entry.get("status", {})
        if status.get("status_str") == "error":
            messages = status.get("messages", [])
            err = "Unknown ComfyUI error"
            for m in messages:
                if isinstance(m, list) and len(m) > 1 and m[0] == "execution_error":
                    err = m[1].get("exception_message", err)
            raise RuntimeError(err)
        outputs = entry.get("outputs", {})
        for node_id, node_output in outputs.items():
            images = node_output.get("images", [])
            if images:
                img = images[0]
                params = {
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output"),
                }
                img_resp = requests.get(f"{config.COMFYUI_URL}/view", params=params, timeout=60)
                img_resp.raise_for_status()
                return img_resp.content
        time.sleep(1)
    raise TimeoutError("ComfyUI did not return an image in time.")


def _build_workflow(prompt: str, negative: str, width: int, height: int, checkpoint: str, steps: int = 25) -> dict:
    wf = json.loads(json.dumps({
        "3": {
            "inputs": {
                "seed": 0,
                "steps": steps,
                "cfg": 7.0,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
            "class_type": "KSampler",
        },
        "4": {"inputs": {"ckpt_name": checkpoint}, "class_type": "CheckpointLoaderSimple"},
        "5": {"inputs": {"width": width, "height": height, "batch_size": 1}, "class_type": "EmptyLatentImage"},
        "6": {"inputs": {"text": "{{POSITIVE}}", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "7": {"inputs": {"text": "{{NEGATIVE}}", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
        "9": {"inputs": {"filename_prefix": "social", "images": ["8", 0]}, "class_type": "SaveImage"},
    }))
    wf_str = json.dumps(wf)
    wf_str = wf_str.replace("{{POSITIVE}}", prompt.replace('"', '\\"'))
    wf_str = wf_str.replace("{{NEGATIVE}}", negative.replace('"', '\\"'))
    wf = json.loads(wf_str)
    wf["3"]["inputs"]["seed"] = random.randint(1, 1_000_000_000)
    wf["5"]["inputs"]["width"] = width
    wf["5"]["inputs"]["height"] = height
    wf["3"]["inputs"]["steps"] = steps
    return wf


def generate_frames(plan: dict, output_dir: str) -> list[str]:
    """Generate 3 image frames for the video plan and return their file paths."""
    os.makedirs(output_dir, exist_ok=True)
    checkpoint = _find_checkpoint()
    if not checkpoint:
        raise FileNotFoundError("No checkpoint found in ComfyUI/models/checkpoints.")
    negative = "blurry, low quality, watermark, text, logo, signature, cropped, worst quality"
    prompts = plan.get("visual_prompts", [])
    if len(prompts) < 3:
        base = plan.get("source_trend", "trending topic")
        prompts += [f"Cinematic shot of {base}"] * (3 - len(prompts))

    paths = []
    for i, prompt in enumerate(prompts[:3]):
        wf = _build_workflow(prompt, negative, config.SHORT_WIDTH, config.SHORT_HEIGHT, checkpoint)
        prompt_id = _queue_prompt(wf)
        image_data = _wait_for_image(prompt_id)
        path = os.path.join(output_dir, f"frame_{i:02d}_{uuid.uuid4().hex[:8]}.png")
        with open(path, "wb") as f:
            f.write(image_data)
        paths.append(path)
    return paths


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def compose_video(frame_paths: list[str], plan: dict, output_path: str) -> str:
    """Stitch frames into a vertical 9:16 video with overlaid captions."""
    if not _has_ffmpeg():
        raise RuntimeError("ffmpeg is not installed or not on PATH. Install ffmpeg to generate videos.")
    if len(frame_paths) < 3:
        raise ValueError("Need at least 3 frames to compose a video.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Prepare a clean concat list with each frame held for CLIP_SECONDS
    concat_file = os.path.join(os.path.dirname(output_path), f"concat_{uuid.uuid4().hex[:8]}.txt")
    try:
        with open(concat_file, "w", encoding="utf-8") as f:
            for frame in frame_paths:
                escaped = frame.replace("\\", "/")
                f.write(f"file '{escaped}'\n")
                f.write(f"duration {config.CLIP_SECONDS}\n")
            # ffmpeg requires the last frame repeated to match final duration
            f.write(f"file '{frame_paths[-1].replace(chr(92), chr(47))}'\n")

        title = plan.get("short_title", "Trending Now")
        safe_title = title.replace("'", "'\\''")
        filter_text = (
            f"drawtext=text='{safe_title}':fontcolor=white:fontsize=48:"
            "box=1:boxcolor=black@0.5:boxborderw=10:x=(w-text_w)/2:y=80:enable='lt(t,18)',"
            "zoompan=z='min(zoom+0.0015,1.15)':d=1440:s=1080x1920:fps=24,"
            "format=yuv420p"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-vf", filter_text,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(config.FPS),
            "-t", "18",
            output_path,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_path
    finally:
        try:
            os.remove(concat_file)
        except FileNotFoundError:
            pass


def generate_video(plan: dict, run_id: str) -> str:
    """Full pipeline: frames -> stitched vertical video. Returns path to mp4."""
    frame_dir = os.path.join(config.FRAME_DIR, run_id)
    video_path = os.path.join(config.VIDEO_DIR, f"{run_id}.mp4")
    frames = generate_frames(plan, frame_dir)
    compose_video(frames, plan, video_path)
    return video_path
