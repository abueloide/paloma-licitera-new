#!/bin/bash

echo "⏹️  Deteniendo Paloma Licitera Dashboard..."

# Detener backend
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "   Deteniendo backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null
        sleep 1
        # Forzar si no se detuvo
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            kill -9 $BACKEND_PID 2>/dev/null
        fi
        echo "   ✅ Backend detenido"
    else
        echo "   ℹ️  Backend no estaba ejecutándose"
    fi
    rm -f .backend.pid
else
    echo "   ℹ️  No se encontró PID del backend"
fi

# Detener frontend
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "   Deteniendo frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null
        sleep 1
        # Forzar si no se detuvo
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            kill -9 $FRONTEND_PID 2>/dev/null
        fi
        echo "   ✅ Frontend detenido"
    else
        echo "   ℹ️  Frontend no estaba ejecutándose"
    fi
    rm -f .frontend.pid
else
    echo "   ℹ️  No se encontró PID del frontend"
fi

# Limpiar cualquier proceso huérfano
echo "   🧹 Limpiando procesos huérfanos..."
pkill -f "npm run dev" 2>/dev/null
pkill -f "vite" 2>/dev/null
pkill -f "python src/api.py" 2>/dev/null
pkill -f "uvicorn" 2>/dev/null

echo ""
echo "✅ Dashboard detenido completamente"
