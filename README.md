# Universal AI Studio

**Zero-cloud, local AI studio. Chat with two models side-by-side, generate images with SDXL, and create social-video drafts locally.**

## Support, telemetry, and tester diagnostics

Universal AI Studio includes local-first diagnostics so tester reports can contain useful evidence instead of screenshots alone.

While the app is running it writes rotating structured telemetry and a lightweight heartbeat every second. On Windows the default log folder is:

~~~text
%LOCALAPPDATA%\UniversalAIStudio\logs
~~~

The telemetry captures:

- application startup and session ID;
- one-second health heartbeat;
- Flask request path/status/timing;
- Ollama, ComfyUI, FFmpeg, disk, and workspace health;
- chat request start/completion/failure;
- image generation queue/completion/failure;
- social-agent job state and render failures;
- uncaught Python and background-thread exceptions;
- launcher output plus Universal AI Studio and ComfyUI startup stderr/stdout.

Open **Support & Diagnostics** from the Studio header. Testers can:

- download a redacted **Support Bundle** ZIP;
- open the local logs folder;
- jump directly back to the main GitHub repository;
- create a prefilled GitHub issue containing the current telemetry session ID; and
- when a private support collector is configured, explicitly send the bundle to the developer.

Support bundles include the current structured telemetry, sanitized launcher/service logs, system/runtime health, selected non-secret environment settings, session metadata, and repository links.

Universal AI Studio does not intentionally log request bodies, chat prompts, passwords, OAuth tokens, API secrets, or cookies in the request telemetry layer. Known secret/token-shaped values are redacted where detectable. Logs can still contain filenames, model names, local directory paths, and exception text because those details are often necessary for diagnosis.





## Clone the Repository

```bash
git clone https://github.com/SensoredRooster/universal-ai-studio.git
cd universal-ai-studio
```

To update the project later from the same folder:

```bash
git pull
```

## What's Included

✅ **Qwen2.5-Coder 7B** - Fast code completion & analysis  
✅ **DeepSeek-Coder 6.7B** - Advanced code review & suggestions  
✅ **ComfyUI** - Local image generation backend  
✅ **SDXL Base 1.0** - High-quality text-to-image model  
✅ **Ollama** - Local AI engine (runs offline)  
✅ **Web UI** - Beautiful interface at http://localhost:5000  
✅ **Social Agent** - Trend-assisted video drafts, clip import, preview, download, and optional posting workflow

## Installation (First Time Only)

1. **Double-click `install.bat`** and approve the administrator prompt.
2. Wait for the installer to finish. It installs Python 3.11, Git, FFmpeg, Ollama, the two chat models, ComfyUI, its dependencies, and SDXL Base.

The installer is safe to run again. It skips completed downloads and resumes an interrupted SDXL download.

## Daily Usage

**Double-click `run.bat`** - That's it!
- Ollama starts if it is not already running
- ComfyUI starts after its model is ready
- The web interface opens automatically at http://localhost:5000
- Switch between **💬 Chat**, **🎨 Image Studio**, and **🚀 Social Agent** tabs

## How to Use

### Chat
- **The Architect / Qwen** plans against the live capability registry and selects executable production paths instead of assuming every tool is present.
- **The Inspector / DeepSeek** acts as an independent verification and QA role. It challenges unsupported claims, checks capability requirements, and reports concrete failures/fixes.
- Type your question → Hit **Send** or press Enter.
- Normal chat still works, but production requests now receive role-specific system context.

### Image Studio
- Switch to the **🎨 Image Studio** tab
- Enter a prompt, adjust size/steps if desired
- Click **Generate Image**
- The image appears when ComfyUI finishes (typically 30s–2m)
- Click **Download PNG** to save it

### Social Agent
- Switch to the **🚀 Social Agent** tab
- Find trend topics or enter your own ideas
- Generate a video draft, preview it, and download it locally
- Import your own clips when you want to use them in a generated video

## Agentic production foundation

Universal AI Studio now includes a first-pass capability registry and declarative
production-pipeline layer. The goal is to let the Architect plan against what
the current machine can actually execute instead of assuming every provider,
model, or media tool is available.

The live preflight endpoint is:

~~~text
GET /api/capabilities
~~~

It reports discovered tools, availability/degraded state, capability groupings,
and the current pipeline catalog. The initial contracts cover Ollama chat,
ComfyUI/SDXL image generation, local Wan video generation, FFmpeg composition,
and ffprobe validation.

Production manifests live under `pipeline_defs/`. Current manifests include
`social-short.json` and `image-generation.json`. The Architect ranks pipelines
against the live support envelope before planning work.

Structured orchestration endpoints:

~~~text
POST /api/orchestrate/plan
POST /api/orchestrate/inspect
~~~

The Social Agent also consumes the Architect capability context when it creates
video plans. After rendering, The Inspector's deterministic QA gate uses
`ffprobe` to verify that the output exists, is readable, has a video stream,
meets the expected 9:16 aspect ratio, and has a valid duration before a draft
can continue to save/publish. Failed QA blocks the pipeline instead of reporting
a broken render as complete.

## Production runs and checkpoints

Production work now persists under:

~~~text
workspace/runs/<run-id>/
~~~

Each run contains `run.json`, an append-only `events.jsonl`, and JSON artifacts
for completed stages. The Social Agent checkpoints research, planning, render,
Inspector QA, and save/publish. A failed run can resume from the latest valid
checkpoint instead of repeating completed stages. If a saved render artifact
points to a missing file, that checkpoint is invalidated and rendering runs again.

