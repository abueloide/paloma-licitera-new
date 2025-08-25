#!/bin/bash

# =================================================================
# PALOMA LICITERA - INSTALACIÓN COMPLETA DE DEPENDENCIAS
# =================================================================
# Este script asegura que TODAS las dependencias estén instaladas
# correctamente antes de iniciar el dashboard
# =================================================================

set -e  # Salir en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐦 ====================================================${NC}"
echo -e "${BLUE}   PALOMA LICITERA - INSTALACIÓN DE DEPENDENCIAS${NC}"
echo -e "${BLUE}====================================================${NC}"
echo ""

# ---------------------------------------------
# 1. VERIFICAR SISTEMA OPERATIVO
# ---------------------------------------------
echo -e "${YELLOW}📋 PASO 1: Detectando sistema operativo...${NC}"
OS=""
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo -e "${GREEN}✅ Sistema Linux detectado${NC}"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo -e "${GREEN}✅ Sistema macOS detectado${NC}"
else
    echo -e "${RED}❌ Sistema operativo no soportado${NC}"
    exit 1
fi

# ---------------------------------------------
# 2. VERIFICAR PREREQUISITOS BÁSICOS
# ---------------------------------------------
echo ""
echo -e "${YELLOW}📋 PASO 2: Verificando prerequisitos básicos...${NC}"

# Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no está instalado${NC}"
    echo "   Por favor instala Python 3.9 o superior"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✅ Python $PYTHON_VERSION encontrado${NC}"

# Verificar pip
if ! python3 -m pip --version &> /dev/null; then
    echo -e "${YELLOW}⚠️  pip no está instalado, instalando...${NC}"
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py
    rm get-pip.py
fi
echo -e "${GREEN}✅ pip encontrado${NC}"

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js no está instalado${NC}"
    echo "   Por favor instala Node.js 16 o superior"
    echo "   Visita: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js $NODE_VERSION encontrado${NC}"

# Verificar npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm no está instalado${NC}"
    exit 1
fi

NPM_VERSION=$(npm --version)
echo -e "${GREEN}✅ npm $NPM_VERSION encontrado${NC}"

# Verificar PostgreSQL
echo ""
echo -e "${YELLOW}🔍 Verificando PostgreSQL...${NC}"
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}⚠️  PostgreSQL no está instalado o psql no está en PATH${NC}"
    echo "   La aplicación requiere PostgreSQL para funcionar"
    echo "   ¿Continuar de todos modos? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    PSQL_VERSION=$(psql --version | awk '{print $3}')
    echo -e "${GREEN}✅ PostgreSQL $PSQL_VERSION encontrado${NC}"
fi

# ---------------------------------------------
# 3. LIMPIAR INSTALACIONES ANTERIORES
# ---------------------------------------------
echo ""
echo -e "${YELLOW}📋 PASO 3: Limpiando instalaciones anteriores...${NC}"

# Preguntar antes de limpiar
if [ -d "venv" ] || [ -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}⚠️  Se encontraron instalaciones anteriores${NC}"
    echo "   ¿Deseas hacer una instalación limpia? (recomendado) (Y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Nn]$ ]]; then
        echo "   Limpiando entorno virtual Python..."
        rm -rf venv
        echo "   Limpiando node_modules..."
        rm -rf frontend/node_modules
        rm -f frontend/package-lock.json
        echo -e "${GREEN}✅ Limpieza completada${NC}"
    fi
fi

# ---------------------------------------------
# 4. CREAR ENTORNO VIRTUAL PYTHON
# ---------------------------------------------
echo ""
echo -e "${YELLOW}📦 PASO 4: Configurando entorno Python...${NC}"

echo "📌 Creando entorno virtual..."
python3 -m venv venv

# Activar entorno virtual
echo "🔌 Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip, setuptools y wheel
echo "📈 Actualizando herramientas de Python..."
pip install --upgrade pip setuptools wheel

# ---------------------------------------------
# 5. INSTALAR DEPENDENCIAS PYTHON
# ---------------------------------------------
echo ""
echo -e "${YELLOW}📚 PASO 5: Instalando dependencias Python...${NC}"

