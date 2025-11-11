# Script PowerShell untuk menjalankan Django development server dengan port yang bisa dipilih
# Usage: .\runserver.ps1 [port]
# Default port: 8000

param(
    [int]$Port = 8000
)

Write-Host "Starting Django development server on port $Port..." -ForegroundColor Green
python manage.py runserver $Port

