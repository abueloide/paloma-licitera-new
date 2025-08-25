@echo off
REM Paloma Licitera - Windows Startup Script

echo 🕊️  Paloma Licitera - Iniciando proyecto...
echo.

REM Verificar si estamos en el directorio correcto
if not exist "requirements.txt" (
    echo ❌ Error: No se encontró requirements.txt
    echo    Asegúrate de ejecutar este script desde la raíz del proyecto
    pause
    exit /b 1
)

REM Crear entorno virtual si no existe
if not exist ".venv" (
    echo ⚠️  Creando entorno virtual...
    python -m venv .venv
)

REM Activar entorno virtual
call .venv\Scripts\activate.bat

REM Instalar dependencias de Python
echo 📦 Instalando dependencias de Python...
pip install -r requirements.txt > nul 2>&1

echo 📊 Iniciando backend en segundo plano...
start /B python -m src.dashboard.main

REM Esperar un poco para que el backend inicie
timeout /t 3 /nobreak > nul

REM Cambiar al directorio frontend
cd frontend

REM Instalar dependencias de Node.js si no existen
if not exist "node_modules" (
    echo 📦 Instalando dependencias de Node.js...
    call npm install
)

echo 🎨 Iniciando frontend...
echo.
echo 🚀 Proyecto iniciado!
echo.
echo 📊 Backend:  http://localhost:8000
echo 🎨 Frontend: http://localhost:3001
echo.
echo 💡 Para detener, cierra esta ventana
echo.

REM Iniciar el frontend (esto mantendrá la ventana abierta)
call npm run dev

REM El frontend se ejecutará hasta que se cierre la ventana
pause