@echo off
REM Script untuk menjalankan Django development server dengan port yang bisa dipilih
REM Usage: runserver.bat [port]
REM Default port: 8000

set PORT=%1
if "%PORT%"=="" set PORT=8000

echo Starting Django development server on port %PORT%...

REM Default: disable Redis for local dev unless explicitly enabled
IF "%REDIS_ENABLED%"=="" (
  set REDIS_ENABLED=false
  echo REDIS_ENABLED not set. Using default: %REDIS_ENABLED%
)

python manage.py runserver %PORT%

