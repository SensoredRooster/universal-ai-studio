# Universal AI Studio

**Zero-cloud, local AI studio. Chat with 2 models side-by-side and generate images with SDXL.**

## What's Included

✅ **Qwen2.5-Coder 7B** - Fast code completion & analysis  
✅ **DeepSeek-Coder 6.7B** - Advanced code review & suggestions  
✅ **ComfyUI** - Local image generation backend  
✅ **SDXL Base 1.0** - High-quality text-to-image model  
✅ **Ollama** - Local AI engine (runs offline)  
✅ **Web UI** - Beautiful interface at http://localhost:5000  

## Installation (First Time Only)

1. **Double-click `install.bat`**
   - It will ask for admin permission
   - Downloads Ollama (~200MB)
   - Pulls both chat models (~8.5GB total)
   - Clones ComfyUI and downloads SDXL Base (~7GB)
   - Takes 20-40 minutes depending on your internet

2. **When done, close the window**

> **Note:** If you skip `install.bat`, double-clicking `run.bat` will automatically start the image backend installer in the background. Chat works immediately; Image Studio becomes available once the download finishes.

## Daily Usage

**Double-click `run.bat`** - That's it!
- Ollama starts in the background
- ComfyUI starts in the background (if installed)
- Web interface opens automatically at http://localhost:5000
- Switch between **💬 Chat** and **🎨 Image Studio** tabs

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
- **RTX 50-series cards (e.g. RTX 5060 Ti):** PyTorch stable builds do not yet include CUDA kernels for the new sm_120 architecture. The launcher automatically detects this and falls back to CPU mode so Image Studio still works. Full GPU speed will become available once PyTorch publishes CUDA 12.8+ wheels.

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

## Sonic Scout (native Windows audio profile manager)

This repository also includes **Sonic Scout**, a separate native Windows WPF application for audio EQ profile management, unrelated to the chat/image features above. It lives in [CSharp/](CSharp/README_CSHARP.md) and its audio pass-through component is documented in [CSharp/SonicPass/README.md](CSharp/SonicPass/README.md).

