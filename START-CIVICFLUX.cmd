@echo off
cd /d "%~dp0"
if not exist ".venv-windows\Scripts\python.exe" (
  echo Run setup-windows.ps1 first to create the Windows environment.
  pause
  exit /b 1
)
echo CivicFlux: http://127.0.0.1:8000
echo Admin ID: ADMIN001
echo Use the password configured in .env or the requested local demo password.
".venv-windows\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
