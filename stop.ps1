$ErrorActionPreference = 'Continue'

$processes = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine -match 'app\.py'
}) + @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine -match 'main\.py.*--listen\s+127\.0\.0\.1\s+--port\s+8188'
})

$uniqueProcesses = @{}
foreach ($proc in $processes) {
    if ($proc -and $proc.ProcessId -and -not $uniqueProcesses.ContainsKey([string]$proc.ProcessId)) {
        $uniqueProcesses[[string]$proc.ProcessId] = $proc
    }
}

if ($uniqueProcesses.Count -eq 0) {
    Write-Host 'No Universal AI Studio or ComfyUI processes were found running.'
    exit 0
}

foreach ($proc in $uniqueProcesses.Values) {
    try {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        Write-Host "Stopped PID $($proc.ProcessId): $($proc.CommandLine)"
    } catch {
        Write-Warning "Could not stop PID $($proc.ProcessId): $($_.Exception.Message)"
    }
}
