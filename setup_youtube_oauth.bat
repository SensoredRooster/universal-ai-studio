@echo off
REM Helper to create the YouTube OAuth client secret directory.
REM Download your Desktop OAuth 2.0 client_secret.json from
REM https://console.cloud.google.com/apis/credentials and place it here.
setlocal
cd /d "%~dp0"

set "DEST=workspace\social\client_secret.json"

if not exist "workspace\social" mkdir "workspace\social"

echo.
echo =====================================================
echo    YOUTUBE OAUTH SETUP
echo =====================================================
echo.
echo 1. Go to https://console.cloud.google.com/apis/credentials
echo 2. Create a project and enable the YouTube Data API v3
echo 3. Create OAuth 2.0 Desktop credentials
echo 4. Download the JSON file and rename it to client_secret.json
echo 5. Copy it to:
echo    %~dp0%DEST%
echo.

if exist "%DEST%" (
    echo Found existing client_secret.json. You can test upload now.
) else (
    echo client_secret.json NOT FOUND at %DEST%
    echo The first upload will fail until this file is in place.
)

echo.
pause
endlocal
