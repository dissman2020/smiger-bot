param(
    [switch]$BuildBackend
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Split-Path -Parent $PSScriptRoot)
}

function Get-CloudflaredPath {
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $candidates = @(
        "C:\Program Files (x86)\cloudflared\cloudflared.exe",
        "C:\Program Files\cloudflared\cloudflared.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) {
            return $path
        }
    }
    throw "cloudflared not found. Install with: winget install --id Cloudflare.cloudflared -e"
}

function Get-EnvValue {
    param(
        [string]$EnvFile,
        [string]$Key
    )
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
    if (-not $line) { return "" }
    return ($line -split "=", 2)[1]
}

function Get-ActiveTelegramToken {
    param([string]$EnvFile)

    $legacy = Get-EnvValue -EnvFile $EnvFile -Key "TELEGRAM_BOT_TOKEN"
    if (-not [string]::IsNullOrWhiteSpace($legacy)) {
        return $legacy
    }

    $accountsRaw = Get-EnvValue -EnvFile $EnvFile -Key "TELEGRAM_BOT_ACCOUNTS"
    if ([string]::IsNullOrWhiteSpace($accountsRaw)) {
        return ""
    }

    try {
        $active = (Get-EnvValue -EnvFile $EnvFile -Key "TELEGRAM_ACTIVE_ACCOUNT").Trim()
        $accounts = $accountsRaw | ConvertFrom-Json
        if ($accounts -isnot [System.Array]) {
            return ""
        }

        function Is-EnabledAccount($acc) {
            if ($null -eq $acc.enabled) { return $true }
            if ($acc.enabled -is [bool]) { return [bool]$acc.enabled }
            $txt = [string]$acc.enabled
            $txt = $txt.Trim().ToLower()
            if ($txt -in @("false", "0", "no", "off")) { return $false }
            return $true
        }

        if (-not [string]::IsNullOrWhiteSpace($active)) {
            foreach ($acc in $accounts) {
                $isEnabled = Is-EnabledAccount $acc
                if ($acc.name -eq $active -and $isEnabled -and -not [string]::IsNullOrWhiteSpace($acc.bot_token)) {
                    return [string]$acc.bot_token
                }
            }
        }

        foreach ($acc in $accounts) {
            $isEnabled = Is-EnabledAccount $acc
            if ($isEnabled -and -not [string]::IsNullOrWhiteSpace($acc.bot_token)) {
                return [string]$acc.bot_token
            }
        }
    }
    catch {
        return ""
    }

    return ""
}

function Set-EnvValue {
    param(
        [string]$EnvFile,
        [string]$Key,
        [string]$Value
    )

    $raw = Get-Content $EnvFile
    $updated = $false
    $out = New-Object System.Collections.Generic.List[string]

    foreach ($line in $raw) {
        if ($line -match "^$Key=") {
            if (-not $updated) {
                $out.Add("$Key=$Value")
                $updated = $true
            }
            continue
        }
        $out.Add($line)
    }

    if (-not $updated) {
        $out.Add("$Key=$Value")
    }

    Set-Content -Path $EnvFile -Value $out -Encoding UTF8
}