Useful endpoints:

~~~text
GET  /api/runs
GET  /api/runs/<run-id>

GET  /social/runs
GET  /social/runs/<run-id>
POST /social/runs/<run-id>/resume
~~~

Structured Architect plans created through `POST /api/orchestrate/plan` also get
their own production run and persisted plan/manifest artifacts.

## Production Board

The main Studio page now includes a live **Production Board** below the existing
workspaces. It refreshes recent runs automatically and shows:

- pipeline and run status;
- current/completed/failed stages;
- persisted artifacts with inline JSON inspection;
- Inspector QA artifacts and other checkpoint outputs;
- recent event history;
- failure details; and
- a **Resume from checkpoint** action for incomplete Social Agent runs.

The board reads the persisted run state rather than a separate UI-only status,
so restarting the browser does not erase the production history.

### SubScript handoff

Production Board runs can be handed to a locally running SubScript instance at
`http://127.0.0.1:8787`. Enter the local video path, optional start/duration,
and optionally mark the job for Smart Highlight. AI Studio sends the versioned
`open-production-job` contract, then mirrors SubScript's compatible stage and
artifact state back into the same Production Board run.

The shared schema is stored at:

~~~text
contracts/open-production-job.schema.json
~~~

SubScript remains the renderer/editor/review owner for handed-off clip jobs;
Universal AI Studio remains the planner/orchestration and cross-tool production
board.

## Features

✨ **Fast** - Runs on your GPU (NVIDIA recommended)  
🔒 **Private** - All processing happens locally, zero cloud  
🎯 **Focused** - Purpose-built for coding assistance  
💬 **Dual-chat** - Compare responses from 2 models simultaneously  
🎨 **Image Studio** - Generate images with ComfyUI + SDXL  

## System Requirements

- Windows 10/11 (64-bit)
- 16GB+ RAM (32GB recommended for image generation)
- 50GB+ free disk space (chat models)
- Additional ~15GB for ComfyUI + SDXL if installing Image Studio
- NVIDIA GPU with 8GB+ VRAM strongly recommended for SDXL
- For GPU acceleration you need Python 3.11/3.12 + CUDA-enabled PyTorch. Python 3.14 currently falls back to CPU mode.
- **RTX 50-series cards (e.g. RTX 5060 Ti):** PyTorch stable builds do not yet include CUDA kernels for the new sm_120 architecture. The launcher automatically detects this and falls back to CPU mode when needed.

## Troubleshooting

**Models not loading?**
```
Open Command Prompt and run: ollama list
Should show qwen2.5-coder and deepseek-coder
```

**ComfyUI not found?**
Double-click `run.bat` — it will automatically install ComfyUI + SDXL in the background.

**Image Studio is very slow?**
Your Python install may be using CPU mode. For GPU speed with an NVIDIA card, use Python 3.11 or 3.12 and install CUDA PyTorch:
```
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

**Port 5000 already in use?**
Edit `run.bat` and change `5000` to another port like `5001`

**Port 8188 already in use?**
Edit `run.bat` and change the ComfyUI `--port 8188` value.

**Slow responses?**
First run of each model is slower. Subsequent queries are faster.

## File Structure

```
universal_ai_studio/
├── install.bat          ← Run once to install
├── run.bat             ← Run daily to start
├── app.py              ← Web UI code
├── requirements.txt    ← Python dependencies
├── ComfyUI/            ← Optional image generation backend
├── workspace/          ← Generated images + chat history
└── models/             ← Model storage
```

## Tips

💡 **Save queries** - Useful questions are answered the same way every time  
💡 **Compare models** - Different models excel at different tasks  
💡 **Try examples** - Ask: "Show me a Python example of X"  
💡 **Code review** - Paste code in DeepSeek for review  
💡 **Prompt engineering** - More detailed image prompts produce better results  

---

**Made for streamers, creators, and developers who value privacy.**

No accounts. No APIs. No clouds. Just you and your AI models, running locally. 🚀

## Production support and tester sharing

Universal AI Studio uses two separate Cloudflare-backed services.

### Support diagnostics

- Worker: `https://universal-ai-studio-support.sensoredrooster-com.workers.dev`
- Upload endpoint: `https://universal-ai-studio-support.sensoredrooster-com.workers.dev/upload`
- R2 bucket: `universal-ai-studio-support-logs`
- The built-in Support page creates redacted support bundles and sends them only after explicit tester confirmation.
- `UAS_SUPPORT_UPLOAD_URL` remains available as a development override.

The production Cloudflare collector is the normal path. `tools/support_collector.py` is retained only as a local/self-hosted fallback.

### Tester Share

- Portal: `https://universal-ai-studio-share.sensoredrooster-com.workers.dev`
- R2 bucket: `universal-ai-studio-share`
- Open it from the Support page with **Tester Share**.
- Folders: `Releases`, `Tester Uploads`, `Screenshots`, `Bug Reports`, `Logs`, `Archived`

Tester access is read/download plus uploads to tester-facing folders. Admin access adds release management, **Latest** build selection, deletes, and archive management.

See [docs/CLOUDFLARE_SUPPORT.md](docs/CLOUDFLARE_SUPPORT.md) and [docs/TESTER_SHARE.md](docs/TESTER_SHARE.md).
