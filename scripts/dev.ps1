# BMIS Backend - Development Launcher (Windows)
# Run from the project root: .\scripts\dev.ps1

$root     = Split-Path $PSScriptRoot -Parent
$python   = "$root\.venv\Scripts\python.exe"
$scripts  = $PSScriptRoot

function Write-Header { param($msg) Write-Host "`n  $msg" -ForegroundColor Cyan }
function Write-Ok     { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn   { param($msg) Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Fail   { param($msg) Write-Host "  [ERR] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "  +-----------------------------------------+" -ForegroundColor Cyan
Write-Host "  |     BMIS Backend - Dev Launcher         |" -ForegroundColor Cyan
Write-Host "  +-----------------------------------------+" -ForegroundColor Cyan

# --- Pre-flight checks ---

Write-Header "Pre-flight checks..."

if (-not (Test-Path "$root\.env")) {
    Write-Fail ".env not found! Copy .env.example to .env and fill in your values."
    exit 1
}
Write-Ok ".env found"

if (-not (Test-Path $python)) {
    Write-Fail "Virtual environment not found."
    Write-Fail "Run: python -m venv .venv  then  pip install -r requirements.txt"
    exit 1
}
Write-Ok "Virtual environment found"

$redisRunning = $false
try {
    $ping = redis-cli ping 2>$null
    if ($ping -eq "PONG") { $redisRunning = $true }
} catch {}

if (-not $redisRunning) {
    Write-Warn "Redis not responding - trying to start redis-server..."
    try {
        Start-Process -FilePath "redis-server" -WindowStyle Minimized -ErrorAction Stop
        Start-Sleep -Seconds 2
        Write-Ok "Redis started"
    } catch {
        Write-Warn "Could not auto-start Redis."
        Write-Warn "Start Redis manually or via Docker: docker run -d -p 6379:6379 redis:7-alpine"
    }
} else {
    Write-Ok "Redis is running"
}

# --- Run migrations ---

Write-Header "Running database migrations..."
Set-Location $root
& $python -m alembic upgrade head
if ($LASTEXITCODE -eq 0) {
    Write-Ok "Migrations up to date"
} else {
    Write-Fail "Migration failed - check your DATABASE_URL in .env"
    exit 1
}

# --- Launch services ---

Write-Header "Starting services..."

$useWT = $false
try { Get-Command wt -ErrorAction Stop | Out-Null; $useWT = $true } catch {}

$api      = "$scripts\_start-api.ps1"
$celeryD  = "$scripts\_start-celery-default.ps1"
$celeryP  = "$scripts\_start-celery-priority.ps1"
$celeryB  = "$scripts\_start-celery-beat.ps1"

if ($useWT) {
    Write-Ok "Windows Terminal detected - opening tabs..."
    $wtArgs = @(
        "new-tab", "--title", "FastAPI",           "powershell", "-NoExit", "-File", "`"$api`"",
        ";", "new-tab", "--title", "Celery-Default",  "powershell", "-NoExit", "-File", "`"$celeryD`"",
        ";", "new-tab", "--title", "Celery-Priority", "powershell", "-NoExit", "-File", "`"$celeryP`"",
        ";", "new-tab", "--title", "Celery-Beat",     "powershell", "-NoExit", "-File", "`"$celeryB`""
    )
    Start-Process wt -ArgumentList $wtArgs
} else {
    Write-Ok "Opening separate PowerShell windows..."
    Start-Process powershell -ArgumentList "-NoExit", "-File", "`"$api`""
    Start-Sleep -Milliseconds 600
    Start-Process powershell -ArgumentList "-NoExit", "-File", "`"$celeryD`""
    Start-Sleep -Milliseconds 600
    Start-Process powershell -ArgumentList "-NoExit", "-File", "`"$celeryP`""
    Start-Sleep -Milliseconds 600
    Start-Process powershell -ArgumentList "-NoExit", "-File", "`"$celeryB`""
}

Write-Host ""
Write-Host "  +-----------------------------------------+" -ForegroundColor Green
Write-Host "  |   All services launched!                |" -ForegroundColor Green
Write-Host "  |                                         |" -ForegroundColor Green
Write-Host "  |   API  ->  http://localhost:8000        |" -ForegroundColor Green
Write-Host "  |   Docs ->  http://localhost:8000/docs   |" -ForegroundColor Green
Write-Host "  +-----------------------------------------+" -ForegroundColor Green
Write-Host ""
