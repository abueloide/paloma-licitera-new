#!/bin/bash

# =================================================================
# PALOMA LICITERA - SCRIPT DE INICIO MEJORADO V2
# =================================================================
# Este script inicia todos los servicios necesarios usando
# el entorno virtual Python para garantizar las dependencias
# =================================================================

set -e  # Salir en caso de error

echo "🐦 ===================================================="
echo "   PALOMA LICITERA - INICIANDO DASHBOARD V2"
echo "===================================================="
echo ""

# ---------------------------------------------
# 1. VERIFICACIONES INICIALES
# ---------------------------------------------
echo "🔍 Verificando entorno..."

# Verificar que existe el entorno virtual
if [ ! -d "venv" ]; then
    echo "❌ No se encontró el entorno virtual"
    echo "   Por favor ejecuta primero: ./install.sh"
    exit 1
fi

# Verificar que existe node_modules
if [ ! -d "frontend/node_modules" ]; then
    echo "❌ No se encontraron las dependencias del frontend"
    echo "   Por favor ejecuta primero: ./install.sh"
    exit 1
fi

# Activar entorno virtual
echo "🔌 Activando entorno virtual Python..."
source venv/bin/activate

# Verificar que uvicorn está instalado
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "❌ uvicorn no está instalado en el entorno virtual"
    echo "   Por favor ejecuta: ./install.sh"
    exit 1
fi

echo "✅ Entorno verificado correctamente"

# ---------------------------------------------
# 2. VERIFICAR POSTGRESQL
# ---------------------------------------------
echo ""
echo "🗄️  Verificando PostgreSQL..."

if ! psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1" > /dev/null 2>&1; then
    echo "❌ No se puede conectar a PostgreSQL"
    echo ""
    echo "   Por favor verifica:"
    echo "   1. PostgreSQL está ejecutándose"
    echo "   2. La base de datos 'paloma_licitera' existe"
    echo "   3. Las credenciales en config.yaml son correctas"
    echo ""
    echo "   Para crear la base de datos:"
    echo "   $ psql -U postgres -c \"CREATE DATABASE paloma_licitera;\""
    echo ""
    echo "   ¿Continuar sin base de datos? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    # Contar registros
    RECORD_COUNT=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
    echo "✅ PostgreSQL conectado"
    echo "📊 Base de datos contiene $RECORD_COUNT licitaciones"
    
    if [ "$RECORD_COUNT" -lt 100 ]; then
        echo "⚠️  La base de datos tiene pocos datos"
        echo "   Considera ejecutar el proceso ETL para obtener más datos"
    fi
fi

# ---------------------------------------------
# 3. LIMPIAR PUERTOS SI ESTÁN OCUPADOS
# ---------------------------------------------
echo ""
echo "🧹 Verificando puertos..."

check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Puerto $1 en uso, liberando..."
        kill -9 $(lsof -ti:$1) 2>/dev/null || true
        sleep 1
    fi
}

check_port 8000
check_port 3001
echo "✅ Puertos listos"

# ---------------------------------------------
# 4. CREAR DIRECTORIOS NECESARIOS
# ---------------------------------------------
mkdir -p logs
mkdir -p data

# ---------------------------------------------
# 5. INICIAR BACKEND
# ---------------------------------------------
echo ""
echo "🚀 Iniciando servicios..."
echo ""
echo "📡 Iniciando Backend API (puerto 8000)..."

# Cambiar al directorio src para que encuentre config.yaml
cd src
python3 -m uvicorn api:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Esperar a que el backend inicie
echo "   Esperando a que el backend inicie..."
for i in {1..10}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "   ✅ Backend iniciado correctamente (PID: $BACKEND_PID)"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "   ❌ El backend no responde después de 10 segundos"
        echo "   Verificando logs..."
        tail -n 20 logs/backend.log
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# ---------------------------------------------
# 6. INICIAR FRONTEND
# ---------------------------------------------
echo ""
echo "🎨 Iniciando Frontend (puerto 3001)..."

cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Esperar a que el frontend inicie
echo "   Esperando a que el frontend inicie..."
for i in {1..15}; do
    if curl -s http://localhost:3001/ > /dev/null 2>&1; then
        echo "   ✅ Frontend iniciado correctamente (PID: $FRONTEND_PID)"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "   ⚠️  El frontend tarda en responder"
        echo "   Puede estar compilando..."
    fi
    sleep 1
done

# ---------------------------------------------
# 7. GUARDAR PIDS
# ---------------------------------------------
echo "BACKEND_PID=$BACKEND_PID" > .pids
echo "FRONTEND_PID=$FRONTEND_PID" >> .pids

# ---------------------------------------------
# 8. MOSTRAR INFORMACIÓN FINAL
# ---------------------------------------------
echo ""
echo "===================================================="
echo "✨ ¡DASHBOARD INICIADO CORRECTAMENTE!"
echo "===================================================="
echo ""
echo "🌐 URLs disponibles:"
echo "   • Dashboard:  http://localhost:3001"
echo "   • API:        http://localhost:8000"
echo "   • API Docs:   http://localhost:8000/docs"
echo ""
echo "📊 Estado:"
echo "   • Backend PID:  $BACKEND_PID"
echo "   • Frontend PID: $FRONTEND_PID"
if [ -n "$RECORD_COUNT" ]; then
    echo "   • Registros BD: $RECORD_COUNT licitaciones"
fi
echo ""
echo "📋 Comandos útiles:"
echo "   • Ver logs backend:  tail -f logs/backend.log"
echo "   • Ver logs frontend: tail -f logs/frontend.log"
echo "   • Detener servicios: ./stop_dashboard.sh"
echo ""
echo "⏹️  Para detener: Ctrl+C o ejecuta ./stop_dashboard.sh"
echo ""

# ---------------------------------------------
# 9. ABRIR NAVEGADOR
# ---------------------------------------------
echo "🌐 Abriendo dashboard en el navegador..."
sleep 2

if command -v open > /dev/null 2>&1; then
    open http://localhost:3001 >/dev/null 2>&1
elif command -v xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost:3001 >/dev/null 2>&1
elif command -v start > /dev/null 2>&1; then
    start http://localhost:3001 >/dev/null 2>&1
fi

# ---------------------------------------------
# 10. MANTENER SCRIPT ACTIVO
# ---------------------------------------------

# Configurar trap para limpiar al salir
trap 'echo ""; echo "🛑 Deteniendo servicios..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true; rm -f .pids; deactivate 2>/dev/null || true; echo "✅ Servicios detenidos"; exit 0' INT TERM

# Monitorear servicios
echo "📍 Monitoreando servicios (Ctrl+C para detener)..."
echo ""

while true; do
    # Verificar que los procesos siguen ejecutándose
    if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "❌ El backend se ha detenido inesperadamente"
        echo "   Revisa logs/backend.log para más detalles"
        kill $FRONTEND_PID 2>/dev/null || true
        rm -f .pids
        exit 1
    fi
    
    if ! ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "❌ El frontend se ha detenido inesperadamente"
        echo "   Revisa logs/frontend.log para más detalles"
        kill $BACKEND_PID 2>/dev/null || true
        rm -f .pids
        exit 1
    fi
    
    sleep 5
done
