#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🐦 ====================================================="
echo "   PALOMA LICITERA - INSTALACIÓN DESDE CERO"
echo "   Dashboard de Licitaciones v2.0 (Docker + Scheduler)"
echo -e "=====================================================${NC}"
echo ""

# Función timeout para macOS
timeout_cmd() {
    local timeout_duration=$1
    shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "$timeout_duration" "$@"
    else
        # macOS no tiene timeout, usamos gtimeout si está disponible
        if command -v gtimeout >/dev/null 2>&1; then
            gtimeout "$timeout_duration" "$@"
        else
            # Fallback: ejecutar sin timeout
            echo -e "${YELLOW}   ⚠️  Ejecutando sin timeout (macOS)${NC}"
            "$@"
        fi
    fi
}

# Función para verificar comandos
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 no encontrado${NC}"
        return 1
    else
        VERSION=$($2 2>/dev/null || echo "")
        echo -e "${GREEN}✅ $1 ${VERSION} encontrado${NC}"
        return 0
    fi
}

# Función para mostrar progreso
show_progress() {
    echo -e "${BLUE}🔄 $1...${NC}"
}

# Función para limpiar Docker completamente
clean_docker() {
    echo -e "${YELLOW}🧹 Limpiando instalación anterior...${NC}"
    
    # Detener contenedores
    docker-compose down -v 2>/dev/null || true
    
    # Limpiar imágenes relacionadas
    docker images | grep paloma | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
    docker images | grep none | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
    
    # Limpiar sistema
    docker system prune -f 2>/dev/null || true
    docker volume prune -f 2>/dev/null || true
    
    echo -e "${GREEN}✅ Docker limpiado${NC}"
}

# Función para manejo de errores
handle_error() {
    echo -e "${RED}❌ Error en la instalación${NC}"
    echo ""
    echo -e "${YELLOW}🔍 Para diagnosticar el problema:${NC}"
    echo "   1. Ver logs de PostgreSQL: docker-compose logs postgres"
    echo "   2. Ver logs completos: docker-compose logs"
    echo "   3. Verificar puertos: lsof -i :5432 -i :8000"
    echo ""
    echo -e "${BLUE}🧹 Para limpiar e intentar de nuevo:${NC}"
    echo "   ./cleanup.sh"
    echo "   ./install.sh"
    echo ""
    exit 1
}

# PASO 0: Verificar si es una re-instalación
if docker-compose ps 2>/dev/null | grep -q "paloma"; then
    echo -e "${YELLOW}⚠️  Se detectó una instalación anterior${NC}"
    echo -n "¿Deseas limpiar y reinstalar completamente? (y/N): "
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        clean_docker
    fi
fi

# PASO 0: Mostrar opciones de instalación
echo -e "${YELLOW}📋 MÉTODO DE INSTALACIÓN${NC}"
echo ""
echo "Elige el método de instalación:"
echo -e "  ${GREEN}1) Docker (Recomendado)${NC} - Instalación automática completa"
echo -e "  ${YELLOW}2) Manual${NC} - Python local + PostgreSQL"
echo ""
echo -n "Selecciona opción (1 o 2): "
read -r INSTALL_METHOD

if [[ "$INSTALL_METHOD" == "1" ]]; then
    DOCKER_INSTALL=true
    echo -e "${GREEN}✅ Instalación con Docker seleccionada${NC}"
else
    DOCKER_INSTALL=false
    echo -e "${YELLOW}⚡ Instalación manual seleccionada${NC}"
fi

echo ""

# PASO 1: Verificar prerequisitos
echo -e "${YELLOW}📋 PASO 1: Verificando prerequisitos...${NC}"
echo ""