# Crear requirements.txt actualizado si no existe
if [ ! -f "requirements.txt" ]; then
    echo "📝 Creando requirements.txt..."
    cat > requirements.txt <<EOF
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

# Utilities
chardet==5.2.0
EOF
fi

echo "📦 Instalando paquetes Python..."
pip install -r requirements.txt

# Instalar navegadores de Playwright
echo ""
echo "🌐 Instalando navegadores para Playwright..."
playwright install chromium
playwright install-deps

# Verificar instalación de paquetes críticos
echo ""
echo -e "${YELLOW}✔️  Verificando paquetes críticos de Python...${NC}"
python3 -c "import uvicorn" && echo -e "${GREEN}   ✅ uvicorn instalado${NC}" || echo -e "${RED}   ❌ uvicorn NO instalado${NC}"
python3 -c "import fastapi" && echo -e "${GREEN}   ✅ fastapi instalado${NC}" || echo -e "${RED}   ❌ fastapi NO instalado${NC}"
python3 -c "import psycopg2" && echo -e "${GREEN}   ✅ psycopg2 instalado${NC}" || echo -e "${RED}   ❌ psycopg2 NO instalado${NC}"
python3 -c "import pandas" && echo -e "${GREEN}   ✅ pandas instalado${NC}" || echo -e "${RED}   ❌ pandas NO instalado${NC}"
python3 -c "import playwright" && echo -e "${GREEN}   ✅ playwright instalado${NC}" || echo -e "${RED}   ❌ playwright NO instalado${NC}"
python3 -c "import yaml" && echo -e "${GREEN}   ✅ pyyaml instalado${NC}" || echo -e "${RED}   ❌ pyyaml NO instalado${NC}"
python3 -c "import sqlalchemy" && echo -e "${GREEN}   ✅ sqlalchemy instalado${NC}" || echo -e "${RED}   ❌ sqlalchemy NO instalado${NC}"

# ---------------------------------------------
# 6. INSTALAR DEPENDENCIAS FRONTEND
# ---------------------------------------------
echo ""
echo -e "${YELLOW}🎨 PASO 6: Instalando dependencias Frontend...${NC}"

cd frontend

# Verificar package.json
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ package.json no encontrado en frontend/${NC}"
    exit 1
fi

# Limpiar caché de npm
echo "🧹 Limpiando caché de npm..."
npm cache clean --force

# Instalar dependencias
echo "📦 Instalando paquetes npm (esto puede tomar varios minutos)..."
npm install

# Verificar instalación
if [ -d "node_modules" ]; then
    NODE_MODULES_COUNT=$(ls node_modules | wc -l)
    echo -e "${GREEN}✅ $NODE_MODULES_COUNT paquetes npm instalados${NC}"
else
    echo -e "${RED}❌ Error instalando dependencias npm${NC}"
    exit 1
fi

cd ..

# ---------------------------------------------
# 7. VERIFICAR CONFIGURACIÓN
# ---------------------------------------------
echo ""
echo -e "${YELLOW}⚙️  PASO 7: Verificando configuración...${NC}"

# Verificar config.yaml
if [ ! -f "config.yaml" ]; then
    if [ -f "config.example.yaml" ]; then
        echo "📋 Creando config.yaml desde ejemplo..."
        cp config.example.yaml config.yaml
        echo -e "${YELLOW}   ⚠️  Por favor edita config.yaml con tus credenciales de PostgreSQL${NC}"
    else
        echo -e "${RED}❌ No se encontró config.yaml ni config.example.yaml${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ config.yaml encontrado${NC}"
fi

# ---------------------------------------------
# 8. VERIFICAR BASE DE DATOS
# ---------------------------------------------
echo ""
echo -e "${YELLOW}🗄️  PASO 8: Verificando base de datos...${NC}"

