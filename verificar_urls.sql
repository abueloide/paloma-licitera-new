-- Script para verificar el estado de las URLs en la base de datos

-- 1. Ver cuántos registros hay por fuente
SELECT fuente, COUNT(*) as total
FROM licitaciones
GROUP BY fuente
ORDER BY total DESC;

-- 2. Ver ejemplos de URLs de TIANGUIS_DIGITAL (si existen)
SELECT id, numero_procedimiento, url_original
FROM licitaciones
WHERE fuente = 'TIANGUIS_DIGITAL'
LIMIT 5;

-- 3. Ver ejemplos de URLs de COMPRASMX
SELECT id, numero_procedimiento, url_original
FROM licitaciones
WHERE fuente = 'COMPRASMX'
LIMIT 5;

-- 4. Ver todas las fuentes distintas
SELECT DISTINCT fuente
FROM licitaciones;

-- 5. Contar cuántos registros de ComprasMX necesitan corrección
SELECT COUNT(*) as comprasmx_sin_url_correcta
FROM licitaciones
WHERE fuente = 'COMPRASMX'
  AND (url_original IS NULL 
       OR url_original = 'https://comprasmx.buengobierno.gob.mx/'
       OR url_original LIKE '%/procedimiento/%'
       OR url_original NOT LIKE '%/sitiopublico/detalle/%');

-- 6. Ver patrones de URLs existentes
SELECT fuente, 
       LEFT(url_original, 50) as url_patron,
       COUNT(*) as cantidad
FROM licitaciones
WHERE url_original IS NOT NULL
GROUP BY fuente, LEFT(url_original, 50)
ORDER BY fuente, cantidad DESC;
