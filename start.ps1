$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = @(
    'C:\Users\' + $env:USERNAME + '\AppData\Local\Programs\Python\Python311\python.exe',
    (Get-Command python -ErrorAction SilentlyContinue).Source
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $python) { throw 'Python is not installed. Double-click install.bat first.' }

function Wait-Port($port, $seconds = 60) {
    for ($attempt = 0; $attempt -lt $seconds; $attempt++) {
        if (Test-NetConnection 127.0.0.1 -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

Write-Host 'Starting Ollama...'
if (-not (Wait-Port 11434 1)) {
    $ollamaApp = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama app.exe'
    if (Test-Path $ollamaApp) { Start-Process $ollamaApp } else { Start-Process 'ollama' -ArgumentList 'serve' }
}
if (-not (Wait-Port 11434 60)) { Write-Warning 'Ollama did not become ready. Chat models may be unavailable.' }

$checkpoint = Join-Path $root 'ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors'
$comfyReady = Test-Path $checkpoint
if ($comfyReady) { $comfyReady = (Get-Item $checkpoint).Length -ge 6GB }
if ($comfyReady -and -not (Wait-Port 8188 1)) {
    Write-Host 'Starting ComfyUI...'
    Start-Process -FilePath $python -ArgumentList 'main.py --listen 127.0.0.1 --port 8188' -WorkingDirectory (Join-Path $root 'ComfyUI')
}
if ($comfyReady) {
    if (-not (Wait-Port 8188 120)) { Write-Warning 'ComfyUI did not become ready. Image and social generation may be unavailable.' }
} else {
    Write-Warning 'SDXL is not installed yet. Run install.bat to finish image setup.'
}

if (-not (Wait-Port 5000 1)) {
    Write-Host 'Starting Universal AI Studio...'
    Start-Process -FilePath $python -ArgumentList 'app.py' -WorkingDirectory $root
}
if (Wait-Port 5000 60) {
    Start-Process 'http://127.0.0.1:5000'
    Write-Host 'Universal AI Studio is ready.' -ForegroundColor Green
} else {
    Write-Warning 'Universal AI Studio did not become ready.'
}
