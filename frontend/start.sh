#!/bin/bash
# Start script for Paloma Licitera Frontend

echo "🦜 Iniciando Paloma Licitera Frontend..."
echo "========================================"

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Este script debe ejecutarse desde la carpeta /frontend"
    echo "📍 Cambia al directorio: cd frontend"
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependencias..."
    npm install
fi

echo "🚀 Iniciando servidor de desarrollo en http://localhost:3000"
echo "🔗 El frontend se conectará al backend en http://localhost:8000"
echo ""
echo "Presiona Ctrl+C para detener el servidor"
echo "========================================"

# Start the development server
npm run dev