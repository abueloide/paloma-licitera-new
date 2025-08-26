-- Script para corregir las URLs incorrectas de Tianguis Digital en PostgreSQL
-- Fecha: 2025-08-26
-- Problema: Las URLs apuntan a tianguisdigital.cdmx.gob.mx/ocds/tender/{ocid}
-- Solución: Cambiar a datosabiertostianguisdigital.cdmx.gob.mx/proceso/{id}
--
-- INSTRUCCIONES DE USO:
-- 1. Conectar a la base de datos: psql -h localhost -U postgres -d paloma_licitera
-- 2. Ejecutar este script: \i fix_tianguis_urls_postgresql.sql
-- 3. O ejecutar directamente: psql -h localhost -U postgres -d paloma_licitera -f fix_tianguis_urls_postgresql.sql

BEGIN;

-- 1. Primero, veamos cuántas licitaciones de Tianguis tienen la URL incorrecta
SELECT COUNT(*) as total_incorrectas
FROM licitaciones 
WHERE fuente = 'TIANGUIS_DIGITAL' 
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx/ocds%';

-- 2. Ver algunos ejemplos antes de actualizar
SELECT id, numero_procedimiento, titulo, url_original
FROM licitaciones 
WHERE fuente = 'TIANGUIS_DIGITAL' 
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx/ocds%'
LIMIT 5;

-- 3. ACTUALIZACIÓN MASIVA
-- Para URLs con formato /ocds/tender/ocds-87sd3t-XXXXXX
-- Extraemos solo el número final XXXXXX del OCID

-- Actualización para PostgreSQL - Extrae el último segmento después del último guión
UPDATE licitaciones
SET url_original = CONCAT(
    'https://datosabiertostianguisdigital.cdmx.gob.mx/proceso/',
    SPLIT_PART(
        REPLACE(url_original, 'https://tianguisdigital.cdmx.gob.mx/ocds/tender/', ''),
        '-',
        3  -- Toma la tercera parte (después de 'ocds-87sd3t-')
    )
)
WHERE fuente = 'TIANGUIS_DIGITAL'
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx/ocds/tender/ocds-%';

-- Alternativa más robusta usando expresiones regulares
UPDATE licitaciones
SET url_original = 'https://datosabiertostianguisdigital.cdmx.gob.mx/proceso/' || 
    REGEXP_REPLACE(url_original, '.*-([0-9]+)$', '\1')
WHERE fuente = 'TIANGUIS_DIGITAL'
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx/ocds/tender/ocds-%'
  AND url_original ~ '-[0-9]+$';  -- Verifica que termine con guión y números

-- Para URLs que no siguen el patrón OCDS (si las hay)
UPDATE licitaciones
SET url_original = REPLACE(
    url_original,
    'https://tianguisdigital.cdmx.gob.mx/ocds/tender/',
    'https://datosabiertostianguisdigital.cdmx.gob.mx/proceso/'
)
WHERE fuente = 'TIANGUIS_DIGITAL'
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx/ocds/tender/%'
  AND url_original NOT LIKE '%ocds-%';

-- 4. Verificar los cambios
SELECT COUNT(*) as total_corregidas
FROM licitaciones 
WHERE fuente = 'TIANGUIS_DIGITAL' 
  AND url_original LIKE '%datosabiertostianguisdigital.cdmx.gob.mx/proceso%';

-- 5. Ver algunos ejemplos después de actualizar
SELECT id, numero_procedimiento, titulo, url_original
FROM licitaciones 
WHERE fuente = 'TIANGUIS_DIGITAL' 
  AND url_original LIKE '%datosabiertostianguisdigital.cdmx.gob.mx/proceso%'
LIMIT 5;

-- 6. Verificar si quedó alguna sin corregir
SELECT COUNT(*) as sin_corregir
FROM licitaciones 
WHERE fuente = 'TIANGUIS_DIGITAL' 
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx%';

-- 7. Mostrar las que no se pudieron corregir (si las hay)
SELECT id, numero_procedimiento, url_original
FROM licitaciones 
WHERE fuente = 'TIANGUIS_DIGITAL' 
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx%'
LIMIT 10;

-- Si todo está bien, confirmar los cambios
COMMIT;

-- NOTA: Si algo sale mal, puedes hacer ROLLBACK; en lugar de COMMIT;
-- O comentar el BEGIN y COMMIT para ejecutar sin transacción
