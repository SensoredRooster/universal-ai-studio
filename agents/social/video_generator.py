"""Generate short videos from ComfyUI image frames using ffmpeg."""
import json
import os
import random
import shutil
import subprocess
import time
import uuid

import requests
from PIL import Image, ImageDraw, ImageFont

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


def _wait_for_image(prompt_id: str, timeout: int = 300) -> bytes | None:
    start = time.time()
    last_info = ""
    while time.time() - start < timeout:
        resp = requests.get(f"{config.COMFYUI_URL}/history/{prompt_id}", timeout=30)
        resp.raise_for_status()
        history = resp.json()
        if prompt_id not in history:
            # ComfyUI may still be loading the model; keep polling but report progress
            elapsed = int(time.time() - start)
            if elapsed % 10 == 0 and elapsed != last_info:
                print(f"  [ComfyUI] waiting for prompt {prompt_id[:8]}... ({elapsed}s)")
                last_info = elapsed
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
            for key in ("images", "video", "gifs"):
                items = node_output.get(key, [])
                if items:
                    item = items[0]
                    params = {
                        "filename": item["filename"],
                        "subfolder": item.get("subfolder", ""),
                        "type": item.get("type", "output"),
                    }
                    file_resp = requests.get(f"{config.COMFYUI_URL}/view", params=params, timeout=300)
                    file_resp.raise_for_status()
                    return file_resp.content
        time.sleep(1)
    raise TimeoutError(
        "ComfyUI did not return an image within 5 minutes. "
        "The SDXL checkpoint may still be downloading or ComfyUI may be busy loading the model. "
        "Wait for the installer window to finish, then try again."
    )


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


def generate_frames(plan: dict, output_dir: str, progress_callback=None) -> list[str]:
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
    report = progress_callback or (lambda progress, message: None)
    for i, prompt in enumerate(prompts[:3]):
        enhanced_prompt = (
            f"{prompt}, high detail, sharp focus, professional editorial composition, "
            "cinematic lighting, intricate details"
        )
        wf = _build_workflow(enhanced_prompt, negative, config.SHORT_WIDTH, config.SHORT_HEIGHT, checkpoint, steps=30)
        prompt_id = _queue_prompt(wf)
        image_data = _wait_for_image(prompt_id)
        path = os.path.join(output_dir, f"frame_{i:02d}_{uuid.uuid4().hex[:8]}.png")
        with open(path, "wb") as f:
            f.write(image_data)
        paths.append(path)
        report(30 + ((i + 1) * 20), f"Generated visual {i + 1} of 3")
    return paths


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _wan_available() -> bool:
    """True when all Wan 2.2 model files are fully downloaded."""
    required = [
        (os.path.join(config.MODELS_DIR, "diffusion_models", config.WAN_DIFFUSION_MODEL), 9_000_000_000),
        (os.path.join(config.MODELS_DIR, "vae", config.WAN_VAE), 1_000_000_000),
        (os.path.join(config.MODELS_DIR, "text_encoders", config.WAN_TEXT_ENCODER), 5_000_000_000),
    ]
    return all(os.path.isfile(p) and os.path.getsize(p) >= size for p, size in required)


def _build_wan_workflow(prompt: str, negative: str) -> dict:
    """Wan 2.2 5B text-to-video workflow (API format)."""
    return {
        "1": {"inputs": {"unet_name": config.WAN_DIFFUSION_MODEL, "weight_dtype": "default"},
              "class_type": "UNETLoader"},
        "2": {"inputs": {"clip_name": config.WAN_TEXT_ENCODER, "type": "wan", "device": "default"},
              "class_type": "CLIPLoader"},
        "3": {"inputs": {"vae_name": config.WAN_VAE}, "class_type": "VAELoader"},
        "4": {"inputs": {"model": ["1", 0], "shift": 8.0}, "class_type": "ModelSamplingSD3"},
        "5": {"inputs": {"text": prompt, "clip": ["2", 0]}, "class_type": "CLIPTextEncode"},
        "6": {"inputs": {"text": negative, "clip": ["2", 0]}, "class_type": "CLIPTextEncode"},
        "7": {"inputs": {"width": config.WAN_WIDTH, "height": config.WAN_HEIGHT,
                          "length": config.WAN_CLIP_FRAMES, "batch_size": 1, "vae": ["3", 0]},
              "class_type": "Wan22ImageToVideoLatent"},
        "8": {"inputs": {"seed": random.randint(1, 1_000_000_000), "steps": config.WAN_STEPS,
                          "cfg": config.WAN_CFG, "sampler_name": "uni_pc", "scheduler": "simple",
                          "denoise": 1.0, "model": ["4", 0], "positive": ["5", 0],
                          "negative": ["6", 0], "latent_image": ["7", 0]},
              "class_type": "KSampler"},
        "9": {"inputs": {"samples": ["8", 0], "vae": ["3", 0]}, "class_type": "VAEDecode"},
        "10": {"inputs": {"images": ["9", 0], "fps": config.WAN_FPS}, "class_type": "CreateVideo"},
        "11": {"inputs": {"video": ["10", 0], "filename_prefix": "social_wan",
                           "format": "mp4", "codec": "h264"},
               "class_type": "SaveVideo"},
    }


