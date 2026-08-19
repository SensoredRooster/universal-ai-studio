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
if exist "ComfyUI\main.py" (
  start "ComfyUI" cmd /c "cd /d ComfyUI && python main.py --listen 127.0.0.1 --port 8188"
  echo ComfyUI launching on http://127.0.0.1:8188
  timeout /t 8
) else (
  echo ComfyUI not found. Image Studio will be unavailable until you run install.bat.
)

echo.
echo Starting web interface...
python app.py

endlocal
