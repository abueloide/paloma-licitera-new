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
        fi
    fi

    # Verificar que Docker esté corriendo
    if ! docker ps &> /dev/null; then
        echo -e "${RED}❌ Docker no está ejecutándose${NC}"
        echo "   Inicia Docker y vuelve a ejecutar este script"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker está ejecutándose correctamente${NC}"

else
    # Verificar Python 3
    if ! check_command "python3" "python3 --version 2>&1 | cut -d' ' -f2"; then
        echo -e "${RED}❌ Python 3.8+ requerido${NC}"
        exit 1
    fi

    # Verificar Node.js
    if ! check_command "node" "node --version"; then
        echo -e "${RED}❌ Node.js 16+ requerido${NC}"
        exit 1
    fi

    # Verificar npm
    if ! check_command "npm" "npm --version"; then
        echo -e "${RED}❌ npm requerido${NC}"
        exit 1
    fi

    # Verificar PostgreSQL
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
echo "   • data/raw - Datos crudos de scrapers"
echo "   • data/processed - Datos procesados"  
echo "   • logs - Logs del sistema"

# PASO 3: Configurar permisos de scripts
echo ""
echo -e "${YELLOW}🔧 PASO 3: Configurando permisos de scripts...${NC}"
echo ""

show_progress "Asignando permisos"
chmod +x docker-start.sh docker-stop.sh run-scheduler.sh 2>/dev/null || true

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
    
    show_progress "Construyendo imágenes Docker (esto puede tomar varios minutos)"
    if docker-compose build --no-cache; then
        echo -e "${GREEN}✅ Contenedores construidos exitosamente${NC}"
    else
        echo -e "${RED}❌ Error construyendo contenedores${NC}"
        exit 1
    fi

    # PASO 5: Iniciar servicios
    echo ""
    echo -e "${YELLOW}🚀 PASO 5: Iniciando servicios...${NC}"
    echo ""

    show_progress "Iniciando PostgreSQL"
    docker-compose up -d postgres

    show_progress "Esperando PostgreSQL (30 segundos)"
    sleep 30

    show_progress "Verificando PostgreSQL"
    if docker-compose exec -T postgres pg_isready -U postgres; then
        echo -e "${GREEN}✅ PostgreSQL iniciado correctamente${NC}"
    else
        echo -e "${RED}❌ Error iniciando PostgreSQL${NC}"
        echo "Ver logs: docker-compose logs postgres"
        exit 1
    fi

    show_progress "Iniciando aplicación y scheduler"
    docker-compose up -d paloma-app scheduler

    # PASO 6: Verificar servicios
    echo ""
    echo -e "${YELLOW}✅ PASO 6: Verificando servicios...${NC}"
    echo ""

    sleep 10

    # Verificar que los contenedores estén corriendo
    if docker-compose ps | grep -q "running"; then
        echo -e "${GREEN}✅ Servicios Docker iniciados${NC}"
        docker-compose ps
    else
        echo -e "${RED}❌ Error en servicios Docker${NC}"
        docker-compose logs
        exit 1
    fi

    # Verificar API
    show_progress "Verificando API"
    for i in {1..10}; do
        if curl -s http://localhost:8000/ > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API respondiendo en http://localhost:8000${NC}"
            break
        fi
        sleep 3
        if [ $i -eq 10 ]; then
            echo -e "${YELLOW}⚠️  API no responde aún, pero puede estar iniciando${NC}"
        fi
    done

    # PASO 7: Primera carga de datos (opcional)
    echo ""
    echo -e "${YELLOW}📊 PASO 7: Carga inicial de datos${NC}"
    echo ""
    
    echo -n "¿Deseas ejecutar una carga inicial de datos? (y/N): "
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${BLUE}🔄 Ejecutando carga incremental...${NC}"
        ./run-scheduler.sh incremental
        echo -e "${GREEN}✅ Carga inicial completada${NC}"
    else
        echo -e "${YELLOW}ℹ️  Puedes ejecutar datos después con: ./run-scheduler.sh incremental${NC}"
    fi

