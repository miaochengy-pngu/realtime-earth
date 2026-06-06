<#
  stop-remote-demo.ps1 — Stop all Realtime Earth demo processes.
#>

$ErrorActionPreference = "Continue"

Write-Host "Stopping Realtime Earth demo processes..." -ForegroundColor Yellow

# Kill by name
@("python", "cloudflared") | ForEach-Object {
    $procs = Get-Process -Name $_ -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        try { $p | Stop-Process -Force -ErrorAction SilentlyContinue } catch {}
        Write-Host "  Stopped $($p.ProcessName) PID $($p.Id)" -ForegroundColor Green
    }
}

# Also kill any uvicorn workers
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | ForEach-Object {
    try { $_ | Stop-Process -Force } catch {}
    Write-Host "  Stopped uvicorn PID $($_.Id)" -ForegroundColor Green
}

# Stop background jobs
$LogDir = "C:\Users\繆成玉\.mavis\sessions\mvs_0d84bec26def4e9b81feb96737d61ad9\workspace\realtime-earth\logs"
$jobFile = "$LogDir\job_ids.json"
if (Test-Path $jobFile) {
    $ids = Get-Content $jobFile -Raw | ConvertFrom-Json
    foreach ($prop in $ids.PSObject.Properties) {
        $job = Get-Job -Id $prop.Value -ErrorAction SilentlyContinue
        if ($job) {
            Stop-Job $job
            Remove-Job $job
            Write-Host "  Stopped Job $($prop.Name) (ID $($prop.Value))" -ForegroundColor Green
        }
    }
}

Write-Host "`nDone." -ForegroundColor Green
