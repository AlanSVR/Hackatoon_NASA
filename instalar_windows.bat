@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python no aparece en PATH.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" tools\generate_demo.py
if errorlevel 1 goto fail
echo.
echo BACKEND INSTALADO. Abre iniciar_backend.bat.
echo Para la web ejecuta iniciar_frontend.bat (necesitas Node.js).
pause
exit /b 0
:fail
echo ERROR: revisa los mensajes anteriores.
pause
exit /b 1
