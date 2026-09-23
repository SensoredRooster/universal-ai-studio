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



Remote upload is disabled by default. To enable the **Send Diagnostics to Developer** button on a tester machine, configure:

~~~text
UAS_SUPPORT_UPLOAD_URL=https://your-support-service.example/upload
UAS_SUPPORT_UPLOAD_TOKEN=your-private-bearer-token
~~~

The tester must click the button and confirm before anything is uploaded.

An authenticated reference collector is included at:

~~~text
tools/support_collector.py
~~~

Run it only on infrastructure you control. It validates ZIP uploads, enforces a size limit, stores bundles in a dedicated inbox, records the tester session ID, and exposes authenticated list/download routes.


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
- **Left panel (The Architect / Qwen2.5)**: Ask for quick code help
- **Right panel (The Inspector / DeepSeek)**: Ask for detailed code review
- Type your question → Hit "Send" or press Enter
- Both models respond in real-time

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
