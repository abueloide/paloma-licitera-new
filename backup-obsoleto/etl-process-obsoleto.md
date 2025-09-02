# ETL Process Backup - OBSOLETO

Esta carpeta contiene el ETL process obsoleto que ha sido reemplazado por los CORNERSTONES.

## ¿Por qué está aquí?

El directorio `etl-process/` original contenía:
- Múltiples versiones obsoletas de extractores DOF y ComprasMX
- Referencias fragmentadas que no funcionaban correctamente
- Código duplicado sin coordinación

## Cornerstones implementados

✅ **DOF**: `cornerstones/dof/dof_haiku_extractor.py` - Extractor con Claude Haiku 3.5
✅ **ComprasMX**: `cornerstones/comprasmx/comprasmx_scraper_consolidado.py` - Scraper funcional consolidado

## Próximos pasos

1. Alinear modelo de datos híbrido con outputs de cornerstones
2. Actualizar scripts .sh para usar cornerstones
3. Limpiar referencias obsoletas en ETL principal
4. Integrar cornerstones con paloma.sh e install.sh

## Fecha de migración

2025-09-01
