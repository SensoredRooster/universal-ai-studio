@echo off
REM Registers a daily Windows Task Scheduler job for the Social Agent.
REM The agent will generate and post YouTube Shorts at the scheduled times.
setlocal
cd /d "%~dp0"

set "PY311=C:\Users\brand\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY311%" (
  set "PYTHON=%PY311%"
) else (
  set "PYTHON=python"
)

set "TASK_NAME=UniversalAI-SocialAgent"
set "SCRIPT=%~dp0agents\social\cli.py"
set "LOG=%~dp0workspace\social\scheduler.log"

if not exist "workspace\social" mkdir "workspace\social"

echo.
echo Registering task: %TASK_NAME%
echo.

schtasks /Create ^
  /TN "%TASK_NAME%" ^
  /TR "\"%PYTHON%\" \"%SCRIPT%\" --scheduler" ^
  /SC DAILY ^
  /ST 08:00 ^
  /RL HIGHEST ^
  /F ^
  /RU "%USERNAME%"

if errorlevel 1 (
    echo.
    echo Failed to register task. Run this batch as Administrator.
    pause
    exit /b 1
)

echo.
echo Task registered. It will run daily at 08:00.
echo Logs will be written to: %LOG%
echo.
pause
endlocal
