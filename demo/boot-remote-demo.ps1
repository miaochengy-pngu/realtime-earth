<#
  boot-remote-demo.ps1 — Boot Realtime Earth for remote access (background mode).

  This script:
    1. Starts backend on :8000 (background)
    2. Starts frontend static server on :8080 (background)
    3. Starts cloudflared tunnel to :8080 (background)
    4. Waits for public URL and writes it to PUBLIC_URL.txt

  Does NOT block. Re-run stop-remote-demo.ps1 to shut everything down.
#>

$ErrorActionPreference = "Continue"
$ProjectDir = "C:\Users\繆成玉\.mavis\sessions\mvs_0d84bec26def4e9b81feb96737d61ad9\workspace\realtime-earth"
$BackendDir = "$ProjectDir\backend"
$FrontendDir = "$ProjectDir\demo"
$CfExe = "$env:USERPROFILE\tools\cloudflared.exe"
$LogDir = "$env:TEMP\realtime-earth-logs"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "  Realtime Earth — Boot Remote Demo" -ForegroundColor Cyan
Write-Host "================================================`n" -ForegroundColor Cyan

# Clean up any previous run
Get-Process -Name "python", "cloudflared" -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowTitle -eq '' -or $_.ProcessName -eq "cloudflared" } |
    ForEach-Object {
        try { $_ | Stop-Process -Force } catch {}
    }
Start-Sleep -Seconds 1

# ---- 1. Backend ----
Write-Host "[1/3] Starting backend (logs: $LogDir\backend.log)..." -ForegroundColor Yellow
$BackendJob = Start-Job -ScriptBlock {
    param($dir, $log)
    $env:REALTIME_EARTH_LOG_LEVEL = "INFO"
    $env:REALTIME_EARTH_CORS_ORIGINS = "*"
    & cmd /c "cd /d `"$dir`" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info" 2>&1 | Out-File -Append -FilePath $log
} -ArgumentList $BackendDir, "$LogDir\backend.log"
Write-Host "  Backend Job ID: $($BackendJob.Id)" -ForegroundColor Green

# Wait for backend
Write-Host "  Waiting for backend..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/healthz" -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
}
if ($ready) { Write-Host "  Backend ready after ${i}s" -ForegroundColor Green }
else { Write-Host "  WARN: Backend not ready yet, continuing..." -ForegroundColor Yellow }

# ---- 2. Frontend ----
Write-Host "`n[2/3] Starting frontend (logs: $LogDir\frontend.log)..." -ForegroundColor Yellow
$FrontendJob = Start-Job -ScriptBlock {
    param($dir, $log)
    & cmd /c "cd /d `"$dir`" && python -m http.server 8080 --bind 0.0.0.0" 2>&1 | Out-File -Append -FilePath $log
} -ArgumentList $FrontendDir, "$LogDir\frontend.log"
Write-Host "  Frontend Job ID: $($FrontendJob.Id)" -ForegroundColor Green
Start-Sleep -Seconds 2

try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8080/" -TimeoutSec 3
    Write-Host "  Frontend OK: HTTP $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  WARN: Frontend not responding" -ForegroundColor Yellow
}

# ---- 3. cloudflared tunnel ----
Write-Host "`n[3/3] Starting cloudflared tunnel (logs: $LogDir\cloudflared.log)..." -ForegroundColor Yellow
$CfJob = Start-Job -ScriptBlock {
    param($exe, $log)
    & $exe tunnel --url http://127.0.0.1:8080 --no-autoupdate 2>&1 | Out-File -Append -FilePath $log
} -ArgumentList $CfExe, "$LogDir\cloudflared.log"
Write-Host "  cloudflared Job ID: $($CfJob.Id)" -ForegroundColor Green

# Wait for URL
Write-Host "  Waiting for tunnel URL..." -ForegroundColor Yellow
$url = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path "$LogDir\cloudflared.log") {
        $content = Get-Content "$LogDir\cloudflared.log" -Raw -ErrorAction SilentlyContinue
        if ($content -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
            $url = ($content | Select-String -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches).Matches[0].Value
            break
        }
    }
}

if ($url) {
    Write-Host "`n================================================" -ForegroundColor Green
    Write-Host "  TUNNEL READY!" -ForegroundColor Green
    Write-Host "" -ForegroundColor Green
    Write-Host "  Public URL:   $url" -ForegroundColor Yellow
    Write-Host "" -ForegroundColor Green
    Write-Host "  Open this URL in your browser!" -ForegroundColor Yellow
    Write-Host "  Backend:      http://127.0.0.1:8000/healthz" -ForegroundColor Gray
    Write-Host "  Frontend:     http://127.0.0.1:8080" -ForegroundColor Gray
    Write-Host "  Logs:         $LogDir" -ForegroundColor Gray
    Write-Host "================================================`n" -ForegroundColor Green

    $url | Out-File "$ProjectDir\PUBLIC_URL.txt" -Encoding utf8
    Write-Host "  URL saved to: $ProjectDir\PUBLIC_URL.txt" -ForegroundColor Green

    # Save job IDs for cleanup
    @{
        backend = $BackendJob.Id
        frontend = $FrontendJob.Id
        cloudflared = $CfJob.Id
    } | ConvertTo-Json | Out-File "$LogDir\job_ids.json" -Encoding utf8
} else {
    Write-Host "`n  ERR: cloudflared did not produce a URL" -ForegroundColor Red
    Write-Host "  Last log lines:" -ForegroundColor Yellow
    if (Test-Path "$LogDir\cloudflared.log") {
        Get-Content "$LogDir\cloudflared.log" -Tail 30 | ForEach-Object { Write-Host "    $_" }
    }
    Write-Host "`n  Diagnostics:" -ForegroundColor Yellow
    Write-Host "    cloudflared log: $LogDir\cloudflared.log" -ForegroundColor Gray
    Write-Host "    backend log:     $LogDir\backend.log" -ForegroundColor Gray
}
