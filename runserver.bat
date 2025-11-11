@echo off
REM Script untuk menjalankan Django development server dengan port yang bisa dipilih
REM Usage: runserver.bat [port]
REM Default port: 8000

set PORT=%1
if "%PORT%"=="" set PORT=8000

echo Starting Django development server on port %PORT%...
python manage.py runserver %PORT%

