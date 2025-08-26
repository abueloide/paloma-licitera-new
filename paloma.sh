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

# =================================================================
# FUNCIÓN PARA INSTALAR Y CONFIGURAR POSTGRESQL
# =================================================================
setup_postgres() {
    echo "🔧 Configurando PostgreSQL..."
    
    # Detectar sistema operativo
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        print_info "Sistema detectado: macOS"
        
        # Verificar si Homebrew está instalado
        if ! command -v brew &> /dev/null; then
            print_error "Homebrew no está instalado"
            echo "Instala Homebrew primero: https://brew.sh"
            return 1
        fi
        
        # Verificar si PostgreSQL está instalado
        if brew list postgresql@14 &>/dev/null || brew list postgresql &>/dev/null; then
            print_status "PostgreSQL ya está instalado"
        else
            print_info "Instalando PostgreSQL..."
            brew install postgresql@14
            if [ $? -ne 0 ]; then
                print_error "Error instalando PostgreSQL"
                return 1
            fi
            print_status "PostgreSQL instalado"
        fi
        
        # Iniciar PostgreSQL si no está corriendo
        if ! psql -h localhost -U postgres -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
            print_info "Iniciando PostgreSQL..."
            brew services start postgresql@14 2>/dev/null || brew services start postgresql 2>/dev/null
            
            # Esperar a que inicie
            sleep 3
            
            # Crear usuario postgres si no existe
            createuser -s postgres 2>/dev/null || true
        fi
        
        # Verificar nuevamente
        if psql -h localhost -U postgres -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
            print_status "PostgreSQL está funcionando"
            
            # Crear base de datos si no existe
            if ! psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -qw paloma_licitera; then
                print_info "Creando base de datos 'paloma_licitera'..."
                psql -h localhost -U postgres -c "CREATE DATABASE paloma_licitera;" 2>/dev/null
                if [ $? -eq 0 ]; then
                    print_status "Base de datos creada"
                else
                    print_warning "La base de datos ya existe o hubo un error menor"
                fi
            else
                print_status "Base de datos 'paloma_licitera' ya existe"
            fi
            
            # Crear tablas con el esquema CORRECTO
            create_database_tables
            return $?
        else
            print_error "PostgreSQL no pudo iniciarse"
            echo "Intenta ejecutar manualmente:"
            echo "  brew services restart postgresql@14"
            return 1
        fi
        
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        print_info "Sistema detectado: Linux"
        
        # Verificar si PostgreSQL está instalado
        if command -v psql &> /dev/null; then
            print_status "PostgreSQL está instalado"
            
            # Intentar iniciar si no está corriendo
            if ! psql -h localhost -U postgres -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
                print_info "Iniciando PostgreSQL..."
                sudo systemctl start postgresql 2>/dev/null || sudo service postgresql start 2>/dev/null
                sleep 3
            fi
        else
            print_warning "PostgreSQL no está instalado"
            echo "Instala PostgreSQL con:"
            echo "  Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
            echo "  Fedora/RedHat: sudo dnf install postgresql postgresql-server"
            return 1
        fi
    else
        print_error "Sistema operativo no soportado para instalación automática"
        return 1
    fi
}

