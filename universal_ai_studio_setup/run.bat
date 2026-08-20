@echo off
REM Universal AI Studio - LAUNCHER
REM Run this daily to start your AI Studio

setlocal
cd /d "%~dp0"

REM Prefer Python 3.11 for GPU acceleration. Fall back to system python if not found.
set "PY311=C:\Users\brand\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY311%" (
  set "PYTHON=%PY311%"
) else (
  set "PYTHON=python"
)

echo.
echo ===== UNIVERSAL AI STUDIO =====
echo Using Python: %PYTHON%
echo.

echo Starting Ollama service...
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe" (
  start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
) else (
  start ollama serve
)
timeout /t 5

echo.
echo Starting ComfyUI (Image Studio backend)...
if not exist "ComfyUI\main.py" (
  echo ComfyUI not found. Starting background installer...
  echo Chat will work now. Image Studio will be ready after installation finishes.
  start "Install Image Backend" "%~dp0install_comfyui.bat"
  timeout /t 5
) else if not exist "ComfyUI\models\checkpoints\*.safetensors" (
  echo ComfyUI found, but no checkpoint. Starting background installer...
  echo Chat will work now. Image Studio will be ready after the model downloads.
  start "Install Image Backend" "%~dp0install_comfyui.bat"
  timeout /t 5
) else (
  echo Detecting GPU support with %PYTHON%...
  %PYTHON% -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
  if errorlevel 1 (
    echo CUDA not available. Starting ComfyUI in CPU mode (slower but works everywhere).
    start "ComfyUI" cmd /c "cd /d ComfyUI && %PYTHON% main.py --listen 127.0.0.1 --port 8188 --cpu"
  ) else (
    REM Check for GPU architectures too new for this PyTorch build (e.g. RTX 50-series sm_120).
    %PYTHON% -c "import torch; cap=torch.cuda.get_device_capability(); exit(0 if cap[0]*10+cap[1] <= 90 else 1)" >nul 2>&1
    if errorlevel 1 (
      for /f "delims=" %%%%g in ('%PYTHON% -c "import torch; print(torch.cuda.get_device_name(0))"') do set "GPU_NAME=%%%%g"
      echo WARNING: %GPU_NAME% is newer than this PyTorch build supports.
      echo Starting ComfyUI in CPU mode so image generation works reliably.
      echo For full GPU speed on this card install a newer PyTorch with CUDA 12.8+.
      start "ComfyUI" cmd /c "cd /d ComfyUI && %PYTHON% main.py --listen 127.0.0.1 --port 8188 --cpu"
    ) else (
      echo CUDA available. Starting ComfyUI with GPU acceleration.
      start "ComfyUI" cmd /c "cd /d ComfyUI && %PYTHON% main.py --listen 127.0.0.1 --port 8188"
    )
  )
  echo ComfyUI launching on http://127.0.0.1:8188
  timeout /t 8
)

echo.
echo Starting web interface...
%PYTHON% app.py

endlocal
