<#
  serve-remote.ps1 — Boot Realtime Earth for remote demo access.

  Starts:
    1. FastAPI backend on :8000
    2. Static frontend on :8080 (proxies /api and /ws to :8000)
    3. cloudflared tunnel exposing :8080 to a public trycloudflare.com URL

  Output: a public HTTPS URL that anyone can open in their browser.
#>

$ErrorActionPreference = "Continue"
$BackendDir = "C:\Users\繆成玉\.mavis\sessions\mvs_0d84bec26def4e9b81feb96737d61ad9\workspace\realtime-earth\backend"
$FrontendDir = "C:\Users\繆成玉\.mavis\sessions\mvs_0d84bec26def4e9b81feb96737d61ad9\workspace\realtime-earth\demo"
$CfExe = "$env:USERPROFILE\tools\cloudflared.exe"

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "  Realtime Earth — Remote Demo Launcher" -ForegroundColor Cyan
Write-Host "================================================`n" -ForegroundColor Cyan

# ---- 1. Start backend ----
Write-Host "[1/3] Starting backend on :8000..." -ForegroundColor Yellow
$BackendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    $env:REALTIME_EARTH_LOG_LEVEL = "INFO"
    $env:REALTIME_EARTH_CORS_ORIGINS = "*"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
} -ArgumentList $BackendDir
Write-Host "  Backend PID: $($BackendJob.Id)" -ForegroundColor Green

# Wait for backend
Write-Host "  Waiting for backend to be ready..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/healthz" -TimeoutSec 3
        if ($r.StatusCode -eq 200) {
            $ready = $true
            Write-Host "  Backend ready after ${i}s" -ForegroundColor Green
            break
        }
    } catch { }
}
if (-not $ready) {
    Write-Host "  WARN: Backend not responding on :8000 yet, but continuing..." -ForegroundColor Yellow
}

# ---- 2. Start frontend (simple Python HTTP server) ----
Write-Host "`n[2/3] Starting frontend on :8080..." -ForegroundColor Yellow
$FrontendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    python -m http.server 8080 --bind 0.0.0.0
} -ArgumentList $FrontendDir
Write-Host "  Frontend PID: $($FrontendJob.Id)" -ForegroundColor Green

Start-Sleep -Seconds 2
try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8080/" -TimeoutSec 3
    Write-Host "  Frontend serving HTTP $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  WARN: Frontend not responding on :8080" -ForegroundColor Yellow
}

# ---- 3. Start cloudflared tunnel ----
Write-Host "`n[3/3] Starting cloudflared tunnel..." -ForegroundColor Yellow
if (-not (Test-Path $CfExe)) {
    Write-Host "  ERR: cloudflared not found at $CfExe" -ForegroundColor Red
} else {
    $CfJob = Start-Job -ScriptBlock {
        param($exe)
        & $exe tunnel --url http://127.0.0.1:8080 --no-autoupdate 2>&1
    } -ArgumentList $CfExe

    Write-Host "  cloudflared PID: $($CfJob.Id)" -ForegroundColor Green
    Write-Host "  Waiting for tunnel URL (this usually takes 5-15s)..." -ForegroundColor Yellow

    $url = $null
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        $logs = Receive-Job $CfJob -Keep 2>&1 | Out-String
        if ($logs -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
            $url = ($logs | Select-String -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches).Matches[0].Value
            break
        }
    }

    if ($url) {
        Write-Host "`n================================================" -ForegroundColor Green
        Write-Host "  TUNNEL READY!" -ForegroundColor Green
        Write-Host "  Public URL: $url" -ForegroundColor Yellow
        Write-Host "  Open this URL in any browser." -ForegroundColor Yellow
        Write-Host "================================================`n" -ForegroundColor Green

        # Persist URL to file
        $url | Out-File "C:\Users\繆成玉\.mavis\sessions\mvs_0d84bec26def4e9b81feb96737d61ad9\workspace\realtime-earth\PUBLIC_URL.txt"

        # Tail the tunnel logs
        Write-Host "Tailing cloudflared logs (Ctrl+C to stop everything)..." -ForegroundColor Cyan
        while ($true) {
            $logs = Receive-Job $CfJob -Keep 2>&1
            foreach ($l in $logs) { Write-Host "[cf] $l" }
            Start-Sleep -Seconds 1
        }
    } else {
        Write-Host "  ERR: cloudflared did not produce a URL after 30s" -ForegroundColor Red
        Write-Host "  Last logs:" -ForegroundColor Yellow
        Receive-Job $CfJob -Keep 2>&1 | Select-Object -Last 30 | ForEach-Object { Write-Host "    $_" }
    }
}
