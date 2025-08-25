#!/bin/bash

# =================================================================
# SCRIPT DE INSTALACIÓN LIMPIA PARA PALOMA LICITERA
# Este script elimina todo lo anterior y hace una instalación fresca
# =================================================================

echo "🧹 INSTALACIÓN LIMPIA DE PALOMA LICITERA"
echo "========================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 1. LIMPIEZA COMPLETA
echo "🧹 Paso 1: Limpiando instalación anterior..."
echo "----------------------------------------"

# Matar procesos si están corriendo
print_status "Deteniendo procesos existentes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true

# Eliminar entorno virtual anterior
if [ -d "venv" ]; then
    print_status "Eliminando entorno virtual anterior..."
    rm -rf venv
fi

# Limpiar cache de pip
print_status "Limpiando cache de pip..."
pip cache purge 2>/dev/null || true

# Limpiar node_modules del frontend
if [ -d "frontend/node_modules" ]; then
    print_status "Eliminando node_modules del frontend..."
    rm -rf frontend/node_modules
fi

echo ""
echo "🔧 Paso 2: Creando nuevo entorno virtual..."
echo "----------------------------------------"

# Crear nuevo entorno virtual
python3 -m venv venv
if [ $? -ne 0 ]; then
    print_error "No se pudo crear el entorno virtual"
    exit 1
fi

# Activar entorno virtual
source venv/bin/activate
print_status "Entorno virtual creado y activado"

echo ""
echo "📦 Paso 3: Instalando dependencias mínimas del backend..."
echo "----------------------------------------"

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias mínimas para el backend
print_status "Instalando FastAPI y servidor..."
pip install fastapi uvicorn[standard]

print_status "Instalando conexión a PostgreSQL..."
pip install psycopg2-binary sqlalchemy

print_status "Instalando utilidades..."
pip install pyyaml pandas python-dotenv

print_status "Instalando dependencias adicionales..."
pip install httpx beautifulsoup4 lxml requests

echo ""
echo "🎨 Paso 4: Preparando frontend..."
echo "----------------------------------------"

cd frontend

# Arreglar el import incorrecto en Dashboard.tsx
if grep -q "@/lib/api" src/components/Dashboard.tsx 2>/dev/null; then
    print_status "Corrigiendo import en Dashboard.tsx..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' 's/@\/lib\/api/@\/services\/api/g' src/components/Dashboard.tsx
    else
        # Linux
        sed -i 's/@\/lib\/api/@\/services\/api/g' src/components/Dashboard.tsx
    fi
fi

print_status "Instalando dependencias del frontend..."
npm install

cd ..

echo ""
echo "🐘 Paso 5: Verificando PostgreSQL..."
echo "----------------------------------------"

# Verificar PostgreSQL
if psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -qw paloma_licitera; then
    print_status "Base de datos 'paloma_licitera' encontrada"
    
    # Verificar si hay datos
    RECORD_COUNT=$(psql -h localhost -U postgres -d paloma_licitera -tAc "SELECT COUNT(*) FROM licitaciones;" 2>/dev/null || echo "0")
    if [ "$RECORD_COUNT" -gt 0 ]; then
        print_status "La base de datos contiene $RECORD_COUNT registros"
    else
        print_warning "La base de datos está vacía"
    fi
else
    print_error "Base de datos 'paloma_licitera' no encontrada"
    echo "Créala con: createdb -U postgres paloma_licitera"
fi

echo ""
echo "🚀 Paso 6: Creando scripts de inicio..."
echo "----------------------------------------"

# Crear script para iniciar backend
cat > start_backend.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
cd src
echo "🚀 Iniciando backend en http://localhost:8000"
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
EOF
chmod +x start_backend.sh
print_status "Script 'start_backend.sh' creado"

# Crear script para iniciar frontend
cat > start_frontend.sh << 'EOF'
#!/bin/bash
cd frontend
echo "🎨 Iniciando frontend en http://localhost:3001"
npm run dev
EOF
chmod +x start_frontend.sh
print_status "Script 'start_frontend.sh' creado"

# Crear script para iniciar todo
cat > start_all.sh << 'EOF'
#!/bin/bash

echo "🐦 Iniciando Paloma Licitera..."
echo ""

# Iniciar backend en background
echo "Iniciando backend..."
./start_backend.sh > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Esperar a que el backend esté listo
sleep 3

# Verificar si el backend está respondiendo
if curl -s http://localhost:8000 > /dev/null; then
    echo "✅ Backend corriendo en http://localhost:8000"
else
    echo "❌ Backend no responde"
fi

# Iniciar frontend
echo "Iniciando frontend..."
./start_frontend.sh
EOF
chmod +x start_all.sh
print_status "Script 'start_all.sh' creado"

# Crear directorio para logs
mkdir -p logs

echo ""
echo "✨ ================================== ✨"
echo "   INSTALACIÓN COMPLETADA CON ÉXITO"
echo "✨ ================================== ✨"
echo ""
echo "📋 INSTRUCCIONES DE USO:"
echo ""
echo "OPCIÓN 1 - Iniciar todo junto:"
echo "  ./start_all.sh"
echo ""
echo "OPCIÓN 2 - Iniciar por separado:"
echo "  Terminal 1: ./start_backend.sh"
echo "  Terminal 2: ./start_frontend.sh"
echo ""
echo "🌐 ACCESO:"
echo "  Frontend: http://localhost:3001"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "⚠️  IMPORTANTE:"
echo "  - Asegúrate de que PostgreSQL esté corriendo"
echo "  - La base de datos debe llamarse 'paloma_licitera'"
echo ""

# Preguntar si quiere iniciar ahora
echo "¿Deseas iniciar el sistema ahora? (s/n)"
read -r response
if [[ "$response" =~ ^[Ss]$ ]]; then
    echo ""
    print_status "Iniciando sistema..."
    ./start_all.sh
fi
