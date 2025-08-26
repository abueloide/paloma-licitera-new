-- Script para corregir las URLs incorrectas de Tianguis Digital
-- Fecha: 2025-08-26
-- Problema: Las URLs apuntan a tianguisdigital.cdmx.gob.mx/ocds/tender/{ocid}
-- Solución: Cambiar a datosabiertostianguisdigital.cdmx.gob.mx/proceso/{id}

-- Primero, veamos cuántas licitaciones de Tianguis tienen la URL incorrecta
SELECT COUNT(*) as total_incorrectas
FROM licitaciones 
WHERE fuente = 'TIANGUIS_DIGITAL' 
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx/ocds%';

-- Ver algunos ejemplos antes de actualizar
SELECT id, numero_procedimiento, titulo, url_original
FROM licitaciones 
WHERE fuente = 'TIANGUIS_DIGITAL' 
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx/ocds%'
LIMIT 5;

-- ACTUALIZACIÓN MASIVA
-- Estrategia 1: Para URLs con formato /ocds/tender/ocds-87sd3t-XXXXXX
-- Extraemos solo el número final XXXXXX del OCID
UPDATE licitaciones
SET url_original = CONCAT(
    'https://datosabiertostianguisdigital.cdmx.gob.mx/proceso/',
    SUBSTRING_INDEX(url_original, '-', -1)  -- Toma la última parte después del último guión
)
WHERE fuente = 'TIANGUIS_DIGITAL'
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx/ocds/tender/ocds-%';

-- Estrategia 2: Para URLs que ya tienen solo un número al final
UPDATE licitaciones
SET url_original = REPLACE(
    url_original,
    'https://tianguisdigital.cdmx.gob.mx/ocds/tender/',
    'https://datosabiertostianguisdigital.cdmx.gob.mx/proceso/'
)
WHERE fuente = 'TIANGUIS_DIGITAL'
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx/ocds/tender/%'
  AND url_original NOT LIKE '%ocds-%';

-- Verificar los cambios
SELECT COUNT(*) as total_corregidas
FROM licitaciones 
WHERE fuente = 'TIANGUIS_DIGITAL' 
  AND url_original LIKE '%datosabiertostianguisdigital.cdmx.gob.mx/proceso%';

-- Ver algunos ejemplos después de actualizar
SELECT id, numero_procedimiento, titulo, url_original
FROM licitaciones 
WHERE fuente = 'TIANGUIS_DIGITAL' 
  AND url_original LIKE '%datosabiertostianguisdigital.cdmx.gob.mx/proceso%'
LIMIT 5;

-- Verificar si quedó alguna sin corregir
SELECT COUNT(*) as sin_corregir
FROM licitaciones 
WHERE fuente = 'TIANGUIS_DIGITAL' 
  AND url_original LIKE '%tianguisdigital.cdmx.gob.mx%';
