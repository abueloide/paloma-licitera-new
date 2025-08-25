#!/bin/bash
set -e

echo "🐳 Iniciando Paloma Licitera con Docker..."

# Crear directorios necesarios
mkdir -p data/raw data/processed logs

# Construir e iniciar servicios
docker-compose up -d postgres

echo "⏳ Esperando PostgreSQL..."
sleep 10

# Verificar conexión a PostgreSQL
docker-compose exec postgres psql -U postgres -d paloma_licitera -c "SELECT 1;"

# Iniciar aplicación y scheduler
docker-compose up -d paloma-app scheduler

echo "✅ Servicios iniciados:"
echo "   - PostgreSQL: localhost:5432"
echo "   - API: http://localhost:8000"
echo "   - Scheduler: Modo daemon activo"

echo "📊 Verificar status:"
echo "   docker-compose exec scheduler python -m src.scheduler status"