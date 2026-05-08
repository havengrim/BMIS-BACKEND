# BMIS Backend - Stop All Services
# Run from the project root: .\scripts\stop.ps1

function Write-Ok   { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  [!!]  $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "  +-----------------------------------------+" -ForegroundColor Red
Write-Host "  |     BMIS Backend - Stop All Services    |" -ForegroundColor Red
Write-Host "  +-----------------------------------------+" -ForegroundColor Red
Write-Host ""

# Stop uvicorn (FastAPI)
$uvicorn = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
if ($uvicorn) {
    Stop-Process -Name "uvicorn" -Force
    Write-Ok "FastAPI (uvicorn) stopped"
} else {
    Write-Warn "FastAPI (uvicorn) was not running"
}

# Stop celery workers
$celery = Get-Process -Name "celery" -ErrorAction SilentlyContinue
if ($celery) {
    Stop-Process -Name "celery" -Force
    Write-Ok "Celery workers stopped ($($celery.Count) process(es))"
} else {
    Write-Warn "Celery was not running"
}

# Stop any python processes spawned by celery (worker subprocesses)
$celeryPy = Get-WmiObject Win32_Process -Filter "CommandLine LIKE '%celery_app%'" -ErrorAction SilentlyContinue
if ($celeryPy) {
    $celeryPy | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Ok "Celery subprocesses stopped"
}

Write-Host ""
Write-Host "  +-----------------------------------------+" -ForegroundColor Green
Write-Host "  |   All services stopped.                 |" -ForegroundColor Green
Write-Host "  +-----------------------------------------+" -ForegroundColor Green
Write-Host ""
