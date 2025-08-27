-- =============================================
-- MIGRACIÓN: Modelo Híbrido de Licitaciones
-- Fecha: 2025-01-29
-- Versión: 001
-- Descripción: Agrega campos para modelo híbrido
--              y migra datos existentes
-- =============================================

-- PASO 1: Agregar nuevos campos a la tabla licitaciones
-- -------------------------------------------------------

-- Campo para entidad federativa (estado)
ALTER TABLE licitaciones 
ADD COLUMN IF NOT EXISTS entidad_federativa VARCHAR(100);

-- Campo para municipio
ALTER TABLE licitaciones 
ADD COLUMN IF NOT EXISTS municipio VARCHAR(100);

-- Campo para datos específicos por fuente (JSONB)
ALTER TABLE licitaciones 
ADD COLUMN IF NOT EXISTS datos_especificos JSONB;


-- PASO 2: Crear índices optimizados para nuevos campos
-- -----------------------------------------------------

-- Índice para búsquedas por entidad federativa
CREATE INDEX IF NOT EXISTS idx_entidad_federativa 
ON licitaciones(entidad_federativa);

-- Índice para búsquedas por municipio
CREATE INDEX IF NOT EXISTS idx_municipio 
ON licitaciones(municipio);

-- Índice GIN para búsquedas en JSONB datos_especificos
CREATE INDEX IF NOT EXISTS idx_datos_especificos_gin 
ON licitaciones USING GIN(datos_especificos);

-- Índice para búsquedas por entidad+municipio (compuesto)
CREATE INDEX IF NOT EXISTS idx_entidad_municipio 
ON licitaciones(entidad_federativa, municipio);


-- PASO 3: Migrar datos existentes de datos_originales → datos_especificos
-- ------------------------------------------------------------------------

-- Copiar datos_originales a datos_especificos para todos los registros existentes
UPDATE licitaciones 
SET datos_especificos = datos_originales 
WHERE datos_especificos IS NULL 
  AND datos_originales IS NOT NULL;


-- PASO 4: Actualizar entidad_federativa para ComprasMX
-- -----------------------------------------------------

-- Mapear campo entidad_federativa_contratacion → entidad_federativa
UPDATE licitaciones 
SET entidad_federativa = datos_originales->>'entidad_federativa_contratacion'
WHERE fuente = 'ComprasMX' 
  AND entidad_federativa IS NULL
  AND datos_originales->>'entidad_federativa_contratacion' IS NOT NULL;


-- PASO 5: Actualizar municipio para ComprasMX (si existe)
-- --------------------------------------------------------

UPDATE licitaciones 
SET municipio = datos_originales->>'municipio'
WHERE fuente = 'ComprasMX' 
  AND municipio IS NULL
  AND datos_originales->>'municipio' IS NOT NULL;


-- PASO 6: Preparar estructura datos_especificos para ComprasMX
-- -------------------------------------------------------------

UPDATE licitaciones 
SET datos_especificos = jsonb_build_object(
    'tipo_procedimiento', COALESCE(datos_originales->>'tipo_procedimiento', tipo_procedimiento),
    'caracter', COALESCE(datos_originales->>'caracter', caracter),
    'forma_procedimiento', datos_originales->>'forma_procedimiento',
    'medio_utilizado', datos_originales->>'medio_utilizado',
    'codigo_contrato', datos_originales->>'codigo_contrato',
    'plantilla_convenio', datos_originales->>'plantilla_convenio',
    'fecha_inicio_contrato', datos_originales->>'fecha_inicio_contrato',
    'fecha_fin_contrato', datos_originales->>'fecha_fin_contrato',
    'convenio_modificatorio', datos_originales->>'convenio_modificatorio',
    'ramo', datos_originales->>'ramo',
    'clave_programa', datos_originales->>'clave_programa',
    'aportacion_federal', datos_originales->>'aportacion_federal',
    'fecha_celebracion', datos_originales->>'fecha_celebracion',
    'contrato_marco', datos_originales->>'contrato_marco',
    'compra_consolidada', datos_originales->>'compra_consolidada',
    'plurianual', datos_originales->>'plurianual',
    'clave_cartera_shcp', datos_originales->>'clave_cartera_shcp'
)
WHERE fuente = 'ComprasMX'
  AND datos_especificos IS NULL;


