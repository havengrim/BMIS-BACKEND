Set-Location (Split-Path $PSScriptRoot -Parent)
. ".\.venv\Scripts\Activate.ps1"
celery -A app.workers.celery_app beat --loglevel=info
