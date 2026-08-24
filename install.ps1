$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Require-Command($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "$name is not available. Reopen this installer after winget finishes and try again."
    }
}

Write-Host 'Universal AI Studio setup'
Write-Host 'Installing required programs through winget...'
$packages = @(
    @{ Id = 'Python.Python.3.11'; Name = 'Python 3.11' },
    @{ Id = 'Git.Git'; Name = 'Git' },
    @{ Id = 'Gyan.FFmpeg'; Name = 'FFmpeg' },
    @{ Id = 'Ollama.Ollama'; Name = 'Ollama' }
)
foreach ($package in $packages) {
    Write-Host "Installing $($package.Name)..."
    winget install --id $package.Id --exact --silent --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1978335189) {
        throw "Failed to install $($package.Name) (exit code $LASTEXITCODE)."
    }
}
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')

$pythonCandidates = @(
    'C:\Users\' + $env:USERNAME + '\AppData\Local\Programs\Python\Python311\python.exe',
    (Get-Command python -ErrorAction SilentlyContinue).Source
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $pythonCandidates) { throw 'Python 3.11 was installed but could not be located. Restart Windows and run install.bat again.' }
$python = $pythonCandidates

$ollama = (Get-Command ollama -ErrorAction SilentlyContinue).Source
if (-not $ollama) {
    $ollama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
}
if (-not (Test-Path $ollama)) { throw 'Ollama was installed but could not be located. Restart Windows and run install.bat again.' }
if (-not (Test-NetConnection 127.0.0.1 -Port 11434 -InformationLevel Quiet -WarningAction SilentlyContinue)) {
    Start-Process $ollama -ArgumentList 'serve'
}
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    if (Test-NetConnection 127.0.0.1 -Port 11434 -InformationLevel Quiet -WarningAction SilentlyContinue) { break }
    Start-Sleep -Seconds 1
}
if (-not (Test-NetConnection 127.0.0.1 -Port 11434 -InformationLevel Quiet -WarningAction SilentlyContinue)) { throw 'Ollama did not become ready.' }

Write-Host 'Downloading chat models...'
& $ollama pull qwen2.5-coder:7b-instruct
if ($LASTEXITCODE -ne 0) { throw 'Qwen2.5-Coder download failed. Run install.bat again to retry.' }
& $ollama pull deepseek-coder:6.7b-instruct
if ($LASTEXITCODE -ne 0) { throw 'DeepSeek-Coder download failed. Run install.bat again to retry.' }

New-Item -ItemType Directory -Force -Path 'models', 'workspace', 'workspace\social', 'ComfyUI\models\checkpoints' | Out-Null
Write-Host 'Installing Universal AI Studio Python packages...'
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Universal AI Studio Python dependencies failed to install.' }

if (-not (Test-Path 'ComfyUI\main.py')) {
    Write-Host 'Downloading ComfyUI...'
    Require-Command git
    git clone https://github.com/comfyanonymous/ComfyUI.git ComfyUI
}
Write-Host 'Installing ComfyUI Python packages...'
& $python -m pip install -r ComfyUI\requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'ComfyUI dependencies failed to install.' }

$checkpoint = 'ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors'
$tempCheckpoint = "$checkpoint.download"
if (Test-Path $checkpoint) {
    $existing = Get-Item $checkpoint
    if ($existing.Length -lt 6GB) {
        Move-Item -Force $checkpoint $tempCheckpoint
    }
}
if (-not (Test-Path $checkpoint)) {
    Write-Host 'Downloading SDXL Base (~6.9 GB). This may take a while...'
    curl.exe -L --fail --retry 5 --retry-delay 5 -C - 'https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors' -o $tempCheckpoint
    if ($LASTEXITCODE -ne 0) { throw 'SDXL download failed. Run install.bat again to resume.' }
    Move-Item -Force $tempCheckpoint $checkpoint
}

Write-Host ''
Write-Host 'Installation complete. Double-click run.bat to start everything.' -ForegroundColor Green
Read-Host 'Press Enter to close'
