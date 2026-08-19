@echo off
REM Universal AI Studio - ComfyUI + SDXL installer
REM Called automatically by run.bat if image backend is missing.

setlocal
cd /d "%~dp0"

title Universal AI Studio - Installing Image Backend

echo.
echo =====================================================
echo    INSTALLING IMAGE STUDIO BACKEND
echo =====================================================
echo.
echo This downloads ComfyUI + SDXL Base (~7GB).
echo The chat features will work while this runs.
echo.

if not exist "ComfyUI" (
  echo [1/3] Cloning ComfyUI...
  git clone https://github.com/comfyanonymous/ComfyUI.git ComfyUI
) else (
  echo [1/3] ComfyUI already cloned.
)

echo.
echo [2/3] Installing ComfyUI dependencies...
python -m pip install -q -r ComfyUI\requirements.txt

echo.
echo Detecting GPU support...
python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
if errorlevel 1 (
  echo CUDA not available for this Python install. ComfyUI will run in CPU mode.
  echo For GPU speed, use Python 3.11/3.12 and reinstall torch with CUDA.
) else (
  echo CUDA available. GPU acceleration enabled.
)

echo.
echo [3/3] Downloading SDXL Base checkpoint (~6.9GB)...
if not exist "ComfyUI\models\checkpoints" mkdir "ComfyUI\models\checkpoints"
if not exist "ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors" (
  powershell -Command "try { Invoke-WebRequest -Uri 'https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors' -OutFile 'ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors' -ErrorAction Stop; Write-Host 'SDXL download complete.' } catch { Write-Host 'ERROR: Failed to download SDXL. You can rerun this script or place your own .safetensors in ComfyUI\models\checkpoints' }"
) else (
  echo SDXL checkpoint already exists.
)

echo.
echo =====================================================
echo    IMAGE BACKEND READY
echo =====================================================
echo.
echo Close this window and restart run.bat to use Image Studio.
echo.
pause
endlocal
