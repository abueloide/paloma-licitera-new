#!/bin/bash

# Script para iniciar el dashboard de Paloma Licitera

echo "🐦 Iniciando Paloma Licitera Dashboard..."

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    exit 1
fi

# Verificar si Node.js está instalado
if ! command -v node &> /dev/null; then
    echo "❌ Node.js no está instalado"
    exit 1
fi

# Verificar PostgreSQL
if ! psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1" > /dev/null 2>&1; then
    echo "❌ No se puede conectar a PostgreSQL. Verifique:"
    echo "   1. PostgreSQL está ejecutándose"
    echo "   2. La base de datos 'paloma_licitera' existe"
    echo "   3. El usuario 'postgres' tiene permisos"
    exit 1
fi

# Verificar que tenemos los datos
RECORD_COUNT=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;")
echo "📊 Base de datos contiene $RECORD_COUNT licitaciones"

if [ "$RECORD_COUNT" -lt 1000 ]; then
    echo "⚠️  La base de datos parece tener pocos datos. ¿Continuar? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Crear directorio para logs si no existe
mkdir -p logs

# Función para verificar si un puerto está en uso
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  El puerto $1 está en uso"
        return 1
    else
        return 0
    fi
}

# Limpiar puertos si están ocupados
if ! check_port 8000; then
    echo "   🧹 Liberando puerto 8000..."
    kill -9 $(lsof -ti:8000) 2>/dev/null || echo "   No se pudo liberar puerto 8000"
fi

if ! check_port 3001; then
    echo "   🧹 Liberando puerto 3001..."
    kill -9 $(lsof -ti:3001) 2>/dev/null || echo "   No se pudo liberar puerto 3001"
fi

echo ""
echo "📦 Instalando dependencias del backend..."
pip install -r requirements.txt

echo ""
echo "📦 Instalando dependencias del frontend..."
cd frontend
npm install
cd ..

echo ""
echo "🚀 Iniciando servicios..."

# Iniciar backend API (usando api.py que conecta a PostgreSQL)
echo "   📡 Iniciando backend API (puerto 8000)..."
cd src
python3 -m uvicorn api:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Esperar un poco para que el backend se inicie
sleep 3

# Verificar si el backend se inició correctamente
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo "   ✅ Backend iniciado (PID: $BACKEND_PID)"
    
    # Verificar que responde
    if curl -s http://localhost:8000/ > /dev/null; then
        echo "   ✅ Backend responde correctamente"
    else
        echo "   ⚠️  Backend iniciado pero no responde. Ver logs/backend.log"
    fi
else
    echo "   ❌ Error al iniciar el backend"
    echo "   Ver logs en: logs/backend.log"
    head -20 logs/backend.log
    exit 1
fi

# Iniciar frontend
echo "   🎨 Iniciando frontend (puerto 3001)..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Esperar un poco para que el frontend se inicie
sleep 5

# Verificar si el frontend se inició correctamente
if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo "   ✅ Frontend iniciado (PID: $FRONTEND_PID)"
else
    echo "   ❌ Error al iniciar el frontend"
    echo "   Ver logs en: logs/frontend.log"
    head -20 logs/frontend.log
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo "✨ ¡Dashboard iniciado correctamente!"
echo ""
echo "📊 Dashboard: http://localhost:3001"
echo "📡 API:       http://localhost:8000"
echo "📈 Datos:     $RECORD_COUNT licitaciones en PostgreSQL"
echo ""
echo "📋 Para ver logs:"
echo "   Backend:  tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
echo ""
echo "⏹️  Para detener los servicios:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Guardar PIDs para poder detenerlos después
echo "BACKEND_PID=$BACKEND_PID" > .pids
echo "FRONTEND_PID=$FRONTEND_PID" >> .pids

echo "ℹ️  Los servicios están ejecutándose en segundo plano."
echo "   Presiona Ctrl+C para detenerlos, o ejecuta:"
echo "   ./stop_dashboard.sh"

# Mantener el script corriendo para poder detener con Ctrl+C
trap 'echo ""; echo "🛑 Deteniendo servicios..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f .pids; echo "✅ Servicios detenidos"; exit 0' INT

# Mostrar URL y esperar
echo ""
echo "🌐 Abriendo dashboard en el navegador..."
sleep 2

# Intentar abrir el navegador (funciona en la mayoría de sistemas)
if command -v open > /dev/null 2>&1; then
    open http://localhost:3001 >/dev/null 2>&1
elif command -v xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost:3001 >/dev/null 2>&1
fi

# Esperar indefinidamente
while true; do
    sleep 1
done