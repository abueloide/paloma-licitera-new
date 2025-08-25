#!/bin/bash

# =================================================================
# INSTALACIÓN Y ARRANQUE DE PALOMA LICITERA
# Un solo script que lo hace todo
# =================================================================

echo "🐦 PALOMA LICITERA - INSTALACIÓN Y ARRANQUE"
echo "==========================================="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Funciones de utilidad
print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# Detectar el comando a ejecutar
COMMAND=${1:-install}

case $COMMAND in
    install)
        echo "📦 INSTALANDO SISTEMA..."
        echo "------------------------"
        
        # Limpiar procesos
        print_status "Deteniendo procesos anteriores..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        lsof -ti:3001 | xargs kill -9 2>/dev/null || true
        
        # Limpiar instalación anterior
        [ -d "venv" ] && rm -rf venv
        [ -d "frontend/node_modules" ] && rm -rf frontend/node_modules
        
        # Crear entorno virtual
        print_status "Creando entorno virtual..."
        python3 -m venv venv
        source venv/bin/activate
        
        # Instalar backend
        print_status "Instalando dependencias del backend..."
        pip install --upgrade pip
        pip install fastapi uvicorn[standard] psycopg2-binary sqlalchemy pyyaml pandas python-dotenv httpx beautifulsoup4 lxml requests
        
        # Arreglar bug del frontend
        if grep -q "@/lib/api" frontend/src/components/Dashboard.tsx 2>/dev/null; then
            print_status "Corrigiendo import en Dashboard.tsx..."
            sed -i.bak 's/@\/lib\/api/@\/services\/api/g' frontend/src/components/Dashboard.tsx
            rm frontend/src/components/Dashboard.tsx.bak 2>/dev/null || true
        fi
        
        # Instalar frontend
        print_status "Instalando dependencias del frontend..."
        cd frontend && npm install && cd ..
        
        # Verificar PostgreSQL
        if psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1" > /dev/null 2>&1; then
            RECORDS=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
            print_status "PostgreSQL conectado - $RECORDS registros encontrados"
        else
            print_error "No se puede conectar a PostgreSQL/paloma_licitera"
            echo "Asegúrate de que PostgreSQL esté corriendo y la base de datos exista"
        fi
        
        mkdir -p logs
        
        echo ""
        print_status "INSTALACIÓN COMPLETADA"
        echo ""
        echo "Para iniciar el sistema:"
        echo "  ./paloma.sh start"
        echo ""
        ;;
        
    start)
        echo "🚀 INICIANDO SISTEMA..."
        echo "----------------------"
        
        # Verificar entorno virtual
        if [ ! -d "venv" ]; then
            print_error "No se encontró instalación. Ejecuta primero: ./paloma.sh install"
            exit 1
        fi
        
        # Limpiar procesos anteriores
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        lsof -ti:3001 | xargs kill -9 2>/dev/null || true
        
        # Iniciar backend
        print_status "Iniciando backend en http://localhost:8000..."
        source venv/bin/activate
        cd src && python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
        BACKEND_PID=$!
        cd ..
        
        # Esperar a que el backend esté listo (máximo 30 segundos)
        echo -n "Esperando que el backend arranque"
        for i in {1..30}; do
            if curl -s http://localhost:8000 > /dev/null 2>&1; then
                echo ""
                print_status "Backend corriendo (PID: $BACKEND_PID)"
                break
            fi
            echo -n "."
            sleep 1
        done
        
        # Verificar si arrancó
        if ! curl -s http://localhost:8000 > /dev/null 2>&1; then
            echo ""
            print_error "Backend no responde después de 30 segundos"
            echo "Revisa logs/backend.log para más detalles"
            echo ""
            echo "Últimas líneas del log:"
            tail -20 logs/backend.log
            exit 1
        fi
        
        # Iniciar frontend
        print_status "Iniciando frontend en http://localhost:3001..."
        cd frontend
        npm run dev > ../logs/frontend.log 2>&1 &
        FRONTEND_PID=$!
        cd ..
        
        # Esperar a que el frontend esté listo
        echo -n "Esperando que el frontend arranque"
        for i in {1..15}; do
            if curl -s http://localhost:3001 > /dev/null 2>&1; then
                echo ""
                print_status "Frontend corriendo (PID: $FRONTEND_PID)"
                break
            fi
            echo -n "."
            sleep 1
        done
        
        # Verificar si el frontend arrancó
        if ! curl -s http://localhost:3001 > /dev/null 2>&1; then
            echo ""
            print_warning "Frontend puede estar tardando en arrancar. Revisa logs/frontend.log"
        fi
        
        echo ""
        echo "================================"
        print_status "SISTEMA INICIADO"
        echo "--------------------------------"
        echo "🌐 Frontend: http://localhost:3001"
        echo "📚 API Docs: http://localhost:8000/docs"
        echo "--------------------------------"
        echo "Para detener: ./paloma.sh stop"
        echo "Para ver logs: ./paloma.sh logs"
        echo "================================"
        echo ""
        ;;
        
    stop)
        echo "🛑 DETENIENDO SISTEMA..."
        echo "------------------------"
        
        print_status "Deteniendo procesos..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null && print_status "Backend detenido" || print_warning "Backend no estaba corriendo"
        lsof -ti:3001 | xargs kill -9 2>/dev/null && print_status "Frontend detenido" || print_warning "Frontend no estaba corriendo"
        
        echo ""
        print_status "Sistema detenido"
        ;;
        
    status)
        echo "📊 ESTADO DEL SISTEMA"
        echo "--------------------"
        
        # PostgreSQL
        if psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1" > /dev/null 2>&1; then
            RECORDS=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
            print_status "PostgreSQL: OK ($RECORDS registros)"
        else
            print_error "PostgreSQL: NO CONECTADO"
        fi
        
        # Backend
        if curl -s http://localhost:8000 > /dev/null 2>&1; then
            print_status "Backend: CORRIENDO (puerto 8000)"
        else
            print_error "Backend: DETENIDO"
        fi
        
        # Frontend
        if curl -s http://localhost:3001 > /dev/null 2>&1; then
            print_status "Frontend: CORRIENDO (puerto 3001)"
        else
            print_error "Frontend: DETENIDO"
        fi
        
        # Si algo no está corriendo, mostrar cómo iniciar
        if ! curl -s http://localhost:8000 > /dev/null 2>&1 || ! curl -s http://localhost:3001 > /dev/null 2>&1; then
            echo ""
            echo "Para iniciar el sistema: ./paloma.sh start"
        fi
        ;;
        
    logs)
        echo "📋 MOSTRANDO LOGS"
        echo "-----------------"
        
        echo "Selecciona qué logs ver:"
        echo "1) Backend"
        echo "2) Frontend"
        echo "3) Ambos"
        echo -n "Opción: "
        read option
        
        case $option in
            1)
                if [ -f "logs/backend.log" ]; then
                    echo "Backend logs (últimas 50 líneas):"
                    echo "-------------------------------"
                    tail -50 logs/backend.log
                else
                    print_warning "No hay logs del backend"
                fi
                ;;
            2)
                if [ -f "logs/frontend.log" ]; then
                    echo "Frontend logs (últimas 50 líneas):"
                    echo "-------------------------------"
                    tail -50 logs/frontend.log
                else
                    print_warning "No hay logs del frontend"
                fi
                ;;
            3)
                echo "=== BACKEND LOGS ==="
                if [ -f "logs/backend.log" ]; then
                    tail -25 logs/backend.log
                else
                    print_warning "No hay logs del backend"
                fi
                echo ""
                echo "=== FRONTEND LOGS ==="
                if [ -f "logs/frontend.log" ]; then
                    tail -25 logs/frontend.log
                else
                    print_warning "No hay logs del frontend"
                fi
                ;;
            *)
                print_error "Opción inválida"
                ;;
        esac
        ;;
        
    *)
        echo "Uso: $0 {install|start|stop|status|logs}"
        echo ""
        echo "  install - Instala todas las dependencias"
        echo "  start   - Inicia backend y frontend"
        echo "  stop    - Detiene todos los servicios"
        echo "  status  - Muestra el estado del sistema"
        echo "  logs    - Muestra los logs del sistema"
        echo ""
        exit 1
        ;;
esac