if [ "$DOCKER_INSTALL" = true ]; then
    # Verificar Docker y Docker Compose
    if ! check_command "docker" "docker --version | awk '{print \$3}' | sed 's/,//g'"; then
        echo -e "${RED}❌ Docker no encontrado${NC}"
        echo "   Instala Docker desde: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! check_command "docker-compose" "docker-compose --version | awk '{print \$3}' | sed 's/,//g'"; then
        # Intentar docker compose (versión nueva)
        if ! docker compose version &> /dev/null; then
            echo -e "${RED}❌ Docker Compose no encontrado${NC}"
            echo "   Instala Docker Compose desde: https://docs.docker.com/compose/install/"
            exit 1
        else
            echo -e "${GREEN}✅ docker compose encontrado${NC}"
            # Crear alias para docker-compose
            alias docker-compose='docker compose'
        fi
    fi

    # Verificar que Docker esté corriendo
    if ! docker ps &> /dev/null; then
        echo -e "${RED}❌ Docker no está ejecutándose${NC}"
        echo "   Inicia Docker y vuelve a ejecutar este script"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker está ejecutándose correctamente${NC}"

    # Verificar que no haya conflictos de puertos
    if lsof -i :5432 >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Puerto 5432 está en uso (probablemente PostgreSQL local)${NC}"
        echo "   Esto podría causar conflictos. ¿Continuar? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            echo "   Para usar PostgreSQL local, elige la opción 2 (Manual)"
            exit 1
        fi
    fi

    if lsof -i :8000 >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Puerto 8000 está en uso${NC}"
        echo "   Deteniendo proceso en puerto 8000..."
        lsof -ti :8000 | xargs kill -9 2>/dev/null || true
    fi

    # Verificar espacio en disco (macOS)
    AVAILABLE_SPACE=$(df / | awk 'NR==2 {print $4}')
    if [ "$AVAILABLE_SPACE" -lt 2097152 ]; then # 2GB en KB
        echo -e "${YELLOW}⚠️  Espacio en disco bajo (menos de 2GB disponible)${NC}"
        echo "   La instalación podría fallar por falta de espacio"
    fi

else
    # Verificaciones para instalación manual
    if ! check_command "python3" "python3 --version 2>&1 | cut -d' ' -f2"; then
        echo -e "${RED}❌ Python 3.8+ requerido${NC}"
        exit 1
    fi

    if ! check_command "node" "node --version"; then
        echo -e "${RED}❌ Node.js 16+ requerido${NC}"
        exit 1
    fi

    if ! check_command "npm" "npm --version"; then
        echo -e "${RED}❌ npm requerido${NC}"
        exit 1
    fi

    if ! check_command "psql" "psql --version | awk '{print \$3}'"; then
        echo -e "${YELLOW}⚠️  PostgreSQL no encontrado - necesitarás configurarlo${NC}"
    fi
fi

# Verificar Git
if ! check_command "git" "git --version | awk '{print \$3}'"; then
    echo -e "${RED}❌ Git requerido${NC}"
    exit 1
fi

# PASO 2: Crear directorios necesarios
echo ""
echo -e "${YELLOW}📁 PASO 2: Creando estructura de directorios...${NC}"
echo ""

show_progress "Creando directorios"
mkdir -p data/raw data/processed logs

if [ "$DOCKER_INSTALL" = false ]; then
    mkdir -p exports
fi

echo -e "${GREEN}✅ Directorios creados${NC}"

# PASO 3: Configurar permisos de scripts
echo ""
echo -e "${YELLOW}🔧 PASO 3: Configurando permisos de scripts...${NC}"
echo ""

show_progress "Asignando permisos"
chmod +x docker-start.sh docker-stop.sh run-scheduler.sh cleanup.sh 2>/dev/null || true

if [ "$DOCKER_INSTALL" = false ]; then
    chmod +x start_dashboard.sh stop_dashboard.sh 2>/dev/null || true
fi

echo -e "${GREEN}✅ Permisos configurados${NC}"

