@echo off
REM End-to-end smoke test for the Social Agent (draft only, no upload).
setlocal
cd /d "%~dp0"

set "PY311=C:\Users\brand\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY311%" (
  set "PYTHON=%PY311%"
) else (
  set "PYTHON=python"
)

echo.
echo ===== SOCIAL AGENT SMOKE TEST =====
echo.
%PYTHON% -m agents.social.cli --topics "AI"
if errorlevel 1 (
    echo.
    echo Smoke test failed. Check output above.
    pause
    exit /b 1
)

echo.
echo Smoke test complete. If a draft video was generated, it is in workspace/social/videos.
echo.
pause
endlocal