else
    # INSTALACIÓN MANUAL
    echo ""
    echo -e "${PURPLE}⚡ INSTALACIÓN MANUAL${NC}"
    echo ""

    # PASO 4: Configurar entorno Python
    echo -e "${YELLOW}📦 PASO 4: Configurando entorno Python...${NC}"
    echo ""

    show_progress "Creando entorno virtual"
    python3 -m venv venv
    
    show_progress "Activando entorno virtual"
    source venv/bin/activate

    show_progress "Actualizando pip"
    pip install --upgrade pip --quiet

    show_progress "Instalando dependencias Python"
    pip install -r requirements.txt

    echo -e "${GREEN}✅ Entorno Python configurado${NC}"

    # PASO 5: Instalar dependencias Frontend
    echo ""
    echo -e "${YELLOW}🎨 PASO 5: Configurando Frontend...${NC}"
    echo ""

    cd frontend
    show_progress "Limpiando caché npm"
    npm cache clean --force

    show_progress "Instalando dependencias npm"
    npm install

    cd ..
    echo -e "${GREEN}✅ Frontend configurado${NC}"

    # PASO 6: Configurar base de datos
    echo ""
    echo -e "${YELLOW}🗄️  PASO 6: Configuración de base de datos...${NC}"
    echo ""

    if command -v psql &> /dev/null; then
        echo -e "${GREEN}ℹ️  PostgreSQL encontrado${NC}"
        echo "   Asegúrate de que PostgreSQL esté ejecutándose"
        echo "   Configura las credenciales en config.yaml"
    else
        echo -e "${YELLOW}⚠️  PostgreSQL no encontrado${NC}"
        echo "   Instala PostgreSQL o configura una instancia remota"
    fi
fi

# RESUMEN FINAL
echo ""
echo -e "${GREEN}====================================================="
echo "✅ INSTALACIÓN COMPLETADA CON ÉXITO"
echo -e "=====================================================${NC}"
echo ""

if [ "$DOCKER_INSTALL" = true ]; then
    echo -e "${CYAN}🐳 INSTALACIÓN DOCKER COMPLETADA${NC}"
    echo ""
    echo -e "${BLUE}📋 Servicios iniciados:${NC}"
    echo "   • PostgreSQL: localhost:5432"
    echo "   • API REST: http://localhost:8000"
    echo "   • Scheduler: Modo daemon activo"
    echo ""
    echo -e "${YELLOW}🚀 COMANDOS DISPONIBLES:${NC}"
    echo ""
    echo -e "   ${GREEN}./run-scheduler.sh status${NC}          # Ver estado del sistema"
    echo -e "   ${GREEN}./run-scheduler.sh incremental${NC}     # Actualización incremental"
    echo -e "   ${GREEN}./run-scheduler.sh historico --fuente=all --desde=2025-01-01${NC}  # Descarga histórica"
    echo -e "   ${GREEN}docker-compose logs -f scheduler${NC}   # Ver logs del scheduler"
    echo -e "   ${GREEN}./docker-stop.sh${NC}                  # Detener servicios"
    echo ""
    echo -e "${PURPLE}📊 ACCESOS:${NC}"
    echo "   • Dashboard: http://localhost:8000"
    echo "   • API Docs: http://localhost:8000/docs"
    echo ""
    echo -e "${CYAN}🔄 AUTOMATIZACIÓN:${NC}"
    echo "   • ComprasMX y Tianguis: cada 6 horas"
    echo "   • DOF: martes y jueves 9:00-10:00 AM y 21:00-22:00 PM"
    echo "   • Sitios masivos: domingos 2:00 AM"

else
    echo -e "${PURPLE}⚡ INSTALACIÓN MANUAL COMPLETADA${NC}"
    echo ""
    echo -e "${YELLOW}🚀 Para iniciar la aplicación:${NC}"
    echo ""
    echo -e "   ${GREEN}./start_dashboard.sh${NC}"
    echo ""
    echo -e "${YELLOW}⏹️  Para detener la aplicación:${NC}"
    echo ""
    echo -e "   ${GREEN}./stop_dashboard.sh${NC}"
    echo ""
    echo -e "${BLUE}📝 NOTAS:${NC}"
    echo "   • Configura PostgreSQL en config.yaml"
    echo "   • Los logs se guardan en logs/"
    echo "   • El frontend estará en http://localhost:3001"
    echo "   • La API estará en http://localhost:8000"
fi

echo ""
echo -e "${GREEN}🎉 ¡Paloma Licitera está lista para usar!${NC}"
echo ""

# Preguntar si abrir en navegador
if [ "$DOCKER_INSTALL" = true ]; then
    echo -n "¿Deseas abrir el dashboard en el navegador? (y/N): "
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        sleep 2
        if command -v open &> /dev/null; then
            open http://localhost:8000
        elif command -v xdg-open &> /dev/null; then
            xdg-open http://localhost:8000
        else
            echo "Abre manualmente: http://localhost:8000"
        fi
    fi
fi