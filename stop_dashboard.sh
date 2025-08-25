#!/bin/bash

# Script para detener el dashboard de Paloma Licitera

echo "🛑 Deteniendo Paloma Licitera Dashboard..."

# Leer PIDs si existen
if [ -f ".pids" ]; then
    source .pids
    
    if [ ! -z "$BACKEND_PID" ] && ps -p $BACKEND_PID > /dev/null; then
        echo "   📡 Deteniendo backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        echo "   ✅ Backend detenido"
    fi
    
    if [ ! -z "$FRONTEND_PID" ] && ps -p $FRONTEND_PID > /dev/null; then
        echo "   🎨 Deteniendo frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        echo "   ✅ Frontend detenido"
    fi
    
    rm -f .pids
else
    echo "   ⚠️  No se encontró archivo .pids"
    echo "   Intentando detener procesos por puerto..."
    
    # Buscar y detener procesos en puertos específicos
    BACKEND_PROCESS=$(lsof -ti:8000)
    if [ ! -z "$BACKEND_PROCESS" ]; then
        echo "   📡 Deteniendo proceso en puerto 8000..."
        kill $BACKEND_PROCESS
        echo "   ✅ Proceso backend detenido"
    fi
    
    FRONTEND_PROCESS=$(lsof -ti:3001)
    if [ ! -z "$FRONTEND_PROCESS" ]; then
        echo "   🎨 Deteniendo proceso en puerto 3001..."
        kill $FRONTEND_PROCESS
        echo "   ✅ Proceso frontend detenido"
    fi
fi

echo ""
echo "✅ Dashboard detenido correctamente"