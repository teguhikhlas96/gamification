# Script PowerShell untuk menjalankan Django development server dengan port yang bisa dipilih
# Usage: .\runserver.ps1 [port]
# Default port: 8000

param(
    [int]$Port = 8000
)

Write-Host "Starting Django development server on port $Port..." -ForegroundColor Green

# Default: disable Redis for local dev unless explicitly enabled
if (-not $env:REDIS_ENABLED) {
    $env:REDIS_ENABLED = "false"
    Write-Host "REDIS_ENABLED not set. Using default: $env:REDIS_ENABLED" -ForegroundColor Yellow
}

python manage.py runserver $Port

