Set-Location (Split-Path $PSScriptRoot -Parent)
. ".\.venv\Scripts\Activate.ps1"
uvicorn app.main:app --reload --port 8000
Read-Host "Press Enter to close"
