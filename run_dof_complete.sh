#!/bin/bash
# Script rápido para ejecutar flujo completo DOF
# Uso: ./run_dof_complete.sh

set -e  # Salir si hay errores

echo "🐦 PALOMA LICITERA - FLUJO COMPLETO DOF"
echo "======================================"
echo "📅 Procesando: Agosto 2025 (Martes y Jueves)"
echo "🔄 Flujo: Descarga PDFs → Convierte TXT → Extrae con IA"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "ejecutar_dof_completo.py" ]; then
    echo "❌ Error: Ejecutar desde la raíz del proyecto paloma-licitera-new"
    exit 1
fi

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no encontrado"
    exit 1
fi

# Verificar .env
if [ ! -f ".env" ]; then
    echo "❌ Error: Archivo .env no encontrado"
    echo "   Crear .env con: ANTHROPIC_API_KEY=tu_api_key_aqui"
    exit 1
fi

# Instalar dependencias si es necesario
echo "📦 Instalando dependencias..."
pip install -q requests pymupdf pdfminer.six urllib3 certifi anthropic python-dotenv

echo ""
echo "🚀 INICIANDO FLUJO COMPLETO..."
echo "⏳ Esto puede tomar 20-30 minutos total"
echo ""

# Ejecutar el script principal
python3 ejecutar_dof_completo.py

# Verificar resultado
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ FLUJO COMPLETADO EXITOSAMENTE"
    echo ""
    echo "📁 Archivos generados en:"
    echo "   - data/raw/dof/ (PDFs y TXT originales)"
    echo "   - data/processed/dof/ (JSONs con licitaciones extraídas)"
    echo ""
    echo "🎯 ¡Listo! Ya tienes las licitaciones del DOF procesadas con IA"
else
    echo ""
    echo "❌ FLUJO FALLÓ - Revisar logs arriba"
    exit 1
fi
