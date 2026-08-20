@echo off
setlocal
cd /d "%~dp0\.."
set "OUTPUT=%USERPROFILE%\Desktop\SonicScout"
dotnet publish CSharp\SonicScout.CSharp.csproj --configuration Release --runtime win-x64 --self-contained false --output "%OUTPUT%"
if errorlevel 1 (
  echo Publish failed.
  pause
  exit /b 1
)
if not exist "%OUTPUT%\profiles" mkdir "%OUTPUT%\profiles"
copy /Y "profiles\*.txt" "%OUTPUT%\profiles\" >nul
copy /Y "CSharp\setup_audio_stack.ps1" "%OUTPUT%\setup_audio_stack.ps1" >nul
copy /Y "CSharp\run_audio_stack_setup.bat" "%OUTPUT%\run_audio_stack_setup.bat" >nul
if not exist "%OUTPUT%\installers" mkdir "%OUTPUT%\installers"
if exist "CSharp\installers" (
  xcopy /E /I /Y "CSharp\installers" "%OUTPUT%\installers\" >nul
) else (
  > "%OUTPUT%\installers\PLACE_INSTALLERS_HERE.txt" (
    echo Place dependency installers in this folder before running run_audio_stack_setup.bat:
    echo - Equalizer APO installer
    echo - VB-Cable or Hi-Fi Cable installer
    echo - Voicemeeter installer ^(optional fallback^)
  )
)
echo Published to:
echo %OUTPUT%
pause
endlocal
