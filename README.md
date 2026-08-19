# Universal AI Studio

**Zero-cloud, local AI chatbot. Chat with 2 models side-by-side.**

## What's Included

✅ **Qwen2.5-Coder 7B** - Fast code completion & analysis  
✅ **DeepSeek-Coder 6.7B** - Advanced code review & suggestions  
✅ **Ollama** - Local AI engine (runs offline)  
✅ **Web UI** - Beautiful chat interface at http://localhost:5000  

## Installation (First Time Only)

1. **Double-click `install.bat`**
   - It will ask for admin permission
   - Downloads Ollama (~200MB)
   - Pulls both AI models (~8.5GB total)
   - Takes 10-15 minutes

2. **When done, close the window**

## Daily Usage

**Double-click `run.bat`** - That's it!
- Ollama starts in the background
- Web interface opens automatically at http://localhost:5000
- Chat with both models side-by-side

## How to Use

- **Left panel (Qwen2.5)**: Ask for quick code help
- **Right panel (DeepSeek)**: Ask for detailed code review
- Type your question → Hit "Send" or press Enter
- Both models respond in real-time

## Features

✨ **Fast** - Runs on your GPU (NVIDIA recommended)  
🔒 **Private** - All processing happens locally, zero cloud  
🎯 **Focused** - Purpose-built for coding assistance  
💬 **Dual-chat** - Compare responses from 2 models simultaneously  

## System Requirements

- Windows 10/11 (64-bit)
- 16GB+ RAM
- 50GB+ free disk space (for models)
- NVIDIA GPU recommended (but not required)

## Troubleshooting

**Models not loading?**
```
Open Command Prompt and run: ollama list
Should show qwen2.5-coder and deepseek-coder
```

**Port 5000 already in use?**
Edit `run.bat` and change `5000` to another port like `5001`

**Slow responses?**
First run of each model is slower. Subsequent queries are faster.

## File Structure

```
universal_ai_studio/
├── install.bat          ← Run once to install
├── run.bat             ← Run daily to start
├── app.py              ← Web UI code
├── requirements.txt    ← Python dependencies
├── workspace/          ← Chat history
└── models/             ← Model storage
```

## Tips

💡 **Save queries** - Useful questions are answered the same way every time  
💡 **Compare models** - Different models excel at different tasks  
💡 **Try examples** - Ask: "Show me a Python example of X"  
💡 **Code review** - Paste code in DeepSeek for review  

---

**Made for streamers, creators, and developers who value privacy.**

No accounts. No APIs. No clouds. Just you and your AI models, running locally. 🚀
