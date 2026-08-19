@echo off
REM Universal AI Studio - LAUNCHER
REM Run this daily to start your AI Studio

setlocal
cd /d "%~dp0"

echo.
echo ===== UNIVERSAL AI STUDIO =====
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
  start "ComfyUI" cmd /c "cd /d ComfyUI && python main.py --listen 127.0.0.1 --port 8188"
  echo ComfyUI launching on http://127.0.0.1:8188
  timeout /t 8
)

echo.
echo Starting web interface...
python app.py

endlocal
