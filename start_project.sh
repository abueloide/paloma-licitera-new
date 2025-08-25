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
        python3 -m venv .venv
    fi
    
    # Activar entorno virtual
    source .venv/bin/activate
    
    # Instalar dependencias
    echo -e "${YELLOW}📦 Instalando dependencias de Python...${NC}"
    pip install -r requirements.txt > /dev/null 2>&1
    
    # Verificar que existe config.yaml
    if [ ! -f "config.yaml" ]; then
        if [ -f "config.example.yaml" ]; then
            echo -e "${YELLOW}⚠️  Copiando config.example.yaml a config.yaml...${NC}"
            cp config.example.yaml config.yaml
        else
            echo -e "${RED}❌ Error: No se encontró config.yaml ni config.example.yaml${NC}"
            exit 1
        fi
    fi
    
    # Iniciar el backend usando el API principal
    python3 src/api.py &
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
    
    # Configurar puerto 3001 en vite.config.ts si no está configurado
    if ! grep -q "port: 3001" vite.config.ts 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Configurando puerto 3001 en vite.config.ts...${NC}"
        # Backup del archivo original
        cp vite.config.ts vite.config.ts.backup 2>/dev/null || true
        
        # Crear nuevo vite.config.ts con puerto 3001
        cat > vite.config.ts << 'EOF'
import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3001,
    host: true
  }
})
EOF
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
    
    # Matar cualquier proceso que pueda quedar
    pkill -f "python.*src/api.py" 2>/dev/null
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
echo -e "${YELLOW}⏳ Esperando que el backend esté listo...${NC}"
sleep 5  # Esperar a que el backend esté listo

start_frontend
echo -e "${YELLOW}⏳ Esperando que el frontend esté listo...${NC}"
sleep 3  # Esperar a que el frontend esté listo

echo ""
echo -e "${GREEN}🚀 ¡Proyecto iniciado exitosamente!${NC}"
echo ""
echo -e "${BLUE}📊 Backend API:${NC}  http://localhost:8000"
echo -e "${BLUE}📊 Backend Docs:${NC} http://localhost:8000/docs"
echo -e "${BLUE}🎨 Frontend:${NC}     http://localhost:3001"
echo ""
echo -e "${YELLOW}💡 Para detener todo, presiona Ctrl+C${NC}"
echo ""

# Esperar indefinidamente hasta que el usuario presione Ctrl+C
wait