def _caption_png(text: str, out_path: str) -> str:
    """Render a transparent 1080x1920 caption overlay."""
    img = Image.new("RGBA", (config.SHORT_WIDTH, config.SHORT_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = None
    for candidate in ("C:\\Windows\\Fonts\\segoeuib.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"):
        try:
            font = ImageFont.truetype(candidate, 48)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    max_width = config.SHORT_WIDTH - 140
    words, lines, current = text.split(), [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_height = font.size + 10
    total_height = len(lines) * line_height + 24
    box_top = 96
    draw.rounded_rectangle(
        [48, box_top, config.SHORT_WIDTH - 48, box_top + total_height],
        radius=18, fill=(8, 14, 28, 190), outline=(90, 190, 255, 220), width=3,
    )
    y = box_top + 12
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        draw.text(((config.SHORT_WIDTH - (bbox[2] - bbox[0])) // 2, y), line,
                  font=font, fill=(255, 255, 255, 255))
        y += line_height
    img.save(out_path, "PNG")
    return out_path


def generate_video_wan(plan: dict, run_id: str, progress_callback=None) -> str:
    """Generate real motion video: one Wan 2.2 clip per scene, then stitch."""
    report = progress_callback or (lambda progress, message: None)
    work_dir = os.path.join(config.FRAME_DIR, run_id)
    os.makedirs(work_dir, exist_ok=True)
    output_path = os.path.join(config.VIDEO_DIR, f"{run_id}.mp4")
    os.makedirs(config.VIDEO_DIR, exist_ok=True)

    negative = ("static, still image, blurry, low quality, watermark, text, logo, "
                "distorted faces, jerky motion, worst quality")
    prompts = plan.get("visual_prompts", [])[:3]
    if len(prompts) < 3:
        base = plan.get("source_trend", "trending topic")
        prompts += [f"Cinematic slow motion shot of {base}"] * (3 - len(prompts))

    voiceover = plan.get("voiceover_script", [])
    title = plan.get("short_title", "Trending Now")

    scene_files = []
    for i, prompt in enumerate(prompts):
        report(25 + i * 20, f"Generating video scene {i + 1} of 3")
        motion_prompt = (f"{prompt}, smooth cinematic camera movement, high detail, "
                         "vivid colors, professional cinematography")
        wf = _build_wan_workflow(motion_prompt, negative)
        prompt_id = _queue_prompt(wf)
        video_bytes = _wait_for_image(prompt_id, timeout=1800)
        raw_path = os.path.join(work_dir, f"scene_{i}.mp4")
        with open(raw_path, "wb") as f:
            f.write(video_bytes)

        caption = voiceover[i] if i < len(voiceover) else title
        overlay_path = _caption_png(caption, os.path.join(work_dir, f"caption_{i}.png"))
        scene_out = os.path.join(work_dir, f"scene_{i}_final.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", raw_path, "-i", overlay_path,
            "-filter_complex",
            (f"[0:v]scale={config.SHORT_WIDTH}:{config.SHORT_HEIGHT}:"
             f"force_original_aspect_ratio=increase,"
             f"crop={config.SHORT_WIDTH}:{config.SHORT_HEIGHT},setsar=1[v];"
             f"[v][1:v]overlay=0:0,format=yuv420p[out]"),
            "-map", "[out]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-r", str(config.FPS), scene_out,
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        scene_files.append(scene_out)

    report(90, "Stitching final video")
    concat_inputs = []
    for f in scene_files:
        concat_inputs.extend(["-i", f])
    streams = "".join(f"[{i}:v]" for i in range(len(scene_files)))
    subprocess.run([
        "ffmpeg", "-y", *concat_inputs,
        "-filter_complex", f"{streams}concat=n={len(scene_files)}:v=1:a=0[out]",
        "-map", "[out]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", output_path,
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    report(95, "Video ready")
    return output_path


def _overlay_text(frame_path: str, text: str) -> str:
    """Burn a title into the center-top of a frame using Pillow."""
    with Image.open(frame_path).convert("RGBA") as img:
        # Scale to target short dimensions if needed
        img = img.resize((config.SHORT_WIDTH, config.SHORT_HEIGHT), Image.LANCZOS)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Try a few common Windows fonts
        font_candidates = [
            "C:\\Windows\\Fonts\\segoeuib.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "C:\\Windows\\Fonts\\calibrib.ttf",
        ]
        font = None
        for candidate in font_candidates:
            try:
                font = ImageFont.truetype(candidate, 48)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        # Wrap text to fit width
        max_width = config.SHORT_WIDTH - 120
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = current + " " + word if current else word
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        # Keep captions readable without covering the visual.
        line_height = font.size + 10
        total_height = len(lines) * line_height + 24
        box_top = 72
        draw.rounded_rectangle(
            [48, box_top, config.SHORT_WIDTH - 48, box_top + total_height],
            radius=18,
            fill=(8, 14, 28, 190),
            outline=(90, 190, 255, 220),
            width=3,
        )

        # Draw each line centered
        y = box_top + 10
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            x = (config.SHORT_WIDTH - (bbox[2] - bbox[0])) // 2
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
            y += line_height

        composed = Image.alpha_composite(img, overlay).convert("RGB")
        out_path = frame_path.replace(".png", "_captioned.png")
        composed.save(out_path, "PNG")
        return out_path


def compose_video(frame_paths: list[str], plan: dict, output_path: str) -> str:
    """Stitch frames into a vertical 9:16 video with overlaid captions."""
    if not _has_ffmpeg():
        raise RuntimeError("ffmpeg is not installed or not on PATH. Install ffmpeg to generate videos.")
    if len(frame_paths) < 3:
        raise ValueError("Need at least 3 frames to compose a video.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    title = plan.get("short_title", "Trending Now")
    voiceover = plan.get("voiceover_script", [])
    captions = [voiceover[i] if i < len(voiceover) else title for i in range(len(frame_paths))]
    captioned_frames = [_overlay_text(frame, caption) for frame, caption in zip(frame_paths, captions)]

    # Build inputs: each frame is a looping still image for CLIP_SECONDS
    inputs = []
    filter_parts = []
    for i, frame in enumerate(captioned_frames):
        inputs.extend(["-loop", "1", "-t", str(config.CLIP_SECONDS), "-i", frame])
        filter_parts.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
            f"zoompan=z='1.0+0.06*on/143':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d=144:s=1080x1920:fps={config.FPS},"
            f"setsar=1,format=yuv420p[v{i}]"
        )

    concat = "".join(f"[v{i}]" for i in range(len(captioned_frames)))
    filter_parts.append(f"{concat}concat=n={len(captioned_frames)}:v=1:a=0[final]")

    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[final]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-r", str(config.FPS),
        "-t", str(config.CLIP_SECONDS * len(captioned_frames)),
        output_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path


def generate_video(plan: dict, run_id: str, progress_callback=None) -> str:
    """Full pipeline. Uses Wan 2.2 text-to-video when available, else SDXL slideshow."""
    if not _has_ffmpeg():
        raise RuntimeError("ffmpeg is not installed or not on PATH. Install ffmpeg to generate videos.")
    report = progress_callback or (lambda progress, message: None)
    if _wan_available():
        return generate_video_wan(plan, run_id, progress_callback)
    frame_dir = os.path.join(config.FRAME_DIR, run_id)
    video_path = os.path.join(config.VIDEO_DIR, f"{run_id}.mp4")
    frames = generate_frames(plan, frame_dir, report)
    report(92, "Composing animated video")
    compose_video(frames, plan, video_path)
    report(95, "Video ready")
    return video_path
