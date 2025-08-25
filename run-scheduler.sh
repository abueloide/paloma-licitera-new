#!/bin/bash
# Ejecutar comandos del scheduler en Docker

if [ $# -eq 0 ]; then
    echo "Uso: ./run-scheduler.sh [comando]"
    echo ""
    echo "Comandos disponibles:"
    echo "  historico --fuente=comprasmx --desde=2025-01-01"
    echo "  incremental --fuente=all"
    echo "  batch diario"
    echo "  status"
    echo "  stats --dias=30"
    exit 1
fi

docker-compose exec scheduler python -m src.scheduler "$@"