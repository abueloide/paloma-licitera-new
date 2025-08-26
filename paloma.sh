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
# FUNCIÓN DE DIAGNÓSTICO Y VERIFICACIÓN DE POSTGRESQL
# =================================================================
check_and_fix_postgres() {
    echo "🔍 Verificando PostgreSQL..."
    
    # Verificar si PostgreSQL está corriendo
    if psql -h localhost -U postgres -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
        print_status "PostgreSQL está corriendo"
        
        # Verificar si la base de datos existe
        if psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -qw paloma_licitera; then
            print_status "Base de datos 'paloma_licitera' existe"
            
            # Verificar tabla
            if psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1 FROM licitaciones LIMIT 1;" > /dev/null 2>&1; then
                RECORDS=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
                print_status "Tabla 'licitaciones' existe con $RECORDS registros"
                return 0
            else
                print_warning "Tabla 'licitaciones' no existe, creándola..."
                create_database_tables
                return $?
            fi
        else
            print_warning "Base de datos 'paloma_licitera' no existe"
            echo -n "¿Deseas crearla? (s/n): "
            read respuesta
            if [ "$respuesta" = "s" ]; then
                print_info "Creando base de datos..."
                psql -h localhost -U postgres -c "CREATE DATABASE paloma_licitera;" 2>/dev/null
                if [ $? -eq 0 ]; then
                    print_status "Base de datos creada"
                    create_database_tables
                    return $?
                else
                    print_error "No se pudo crear la base de datos"
                    return 1
                fi
            else
                return 1
            fi
        fi
    else
        print_error "PostgreSQL no está corriendo o no está instalado"
        
        # Detectar sistema operativo
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            print_info "Detectado: macOS"
            
            # Verificar si está instalado con Homebrew
            if command -v brew &> /dev/null; then
                if brew list postgresql@14 &>/dev/null || brew list postgresql &>/dev/null; then
                    print_info "PostgreSQL está instalado, intentando iniciar..."
                    
                    # Intentar iniciar PostgreSQL
                    brew services start postgresql@14 2>/dev/null || brew services start postgresql 2>/dev/null
                    
                    sleep 3
                    
                    # Verificar de nuevo
                    if psql -h localhost -U postgres -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
                        print_status "PostgreSQL iniciado exitosamente"
                        return check_and_fix_postgres
                    else
                        print_error "No se pudo iniciar PostgreSQL"
                        print_info "Intenta ejecutar manualmente:"
                        echo "  brew services restart postgresql@14"
                        return 1
                    fi
                else
                    print_warning "PostgreSQL no está instalado"
                    echo -n "¿Deseas instalarlo con Homebrew? (s/n): "
                    read respuesta
                    if [ "$respuesta" = "s" ]; then
                        brew install postgresql@14
                        brew services start postgresql@14
                        createuser -s postgres 2>/dev/null || true
                        sleep 3
                        return check_and_fix_postgres
                    else
                        return 1
                    fi
                fi
            else
                print_error "Homebrew no está instalado"
                echo "Instala PostgreSQL manualmente o instala Homebrew primero"
                return 1
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            print_info "Detectado: Linux"
            print_info "Intenta iniciar PostgreSQL con:"
            echo "  sudo systemctl start postgresql"
            echo "  sudo service postgresql start"
            return 1
        else
            print_error "Sistema operativo no soportado automáticamente"
            return 1
        fi
    fi
}

# Función para crear las tablas de la base de datos
create_database_tables() {
    print_info "Creando estructura de base de datos..."
    
    # Crear tabla principal
    psql -h localhost -U postgres -d paloma_licitera << EOF
CREATE TABLE IF NOT EXISTS licitaciones (
    id SERIAL PRIMARY KEY,
    fuente VARCHAR(50) NOT NULL,
    fecha_publicacion DATE,
    fecha_limite DATE,
    titulo TEXT,
    descripcion TEXT,
    entidad_compradora VARCHAR(500),
    entidad_convocante VARCHAR(500),
    tipo_contratacion VARCHAR(100),
    tipo_licitacion VARCHAR(100),
    estado VARCHAR(50),
    monto_minimo DECIMAL(20,2),
    monto_maximo DECIMAL(20,2),
    moneda VARCHAR(10),
    url TEXT,
    numero_procedimiento VARCHAR(200),
    fecha_inicio_vigencia DATE,
    fecha_fin_vigencia DATE,
    notas TEXT,
    archivo_origen VARCHAR(200),
    datos_originales JSONB,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fuente, numero_procedimiento)
);

