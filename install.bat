@echo off
REM Universal AI Studio - ONE-CLICK INSTALLER
REM Install on any PC: Ollama + 2 Models + Web UI
REM Everything runs locally - zero cloud dependency

setlocal enabledelayedexpansion

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
python -m pip install -q -r requirements.txt
echo OK - Dependencies installed
echo.

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
echo   * Zero cloud dependency - runs locally
echo.
pause
