#!/bin/bash
# Ejecutar comandos del scheduler en Docker

if [ $# -eq 0 ]; then
    echo "🐦 Paloma Licitera - Scheduler Commands"
    echo ""
    echo "Uso: ./run-scheduler.sh [comando]"
    echo ""
    echo "🚀 DESCARGA INICIAL (solo primera vez):"
    echo "  descarga-inicial --desde=2024-01-01    # Descarga REAL de 12 meses"
    echo ""
    echo "📊 COMANDOS REGULARES:"
    echo "  incremental --fuente=all               # Nuevas licitaciones (usar regularmente)"
    echo "  historico --fuente=comprasmx --desde=2025-01-01  # Histórico específico"
    echo "  batch diario                           # Ejecución programada"
    echo "  status                                 # Estado y estadísticas"
    echo "  stats --dias=30                       # Estadísticas detalladas"
    echo ""
    echo "🎯 EJEMPLOS DE USO:"
    echo "  ./run-scheduler.sh descarga-inicial --desde=2024-01-01"
    echo "  ./run-scheduler.sh incremental"
    echo "  ./run-scheduler.sh status"
    exit 1
fi

docker-compose exec scheduler python -m src.scheduler "$@"