if [ "$DOCKER_INSTALL" = true ]; then
    # INSTALACIÓN DOCKER
    echo ""
    echo -e "${CYAN}🐳 INSTALACIÓN DOCKER${NC}"
    echo ""

    # PASO 4: Construir contenedores
    echo -e "${YELLOW}🔨 PASO 4: Construyendo contenedores Docker...${NC}"
    echo ""
    
    show_progress "Construyendo imágenes Docker (puede tomar 5-10 minutos)"
    echo -e "${BLUE}   ℹ️  Descargando dependencias Python y configurando Playwright...${NC}"
    
    # Construir con logs visibles
    if docker-compose build --no-cache; then
        echo -e "${GREEN}✅ Contenedores construidos exitosamente${NC}"
    else
        echo -e "${RED}❌ Error construyendo contenedores${NC}"
        handle_error
    fi

    # PASO 5: Iniciar servicios paso a paso
    echo ""
    echo -e "${YELLOW}🚀 PASO 5: Iniciando servicios...${NC}"
    echo ""

    show_progress "Iniciando PostgreSQL"
    docker-compose up -d postgres

    show_progress "Esperando PostgreSQL (60 segundos para macOS)"
    sleep 60

    # Verificar PostgreSQL con más intentos para macOS
    show_progress "Verificando PostgreSQL"
    POSTGRES_READY=false
    for i in {1..10}; do
        if docker-compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
            echo -e "${GREEN}✅ PostgreSQL iniciado correctamente${NC}"
            POSTGRES_READY=true
            break
        else
            echo -e "${YELLOW}   Reintento $i/10... (PostgreSQL puede tardar más en macOS)${NC}"
            sleep 10
        fi
    done

    if [ "$POSTGRES_READY" = false ]; then
        echo -e "${RED}❌ PostgreSQL no inició correctamente${NC}"
        echo ""
        echo -e "${YELLOW}🔍 Logs de PostgreSQL:${NC}"
        docker-compose logs postgres
        handle_error
    fi

    show_progress "Iniciando aplicación y scheduler"
    docker-compose up -d paloma-app scheduler

    # PASO 6: Verificar servicios
    echo ""
    echo -e "${YELLOW}✅ PASO 6: Verificando servicios...${NC}"
    echo ""

    sleep 20

    # Verificar contenedores
    echo -e "${BLUE}Estado de contenedores:${NC}"
    docker-compose ps

    # Verificar API con paciencia para macOS
    show_progress "Verificando API (puede tardar en macOS)"
    API_READY=false
    for i in {1..20}; do
        if curl -s http://localhost:8000/ > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API respondiendo en http://localhost:8000${NC}"
            API_READY=true
            break
        fi
        sleep 5
        if [ $((i % 4)) -eq 0 ]; then
            echo -e "${YELLOW}   Esperando API... ($i/20)${NC}"
        fi
    done

    if [ "$API_READY" = false ]; then
        echo -e "${YELLOW}⚠️  API tardando en responder${NC}"
        echo "   Verifica manualmente en unos minutos: http://localhost:8000"
        echo ""
        echo -e "${BLUE}Logs de la aplicación:${NC}"
        docker-compose logs --tail=20 paloma-app
    fi

    # PASO 7: DESCARGA INICIAL REAL (12 MESES)
    echo ""
    echo -e "${YELLOW}📊 PASO 7: Descarga inicial de datos (12 meses)${NC}"
    echo ""
    
    echo -e "${BLUE}💡 DESCARGA INICIAL = Últimos 12 meses de licitaciones${NC}"
    echo "   • ComprasMX: ~50,000-100,000 registros"
    echo "   • DOF: ~5,000-10,000 registros" 
    echo "   • Tianguis Digital: ~10,000-20,000 registros"
    echo "   • Tiempo estimado: 30-60 minutos"
    echo ""
    
    echo -n "¿Ejecutar descarga inicial completa (12 meses)? (Y/n): "
    read -r response
    if [[ ! "$response" =~ ^([nN][oO]|[nN])$ ]]; then
        # Calcular fecha de hace 12 meses
        if command -v gdate >/dev/null 2>&1; then
            # macOS con GNU date
            FECHA_INICIAL=$(gdate -d "12 months ago" +%Y-%m-%d)
        elif date -v-12m >/dev/null 2>&1; then
            # macOS con BSD date
            FECHA_INICIAL=$(date -v-12m +%Y-%m-%d)
        else
            # Linux con GNU date
            FECHA_INICIAL=$(date -d "12 months ago" +%Y-%m-%d)
        fi
        
        echo -e "${GREEN}🗓️  Descargando desde: $FECHA_INICIAL${NC}"
        echo -e "${BLUE}🔄 Iniciando descarga histórica de 12 meses...${NC}"
        echo -e "${YELLOW}   ⏳ Esto tomará tiempo, mantén la terminal abierta...${NC}"
        
        sleep 5  # Tiempo para que el scheduler esté completamente listo
        
        if ./run-scheduler.sh historico --fuente=all --desde="$FECHA_INICIAL"; then
            echo -e "${GREEN}✅ Descarga inicial completada${NC}"
            
            # Mostrar estadísticas
            echo ""
            echo -e "${CYAN}📊 ESTADÍSTICAS DE DESCARGA:${NC}"
            ./run-scheduler.sh status | grep -A 10 "by_source" || echo "   Ver estadísticas en: ./run-scheduler.sh status"
            
        else
            echo -e "${YELLOW}⚠️  Error en descarga inicial, pero el sistema está funcionando${NC}"
            echo "   Puedes intentar más tarde con:"
            echo "   ./run-scheduler.sh historico --fuente=all --desde=$FECHA_INICIAL"
        fi
    else
        echo -e "${YELLOW}ℹ️  Descarga inicial omitida${NC}"
        echo "   Puedes ejecutar después:"
        echo "   ./run-scheduler.sh historico --fuente=all --desde=2024-01-01"
        echo "   ./run-scheduler.sh incremental  # Solo nuevas licitaciones"
    fi

