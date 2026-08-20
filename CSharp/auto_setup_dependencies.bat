@echo off
REM Sonic Scout - Auto Dependency Downloader + Installer

net session >nul 2>&1
if errorlevel 1 (
  echo Requesting admin access...
  powershell -Command "Start-Process '%~f0' -Verb RunAs -Wait"
  pause
  exit /b
)

title Sonic Scout - Dependency Setup
cd /d "%~dp0"
cls

echo.
echo =====================================================
echo    SONIC SCOUT - AUTO DEPENDENCY SETUP
echo =====================================================
echo.

set "INSTALLERS=%~dp0installers"
if not exist "%INSTALLERS%" mkdir "%INSTALLERS%"

echo [1/3] Downloading Equalizer APO...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://sourceforge.net/projects/equalizerapo/files/latest/download', '%INSTALLERS%\EqualizerAPO_Setup.exe')"
if exist "%INSTALLERS%\EqualizerAPO_Setup.exe" (
  echo [OK] Equalizer APO downloaded
) else (
  echo [FAIL] Equalizer APO download failed
)
echo.

echo [2/3] Downloading VB-Cable...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip', '%INSTALLERS%\VBCABLE_Driver.zip')"
if exist "%INSTALLERS%\VBCABLE_Driver.zip" (
  powershell -Command "Expand-Archive -Path '%INSTALLERS%\VBCABLE_Driver.zip' -DestinationPath '%INSTALLERS%\VBCABLE' -Force"
  copy /Y "%INSTALLERS%\VBCABLE\VBCABLE_Setup_x64.exe" "%INSTALLERS%\VBCABLE_Setup_x64.exe" >nul 2>&1
  echo [OK] VB-Cable downloaded
) else (
  echo [FAIL] VB-Cable download failed
)
echo.

echo [3/3] Downloading VB-Cable Hi-Fi...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://download.vb-audio.com/Download_CABLE/VBHIFICABLE_Driver_Pack43.zip', '%INSTALLERS%\VBHIFI_Driver.zip')"
if exist "%INSTALLERS%\VBHIFI_Driver.zip" (
  powershell -Command "Expand-Archive -Path '%INSTALLERS%\VBHIFI_Driver.zip' -DestinationPath '%INSTALLERS%\VBHIFI' -Force"
  copy /Y "%INSTALLERS%\VBHIFI\VBCABLE_Setup_x64.exe" "%INSTALLERS%\HIFI_CABLE_Setup_x64.exe" >nul 2>&1
  echo [OK] VB-Cable Hi-Fi downloaded
) else (
  echo [FAIL] VB-Cable Hi-Fi download failed
)
echo.

echo Running Sonic Scout audio stack setup...
echo.
call "%~dp0run_audio_stack_setup.bat"

echo.
echo =====================================================
echo    DONE - RESTART YOUR PC WHEN COMPLETE
echo =====================================================
echo.
pause
