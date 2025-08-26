# Corrección de URLs del DOF - Instrucciones

## Problema Identificado
Las URLs del DOF no estaban apuntando al día correcto porque:
- El campo `fecha_publicacion` contiene la fecha de publicación en ComprasMX (ej: "14/agosto/2025")
- NO teníamos guardada la fecha real del ejemplar del DOF donde apareció la licitación
- Las URLs necesitan la fecha del ejemplar para funcionar correctamente

## Solución Implementada

### Archivos Modificados/Creados:
1. **`etl-process/extractors/dof/estructura_dof_actualizado.py`** - Nueva versión del extractor que:
   - Extrae la fecha del ejemplar del nombre del archivo (formato: DDMMYYYY_EDICION.txt)
   - Guarda la fecha del ejemplar, edición y archivo origen en los datos estructurados
   - Incluye esta información en el JSON generado

2. **`reprocesar_dof.py`** - Script que:
   - Re-procesa todos los archivos TXT del DOF con el extractor actualizado
   - Actualiza la base de datos con las fechas correctas del ejemplar
   - Verifica que las URLs se construyan correctamente

3. **`src/api.py`** - Ya tiene la función `construir_url_dof()` que:
   - Busca `fecha_ejemplar` en `datos_originales`
   - Construye la URL correcta: `https://dof.gob.mx/index_111.php?year=YYYY&month=MM&day=DD#gsc.tab=0`

## Pasos para Ejecutar la Corrección

### 1. Verificar que tienes los archivos del DOF descargados
```bash
ls -la data/raw/dof/*.txt
```
Deberías ver archivos como: `01082025_MAT.txt`, `05082025_VES.txt`, etc.

### 2. Ejecutar el script de re-procesamiento
```bash
python reprocesar_dof.py
```

Este script:
- Re-procesará todos los archivos TXT del DOF
- Generará nuevos JSON con la fecha del ejemplar
- Actualizará la base de datos con esta información
- Mostrará las URLs corregidas

### 3. Verificar en la base de datos
```sql
-- Verificar que los datos_originales tienen fecha_ejemplar
SELECT 
    numero_procedimiento,
    datos_originales->>'fecha_ejemplar' as fecha_ejemplar,
    datos_originales->>'edicion_ejemplar' as edicion
FROM licitaciones 
WHERE fuente = 'DOF' 
AND datos_originales IS NOT NULL
LIMIT 10;
```

### 4. Probar las URLs en el frontend
Las licitaciones del DOF ahora deberían mostrar URLs correctas que apuntan al día del ejemplar del DOF.

## Ejemplo de URL Corregida

**Antes (incorrecto):**
- Usaba `fecha_publicacion`: "14/agosto/2025" 
- URL incorrecta o no funcional

**Después (correcto):**
- Usa `fecha_ejemplar`: "2025-08-01"
- URL: `https://dof.gob.mx/index_111.php?year=2025&month=08&day=01#gsc.tab=0`

## Notas Importantes

1. **Fechas del DOF de Agosto 2025**: El script original descargó martes y jueves de agosto 2025
2. **Formato de archivo**: Los archivos deben tener el formato `DDMMYYYY_EDICION.txt` para extraer la fecha
3. **La URL del DOF no incluye la página específica** - lleva al índice del día completo, lo cual está bien

## Si Necesitas Re-descargar los PDFs del DOF

Si no tienes los archivos o necesitas más:
```bash
cd etl-process/extractors/dof
python dof_extraccion_estructuracion.py
```

Esto descargará los PDFs y generará los TXT necesarios.

## Problemas Conocidos y Soluciones

**Problema**: No se actualizan los registros en la BD
**Solución**: Verificar que los números de licitación coincidan exactamente

**Problema**: Las URLs siguen sin funcionar
**Solución**: Verificar que `datos_originales` tenga el formato JSON correcto con `fecha_ejemplar`

## Para Desarrollo Futuro

Cuando se agreguen nuevos archivos del DOF:
1. Usar el extractor actualizado (`estructura_dof_actualizado.py`)
2. Asegurarse de que el nombre del archivo tenga el formato correcto
3. El ETL debería guardar automáticamente la fecha del ejemplar

---

**Última actualización**: 26 de agosto de 2025
**Autor**: Sistema de corrección automática
