@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero ejecuta instalar_windows.bat
  pause
  exit /b 1
)
echo FastAPI en http://127.0.0.1:8080/docs
".venv\Scripts\python.exe" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8080
pause