-- Crear índices
CREATE INDEX IF NOT EXISTS idx_fuente ON licitaciones(fuente);
CREATE INDEX IF NOT EXISTS idx_fecha_publicacion ON licitaciones(fecha_publicacion);
CREATE INDEX IF NOT EXISTS idx_entidad ON licitaciones(entidad_compradora);
CREATE INDEX IF NOT EXISTS idx_numero ON licitaciones(numero_procedimiento);
EOF

    if [ $? -eq 0 ]; then
        print_status "Estructura de base de datos creada exitosamente"
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
        
        # Verificar PostgreSQL
        check_and_fix_postgres
        PG_STATUS=$?
        
        echo ""
        # Verificar Python y entorno virtual
        echo "🐍 Verificando Python..."
        if [ -d "venv" ]; then
            print_status "Entorno virtual existe"
            source venv/bin/activate
            
            # Verificar dependencias críticas
            python -c "import fastapi, psycopg2, playwright" 2>/dev/null
            if [ $? -eq 0 ]; then
                print_status "Dependencias Python instaladas"
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
        
        # Primero verificar PostgreSQL
        echo ""
        check_and_fix_postgres
        if [ $? -ne 0 ]; then
            print_error "PostgreSQL debe estar funcionando para continuar"
            echo "Resuelve los problemas de PostgreSQL primero"
            exit 1
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
        
        # Crear directorios necesarios
        mkdir -p logs
        mkdir -p data/raw/dof
        mkdir -p data/raw/comprasmx
        mkdir -p data/raw/tianguis
        mkdir -p data/processed
        
        echo ""
        print_status "INSTALACIÓN COMPLETADA"
        echo ""
        echo "Para verificar el sistema: ./paloma.sh doctor"
        echo "Para descargar datos: ./paloma.sh download"
        echo "Para iniciar: ./paloma.sh start"
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
        
        # Procesar DOF con fechas correctas
        if [ -d "data/raw/dof" ] && [ "$(ls -A data/raw/dof/*.txt 2>/dev/null)" ]; then
            print_info "Re-procesando archivos del DOF con fechas correctas..."
            python reprocesar_dof.py
        fi
        
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
            echo "La tabla puede no existir. Ejecuta: ./paloma.sh doctor"
            exit 1
        fi
        ;;
        
    repopulate)
        echo "🔄 REPOBLANDO BASE DE DATOS..."
        echo "------------------------------"
        
        # Verificar PostgreSQL primero
        if ! psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1;" > /dev/null 2>&1; then
            print_error "PostgreSQL no está disponible"
            echo "Ejecuta primero: ./paloma.sh doctor"
            exit 1
        fi
        
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
        echo "  1. Verificar y arreglar PostgreSQL"
        echo "  2. Limpiar completamente la base de datos"
        echo "  3. Descargar TODOS los datos nuevamente"
        echo "  4. Procesar e insertar todos los datos"
        echo ""
        echo -n "¿Estás seguro? (escribe 'SI' para confirmar): "
        read confirmacion
        
        if [ "$confirmacion" != "SI" ]; then
            print_info "Operación cancelada"
            exit 0
        fi
        
        # Paso 0: Verificar PostgreSQL
        print_info "Paso 0/4: Verificando PostgreSQL..."
        check_and_fix_postgres
        if [ $? -ne 0 ]; then
            print_error "Debe resolverse el problema con PostgreSQL primero"
            exit 1
        fi
        
        source venv/bin/activate
        
        # Paso 1: Limpiar base de datos
        print_info "Paso 1/4: Limpiando base de datos..."
        psql -h localhost -U postgres -d paloma_licitera -c "TRUNCATE TABLE licitaciones RESTART IDENTITY;" 2>/dev/null
        
        # Paso 2: Descargar todos los datos
        print_info "Paso 2/4: Descargando todos los datos..."
        print_warning "NOTA: Este proceso puede tardar 10-20 minutos. Por favor sé paciente."
        
        python src/etl.py --fuente all 2>&1 | tee logs/full_reset.log
        
        # Paso 3: Procesar archivos del DOF
        if [ -d "data/raw/dof" ] && [ "$(ls -A data/raw/dof/*.txt 2>/dev/null)" ]; then
            print_info "Paso 3/4: Procesando archivos del DOF con fecha del ejemplar..."
            python reprocesar_dof.py
        fi
        
        # Mostrar estadísticas finales
        echo ""
        echo "================================"
        print_status "RESET COMPLETO FINALIZADO"
        echo "--------------------------------"
        
        TOTAL=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
        echo "Total de registros: $TOTAL"
        
        if [ "$TOTAL" -gt 0 ]; then
            echo ""
            echo "Registros por fuente:"
            psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT fuente, COUNT(*) FROM licitaciones GROUP BY fuente ORDER BY COUNT(*) DESC;" 2>/dev/null | while IFS='|' read fuente count; do
                echo "  - $fuente: $count"
            done
        fi
        echo "================================"
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
                elif [ -f "$BASE_DIR/logs/full_reset.log" ]; then
                    echo "Logs de último reset (últimas 50 líneas):"
                    echo "----------------------------------------"
                    tail -50 "$BASE_DIR/logs/full_reset.log"
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
        echo "  reset-db          - Limpia la base de datos"
        echo "  repopulate        - Re-procesa archivos existentes"
        echo "  full-reset        - Reset completo y recarga todo"
        echo ""
        echo "FLUJO RECOMENDADO:"
        echo "  1. ./paloma.sh doctor         # Verificar sistema"
        echo "  2. ./paloma.sh install        # Si es primera vez"
        echo "  3. ./paloma.sh download       # Descargar datos"
        echo "  4. ./paloma.sh start          # Iniciar sistema"
        echo ""
        echo "SI HAY PROBLEMAS:"
        echo "  ./paloma.sh doctor            # Diagnosticar y arreglar"
        echo ""
        exit 1
        ;;
esac