function Stop-TunnelFromPid {
    param([string]$PidFile)

    if (-not (Test-Path $PidFile)) { return }
    $pidText = (Get-Content $PidFile -Raw).Trim()
    if ([string]::IsNullOrWhiteSpace($pidText)) { return }

    $procId = [int]$pidText
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($p -and $p.ProcessName -eq "cloudflared") {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

function Stop-RepoCloudflared {
    param(
        [string]$BackendLogPath,
        [string]$FrontendLogPath
    )

    $targets = Get-CimInstance Win32_Process -Filter "name='cloudflared.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and (
                $_.CommandLine.Contains($BackendLogPath) -or
                $_.CommandLine.Contains($FrontendLogPath)
            )
        }

    foreach ($proc in $targets) {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Start-QuickTunnel {
    param(
        [string]$CloudflaredExe,
        [string]$OriginUrl,
        [string]$LogFile,
        [string]$PidFile,
        [int]$MetricsPort
    )

    if (Test-Path $LogFile) { Remove-Item $LogFile -Force }
    if (Test-Path $PidFile) { Remove-Item $PidFile -Force }

    Start-Process -FilePath $CloudflaredExe -ArgumentList @(
        "tunnel",
        "--url", $OriginUrl,
        "--protocol", "http2",
        "--edge-ip-version", "4",
        "--no-autoupdate",
        "--metrics", "127.0.0.1:$MetricsPort",
        "--logfile", $LogFile,
        "--pidfile", $PidFile
    ) | Out-Null
}

function Wait-TunnelUrl {
    param([string]$LogFile)

    $regex = "https://[a-z0-9-]+\.trycloudflare\.com"
    for ($i = 0; $i -lt 45; $i++) {
        Start-Sleep -Seconds 1
        if (-not (Test-Path $LogFile)) { continue }
        $txt = Get-Content $LogFile -Raw
        $matches = [regex]::Matches($txt, $regex) | ForEach-Object { $_.Value } | Select-Object -Unique
        $url = $matches | Where-Object { $_ -ne "https://api.trycloudflare.com" } | Select-Object -Last 1
        if ($url) { return $url }
    }
    throw "Timed out waiting for tunnel URL from $LogFile"
}

function Invoke-GetWithRetry {
    param(
        [string]$Uri,
        [int]$Attempts = 12,
        [int]$DelaySeconds = 3
    )

    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            return Invoke-RestMethod -Method Get -Uri $Uri -TimeoutSec 20
        }
        catch {
            if ($i -eq $Attempts) { return $null }
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    return $null
}

$repoRoot = Get-RepoRoot
$envFile = Join-Path $repoRoot ".env"
if (-not (Test-Path $envFile)) {
    throw ".env not found at $envFile"
}

$cloudflared = Get-CloudflaredPath

$backendLog = Join-Path $repoRoot "cloudflared-backend.log"
$backendPid = Join-Path $repoRoot "cloudflared-backend.pid"
$frontendLog = Join-Path $repoRoot "cloudflared-frontend.log"
$frontendPid = Join-Path $repoRoot "cloudflared-frontend.pid"

Stop-TunnelFromPid -PidFile $backendPid
Stop-TunnelFromPid -PidFile $frontendPid
Stop-RepoCloudflared -BackendLogPath $backendLog -FrontendLogPath $frontendLog

Push-Location $repoRoot
try {
    if ($BuildBackend) {
        docker compose up -d --build
    } else {
        docker compose up -d
    }

    Start-QuickTunnel -CloudflaredExe $cloudflared -OriginUrl "http://localhost:8000" -LogFile $backendLog -PidFile $backendPid -MetricsPort 20241
    Start-QuickTunnel -CloudflaredExe $cloudflared -OriginUrl "http://localhost:3000" -LogFile $frontendLog -PidFile $frontendPid -MetricsPort 20242

    $backendPublic = Wait-TunnelUrl -LogFile $backendLog
    $frontendPublic = Wait-TunnelUrl -LogFile $frontendLog

    Set-EnvValue -EnvFile $envFile -Key "TELEGRAM_ENABLED" -Value "true"
    Set-EnvValue -EnvFile $envFile -Key "TELEGRAM_MODE" -Value "webhook"
    Set-EnvValue -EnvFile $envFile -Key "TELEGRAM_WEBHOOK_BASE_URL" -Value $backendPublic

    docker compose up -d --force-recreate backend
    docker compose build --no-cache frontend --build-arg "NEXT_PUBLIC_API_URL=$backendPublic"
    docker compose up -d --force-recreate frontend

    $token = Get-ActiveTelegramToken -EnvFile $envFile
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        try {
            $webhookInfo = Invoke-RestMethod -Method Get -Uri "https://api.telegram.org/bot$token/getWebhookInfo" -TimeoutSec 20
            $webhookUrl = $webhookInfo.result.url
        }
        catch {
            $webhookUrl = "(failed to query Telegram webhook info)"
        }
    } else {
        $webhookUrl = ""
    }

    $health = Invoke-GetWithRetry -Uri "$backendPublic/api/health" -Attempts 15 -DelaySeconds 3

    Write-Host ""
    Write-Host "Quick Tunnel is ready."
    Write-Host "Frontend URL: $frontendPublic"
    Write-Host "Backend URL:  $backendPublic"
    if ($health) {
        Write-Host "Health:       $($health.status)"
    } else {
        Write-Host "Health:       (unavailable right now, tunnel may still be warming up)"
    }
    if ($webhookUrl) {
        Write-Host "Webhook URL:  $webhookUrl"
    } else {
        Write-Host "Webhook URL:  (TELEGRAM_BOT_TOKEN not set)"
    }
    Write-Host ""
    Write-Host "To stop tunnels: .\scripts\stop_quick_tunnel.ps1"
}
finally {
    Pop-Location
}
