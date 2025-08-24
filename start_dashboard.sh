#!/bin/bash
# Script para iniciar Paloma Licitera Dashboard

echo "🦜 Iniciando Paloma Licitera Dashboard..."
echo "=================================="

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "✅ Activando entorno virtual..."
    source venv/bin/activate
fi

# Instalar dependencias si no están instaladas
echo "📦 Verificando dependencias..."
pip install -q fastapi uvicorn psycopg2-binary pyyaml

# Iniciar el servidor API
echo "🚀 Iniciando servidor API en http://localhost:8000"
echo "📊 Dashboard disponible en: dashboard.html"
echo ""
echo "Presiona Ctrl+C para detener el servidor"
echo "=================================="

# Ejecutar el servidor
python src/api_enhanced.py