Set-Location (Split-Path $PSScriptRoot -Parent)
. ".\.venv\Scripts\Activate.ps1"
celery -A app.workers.celery_app worker -Q priority --loglevel=info --pool=solo