# Función para crear las tablas de la base de datos CON EL ESQUEMA CORRECTO
create_database_tables() {
    print_info "Verificando estructura de base de datos..."
    
    # Verificar si la tabla existe y tiene la estructura correcta
    TIENE_MONTO_ESTIMADO=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT column_name FROM information_schema.columns WHERE table_name='licitaciones' AND column_name='monto_estimado';" 2>/dev/null || echo "")
    
    if [ -z "$TIENE_MONTO_ESTIMADO" ]; then
        print_warning "Tabla con estructura antigua detectada, actualizando..."
        
        # Eliminar tabla vieja si existe
        psql -h localhost -U postgres -d paloma_licitera -c "DROP TABLE IF EXISTS licitaciones CASCADE;" 2>/dev/null
    fi
    
    print_info "Creando tabla 'licitaciones' con estructura correcta..."
    
    # Crear tabla con el esquema CORRECTO que coincide con database.py
    psql -h localhost -U postgres -d paloma_licitera << 'EOF'
CREATE TABLE IF NOT EXISTS licitaciones (
    id SERIAL PRIMARY KEY,
    
    -- Campos de identificación
    numero_procedimiento VARCHAR(255) NOT NULL,
    uuid_procedimiento VARCHAR(255),
    hash_contenido VARCHAR(64) UNIQUE,
    
    -- Información básica
    titulo TEXT NOT NULL,
    descripcion TEXT,
    
    -- Entidades
    entidad_compradora VARCHAR(500),
    unidad_compradora VARCHAR(500),
    
    -- Clasificación
    tipo_procedimiento VARCHAR(50),
    tipo_contratacion VARCHAR(50),
    estado VARCHAR(50),
    caracter VARCHAR(50),
    
    -- Fechas
    fecha_publicacion DATE,
    fecha_apertura DATE,
    fecha_fallo DATE,
    fecha_junta_aclaraciones DATE,
    
    -- Montos (CAMPO CRÍTICO QUE FALTABA)
    monto_estimado DECIMAL(15,2),
    moneda VARCHAR(10) DEFAULT 'MXN',
    
    -- Proveedor
    proveedor_ganador TEXT,
    
    -- Metadata
    fuente VARCHAR(50) NOT NULL,
    url_original TEXT,
    fecha_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    datos_originales JSONB,
    
    -- Constraints
    CONSTRAINT uk_licitacion UNIQUE(numero_procedimiento, entidad_compradora, fuente)
);

-- Crear índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_numero_procedimiento ON licitaciones(numero_procedimiento);
CREATE INDEX IF NOT EXISTS idx_entidad ON licitaciones(entidad_compradora);
CREATE INDEX IF NOT EXISTS idx_fecha_pub ON licitaciones(fecha_publicacion);
CREATE INDEX IF NOT EXISTS idx_fuente ON licitaciones(fuente);
CREATE INDEX IF NOT EXISTS idx_estado ON licitaciones(estado);
CREATE INDEX IF NOT EXISTS idx_tipo_procedimiento ON licitaciones(tipo_procedimiento);
CREATE INDEX IF NOT EXISTS idx_tipo_contratacion ON licitaciones(tipo_contratacion);
CREATE INDEX IF NOT EXISTS idx_uuid ON licitaciones(uuid_procedimiento);
CREATE INDEX IF NOT EXISTS idx_hash ON licitaciones(hash_contenido);
EOF

    if [ $? -eq 0 ]; then
        print_status "Estructura de base de datos creada exitosamente"
        
        # Verificar que monto_estimado existe
        VERIFICAR=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT column_name FROM information_schema.columns WHERE table_name='licitaciones' AND column_name='monto_estimado';" 2>/dev/null || echo "")
        if [ -n "$VERIFICAR" ]; then
            print_status "✅ Campo 'monto_estimado' verificado correctamente"
        else
            print_error "❌ Campo 'monto_estimado' NO se creó correctamente"
            return 1
        fi
        
        return 0
    else
        print_error "Error al crear la estructura de base de datos"
        return 1
    fi
}

# =================================================================
# COMANDOS PRINCIPALES
# =================================================================

# Detectar el comando a ejecutar
COMMAND=${1:-help}

