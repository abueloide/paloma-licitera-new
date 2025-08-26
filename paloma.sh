#!/bin/bash

# =================================================================
# PALOMA LICITERA - GESTIÓN COMPLETA DEL SISTEMA
# Un solo script que lo hace todo
# =================================================================

echo "🐦 PALOMA LICITERA - SISTEMA DE GESTIÓN"
echo "========================================"
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funciones de utilidad
print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Guardar el directorio base
BASE_DIR=$(pwd)

# Detectar el comando a ejecutar
COMMAND=${1:-help}

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
        pip install fastapi uvicorn[standard] psycopg2-binary sqlalchemy pyyaml pandas python-dotenv httpx beautifulsoup4 lxml requests pymupdf pdfminer.six
        
        # Arreglar bug del frontend
        if grep -q "@/lib/api" frontend/src/components/Dashboard.tsx 2>/dev/null; then
            print_status "Corrigiendo import en Dashboard.tsx..."
            sed -i.bak 's/@\/lib\/api/@\/services\/api/g' frontend/src/components/Dashboard.tsx
            rm frontend/src/components/Dashboard.tsx.bak 2>/dev/null || true
        fi
        
        # Instalar frontend
        print_status "Instalando dependencias del frontend..."
        cd "$BASE_DIR/frontend" && npm install
        cd "$BASE_DIR"
        
        # Verificar PostgreSQL
        if psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1" > /dev/null 2>&1; then
            RECORDS=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
            print_status "PostgreSQL conectado - $RECORDS registros encontrados"
        else
            print_error "No se puede conectar a PostgreSQL/paloma_licitera"
            echo "Asegúrate de que PostgreSQL esté corriendo y la base de datos exista"
        fi
        
        mkdir -p logs
        mkdir -p data/raw/dof
        mkdir -p data/raw/comprasmx
        mkdir -p data/raw/tianguis
        mkdir -p data/raw/sitios-masivos
        mkdir -p data/processed
        
        echo ""
        print_status "INSTALACIÓN COMPLETADA"
        echo ""
        echo "Para iniciar el sistema: ./paloma.sh start"
        echo "Para descargar datos: ./paloma.sh download"
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
        cd "$BASE_DIR/src" && python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000 > "$BASE_DIR/logs/backend.log" 2>&1 &
        BACKEND_PID=$!
        
        # Esperar a que el backend esté listo
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
        
        # Iniciar frontend
        print_status "Iniciando frontend en http://localhost:3001..."
        cd "$BASE_DIR/frontend" && npm run dev > "$BASE_DIR/logs/frontend.log" 2>&1 &
        FRONTEND_PID=$!
        
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
            
            # Estadísticas por fuente
            echo ""
            echo "Registros por fuente:"
            psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT fuente, COUNT(*) FROM licitaciones GROUP BY fuente ORDER BY COUNT(*) DESC;" 2>/dev/null | while IFS='|' read fuente count; do
                echo "  - $fuente: $count"
            done
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
        ;;
        
    download)
        echo "📥 DESCARGANDO DATOS..."
        echo "----------------------"
        
        source venv/bin/activate
        
        echo "Selecciona qué descargar:"
        echo "1) Todo (ComprasMX, DOF, Tianguis, Sitios Masivos)"
        echo "2) Solo ComprasMX"
        echo "3) Solo DOF"
        echo "4) Solo Tianguis Digital"
        echo "5) Solo Sitios Masivos"
        echo -n "Opción: "
        read option
        
        case $option in
            1)
                print_info "Descargando TODOS los datos (puede tardar varios minutos)..."
                python src/etl.py --fuente all
                ;;
            2)
                print_info "Descargando ComprasMX..."
                python src/etl.py --fuente comprasmx
                ;;
            3)
                print_info "Descargando DOF..."
                python src/etl.py --fuente dof
                ;;
            4)
                print_info "Descargando Tianguis Digital..."
                python src/etl.py --fuente tianguis
                ;;
            5)
                print_info "Descargando Sitios Masivos..."
                python src/etl.py --fuente sitios-masivos
                ;;
            *)
                print_error "Opción inválida"
                exit 1
                ;;
        esac
        
        echo ""
        print_status "Descarga completada"
        echo "Para ver estadísticas: ./paloma.sh status"
        ;;
        
    reset-db)
        echo "🗑️  LIMPIANDO BASE DE DATOS..."
        echo "-----------------------------"
        echo ""
        print_warning "ADVERTENCIA: Esto ELIMINARÁ TODOS los datos de la base de datos"
        echo -n "¿Estás seguro? (escribe 'SI' para confirmar): "
        read confirmacion
        
        if [ "$confirmacion" != "SI" ]; then
            print_info "Operación cancelada"
            exit 0
        fi
        
        print_info "Limpiando base de datos..."
        psql -h localhost -U postgres -d paloma_licitera -c "TRUNCATE TABLE licitaciones RESTART IDENTITY;" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            print_status "Base de datos limpiada"
        else
            print_error "Error al limpiar la base de datos"
            exit 1
        fi
        ;;
        
    repopulate)
        echo "🔄 REPOBLANDO BASE DE DATOS..."
        echo "------------------------------"
        
        source venv/bin/activate
        
        # Verificar que la base esté vacía o preguntar
        RECORDS=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
        if [ "$RECORDS" -gt 0 ]; then
            print_warning "La base de datos tiene $RECORDS registros"
            echo -n "¿Deseas limpiarla primero? (s/n): "
            read limpiar
            
            if [ "$limpiar" = "s" ]; then
                print_info "Limpiando base de datos..."
                psql -h localhost -U postgres -d paloma_licitera -c "TRUNCATE TABLE licitaciones RESTART IDENTITY;" 2>/dev/null
            fi
        fi
        
        print_info "Procesando archivos existentes (sin descargar nuevos)..."
        
        # Re-procesar archivos del DOF con fecha del ejemplar
        if [ -d "data/raw/dof" ] && [ "$(ls -A data/raw/dof/*.txt 2>/dev/null)" ]; then
            print_info "Re-procesando archivos del DOF..."
            python reprocesar_dof.py
        fi
        
        # Ejecutar ETL sin descargar (solo procesamiento)
        print_info "Ejecutando ETL para procesar archivos existentes..."
        python src/etl.py --fuente all --solo-procesamiento
        
        # Mostrar estadísticas finales
        FINAL_RECORDS=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
        
        echo ""
        print_status "Repoblado completado"
        echo "Total de registros: $FINAL_RECORDS"
        ;;
        
    full-reset)
        echo "🔄 RESET COMPLETO Y RECARGA DE DATOS..."
        echo "---------------------------------------"
        echo ""
        print_warning "Esto realizará:"
        echo "  1. Limpiar completamente la base de datos"
        echo "  2. Descargar TODOS los datos nuevamente"
        echo "  3. Procesar e insertar todos los datos"
        echo ""
        echo -n "¿Estás seguro? (escribe 'SI' para confirmar): "
        read confirmacion
        
        if [ "$confirmacion" != "SI" ]; then
            print_info "Operación cancelada"
            exit 0
        fi
        
        source venv/bin/activate
        
        # Paso 1: Limpiar base de datos
        print_info "Paso 1/3: Limpiando base de datos..."
        psql -h localhost -U postgres -d paloma_licitera -c "TRUNCATE TABLE licitaciones RESTART IDENTITY;" 2>/dev/null
        
        # Paso 2: Descargar todos los datos
        print_info "Paso 2/3: Descargando todos los datos (esto puede tardar)..."
        python src/etl.py --fuente all
        
        # Paso 3: Procesar archivos del DOF
        if [ -d "data/raw/dof" ] && [ "$(ls -A data/raw/dof/*.txt 2>/dev/null)" ]; then
            print_info "Paso 3/3: Procesando archivos del DOF con fecha del ejemplar..."
            python reprocesar_dof.py
        fi
        
        # Mostrar estadísticas finales
        echo ""
        echo "================================"
        print_status "RESET COMPLETO FINALIZADO"
        echo "--------------------------------"
        
        TOTAL=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
        echo "Total de registros: $TOTAL"
        echo ""
        echo "Registros por fuente:"
        psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT fuente, COUNT(*) FROM licitaciones GROUP BY fuente ORDER BY COUNT(*) DESC;" 2>/dev/null | while IFS='|' read fuente count; do
            echo "  - $fuente: $count"
        done
        echo "================================"
        ;;
        
    logs)
        echo "📋 MOSTRANDO LOGS"
        echo "-----------------"
        
        echo "Selecciona qué logs ver:"
        echo "1) Backend"
        echo "2) Frontend"
        echo "3) ETL"
        echo "4) Todos"
        echo -n "Opción: "
        read option
        
        case $option in
            1)
                if [ -f "$BASE_DIR/logs/backend.log" ]; then
                    echo "Backend logs (últimas 50 líneas):"
                    echo "-------------------------------"
                    tail -50 "$BASE_DIR/logs/backend.log"
                else
                    print_warning "No hay logs del backend"
                fi
                ;;
            2)
                if [ -f "$BASE_DIR/logs/frontend.log" ]; then
                    echo "Frontend logs (últimas 50 líneas):"
                    echo "-------------------------------"
                    tail -50 "$BASE_DIR/logs/frontend.log"
                else
                    print_warning "No hay logs del frontend"
                fi
                ;;
            3)
                echo "Logs del ETL más reciente:"
                echo "-------------------------"
                # Buscar logs más recientes del ETL
                find . -name "*.log" -path "*/etl-process/*" -o -name "*etl*.log" 2>/dev/null | xargs ls -t | head -1 | xargs tail -50
                ;;
            4)
                echo "=== BACKEND LOGS ==="
                [ -f "$BASE_DIR/logs/backend.log" ] && tail -20 "$BASE_DIR/logs/backend.log" || print_warning "No hay logs del backend"
                echo ""
                echo "=== FRONTEND LOGS ==="
                [ -f "$BASE_DIR/logs/frontend.log" ] && tail -20 "$BASE_DIR/logs/frontend.log" || print_warning "No hay logs del frontend"
                ;;
            *)
                print_error "Opción inválida"
                ;;
        esac
        ;;
    
    help|*)
        echo "Uso: $0 {comando}"
        echo ""
        echo "COMANDOS BÁSICOS:"
        echo "  install      - Instala todas las dependencias"
        echo "  start        - Inicia backend y frontend"
        echo "  stop         - Detiene todos los servicios"
        echo "  status       - Muestra el estado del sistema y estadísticas"
        echo "  logs         - Muestra los logs del sistema"
        echo ""
        echo "GESTIÓN DE DATOS:"
        echo "  download     - Descarga datos de las fuentes (ComprasMX, DOF, etc.)"
        echo "  reset-db     - Limpia la base de datos (elimina todos los registros)"
        echo "  repopulate   - Re-procesa archivos existentes sin descargar nuevos"
        echo "  full-reset   - Limpia BD, descarga TODO y repobla desde cero"
        echo ""
        echo "FLUJO TÍPICO:"
        echo "  1. ./paloma.sh install      # Primera vez"
        echo "  2. ./paloma.sh download     # Descargar datos"
        echo "  3. ./paloma.sh start        # Iniciar sistema"
        echo ""
        echo "RESET COMPLETO:"
        echo "  ./paloma.sh full-reset      # Borra todo y descarga/procesa de nuevo"
        echo ""
        exit 1
        ;;
esac
