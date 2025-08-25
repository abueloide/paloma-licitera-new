#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐦 ===================================================="
echo "   PALOMA LICITERA - INSTALACIÓN COMPLETA"
echo -e "====================================================${NC}"
echo ""

# Función para verificar comandos
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 no encontrado${NC}"
        return 1
    else
        VERSION=$($2)
        echo -e "${GREEN}✅ $1 $VERSION encontrado${NC}"
        return 0
    fi
}

# PASO 1: Verificar prerequisitos
echo -e "${YELLOW}📋 PASO 1: Verificando prerequisitos...${NC}"
echo ""

# Verificar Python 3
if ! check_command "python3" "python3 --version 2>&1 | cut -d' ' -f2"; then
    echo -e "${RED}Por favor instala Python 3.9 o superior${NC}"
    exit 1
fi

# Verificar Node.js
if ! check_command "node" "node --version"; then
    echo -e "${RED}Por favor instala Node.js 18 o superior${NC}"
    exit 1
fi

# Verificar npm
if ! check_command "npm" "npm --version"; then
    echo -e "${RED}Por favor instala npm${NC}"
    exit 1
fi

# Verificar PostgreSQL
echo ""
echo -e "${BLUE}🔍 Verificando PostgreSQL...${NC}"
if command -v psql &> /dev/null; then
    PSQL_VERSION=$(psql --version | awk '{print $3}')
    echo -e "${GREEN}✅ PostgreSQL $PSQL_VERSION encontrado${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL no encontrado (opcional si usas remoto)${NC}"
fi

# PASO 2: Configurar entorno Python
echo ""
echo -e "${YELLOW}📦 PASO 2: Configurando entorno Python...${NC}"
echo ""

# Crear o recrear entorno virtual
if [ -d "venv" ]; then
    echo -e "${BLUE}🔄 Entorno virtual existente encontrado${NC}"
    echo -n "   ¿Deseas recrearlo? (y/N): "
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "   Eliminando entorno anterior..."
        rm -rf venv
        echo "   Creando nuevo entorno virtual..."
        python3 -m venv venv
    fi
else
    echo -e "${BLUE}📁 Creando entorno virtual...${NC}"
    python3 -m venv venv
fi

# Activar entorno virtual
echo -e "${BLUE}🔌 Activando entorno virtual...${NC}"
source venv/bin/activate

# Actualizar pip
echo -e "${BLUE}📈 Actualizando pip...${NC}"
pip install --upgrade pip --quiet

# PASO 3: Instalar dependencias Python
echo ""
echo -e "${YELLOW}📚 PASO 3: Instalando dependencias Python...${NC}"
echo ""

# Crear requirements.txt si no existe
if [ ! -f "requirements.txt" ]; then
    echo -e "${BLUE}📝 Creando requirements.txt...${NC}"
    cat > requirements.txt << 'REQ'
# Core
python-dotenv==1.0.0
pyyaml==6.0.1

# Database
psycopg2-binary>=2.9.10
sqlalchemy>=2.0.25

# Web scraping
playwright>=1.45.0
beautifulsoup4==4.12.2
requests==2.31.0

# Data processing
pandas>=2.2.0
python-dateutil==2.8.2

# API
fastapi>=0.110.0
uvicorn>=0.27.0
pydantic>=2.6.0

# Utils
chardet==5.2.0
REQ
fi

echo -e "${BLUE}📦 Instalando paquetes...${NC}"
pip install -r requirements.txt

# Verificar instalación
echo ""
echo -e "${GREEN}✔️  Verificando paquetes críticos...${NC}"
for package in uvicorn fastapi psycopg2 pandas playwright; do
    if pip show $package &> /dev/null; then
        echo -e "   ${GREEN}✅ $package instalado${NC}"
    else
        echo -e "   ${RED}❌ $package NO instalado${NC}"
    fi
done

# Instalar navegadores para Playwright
echo ""
echo -e "${BLUE}🌐 Instalando navegadores para Playwright...${NC}"
playwright install chromium --quiet

