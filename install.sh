#!/bin/bash

# =================================================================
# PALOMA LICITERA - SCRIPT DE INSTALACIÓN COMPLETO
# =================================================================
# Este script configura todo el entorno necesario para ejecutar
# la plataforma Paloma Licitera de forma confiable
# =================================================================

set -e  # Salir en caso de error

echo "🐦 ===================================================="
echo "   PALOMA LICITERA - INSTALACIÓN COMPLETA"
echo "===================================================="
echo ""

# ---------------------------------------------
# 1. VERIFICAR PREREQUISITOS
# ---------------------------------------------
echo "📋 PASO 1: Verificando prerequisitos..."
echo ""

# Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    echo "   Por favor instala Python 3.9 o superior"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION encontrado"

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js no está instalado"
    echo "   Por favor instala Node.js 16 o superior"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✅ Node.js $NODE_VERSION encontrado"

# Verificar npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm no está instalado"
    exit 1
fi

NPM_VERSION=$(npm --version)
echo "✅ npm $NPM_VERSION encontrado"

# Verificar PostgreSQL
echo ""
echo "🔍 Verificando PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL no está instalado o psql no está en PATH"
    echo "   La aplicación requiere PostgreSQL para funcionar"
    echo "   ¿Continuar de todos modos? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    PSQL_VERSION=$(psql --version | awk '{print $3}')
    echo "✅ PostgreSQL $PSQL_VERSION encontrado"
fi

# ---------------------------------------------
# 2. CREAR ENTORNO VIRTUAL PYTHON
# ---------------------------------------------
echo ""
echo "📦 PASO 2: Configurando entorno Python..."
echo ""

# Verificar si ya existe un entorno virtual
if [ -d "venv" ]; then
    echo "🔄 Entorno virtual existente encontrado"
    echo "   ¿Deseas recrearlo? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "   Eliminando entorno anterior..."
        rm -rf venv
        echo "   Creando nuevo entorno virtual..."
        python3 -m venv venv
    fi
else
    echo "📌 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "🔌 Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo "📈 Actualizando pip..."
pip install --upgrade pip > /dev/null 2>&1

# ---------------------------------------------
# 3. INSTALAR DEPENDENCIAS PYTHON
# ---------------------------------------------
echo ""
echo "📚 PASO 3: Instalando dependencias Python..."
echo ""

# Verificar si requirements.txt existe
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt no encontrado"
    exit 1
fi

echo "📦 Instalando paquetes..."
pip install -r requirements.txt

# Verificar instalación de paquetes críticos
echo ""
echo "✔️  Verificando paquetes críticos..."
python3 -c "import uvicorn" && echo "   ✅ uvicorn instalado" || echo "   ❌ uvicorn NO instalado"
python3 -c "import fastapi" && echo "   ✅ fastapi instalado" || echo "   ❌ fastapi NO instalado"
python3 -c "import psycopg2" && echo "   ✅ psycopg2 instalado" || echo "   ❌ psycopg2 NO instalado"
python3 -c "import pandas" && echo "   ✅ pandas instalado" || echo "   ❌ pandas NO instalado"
python3 -c "import playwright" && echo "   ✅ playwright instalado" || echo "   ❌ playwright NO instalado"

# Instalar navegadores de Playwright si es necesario
echo ""
echo "🌐 Instalando navegadores para Playwright..."
playwright install chromium

# ---------------------------------------------
# 4. INSTALAR DEPENDENCIAS FRONTEND
# ---------------------------------------------
echo ""
echo "🎨 PASO 4: Instalando dependencias Frontend..."
echo ""

cd frontend

# Limpiar node_modules si existe
if [ -d "node_modules" ]; then
    echo "🧹 Limpiando node_modules anterior..."
    rm -rf node_modules
fi

# Limpiar caché de npm
echo "🧹 Limpiando caché de npm..."
npm cache clean --force

# Instalar dependencias
echo "📦 Instalando paquetes npm..."
npm install

cd ..

# ---------------------------------------------
# 5. VERIFICAR CONFIGURACIÓN
# ---------------------------------------------
echo ""
echo "⚙️  PASO 5: Verificando configuración..."
echo ""

# Verificar config.yaml
if [ ! -f "config.yaml" ]; then
    if [ -f "config.example.yaml" ]; then
        echo "📋 Creando config.yaml desde ejemplo..."
        cp config.example.yaml config.yaml
        echo "   ⚠️  Por favor edita config.yaml con tus credenciales de PostgreSQL"
    else
        echo "❌ No se encontró config.yaml ni config.example.yaml"
        exit 1
    fi
else
    echo "✅ config.yaml encontrado"
fi

# ---------------------------------------------
# 6. VERIFICAR BASE DE DATOS
# ---------------------------------------------
echo ""
echo "🗄️  PASO 6: Verificando base de datos..."
echo ""

# Intentar conectar a PostgreSQL
if command -v psql &> /dev/null; then
    if psql -h localhost -U postgres -d paloma_licitera -c "SELECT 1" > /dev/null 2>&1; then
        echo "✅ Conexión a PostgreSQL exitosa"
        
        # Contar registros
        RECORD_COUNT=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
        echo "📊 Base de datos contiene $RECORD_COUNT licitaciones"
    else
        echo "⚠️  No se pudo conectar a PostgreSQL"
        echo "   Verifica que:"
        echo "   1. PostgreSQL está ejecutándose"
        echo "   2. La base de datos 'paloma_licitera' existe"
        echo "   3. El usuario 'postgres' tiene permisos"
        echo ""
        echo "   Para crear la base de datos:"
        echo "   $ psql -U postgres -c \"CREATE DATABASE paloma_licitera;\""
    fi
else
    echo "⚠️  PostgreSQL no disponible para verificación"
fi

# ---------------------------------------------
# 7. CREAR DIRECTORIOS NECESARIOS
# ---------------------------------------------
echo ""
echo "📁 PASO 7: Creando directorios necesarios..."
echo ""

mkdir -p logs
mkdir -p data
echo "✅ Directorios creados"

# ---------------------------------------------
# 8. CREAR SCRIPT DE INICIO MEJORADO
# ---------------------------------------------
echo ""
echo "🚀 PASO 8: Actualizando scripts de inicio..."
echo ""

# Hacer ejecutables los scripts
chmod +x start_dashboard.sh
chmod +x stop_dashboard.sh
echo "✅ Scripts marcados como ejecutables"

# ---------------------------------------------
# RESUMEN FINAL
# ---------------------------------------------
echo ""
echo "===================================================="
echo "✅ INSTALACIÓN COMPLETADA CON ÉXITO"
echo "===================================================="
echo ""
echo "📋 Resumen de la instalación:"
echo "   • Python $PYTHON_VERSION con entorno virtual"
echo "   • Node.js $NODE_VERSION con npm $NPM_VERSION"
echo "   • Dependencias Python instaladas"
echo "   • Dependencias Frontend instaladas"
echo "   • Configuración verificada"
echo ""
echo "🚀 Para iniciar la aplicación:"
echo ""
echo "   ./start_dashboard.sh"
echo ""
echo "⏹️  Para detener la aplicación:"
echo ""
echo "   ./stop_dashboard.sh"
echo ""
echo "📝 IMPORTANTE:"
echo "   • Asegúrate de que PostgreSQL esté ejecutándose"
echo "   • Verifica las credenciales en config.yaml"
echo "   • Los logs se guardarán en logs/"
echo ""
echo "¡Listo para usar! 🎉"
