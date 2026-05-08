Set-Location (Split-Path $PSScriptRoot -Parent)
. ".\.venv\Scripts\Activate.ps1"
celery -A app.workers.celery_app worker -Q default --loglevel=info --pool=solo
Read-Host "Press Enter to close"
