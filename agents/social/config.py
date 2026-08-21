"""Configuration for the social media agent."""
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# ComfyUI integration
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
CHECKPOINT_DIR = os.path.join(ROOT_DIR, "ComfyUI", "models", "checkpoints")

# Local LLM via Ollama
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
PLANNER_MODEL = os.environ.get("PLANNER_MODEL", "qwen2.5-coder:7b-instruct")
CAPTION_MODEL = os.environ.get("CAPTION_MODEL", "qwen2.5-coder:7b-instruct")

# Output directories
SOCIAL_DIR = os.path.join(ROOT_DIR, "workspace", "social")
FRAME_DIR = os.path.join(SOCIAL_DIR, "frames")
VIDEO_DIR = os.path.join(SOCIAL_DIR, "videos")
LOG_DIR = os.path.join(SOCIAL_DIR, "logs")
DB_PATH = os.path.join(SOCIAL_DIR, "social_agent.db")

# YouTube API
CLIENT_SECRETS_FILE = os.environ.get(
    "YT_CLIENT_SECRETS", os.path.join(ROOT_DIR, "workspace", "social", "client_secret.json")
)
CREDENTIALS_FILE = os.environ.get(
    "YT_CREDENTIALS", os.path.join(ROOT_DIR, "workspace", "social", "youtube_credentials.json")
)
YOUTUBE_CATEGORY_ID = "22"  # People & Blogs (common default for Shorts)
YOUTUBE_PRIVACY = "public"

# Video settings
SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920
FPS = 24
CLIP_SECONDS = 6  # duration of each generated image clip
FRAMES_PER_CLIP = FPS * CLIP_SECONDS
SOCIAL_FRAME_WIDTH = int(os.environ.get("SOCIAL_FRAME_WIDTH", "540"))
SOCIAL_FRAME_HEIGHT = int(os.environ.get("SOCIAL_FRAME_HEIGHT", "960"))
SOCIAL_FRAME_STEPS = int(os.environ.get("SOCIAL_FRAME_STEPS", "12"))

# Wan 2.2 text-to-video (used when the model files are present)
MODELS_DIR = os.path.join(ROOT_DIR, "ComfyUI", "models")
WAN_DIFFUSION_MODEL = "wan2.2_ti2v_5B_fp16.safetensors"
WAN_VAE = "wan2.2_vae.safetensors"
WAN_TEXT_ENCODER = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
WAN_WIDTH = 704
WAN_HEIGHT = 1280
WAN_FPS = 24
WAN_CLIP_FRAMES = 121  # ~5s per scene at 24fps
WAN_STEPS = 20
WAN_CFG = 5.0

# Scheduling
DEFAULT_POST_TIME = "09:00"
POSTS_PER_DAY = int(os.environ.get("POSTS_PER_DAY", "3"))