else
    # INSTALACIÓN MANUAL (código simplificado)
    echo ""
    echo -e "${PURPLE}⚡ INSTALACIÓN MANUAL${NC}"
    echo ""

    show_progress "Configurando Python virtual environment"
    python3 -m venv venv
    source venv/bin/activate

    show_progress "Instalando dependencias Python"
    pip install --upgrade pip --quiet
    pip install -r requirements.txt

    show_progress "Configurando Frontend"
    cd frontend
    npm cache clean --force
    npm install
    cd ..

    echo -e "${GREEN}✅ Instalación manual completada${NC}"
fi

# RESUMEN FINAL
echo ""
echo -e "${GREEN}====================================================="
echo "✅ INSTALACIÓN COMPLETADA"
echo -e "=====================================================${NC}"
echo ""

if [ "$DOCKER_INSTALL" = true ]; then
    echo -e "${CYAN}🐳 DOCKER INSTALACIÓN COMPLETADA${NC}"
    echo ""
    echo -e "${PURPLE}📊 ACCESOS:${NC}"
    echo "   • Dashboard: http://localhost:8000"
    echo "   • API Docs: http://localhost:8000/docs"
    echo ""
    echo -e "${YELLOW}🚀 COMANDOS ÚTILES:${NC}"
    echo ""
    echo -e "   ${GREEN}./run-scheduler.sh status${NC}          # Ver estado y estadísticas"
    echo -e "   ${GREEN}./run-scheduler.sh incremental${NC}     # Nuevas licitaciones"
    echo -e "   ${GREEN}./run-scheduler.sh historico --fuente=comprasmx --desde=2024-06-01${NC}  # Histórico específico"
    echo -e "   ${GREEN}docker-compose logs -f${NC}            # Ver logs"
    echo -e "   ${GREEN}./docker-stop.sh${NC}                  # Detener"
    echo -e "   ${GREEN}./cleanup.sh${NC}                      # Limpiar"
    echo ""
    echo -e "${BLUE}🔧 TROUBLESHOOTING:${NC}"
    echo "   • Logs PostgreSQL: docker-compose logs postgres"
    echo "   • Logs API: docker-compose logs paloma-app"
    echo "   • Logs Scheduler: docker-compose logs scheduler"

    # Preguntar si abrir navegador
    echo ""
    echo -n "¿Abrir dashboard en navegador? (y/N): "
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        sleep 3
        if command -v open &> /dev/null; then
            open http://localhost:8000
        fi
    fi
else
    echo -e "${PURPLE}⚡ INSTALACIÓN MANUAL COMPLETADA${NC}"
    echo ""
    echo -e "   ${GREEN}./start_dashboard.sh${NC}     # Iniciar"
    echo -e "   ${GREEN}./stop_dashboard.sh${NC}      # Detener"
fi

echo ""
echo -e "${GREEN}🎉 ¡Paloma Licitera lista para usar!${NC}"