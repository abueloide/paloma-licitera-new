#!/bin/bash

echo "🐦 Iniciando Paloma Licitera Dashboard..."

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "🔌 Activando entorno virtual..."
    source venv/bin/activate
else
    echo "⚠️  No se encontró entorno virtual. Ejecuta ./install.sh primero"
    exit 1
fi

# Verificar PostgreSQL
if command -v psql &> /dev/null; then
    COUNT=$(psql -h localhost -U postgres -d paloma_licitera -t -c "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null | xargs)
    if [ ! -z "$COUNT" ]; then
        echo "📊 Base de datos contiene $COUNT licitaciones"
    fi
fi

# Crear directorio de logs
mkdir -p logs

echo ""
echo "🚀 Iniciando servicios..."

# Matar procesos anteriores si existen
if [ -f .backend.pid ]; then
    OLD_PID=$(cat .backend.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "   ⏹️  Deteniendo backend anterior..."
        kill $OLD_PID 2>/dev/null
    fi
fi

if [ -f .frontend.pid ]; then
    OLD_PID=$(cat .frontend.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "   ⏹️  Deteniendo frontend anterior..."
        kill $OLD_PID 2>/dev/null
    fi
fi

# Iniciar backend
echo "   📡 Iniciando backend API (puerto 8000)..."
python src/api.py > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Verificar que el backend se inició
sleep 2
if ps -p $BACKEND_PID > /dev/null; then
    echo "   ✅ Backend iniciado (PID: $BACKEND_PID)"
    echo $BACKEND_PID > .backend.pid
else
    echo "   ❌ Error al iniciar el backend"
    echo "   Ver logs en: logs/backend.log"
    tail -n 20 logs/backend.log
    exit 1
fi

# Esperar a que el backend esté listo
echo "   ⏳ Esperando a que el backend esté listo..."
for i in {1..10}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "   ✅ Backend respondiendo correctamente"
        break
    fi
    sleep 1
done

# Iniciar frontend
echo "   🎨 Iniciando frontend (puerto 5173)..."
cd frontend && npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Verificar que el frontend se inició
sleep 2
if ps -p $FRONTEND_PID > /dev/null; then
    echo "   ✅ Frontend iniciado (PID: $FRONTEND_PID)"
    echo $FRONTEND_PID > .frontend.pid
else
    echo "   ❌ Error al iniciar el frontend"
    echo "   Ver logs en: logs/frontend.log"
    exit 1
fi

echo ""
echo "======================================"
echo "✅ Dashboard iniciado correctamente"
echo "======================================"
echo ""
echo "🌐 Abrir en el navegador:"
echo "   http://localhost:5173"
echo ""
echo "📊 API disponible en:"
echo "   http://localhost:8000"
echo "   http://localhost:8000/docs (Swagger UI)"
echo ""
echo "📝 Logs disponibles en:"
echo "   - Backend: logs/backend.log"
echo "   - Frontend: logs/frontend.log"
echo ""
echo "⏹️  Para detener: ./stop_dashboard.sh"
echo ""

# Abrir navegador automáticamente
sleep 2
if command -v open &> /dev/null; then
    open http://localhost:5173
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173
fi

# Mantener el script corriendo y mostrar logs
echo "📋 Presiona Ctrl+C para detener todos los servicios"
echo ""

# Trap para limpiar al salir
trap 'echo ""; echo "⏹️  Deteniendo servicios..."; ./stop_dashboard.sh; exit' INT TERM

# Mantener el script vivo
wait
