$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Find-Python {
    $candidates = @(
        (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python311\python.exe'),
        (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python312\python.exe'),
        (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python313\python.exe'),
        (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python314\python.exe'),
        (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) { return $candidate }
    }
    return $null
}

function Wait-Port($port, $seconds = 60) {
    for ($attempt = 0; $attempt -lt $seconds; $attempt++) {
        if (Test-NetConnection 127.0.0.1 -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Has-RunningProcess($namePattern) {
    return @(Get-CimInstance Win32_Process -Filter "Name LIKE '%python.exe%'" | Where-Object {
        $_.CommandLine -match $namePattern
    }).Count -gt 0
}

$python = Find-Python
if (-not $python) { throw 'Python is not installed. Double-click install.bat first.' }

Write-Host 'Checking local services...'

if (-not (Wait-Port 11434 1)) {
    Write-Host 'Starting Ollama...'
    $ollamaApp = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama app.exe'
    if (Test-Path $ollamaApp) {
        Start-Process $ollamaApp
    } else {
        Start-Process 'ollama' -ArgumentList 'serve'
    }
}
if (-not (Wait-Port 11434 60)) { Write-Warning 'Ollama did not become ready. Chat models may be unavailable.' }

$comfyDir = Join-Path $root 'ComfyUI'
$comfyMain = Join-Path $comfyDir 'main.py'
$checkpoint = Join-Path $root 'ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors'
$comfyReady = Test-Path $checkpoint
if ($comfyReady) { $comfyReady = (Get-Item $checkpoint).Length -ge 6GB }

if (-not (Wait-Port 8188 1)) {
    if (-not (Has-RunningProcess 'ComfyUI\\main\.py')) {
        if (Test-Path $comfyMain) {
            Write-Host 'Starting ComfyUI...'
            Start-Process -FilePath $python -ArgumentList 'main.py --listen 127.0.0.1 --port 8188' -WorkingDirectory $comfyDir
        } else {
            Write-Warning 'ComfyUI main.py was not found; install or repair the ComfyUI folder first.'
        }
    }
}
if ($comfyReady) {
    if (-not (Wait-Port 8188 120)) { Write-Warning 'ComfyUI did not become ready. Image and social generation may be unavailable.' }
} else {
    Write-Warning 'SDXL is not installed yet. Run install.bat to finish image setup.'
}

if (-not (Wait-Port 5000 1)) {
    if (-not (Has-RunningProcess 'app\.py')) {
        Write-Host 'Starting Universal AI Studio...'
        Start-Process -FilePath $python -ArgumentList 'app.py' -WorkingDirectory $root
    }
}
if (Wait-Port 5000 60) {
    Start-Process 'http://127.0.0.1:5000'
    Write-Host 'Universal AI Studio is ready.' -ForegroundColor Green
} else {
    Write-Warning 'Universal AI Studio did not become ready.'
}

if (Wait-Port 8188 30) {
    Write-Host 'ComfyUI is ready.' -ForegroundColor Green
} else {
    Write-Warning 'ComfyUI did not become ready.'
}
