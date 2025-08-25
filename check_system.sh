#!/bin/bash

echo "🔍 DIAGNÓSTICO DEL SISTEMA PALOMA LICITERA"
echo "=========================================="
echo ""

# Check PostgreSQL
echo "1. 🐘 PostgreSQL Status:"
if command -v psql &> /dev/null; then
    if psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1" > /dev/null 2>&1; then
        echo "   ✅ PostgreSQL está corriendo"
        RECORD_COUNT=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
        echo "   📊 Registros en licitaciones: $RECORD_COUNT"
    else
        echo "   ❌ PostgreSQL no está accesible"
        echo "   Intentando con Docker..."
        if docker ps | grep postgres > /dev/null 2>&1; then
            echo "   🐳 PostgreSQL container está corriendo"
        else
            echo "   ❌ PostgreSQL container no está corriendo"
            echo ""
            echo "   Para iniciar PostgreSQL con Docker:"
            echo "   docker-compose up -d postgres"
        fi
    fi
else
    echo "   ⚠️  psql no está instalado"
fi

echo ""
echo "2. 🚀 Backend API Status (puerto 8000):"
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "   ✅ Backend API está respondiendo"
    API_INFO=$(curl -s http://localhost:8000/ | python3 -m json.tool 2>/dev/null | head -5)
    echo "   API Info: $API_INFO"
else
    echo "   ❌ Backend API NO está respondiendo en puerto 8000"
    echo ""
    echo "   Para iniciar el backend:"
    echo "   cd src && python3 -m uvicorn api:app --reload --port 8000"
fi

echo ""
echo "3. 🎨 Frontend Status (puerto 3001):"
if curl -s http://localhost:3001/ > /dev/null 2>&1; then
    echo "   ✅ Frontend está corriendo"
else
    echo "   ❌ Frontend NO está corriendo en puerto 3001"
    echo ""
    echo "   Para iniciar el frontend:"
    echo "   cd frontend && npm install && npm run dev"
fi

echo ""
echo "4. 🔌 Puertos en uso:"
echo "   Puerto 5432 (PostgreSQL):"
lsof -i :5432 2>/dev/null | head -2 || echo "   No está en uso"
echo ""
echo "   Puerto 8000 (Backend):"
lsof -i :8000 2>/dev/null | head -2 || echo "   No está en uso"
echo ""
echo "   Puerto 3001 (Frontend):"
lsof -i :3001 2>/dev/null | head -2 || echo "   No está en uso"

echo ""
echo "5. 📁 Archivos críticos:"
[ -f "src/api.py" ] && echo "   ✅ src/api.py existe" || echo "   ❌ src/api.py NO existe"
[ -f "config.yaml" ] && echo "   ✅ config.yaml existe" || echo "   ❌ config.yaml NO existe"
[ -f "frontend/package.json" ] && echo "   ✅ frontend/package.json existe" || echo "   ❌ frontend/package.json NO existe"
[ -f "docker-compose.yml" ] && echo "   ✅ docker-compose.yml existe" || echo "   ❌ docker-compose.yml NO existe"

echo ""
echo "=========================================="
echo "📋 RESUMEN:"
echo ""

# Check overall status
POSTGRES_OK=false
BACKEND_OK=false
FRONTEND_OK=false

if psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1" > /dev/null 2>&1; then
    POSTGRES_OK=true
fi

if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    BACKEND_OK=true
fi

if curl -s http://localhost:3001/ > /dev/null 2>&1; then
    FRONTEND_OK=true
fi

if [ "$POSTGRES_OK" = true ] && [ "$BACKEND_OK" = true ] && [ "$FRONTEND_OK" = true ]; then
    echo "✅ TODOS LOS SERVICIOS ESTÁN FUNCIONANDO"
    echo ""
    echo "🌐 Accede al dashboard en: http://localhost:3001"
else
    echo "⚠️  HAY SERVICIOS QUE NO ESTÁN FUNCIONANDO:"
    [ "$POSTGRES_OK" = false ] && echo "   - PostgreSQL necesita iniciarse"
    [ "$BACKEND_OK" = false ] && echo "   - Backend API necesita iniciarse"
    [ "$FRONTEND_OK" = false ] && echo "   - Frontend necesita iniciarse"
    echo ""
    echo "🚀 Para iniciar todo el sistema, usa:"
    echo "   ./start_dashboard.sh"
    echo ""
    echo "O inicia cada servicio individualmente con los comandos mostrados arriba."
fi

echo ""
echo "=========================================="
