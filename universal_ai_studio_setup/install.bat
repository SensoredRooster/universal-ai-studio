@echo off
REM Universal AI Studio - ONE-CLICK INSTALLER
REM Install on any PC: Ollama + 2 Models + Web UI
REM Everything runs locally - zero cloud dependency

setlocal enabledelayedexpansion

REM Prefer Python 3.11 for GPU acceleration. Fall back to system python if not found.
set "PY311=C:\Users\brand\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY311%" (
  set "PYTHON=%PY311%"
) else (
  set "PYTHON=python"
)

:: Force admin
net session >nul 2>&1
if errorlevel 1 (
  echo Requesting administrator access...
  powershell -Command "Start-Process '%~f0' -Verb RunAs"
  exit /b
)

title Universal AI Studio - Installation
cd /d "%~dp0"
cls

echo Using Python: %PYTHON%

echo.
echo =====================================================
echo    UNIVERSAL AI STUDIO - ONE-CLICK INSTALLER
echo =====================================================
echo.
echo This will install:
echo   * Ollama (Local AI Engine)
echo   * Qwen2.5-Coder 7B (Code Assistant)
echo   * DeepSeek-Coder 6.7B (Code Reviewer)
echo   * Web UI (Chat Interface)
echo.
pause

cls
echo [Step 1/5] Creating workspace...
if not exist "workspace" mkdir workspace
if not exist "models" mkdir models
echo OK - Directories ready
echo.

echo [Step 2/5] Installing Ollama...
powershell -Command "winget install --id Ollama.Ollama --silent --accept-source-agreements --accept-package-agreements 2>nul" >nul
timeout /t 3
echo OK - Ollama installed
echo.

echo [Step 3/5] Starting Ollama service...
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe" (
  start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
) else (
  start ollama serve
)
timeout /t 10
echo OK - Ollama running on localhost:11434
echo.

echo [Step 4/5] Downloading AI Models (this takes 10-15 minutes)...
echo   Pulling Qwen2.5-Coder 7B...
call ollama pull qwen2.5-coder:7b-instruct
echo   OK - Qwen2.5 ready
echo.
echo   Pulling DeepSeek-Coder 6.7B...
call ollama pull deepseek-coder:6.7b-instruct
echo   OK - DeepSeek ready
echo.

echo [Step 5/5] Installing Python dependencies...
%PYTHON% -m pip install -q -r requirements.txt
echo OK - Dependencies installed
echo.

cls
echo.
echo [ComfyUI Setup] Preparing local image generation backend...
echo This downloads ComfyUI + SDXL Base (~7GB total).
echo.

if not exist "ComfyUI" (
  echo [ComfyUI Setup] Cloning ComfyUI...
  git clone https://github.com/comfyanonymous/ComfyUI.git ComfyUI
) else (
  echo [ComfyUI Setup] ComfyUI folder already exists.
)

echo.
echo [ComfyUI Setup] Installing dependencies...
%PYTHON% -m pip install -q -r ComfyUI\requirements.txt

echo.
echo [ComfyUI Setup] Detecting GPU support...
%PYTHON% -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
if errorlevel 1 (
  echo CUDA not available. Image Studio will run in CPU mode.
) else (
  %PYTHON% -c "import torch; cap=torch.cuda.get_device_capability(); exit(0 if cap[0]*10+cap[1] <= 90 else 1)" >nul 2>&1
  if errorlevel 1 (
    for /f "delims=" %%g in ('%PYTHON% -c "import torch; print(torch.cuda.get_device_name(0))"') do echo Detected GPU: %%g
    echo This GPU architecture is newer than the installed PyTorch supports.
    echo Image Studio will run in CPU mode by default to avoid CUDA crashes.
  ) else (
    echo CUDA-compatible GPU detected. Image Studio will use GPU acceleration.
  )
)

echo.
echo [ComfyUI Setup] Downloading SDXL Base checkpoint (~6.9GB)...
if not exist "ComfyUI\models\checkpoints" mkdir "ComfyUI\models\checkpoints"
if not exist "ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors" (
  powershell -Command "try { Invoke-WebRequest -Uri 'https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors' -OutFile 'ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors' -ErrorAction Stop; Write-Host 'SDXL download complete.' } catch { Write-Host 'ERROR: Failed to download SDXL. Place your own .safetensors in ComfyUI\models\checkpoints' }"
) else (
  echo [ComfyUI Setup] SDXL checkpoint already exists.
)

echo.
echo [ComfyUI Setup] Done.

cls
echo.
echo =====================================================
echo    INSTALLATION COMPLETE!
echo =====================================================
echo.
echo Your AI Studio is ready to use!
echo.
echo QUICK START:
echo   Double-click: run.bat
echo   Or from command prompt: python app.py
echo.
echo Then open your browser to: http://localhost:5000
echo.
echo FEATURES:
echo   * Chat with 2 models side-by-side
echo   * Fast code completion (Qwen2.5)
echo   * Advanced code review (DeepSeek)
echo   * Local text-to-image generation (ComfyUI + SDXL)
echo   * Zero cloud dependency - runs locally
echo.
pause
