# Social Agent for Universal AI Studio

Fully autonomous YouTube Shorts agent that researches trends, plans content, generates vertical videos with local ComfyUI/SDXL, and uploads to YouTube.

## How it works

1. **Research** — scrapes Google News RSS, Reddit RSS, and YouTube trending for hot topics.
2. **Planning** — uses a local Ollama model to write titles, descriptions, hashtags, image prompts, and voiceover scripts.
3. **Video generation** — generates 3 SDXL frames at 1080×1920, then stitches them into a 9:16 MP4 with ffmpeg and text overlays.
4. **Upload** — uses the YouTube Data API v3 to post the Short.
5. **Scheduling** — stores posts in SQLite and supports scheduled future publishing.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Install ffmpeg

The video composer requires ffmpeg on PATH. Download from https://ffmpeg.org/download.html or install via winget:

```powershell
winget install Gyan.FFmpeg
```

### 3. YouTube API credentials

1. Go to https://console.cloud.google.com/
2. Create a project, enable the **YouTube Data API v3**
3. Create **OAuth 2.0 Desktop** credentials
4. Download `client_secret.json` and place it in `workspace/social/client_secret.json`
5. The first upload will open a browser for OAuth consent and save `workspace/social/youtube_credentials.json`

### 4. Configure (optional)

Edit `agents/social/config.py` or set environment variables:

```text
YT_CLIENT_SECRETS=C:\path\to\client_secret.json
YT_CREDENTIALS=C:\path\to\youtube_credentials.json
POSTS_PER_DAY=3
DEFAULT_POST_TIME=09:00
```

## Usage

### Web UI

Open Universal AI Studio and click the **🚀 Social Agent** tab.

- **🔍 Find Trends** — preview trending topics
- **🎬 Generate Draft** — create a video without posting
- **📤 Generate & Post** — create and upload to YouTube Shorts immediately

### API

```text
GET  /social/status
GET  /social/trends?topic=AI&topic=technology
POST /social/generate        { "topics": ["AI"] }
POST /social/post            { "topics": ["AI"] }
GET  /social/videos/<filename>
```

### CLI / scheduler

Run one post manually:

```bash
python -m agents.social.cli --topics AI,technology --post
```

Run the background scheduler:

```bash
python -m agents.social.cli --scheduler
```

On Windows, use Task Scheduler to run the scheduler at startup.

## Monitoring

All posts are tracked in `workspace/social/social_agent.db`. Check status with:

```text
GET /social/status
```

Failed posts store error messages so you can diagnose API or generation issues.

## Notes

- This agent uses only local AI for planning and generation. YouTube upload is the only cloud dependency.
- The first upload requires a browser OAuth login. After that, credentials are cached.
- Keep your `client_secret.json` and `youtube_credentials.json` out of git. They are already ignored by the workspace `.gitignore` via `workspace/*`.