# PASO 4: Instalar dependencias Frontend
echo ""
echo -e "${YELLOW}🎨 PASO 4: Instalando dependencias Frontend...${NC}"
echo ""

cd frontend
echo -e "${BLUE}🧹 Limpiando caché de npm...${NC}"
npm cache clean --force

echo -e "${BLUE}📦 Instalando paquetes npm...${NC}"
npm install

cd ..

# PASO 5: Verificar configuración
echo ""
echo -e "${YELLOW}⚙️  PASO 5: Verificando configuración...${NC}"
echo ""

if [ -f "config.yaml" ]; then
    echo -e "${GREEN}✅ config.yaml encontrado${NC}"
else
    echo -e "${YELLOW}📝 Creando config.yaml de ejemplo...${NC}"
    cat > config.yaml << 'CONFIG'
database:
  host: localhost
  port: 5432
  name: paloma_licitera
  user: postgres
  password: postgres

api:
  host: 0.0.0.0
  port: 8000
  reload: true

scrapers:
  tianguis:
    enabled: true
    base_url: "https://tianguisdigital.finanzas.cdmx.gob.mx"
  comprasmx:
    enabled: true
    base_url: "https://comprasmx.hacienda.gob.mx"
CONFIG
    echo -e "${GREEN}✅ config.yaml creado${NC}"
fi

# PASO 6: Verificar base de datos
echo ""
echo -e "${YELLOW}🗄️  PASO 6: Verificando base de datos...${NC}"
echo ""