case $COMMAND in
    doctor|diagnostico)
        echo "🏥 DIAGNÓSTICO DEL SISTEMA"
        echo "--------------------------"
        echo ""
        
        # Verificar e instalar PostgreSQL si es necesario
        setup_postgres
        PG_STATUS=$?
        
        echo ""
        # Verificar Python y entorno virtual
        echo "🐍 Verificando Python..."
        if [ -d "venv" ]; then
            print_status "Entorno virtual existe"
            source venv/bin/activate
            
            # Verificar dependencias críticas
            python -c "import fastapi, psycopg2" 2>/dev/null
            if [ $? -eq 0 ]; then
                print_status "Dependencias Python básicas instaladas"
            else
                print_warning "Faltan algunas dependencias"
                echo "  Ejecuta: ./paloma.sh install"
            fi
        else
            print_warning "Entorno virtual no existe"
            echo "  Ejecuta: ./paloma.sh install"
        fi
        
        echo ""
        # Verificar directorios y archivos
        echo "📁 Verificando archivos de datos..."
        if [ -d "data/raw" ]; then
            DOF_FILES=$(ls data/raw/dof/*.txt 2>/dev/null | wc -l)
            COMPRAS_FILES=$(ls data/raw/comprasmx/*.json 2>/dev/null | wc -l)
            TIANGUIS_FILES=$(ls data/raw/tianguis/*.json 2>/dev/null | wc -l)
            
            echo "  - DOF: $DOF_FILES archivos"
            echo "  - ComprasMX: $COMPRAS_FILES archivos"
            echo "  - Tianguis: $TIANGUIS_FILES archivos"
            
            TOTAL_FILES=$((DOF_FILES + COMPRAS_FILES + TIANGUIS_FILES))
            if [ $TOTAL_FILES -gt 0 ]; then
                print_status "Hay $TOTAL_FILES archivos de datos disponibles"
            else
                print_warning "No hay archivos de datos"
                echo "  Ejecuta: ./paloma.sh download"
            fi
        else
            print_warning "No existe el directorio de datos"
            mkdir -p data/raw/{dof,comprasmx,tianguis}
            print_status "Directorios creados"
        fi
        
        echo ""
        echo "================================"
        if [ $PG_STATUS -eq 0 ]; then
            print_status "SISTEMA LISTO"
            echo ""
            echo "Siguientes pasos:"
            if [ $TOTAL_FILES -gt 0 ]; then
                echo "  1. ./paloma.sh download-quick  # Procesar archivos existentes"
            else
                echo "  1. ./paloma.sh download        # Descargar datos"
            fi
            echo "  2. ./paloma.sh start           # Iniciar sistema"
        else
            print_warning "HAY PROBLEMAS QUE RESOLVER"
            echo ""
            echo "Ejecuta los comandos sugeridos arriba"
        fi
        echo "================================"
        ;;
        
    install)
        echo "📦 INSTALANDO SISTEMA..."
        echo "------------------------"
        
        # Configurar PostgreSQL (instalar si no existe, iniciar si está detenido, crear BD)
        echo ""
        setup_postgres
        if [ $? -ne 0 ]; then
            print_warning "PostgreSQL tuvo problemas pero continuaremos con la instalación"
        fi
        
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
        print_status "Creando entorno virtual Python..."
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
        
        # Crear directorios necesarios
        mkdir -p logs
        mkdir -p data/raw/dof
        mkdir -p data/raw/comprasmx
        mkdir -p data/raw/tianguis
        mkdir -p data/processed
        
        # Verificar estado final de PostgreSQL
        echo ""
        if psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1;" > /dev/null 2>&1; then
            # Verificar que la tabla tenga el campo correcto
            VERIFICAR=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT column_name FROM information_schema.columns WHERE table_name='licitaciones' AND column_name='monto_estimado';" 2>/dev/null || echo "")
            if [ -n "$VERIFICAR" ]; then
                RECORDS=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
                print_status "PostgreSQL conectado - Base de datos lista con $RECORDS registros"
                print_status "✅ Esquema de BD correcto (monto_estimado existe)"
            else
                print_warning "⚠️ Esquema de BD incorrecto - ejecuta: ./paloma.sh reset-db"
            fi
        else
            print_warning "PostgreSQL no está disponible - deberás configurarlo antes de usar el sistema"
            echo "Ejecuta: ./paloma.sh doctor"
        fi
        
        echo ""
        print_status "INSTALACIÓN COMPLETADA"
        echo ""
        echo "Próximos pasos:"
        echo "  1. ./paloma.sh doctor          # Verificar que todo esté bien"
        echo "  2. ./paloma.sh download        # Descargar datos"
        echo "  3. ./paloma.sh start           # Iniciar sistema"
        echo ""
        ;;
        
    start)
        echo "🚀 INICIANDO SISTEMA..."
        echo "----------------------"
        
        # Verificar PostgreSQL primero
        if ! psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1;" > /dev/null 2>&1; then
            print_error "PostgreSQL no está disponible"
            echo "Ejecuta primero: ./paloma.sh doctor"
            exit 1
        fi
        
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
            
            # Verificar esquema
            VERIFICAR=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT column_name FROM information_schema.columns WHERE table_name='licitaciones' AND column_name='monto_estimado';" 2>/dev/null || echo "")
            if [ -n "$VERIFICAR" ]; then
                print_status "Esquema de BD: CORRECTO ✅"
            else
                print_error "Esquema de BD: INCORRECTO ❌ (falta monto_estimado)"
                echo "  Ejecuta: ./paloma.sh reset-db"
            fi
            
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
            echo "  Ejecuta: ./paloma.sh doctor"
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
        
        # Verificar PostgreSQL primero
        if ! psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1;" > /dev/null 2>&1; then
            print_error "PostgreSQL no está disponible"
            echo "Ejecuta primero: ./paloma.sh doctor"
            exit 1
        fi
        
        source venv/bin/activate
        
        echo "Selecciona qué descargar:"
        echo "1) Todo (ComprasMX, DOF, Tianguis)"
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
                print_info "Descargando TODOS los datos..."
                
                python src/etl.py --fuente all 2>&1 | tee logs/etl_download.log
                
                if [ ${PIPESTATUS[0]} -ne 0 ]; then
                    print_warning "El proceso terminó con advertencias. Revisa logs/etl_download.log"
                else
                    print_status "Descarga completada"
                fi
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
        
        # Verificar PostgreSQL primero
        if ! psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1;" > /dev/null 2>&1; then
            print_error "PostgreSQL no está disponible"
            echo "Ejecuta primero: ./paloma.sh doctor"
            exit 1
        fi
        
        source venv/bin/activate
        
        print_info "Procesando archivos existentes sin descargar nuevos..."
        python src/etl.py --fuente all --solo-procesamiento
        
        RECORDS=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
        print_status "Procesamiento completado: $RECORDS registros en la base de datos"
        ;;
        
    reset-db)
        echo "🗑️  LIMPIANDO BASE DE DATOS..."
        echo "-----------------------------"
        
        # Verificar PostgreSQL primero
        if ! psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1;" > /dev/null 2>&1; then
            print_error "PostgreSQL no está disponible"
            echo "Ejecuta primero: ./paloma.sh doctor"
            exit 1
        fi
        
        echo ""
        print_warning "ADVERTENCIA: Esto ELIMINARÁ TODOS los datos y recreará la tabla"
        echo -n "¿Estás seguro? (escribe 'SI' para confirmar): "
        read confirmacion
        
        if [ "$confirmacion" != "SI" ]; then
            print_info "Operación cancelada"
            exit 0
        fi
        
        print_info "Eliminando tabla antigua..."
        psql -h localhost -U postgres -d paloma_licitera -c "DROP TABLE IF EXISTS licitaciones CASCADE;" 2>/dev/null
        
        print_info "Creando tabla con esquema correcto..."
        create_database_tables
        
        if [ $? -eq 0 ]; then
            print_status "Base de datos recreada con esquema correcto"
            echo ""
            echo "Ahora puedes ejecutar:"
            echo "  ./paloma.sh download-quick  # Para procesar archivos existentes"
            echo "  ./paloma.sh download        # Para descargar nuevos datos"
        else
            print_error "Error al recrear la base de datos"
            exit 1
        fi
        ;;
        
    logs)
        echo "📋 MOSTRANDO LOGS"
        echo "-----------------"
        
        echo "Selecciona qué logs ver:"
        echo "1) Backend"
        echo "2) Frontend"
        echo "3) ETL/Descarga"
        echo "4) Todos los recientes"
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
                if [ -f "$BASE_DIR/logs/etl_download.log" ]; then
                    echo "Logs de ETL/Descarga (últimas 50 líneas):"
                    echo "----------------------------------------"
                    tail -50 "$BASE_DIR/logs/etl_download.log"
                else
                    print_warning "No hay logs de ETL/Descarga"
                fi
                ;;
            4)
                echo "=== LOGS RECIENTES ==="
                echo ""
                [ -f "$BASE_DIR/logs/backend.log" ] && echo "Backend:" && tail -10 "$BASE_DIR/logs/backend.log"
                echo ""
                [ -f "$BASE_DIR/logs/frontend.log" ] && echo "Frontend:" && tail -10 "$BASE_DIR/logs/frontend.log"
                echo ""
                [ -f "$BASE_DIR/logs/etl_download.log" ] && echo "ETL:" && tail -10 "$BASE_DIR/logs/etl_download.log"
                ;;
            *)
                print_error "Opción inválida"
                ;;
        esac
        ;;
    
    help|*)
        echo "Uso: $0 {comando} [opciones]"
        echo ""
        echo "COMANDOS PRINCIPALES:"
        echo "  doctor|diagnostico - Verifica y arregla problemas del sistema"
        echo "  install [--clean]  - Instala todas las dependencias"
        echo "  start             - Inicia backend y frontend"
        echo "  stop              - Detiene todos los servicios"
        echo "  status            - Muestra el estado del sistema"
        echo "  logs              - Muestra los logs del sistema"
        echo ""
        echo "GESTIÓN DE DATOS:"
        echo "  download          - Descarga datos de las fuentes"
        echo "  download-quick    - Solo procesa archivos existentes"
        echo "  reset-db          - Elimina y recrea la BD con esquema correcto"
        echo ""
        echo "FLUJO RECOMENDADO PARA INSTALACIÓN:"
        echo "  1. ./paloma.sh install        # Instala todo automáticamente"
        echo "  2. ./paloma.sh download       # Descarga datos"
        echo "  3. ./paloma.sh start          # Inicia sistema"
        echo ""
        echo "SI HAY PROBLEMAS:"
        echo "  ./paloma.sh doctor            # Diagnostica y arregla automáticamente"
        echo "  ./paloma.sh reset-db          # Recrea BD con esquema correcto"
        echo ""
        exit 1
        ;;
esac