# Intentar conectar a PostgreSQL
if command -v psql &> /dev/null; then
    if psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Conexión a PostgreSQL exitosa${NC}"
        
        # Verificar si la tabla existe
        TABLE_EXISTS=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'licitaciones');" 2>/dev/null || echo "f")
        
        if [ "$TABLE_EXISTS" = "t" ]; then
            # Contar registros
            RECORD_COUNT=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
            echo -e "${GREEN}📊 Base de datos contiene $RECORD_COUNT licitaciones${NC}"
        else
            echo -e "${YELLOW}⚠️  La tabla 'licitaciones' no existe${NC}"
            echo "   Necesitas ejecutar el proceso ETL para crear las tablas y obtener datos"
        fi
    else
        echo -e "${YELLOW}⚠️  No se pudo conectar a PostgreSQL${NC}"
        echo "   Verifica que:"
        echo "   1. PostgreSQL está ejecutándose"
        echo "   2. La base de datos 'paloma_licitera' existe"
        echo "   3. El usuario 'postgres' tiene permisos"
        echo ""
        echo "   Para crear la base de datos:"
        echo "   $ psql -U postgres -c \"CREATE DATABASE paloma_licitera;\""
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL no disponible para verificación${NC}"
fi

# ---------------------------------------------
# 9. CREAR DIRECTORIOS NECESARIOS
# ---------------------------------------------
echo ""
echo -e "${YELLOW}📁 PASO 9: Creando directorios necesarios...${NC}"

mkdir -p logs
mkdir -p data/raw/comprasmx
mkdir -p data/raw/dof
mkdir -p data/raw/tianguis
mkdir -p data/processed/tianguis
echo -e "${GREEN}✅ Directorios creados${NC}"

# ---------------------------------------------
# 10. HACER EJECUTABLES LOS SCRIPTS
# ---------------------------------------------
echo ""
echo -e "${YELLOW}🔧 PASO 10: Configurando scripts...${NC}"

chmod +x start_dashboard.sh 2>/dev/null || true
chmod +x start_dashboard_v2.sh 2>/dev/null || true
chmod +x stop_dashboard.sh 2>/dev/null || true
chmod +x install.sh 2>/dev/null || true
echo -e "${GREEN}✅ Scripts marcados como ejecutables${NC}"

# ---------------------------------------------
# RESUMEN FINAL
# ---------------------------------------------
echo ""
echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}✅ INSTALACIÓN COMPLETADA CON ÉXITO${NC}"
echo -e "${GREEN}====================================================${NC}"
echo ""
echo -e "${BLUE}📋 Resumen de la instalación:${NC}"
echo "   • Python $PYTHON_VERSION con entorno virtual activo"
echo "   • Node.js $NODE_VERSION con npm $NPM_VERSION"
echo "   • Todas las dependencias Python instaladas"
echo "   • Todas las dependencias Frontend instaladas"
echo "   • Configuración verificada"
echo "   • Directorios creados"
echo ""
echo -e "${BLUE}🚀 Para iniciar la aplicación:${NC}"
echo ""
echo "   ./start_dashboard_v2.sh"
echo ""
echo -e "${BLUE}⏹️  Para detener la aplicación:${NC}"
echo ""
echo "   ./stop_dashboard.sh"
echo ""
echo -e "${YELLOW}📝 IMPORTANTE:${NC}"
echo "   • Asegúrate de que PostgreSQL esté ejecutándose"
echo "   • Verifica las credenciales en config.yaml"
echo "   • Los logs se guardarán en logs/"
echo ""

# Verificar si hay advertencias
if [ "$TABLE_EXISTS" != "t" ] || [ "$RECORD_COUNT" == "0" ]; then
    echo -e "${YELLOW}⚠️  ATENCIÓN:${NC}"
    echo "   La base de datos está vacía o no tiene tablas."
    echo "   Para cargar datos, ejecuta el proceso ETL:"
    echo "   $ source venv/bin/activate"
    echo "   $ python src/etl.py --all"
    echo ""
fi

echo -e "${GREEN}¡Instalación completa! 🎉${NC}"
echo ""
echo "El entorno virtual está activo. Para desactivarlo: deactivate"
