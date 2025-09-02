#!/bin/bash

# =================================================================
# PALOMA CLEAN - LIMPIEZA DE SCRIPTS OBSOLETOS
# =================================================================

echo "🧹 PALOMA CLEAN - Limpieza de scripts obsoletos"
echo "============================================="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Scripts obsoletos del root a mover
OBSOLETE_SCRIPTS=(
    "comprasmx_scraper_consolidado.py"
    "conversor_texto_json.py"
    "debug_comprasmx_structure.py"
    "debug_step_by_step.py"
    "ejecutar_dof_completo.py"
    "fix_convocatorias_logic.py"
    "hotfix_convocatorias.py"
    "mejora_logging.py"
    "migrate_to_hybrid.py"
    "paloma_manager.py"
    "paloma_sin_sitios.sh"
    "process_dof_with_parser.py"
    "real_sources_analysis.py"
    "reprocesar_dof.py"
    "run_dof_ai.py"
    "test_dof_parser.py"
)

# Directorios obsoletos
OBSOLETE_DIRS=(
    "etl-process"
    "migrations"
)

main() {
    print_info "Iniciando limpieza de arquitectura obsoleta..."
    
    # Crear directorio backup
    mkdir -p backup-obsoleto/root-scripts
    mkdir -p backup-obsoleto/directories
    
    local moved_files=0
    local moved_dirs=0
    
    # Mover scripts obsoletos
    for script in "${OBSOLETE_SCRIPTS[@]}"; do
        if [ -f "$script" ]; then
            print_warning "Moviendo script: $script"
            mv "$script" backup-obsoleto/root-scripts/
            moved_files=$((moved_files + 1))
        fi
    done
    
    # Mover directorios obsoletos (EXCEPTO backup-obsoleto)
    for dir in "${OBSOLETE_DIRS[@]}"; do
        if [ -d "$dir" ] && [ "$dir" != "backup-obsoleto" ]; then
            print_warning "Moviendo directorio: $dir"
            mv "$dir" backup-obsoleto/directories/
            moved_dirs=$((moved_dirs + 1))
        fi
    done
    
    print_status "Scripts movidos: $moved_files"
    print_status "Directorios movidos: $moved_dirs"
    
    # Verificar cornerstones
    print_info "Verificando estructura cornerstones..."
    if [ ! -d "cornerstones" ]; then
        print_error "Directorio cornerstones no existe"
        return 1
    fi
    
    local cornerstone_files=$(find cornerstones -name "*.py" | wc -l)
    print_status "Archivos en cornerstones: $cornerstone_files"
    
    echo ""
    print_status "LIMPIEZA COMPLETADA"
    echo ""
    print_info "Archivos movidos a backup-obsoleto/ (NO eliminados)"
    print_info "Próximo paso: Verificar que cornerstones/ tenga todos los extractores necesarios"
}

# Ejecutar si se llama directamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi