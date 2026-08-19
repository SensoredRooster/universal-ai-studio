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

echo Starting web interface...
python app.py

endlocal
