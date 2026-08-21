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
  echo Starting ComfyUI in CPU mode for reliable compatibility...
  start "ComfyUI" cmd /c "cd /d ComfyUI && %PYTHON% main.py --listen 127.0.0.1 --port 8188 --cpu"
  echo ComfyUI launching on http://127.0.0.1:8188
  timeout /t 8
)

echo.
echo Starting web interface...
%PYTHON% app.py

endlocal
