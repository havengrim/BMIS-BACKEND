#!/usr/bin/env bash
# ============================================================
# BMIS Backend — Production Launcher (Linux / EC2 / Ubuntu)
# Usage: bash scripts/prod.sh
#
# Requires: supervisord  OR  systemd (see comments below)
# This script validates, migrates, then starts all processes
# via supervisord in the foreground (ideal for Docker too).
# ============================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

log()  { echo -e "${CYAN}  [BMIS]${NC} $*"; }
ok()   { echo -e "${GREEN}  [ OK ]${NC} $*"; }
warn() { echo -e "${YELLOW}  [ !! ]${NC} $*"; }
fail() { echo -e "${RED}  [ERR]${NC} $*"; exit 1; }

echo ""
echo -e "${CYAN}  ╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}  ║      BMIS Backend — Prod Launcher        ║${NC}"
echo -e "${CYAN}  ╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Pre-flight checks ───────────────────────────────────────
log "Pre-flight checks..."

[[ -f ".env" ]]         || fail ".env not found! Copy .env.example to .env and configure it."
ok ".env found"

[[ -f ".venv/bin/python" ]] || fail "Virtual environment not found. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
ok "Virtual environment found"

source .venv/bin/activate

# Check APP_ENV
APP_ENV_VAL=$(python -c "from app.core.config import settings; print(settings.APP_ENV)" 2>/dev/null || echo "unknown")
if [[ "$APP_ENV_VAL" != "production" ]]; then
    warn "APP_ENV=$APP_ENV_VAL — expected 'production'. Set APP_ENV=production in .env"
fi
ok "APP_ENV=$APP_ENV_VAL"

# Redis check
redis-cli -u "${REDIS_URL:-redis://localhost:6379}" ping > /dev/null 2>&1 \
    && ok "Redis is reachable" \
    || warn "Redis did not respond — rate limiting and auth cache will not work"

# ── Migrations ──────────────────────────────────────────────
log "Running database migrations..."
python -m alembic upgrade head && ok "Migrations up to date" || fail "Migration failed"

# ── Check supervisor ────────────────────────────────────────
if command -v supervisord &>/dev/null; then
    log "Starting via supervisord..."
    supervisord -c scripts/supervisord.conf
    ok "supervisord started — check logs in logs/"
    echo ""
    echo -e "${GREEN}  API running at http://0.0.0.0:8000${NC}"
    exit 0
fi

# ── Fallback: launch processes with & and trap SIGTERM ──────
warn "supervisord not found — starting processes directly (not recommended for prod; install supervisor)"
log "Starting all services..."

WORKERS=${GUNICORN_WORKERS:-4}

# FastAPI via Gunicorn + Uvicorn workers
gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --workers "$WORKERS" \
    --bind 0.0.0.0:8000 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - &
PIDS=($!)
ok "FastAPI started (pid $!)"

# Celery default worker
celery -A app.workers.celery_app worker \
    -Q default \
    --loglevel=warning \
    --concurrency=4 &
PIDS+=($!)
ok "Celery default worker started (pid $!)"

# Celery priority worker
celery -A app.workers.celery_app worker \
    -Q priority \
    --loglevel=warning \
    --concurrency=2 &
PIDS+=($!)
ok "Celery priority worker started (pid $!)"

# Celery Beat
celery -A app.workers.celery_app beat \
    --loglevel=warning &
PIDS+=($!)
ok "Celery Beat started (pid $!)"

echo ""
echo -e "${GREEN}  ╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}  ║   All services running!                  ║${NC}"
echo -e "${GREEN}  ║   API  →  http://0.0.0.0:8000            ║${NC}"
echo -e "${GREEN}  ║   PIDs: ${PIDS[*]}${NC}"
echo -e "${GREEN}  ╚══════════════════════════════════════════╝${NC}"
echo ""

# Trap SIGTERM/SIGINT to shut down all children cleanly
cleanup() {
    log "Shutting down all services..."
    for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
    ok "Done."
}
trap cleanup SIGTERM SIGINT

# Wait for any child to exit
wait "${PIDS[0]}"