if command -v psql &> /dev/null; then
    # Intentar conectar a PostgreSQL
    if psql -h localhost -U postgres -d paloma_licitera -c "SELECT COUNT(*) FROM licitaciones;" &> /dev/null; then
        COUNT=$(psql -h localhost -U postgres -d paloma_licitera -t -c "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null | xargs)
        echo -e "${GREEN}✅ Conexión a PostgreSQL exitosa${NC}"
        echo -e "${BLUE}📊 Base de datos contiene $COUNT licitaciones${NC}"
    else
        echo -e "${YELLOW}⚠️  No se pudo conectar a la base de datos${NC}"
        echo "   Verifica que PostgreSQL esté ejecutándose y las credenciales en config.yaml"
    fi
else
    echo -e "${YELLOW}⚠️  psql no encontrado, no se puede verificar la base de datos${NC}"
fi

# PASO 7: Actualizar scripts de inicio
echo ""
echo -e "${YELLOW}🚀 PASO 7: Creando scripts optimizados...${NC}"
echo ""

# Crear start_dashboard.sh mejorado
cat > start_dashboard.sh << 'STARTSCRIPT'
#!/bin/bash

echo "🐦 Iniciando Paloma Licitera Dashboard..."

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "🔌 Activando entorno virtual..."
    source venv/bin/activate
else
    echo "⚠️  No se encontró entorno virtual. Ejecuta ./install.sh primero"
    exit 1
fi

# Verificar PostgreSQL
if command -v psql &> /dev/null; then
    COUNT=$(psql -h localhost -U postgres -d paloma_licitera -t -c "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null | xargs)
    if [ ! -z "$COUNT" ]; then
        echo "📊 Base de datos contiene $COUNT licitaciones"
    fi
fi

# Crear directorio de logs
mkdir -p logs

echo ""
echo "🚀 Iniciando servicios..."

# Matar procesos anteriores si existen
if [ -f .backend.pid ]; then
    OLD_PID=$(cat .backend.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "   ⏹️  Deteniendo backend anterior..."
        kill $OLD_PID 2>/dev/null
    fi
fi

if [ -f .frontend.pid ]; then
    OLD_PID=$(cat .frontend.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "   ⏹️  Deteniendo frontend anterior..."
        kill $OLD_PID 2>/dev/null
    fi
fi

# Iniciar backend
echo "   📡 Iniciando backend API (puerto 8000)..."
python src/api.py > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Verificar que el backend se inició
sleep 2
if ps -p $BACKEND_PID > /dev/null; then
    echo "   ✅ Backend iniciado (PID: $BACKEND_PID)"
    echo $BACKEND_PID > .backend.pid
else
    echo "   ❌ Error al iniciar el backend"
    echo "   Ver logs en: logs/backend.log"
    tail -n 20 logs/backend.log
    exit 1
fi

# Esperar a que el backend esté listo
echo "   ⏳ Esperando a que el backend esté listo..."
for i in {1..10}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "   ✅ Backend respondiendo correctamente"
        break
    fi
    sleep 1
done

# Iniciar frontend
echo "   🎨 Iniciando frontend (puerto 5173)..."
cd frontend && npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Verificar que el frontend se inició
sleep 2
if ps -p $FRONTEND_PID > /dev/null; then
    echo "   ✅ Frontend iniciado (PID: $FRONTEND_PID)"
    echo $FRONTEND_PID > .frontend.pid
else
    echo "   ❌ Error al iniciar el frontend"
    echo "   Ver logs en: logs/frontend.log"
    exit 1
fi

echo ""
echo "======================================"
echo "✅ Dashboard iniciado correctamente"
echo "======================================"
echo ""
echo "🌐 Abrir en el navegador:"
echo "   http://localhost:5173"
echo ""
echo "📊 API disponible en:"
echo "   http://localhost:8000"
echo "   http://localhost:8000/docs (Swagger UI)"
echo ""
echo "📝 Logs disponibles en:"
echo "   - Backend: logs/backend.log"
echo "   - Frontend: logs/frontend.log"
echo ""
echo "⏹️  Para detener: ./stop_dashboard.sh"
echo ""

# Abrir navegador automáticamente
sleep 2
if command -v open &> /dev/null; then
    open http://localhost:5173
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173
fi

# Mantener el script corriendo y mostrar logs
echo "📋 Presiona Ctrl+C para detener todos los servicios"
echo ""

# Trap para limpiar al salir
trap 'echo ""; echo "⏹️  Deteniendo servicios..."; ./stop_dashboard.sh; exit' INT TERM

# Mantener el script vivo
wait
STARTSCRIPT

# Crear stop_dashboard.sh mejorado
cat > stop_dashboard.sh << 'STOPSCRIPT'
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
STOPSCRIPT

# Hacer ejecutables los scripts
chmod +x start_dashboard.sh
chmod +x stop_dashboard.sh

echo -e "${GREEN}✅ Scripts creados y marcados como ejecutables${NC}"

# PASO 8: Crear directorios necesarios
echo ""
echo -e "${YELLOW}📁 PASO 8: Creando directorios necesarios...${NC}"
echo ""

mkdir -p logs
mkdir -p data
mkdir -p exports

echo -e "${GREEN}✅ Directorios creados${NC}"

# Resumen final
echo ""
echo -e "${GREEN}===================================================="
echo "✅ INSTALACIÓN COMPLETADA CON ÉXITO"
echo "====================================================${NC}"
echo ""
echo -e "${BLUE}📋 Resumen de la instalación:${NC}"
echo "   • Python con entorno virtual en: venv/"
echo "   • Dependencias Python instaladas"
echo "   • Dependencias Frontend instaladas"
echo "   • Scripts de inicio actualizados"
echo "   • Configuración verificada"
echo ""
echo -e "${YELLOW}🚀 Para iniciar la aplicación:${NC}"
echo ""
echo "   ${GREEN}./start_dashboard.sh${NC}"
echo ""
echo -e "${YELLOW}⏹️  Para detener la aplicación:${NC}"
echo ""
echo "   ${GREEN}./stop_dashboard.sh${NC}"
echo ""
echo -e "${BLUE}📝 NOTAS IMPORTANTES:${NC}"
echo "   • El script activa automáticamente el entorno virtual"
echo "   • Los logs se guardan en logs/"
echo "   • Asegúrate de que PostgreSQL esté ejecutándose"
echo "   • Verifica las credenciales en config.yaml"
echo ""
echo -e "${GREEN}¡Listo para usar! 🎉${NC}"

# Preguntar si quiere iniciar ahora
echo ""
echo -n "¿Deseas iniciar el dashboard ahora? (y/N): "
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo ""
    ./start_dashboard.sh
fi