-- PASO 7: Preparar estructura datos_especificos para DOF
-- -------------------------------------------------------

-- Para DOF necesitamos parsear el texto, pero guardamos estructura base
UPDATE licitaciones 
SET datos_especificos = jsonb_build_object(
    'titulo_original', titulo,
    'descripcion_original', descripcion,
    'fecha_ejemplar', datos_originales->>'fecha_ejemplar',
    'seccion', datos_originales->>'seccion',
    'organismo', datos_originales->>'organismo',
    'notas', datos_originales->>'notas',
    'procesado_parser', false
)
WHERE fuente = 'DOF'
  AND datos_especificos IS NULL;


-- PASO 8: Preparar estructura datos_especificos para Tianguis Digital
-- --------------------------------------------------------------------

UPDATE licitaciones 
SET datos_especificos = jsonb_build_object(
    'ocds_data', CASE 
        WHEN datos_originales ? 'ocid' THEN datos_originales
        ELSE NULL 
    END,
    'classification', datos_originales->'tender'->'classification',
    'procuring_entity', datos_originales->'tender'->'procuringEntity',
    'items', datos_originales->'tender'->'items',
    'documents', datos_originales->'tender'->'documents',
    'milestones', datos_originales->'tender'->'milestones'
)
WHERE fuente = 'Tianguis Digital'
  AND datos_especificos IS NULL;


-- PASO 9: Estadísticas de migración
-- ----------------------------------

DO $$
DECLARE
    total_registros INTEGER;
    registros_migrados INTEGER;
    comprasmx_con_estado INTEGER;
    dof_pendientes INTEGER;
BEGIN
    -- Total de registros
    SELECT COUNT(*) INTO total_registros FROM licitaciones;
    
    -- Registros con datos_especificos migrados
    SELECT COUNT(*) INTO registros_migrados 
    FROM licitaciones 
    WHERE datos_especificos IS NOT NULL;
    
    -- ComprasMX con entidad_federativa
    SELECT COUNT(*) INTO comprasmx_con_estado
    FROM licitaciones 
    WHERE fuente = 'ComprasMX' 
      AND entidad_federativa IS NOT NULL;
    
    -- DOF pendientes de parser
    SELECT COUNT(*) INTO dof_pendientes
    FROM licitaciones 
    WHERE fuente = 'DOF' 
      AND (datos_especificos->>'procesado_parser')::boolean IS FALSE;
    
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'MIGRACIÓN COMPLETADA - ESTADÍSTICAS:';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Total registros: %', total_registros;
    RAISE NOTICE 'Registros migrados: %', registros_migrados;
    RAISE NOTICE 'ComprasMX con estado: %', comprasmx_con_estado;
    RAISE NOTICE 'DOF pendientes de parser: %', dof_pendientes;
    RAISE NOTICE '==============================================';
END $$;


-- PASO 10: Verificación de integridad
-- ------------------------------------

-- Verificar que no perdimos datos
SELECT 
    'VERIFICACIÓN DE INTEGRIDAD' as verificacion,
    COUNT(*) as total_registros,
    SUM(CASE WHEN datos_originales IS NOT NULL THEN 1 ELSE 0 END) as con_datos_originales,
    SUM(CASE WHEN datos_especificos IS NOT NULL THEN 1 ELSE 0 END) as con_datos_especificos,
    SUM(CASE WHEN fuente = 'ComprasMX' AND entidad_federativa IS NOT NULL THEN 1 ELSE 0 END) as comprasmx_con_estado,
    SUM(CASE WHEN fuente = 'DOF' THEN 1 ELSE 0 END) as total_dof
FROM licitaciones;
