@echo off
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
  echo Requesting administrator access for Sonic Scout audio setup...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs -Wait"
  set "RESULT=%ERRORLEVEL%"
  endlocal
  exit /b %RESULT%
)

set "SETUP_SCRIPT=%~dp0setup_audio_stack.ps1"
if not exist "%SETUP_SCRIPT%" (
  echo setup_audio_stack.ps1 was not found.
  pause
  exit /b 1
)

set "INSTALLERS=%~dp0installers"
if not exist "%INSTALLERS%\EqualizerAPO_Setup.exe" (
  set "DOWNLOAD_DEPENDENCIES=1"
)
if not exist "%INSTALLERS%\VBCABLE_Setup_x64.exe" (
  set "DOWNLOAD_DEPENDENCIES=1"
)
if not exist "%INSTALLERS%\HIFI_CABLE_Setup_x64.exe" (
  set "DOWNLOAD_DEPENDENCIES=1"
)

if defined DOWNLOAD_DEPENDENCIES (
  echo Downloading required Sonic Scout audio dependencies...
  call "%~dp0auto_setup_dependencies.bat" /download-only
  if errorlevel 1 (
    echo Audio dependency download failed. Setup cannot continue.
    pause
    exit /b 1
  )
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SETUP_SCRIPT%" -Mode Install
set "RESULT=%ERRORLEVEL%"

if "%RESULT%"=="0" (
  echo.
  echo Sonic Scout audio stack setup completed successfully.
) else (
  echo.
  echo Sonic Scout audio stack setup needs attention. Exit code: %RESULT%
)

pause
endlocal
exit /b %RESULT%
