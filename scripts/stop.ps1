# BMIS Backend - Stop All Services
# Run from the project root: .\scripts\stop.ps1

$root    = Split-Path $PSScriptRoot -Parent
$pidFile = "$root\.bmis-pids"

function Write-Ok   { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  [!!]  $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "  +-----------------------------------------+" -ForegroundColor Red
Write-Host "  |     BMIS Backend - Stop All Services    |" -ForegroundColor Red
Write-Host "  +-----------------------------------------+" -ForegroundColor Red
Write-Host ""

# --- Kill tracked PowerShell windows by PID (from dev.ps1) ---
if (Test-Path $pidFile) {
    $savedPids = Get-Content $pidFile
    foreach ($pid in $savedPids) {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Ok "Stopped window PID $pid ($($proc.Name))"
        }
    }
    Remove-Item $pidFile -Force
    Write-Ok "PID file cleaned up"
} else {
    Write-Warn "No .bmis-pids file found - trying fallback process kill..."
}

# --- Fallback: kill by process name (uvicorn, celery, python with celery_app) ---
$uvicorn = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
if ($uvicorn) {
    Stop-Process -Name "uvicorn" -Force -ErrorAction SilentlyContinue
    Write-Ok "FastAPI (uvicorn) force-stopped"
}

$celery = Get-Process -Name "celery" -ErrorAction SilentlyContinue
if ($celery) {
    Stop-Process -Name "celery" -Force -ErrorAction SilentlyContinue
    Write-Ok "Celery processes force-stopped ($($celery.Count) process(es))"
}

$celeryPy = Get-WmiObject Win32_Process -Filter "CommandLine LIKE '%celery_app%'" -ErrorAction SilentlyContinue
if ($celeryPy) {
    $celeryPy | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Ok "Celery subprocesses force-stopped"
}

Write-Host ""
Write-Host "  +-----------------------------------------+" -ForegroundColor Green
Write-Host "  |   All services stopped.                 |" -ForegroundColor Green
Write-Host "  +-----------------------------------------+" -ForegroundColor Green
Write-Host ""
