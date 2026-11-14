@echo off
cd /d "%~dp0\frontend"
where npm >nul 2>nul
if errorlevel 1 (
  echo ERROR: instala Node.js y npm primero.
  pause
  exit /b 1
)
if not exist "node_modules" (
  echo Instalando dependencias web...
  call npm install
  if errorlevel 1 (
    echo ERROR al instalar paquetes.
    pause
    exit /b 1
  )
)
echo React en http://127.0.0.1:5173
call npm run dev
pause
