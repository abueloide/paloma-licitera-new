#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 ====================================================="
echo "   PALOMA LICITERA - LIMPIEZA DE INSTALACIÓN"
echo "   Limpia instalaciones fallidas o parciales"
echo -e "=====================================================${NC}"
echo ""

echo -e "${YELLOW}⚠️  Este script eliminará completamente:${NC}"
echo "   • Todos los contenedores Docker de Paloma"
echo "   • Imágenes Docker construidas"
echo "   • Volúmenes de datos Docker"
echo "   • Archivos temporales"
echo ""

echo -n "¿Estás seguro de que quieres continuar? (y/N): "
read -r response
if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Operación cancelada"
    exit 0
fi

echo ""
echo -e "${BLUE}🔄 Iniciando limpieza completa...${NC}"

# Detener todos los servicios
echo -e "${YELLOW}⏹️  Deteniendo servicios...${NC}"
docker-compose down -v 2>/dev/null || true
./docker-stop.sh 2>/dev/null || true

# Limpiar contenedores específicos
echo -e "${YELLOW}🗑️  Eliminando contenedores...${NC}"
docker ps -a | grep paloma | awk '{print $1}' | xargs docker rm -f 2>/dev/null || true

# Limpiar imágenes relacionadas con el proyecto
echo -e "${YELLOW}🖼️  Eliminando imágenes...${NC}"
docker images | grep paloma | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
docker images | grep none | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true

# Limpiar volúmenes
echo -e "${YELLOW}💾 Eliminando volúmenes...${NC}"
docker volume ls | grep paloma | awk '{print $2}' | xargs docker volume rm -f 2>/dev/null || true

# Limpieza general del sistema Docker
echo -e "${YELLOW}🧽 Limpieza general de Docker...${NC}"
docker system prune -f 2>/dev/null || true
docker image prune -f 2>/dev/null || true
docker volume prune -f 2>/dev/null || true
docker network prune -f 2>/dev/null || true

# Limpiar archivos temporales y logs antiguos
echo -e "${YELLOW}📄 Limpiando archivos temporales...${NC}"
rm -f .backend.pid .frontend.pid 2>/dev/null || true
rm -f /tmp/docker-build.log 2>/dev/null || true
rm -rf logs/*.log.* 2>/dev/null || true

# Limpiar directorios de datos si el usuario quiere
echo ""
echo -n "¿Quieres también eliminar los datos descargados? (y/N): "
read -r data_response
if [[ "$data_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${YELLOW}🗂️  Eliminando datos...${NC}"
    rm -rf data/raw/* 2>/dev/null || true
    rm -rf data/processed/* 2>/dev/null || true
    echo "   ✅ Datos eliminados"
else
    echo "   ℹ️  Datos conservados"
fi

echo ""
echo -e "${GREEN}✅ LIMPIEZA COMPLETADA${NC}"
echo ""
echo -e "${BLUE}📋 Se han limpiado:${NC}"
echo "   • Contenedores Docker"
echo "   • Imágenes Docker"
echo "   • Volúmenes Docker"
echo "   • Archivos temporales"
echo "   • Logs antiguos"
echo ""
echo -e "${CYAN}🚀 Ahora puedes ejecutar una instalación limpia:${NC}"
echo "   ./install.sh"
echo ""