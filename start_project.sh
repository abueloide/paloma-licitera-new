#!/bin/bash

# Paloma Licitera - Startup Script
# Este script inicia tanto el backend como el frontend

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🕊️  Paloma Licitera - Iniciando proyecto...${NC}"
echo ""

# Verificar si estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Error: No se encontró requirements.txt${NC}"
    echo -e "${RED}   Asegúrate de ejecutar este script desde la raíz del proyecto${NC}"
    exit 1
fi

# Función para verificar si un puerto está en uso
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 0  # Puerto en uso
    else
        return 1  # Puerto libre
    fi
}

# Función para iniciar el backend
start_backend() {
    echo -e "${YELLOW}📊 Iniciando backend (Puerto 8000)...${NC}"
    
    # Verificar si el entorno virtual existe
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}⚠️  Creando entorno virtual...${NC}"
        python -m venv .venv
    fi
    
    # Activar entorno virtual
    source .venv/bin/activate
    
    # Instalar dependencias
    echo -e "${YELLOW}📦 Instalando dependencias de Python...${NC}"
    pip install -r requirements.txt > /dev/null 2>&1
    
    # Iniciar el backend
    python -m src.dashboard.main &
    BACKEND_PID=$!
    echo -e "${GREEN}✅ Backend iniciado (PID: $BACKEND_PID)${NC}"
}

# Función para iniciar el frontend
start_frontend() {
    echo -e "${YELLOW}🎨 Iniciando frontend (Puerto 3001)...${NC}"
    
    cd frontend
    
    # Verificar si node_modules existe
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 Instalando dependencias de Node.js...${NC}"
        npm install
    fi
    
    # Iniciar el frontend
    npm run dev &
    FRONTEND_PID=$!
    echo -e "${GREEN}✅ Frontend iniciado (PID: $FRONTEND_PID)${NC}"
    
    cd ..
}

# Función de limpieza al salir
cleanup() {
    echo -e "\n${YELLOW}🛑 Cerrando servicios...${NC}"
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo -e "${GREEN}✅ Backend cerrado${NC}"
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "${GREEN}✅ Frontend cerrado${NC}"
    fi
    
    # Matar cualquier proceso de Node.js del frontend que pueda quedar
    pkill -f "vite.*3001" 2>/dev/null
    
    echo -e "${BLUE}👋 ¡Hasta luego!${NC}"
    exit 0
}

# Configurar trap para limpieza
trap cleanup SIGINT SIGTERM

# Verificar puertos
if check_port 8000; then
    echo -e "${RED}❌ Puerto 8000 ya está en uso${NC}"
    echo -e "${YELLOW}   Ejecuta: lsof -ti:8000 | xargs kill -9${NC}"
    exit 1
fi

if check_port 3001; then
    echo -e "${RED}❌ Puerto 3001 ya está en uso${NC}"
    echo -e "${YELLOW}   Ejecuta: lsof -ti:3001 | xargs kill -9${NC}"
    exit 1
fi

# Iniciar servicios
start_backend
sleep 3  # Esperar a que el backend esté listo

start_frontend
sleep 3  # Esperar a que el frontend esté listo

echo ""
echo -e "${GREEN}🚀 ¡Proyecto iniciado exitosamente!${NC}"
echo ""
echo -e "${BLUE}📊 Backend:${NC}  http://localhost:8000"
echo -e "${BLUE}🎨 Frontend:${NC} http://localhost:3001"
echo ""
echo -e "${YELLOW}💡 Para detener todo, presiona Ctrl+C${NC}"
echo ""

# Esperar indefinidamente hasta que el usuario presione Ctrl+C
wait