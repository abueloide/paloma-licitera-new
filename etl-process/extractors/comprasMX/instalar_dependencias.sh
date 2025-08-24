#!/bin/bash

echo "==================================="
echo "Instalación de dependencias para ComprasMX Scraper"
echo "==================================="

# Detectar qué Python estás usando
PYTHON_PATH="/opt/homebrew/bin/python3"

echo "Usando Python en: $PYTHON_PATH"
echo ""

# Instalar playwright con el Python correcto
echo "1. Instalando playwright..."
$PYTHON_PATH -m pip install playwright

# Instalar los navegadores necesarios para playwright
echo ""
echo "2. Instalando navegadores para Playwright..."
$PYTHON_PATH -m playwright install chromium

# Verificar instalación
echo ""
echo "3. Verificando instalación..."
$PYTHON_PATH -c "from playwright.async_api import async_playwright; print('✓ Playwright instalado correctamente')"

if [ $? -eq 0 ]; then
    echo ""
    echo "==================================="
    echo "✅ Instalación completada con éxito!"
    echo "==================================="
    echo ""
    echo "Ahora puedes ejecutar el scraper con:"
    echo "$PYTHON_PATH ComprasMX_v2Claude.py"
else
    echo ""
    echo "❌ Error en la instalación. Por favor revisa los mensajes anteriores."
fi
