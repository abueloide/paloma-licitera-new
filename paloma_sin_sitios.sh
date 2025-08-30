#!/bin/bash

# =================================================================
# PALOMA LICITERA - GESTIÓN COMPLETA DEL SISTEMA
# Un solo script que lo hace todo
# VERSIÓN SIN SITIOS-MASIVOS
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
        
        # Limpiar instalación anterior si se solicita
        if [ "$2" == "--clean" ]; then
            print_warning "Limpiando instalación anterior..."
            [ -d "venv" ] && rm -rf venv
            [ -d "frontend/node_modules" ] && rm -rf frontend/node_modules
        fi
        
        # Crear entorno virtual
        print_status "Creando entorno virtual..."
        python3 -m venv venv
        source venv/bin/activate
        
        # Instalar backend - TODAS las dependencias necesarias
        print_status "Instalando dependencias del backend..."
        pip install --upgrade pip
        
        # Dependencias básicas
        pip install fastapi uvicorn[standard] psycopg2-binary sqlalchemy pyyaml pandas python-dotenv
        
        # Dependencias para scrapers
        pip install httpx beautifulsoup4 lxml requests selenium playwright
        
        # Dependencias para procesamiento de PDFs
        pip install pymupdf pdfminer.six PyPDF2
        
        # Instalar navegadores para playwright
        print_status "Instalando navegadores para Playwright (necesario para ComprasMX)..."
        playwright install chromium
        
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
            
            # Crear tabla si no existe
            print_status "Verificando estructura de base de datos..."
            source venv/bin/activate
            python src/database.py --setup 2>/dev/null || true
        else
            print_error "No se puede conectar a PostgreSQL/paloma_licitera"
            echo ""
            echo "Para crear la base de datos, ejecuta:"
            echo "  psql -U postgres -c 'CREATE DATABASE paloma_licitera;'"
            echo ""
        fi
        
        # Crear directorios necesarios
        mkdir -p logs
        mkdir -p data/raw/dof
        mkdir -p data/raw/comprasmx
        mkdir -p data/raw/tianguis
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
        
        # También matar procesos de scrapers si están corriendo
        pkill -f "dof_extraccion" 2>/dev/null || true
        pkill -f "ComprasMX" 2>/dev/null || true
        pkill -f "tianguis" 2>/dev/null || true
        
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
            if [ "$RECORDS" -gt 0 ]; then
                echo ""
                echo "Registros por fuente:"
                psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT fuente, COUNT(*) FROM licitaciones GROUP BY fuente ORDER BY COUNT(*) DESC;" 2>/dev/null | while IFS='|' read fuente count; do
                    echo "  - $fuente: $count"
                done
            fi
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
        
        # Verificar archivos descargados
        echo ""
        echo "Archivos de datos:"
        [ -d "data/raw/dof" ] && DOF_FILES=$(ls data/raw/dof/*.txt 2>/dev/null | wc -l) || DOF_FILES=0
        [ -d "data/raw/comprasmx" ] && COMPRAS_FILES=$(ls data/raw/comprasmx/*.json 2>/dev/null | wc -l) || COMPRAS_FILES=0
        [ -d "data/raw/tianguis" ] && TIANGUIS_FILES=$(ls data/raw/tianguis/*.json 2>/dev/null | wc -l) || TIANGUIS_FILES=0
        echo "  - DOF: $DOF_FILES archivos TXT"
        echo "  - ComprasMX: $COMPRAS_FILES archivos JSON"
        echo "  - Tianguis: $TIANGUIS_FILES archivos JSON"
        ;;
        
    download)
        echo "📥 DESCARGANDO DATOS..."
        echo "----------------------"
        
        source venv/bin/activate
        
        echo "Selecciona qué descargar:"
        echo "1) Todo (DOF + ComprasMX + Tianguis)"
        echo "2) Solo procesar archivos existentes (sin descargar)"
        echo "3) Solo ComprasMX"
        echo "4) Solo DOF"
        echo "5) Solo Tianguis Digital"
        echo -n "Opción: "
        read option
        
        case $option in
            1)
                print_warning "NOTA: El proceso puede tardar varios minutos."
                print_warning "Presiona Ctrl+C si necesitas cancelar."
                echo ""
                print_info "Descargando TODOS los datos (sin sitios-masivos)..."
                
                # Solo descargar fuentes activas (sin sitios-masivos)
                python src/etl.py --fuente dof 2>&1 | tee -a logs/etl_download.log
                python src/etl.py --fuente comprasmx 2>&1 | tee -a logs/etl_download.log
                python src/etl.py --fuente tianguis 2>&1 | tee -a logs/etl_download.log
                
                print_status "Descarga completada"
                ;;
            2)
                print_info "Procesando archivos existentes (sin descargar nuevos)..."
                python src/etl.py --fuente all --solo-procesamiento
                print_status "Procesamiento completado"
                ;;
            3)
                print_info "Descargando ComprasMX..."
                python src/etl.py --fuente comprasmx
                ;;
            4)
                print_info "Descargando DOF..."
                python src/etl.py --fuente dof
                ;;
            5)
                print_info "Descargando Tianguis Digital..."
                python src/etl.py --fuente tianguis
                ;;
            *)
                print_error "Opción inválida"
                exit 1
                ;;
        esac
        
        echo ""
        echo "Para ver estadísticas: ./paloma.sh status"
        ;;
        
    download-quick)
        echo "⚡ DESCARGA RÁPIDA (solo procesamiento)..."
        echo "-------------------------------------------"
        
        source venv/bin/activate
        
        print_info "Procesando archivos existentes sin descargar nuevos..."
        python src/etl.py --fuente all --solo-procesamiento
        
        # Procesar DOF con fechas correctas
        if [ -d "data/raw/dof" ] && [ "$(ls -A data/raw/dof/*.txt 2>/dev/null)" ]; then
            print_info "Re-procesando archivos del DOF con extractor mejorado..."
            cd etl-process/extractors/dof
            for txt_file in ../../../data/raw/dof/*.txt; do
                if [ -f "$txt_file" ]; then
                    echo "Procesando $(basename $txt_file)..."
                    python estructura_dof_mejorado.py "$txt_file" 2>/dev/null || true
                fi
            done
            cd "$BASE_DIR"
        fi
        
        RECORDS=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
        print_status "Proces