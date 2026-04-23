param(
    [switch]$StopCompose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Stop-TunnelFromPid {
    param([string]$PidFile)

    if (-not (Test-Path $PidFile)) { return }
    $pidText = (Get-Content $PidFile -Raw).Trim()
    if ([string]::IsNullOrWhiteSpace($pidText)) {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return
    }

    $procId = [int]$pidText
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($p -and $p.ProcessName -eq "cloudflared") {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }

    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendPid = Join-Path $repoRoot "cloudflared-backend.pid"
$frontendPid = Join-Path $repoRoot "cloudflared-frontend.pid"

Stop-TunnelFromPid -PidFile $backendPid
Stop-TunnelFromPid -PidFile $frontendPid

if ($StopCompose) {
    Push-Location $repoRoot
    try {
        docker compose down
    }
    finally {
        Pop-Location
    }
}

Write-Host "Quick tunnels stopped."
if ($StopCompose) {
    Write-Host "Docker services stopped."
}
