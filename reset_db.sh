#!/bin/bash
# Script para resetear completamente la base de datos con el esquema correcto

echo "🗑️  RESET COMPLETO DE BASE DE DATOS"
echo "===================================="

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⚠️  Esto ELIMINARÁ TODA la base de datos y la recreará${NC}"
echo ""

# Paso 1: Eliminar y recrear la base de datos
echo "1. Eliminando base de datos existente..."
psql -h localhost -U postgres << EOF
DROP DATABASE IF EXISTS paloma_licitera;
CREATE DATABASE paloma_licitera;
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Base de datos recreada${NC}"
else
    echo -e "${RED}❌ Error recreando base de datos${NC}"
    exit 1
fi

# Paso 2: Crear el esquema correcto
echo ""
echo "2. Creando esquema de tablas..."
psql -h localhost -U postgres -d paloma_licitera << 'EOF'
-- Tabla principal de licitaciones con TODOS los campos necesarios
CREATE TABLE licitaciones (
    id SERIAL PRIMARY KEY,
    
    -- Campos de identificación
    numero_procedimiento VARCHAR(255) NOT NULL,
    uuid_procedimiento VARCHAR(255),
    hash_contenido VARCHAR(64) UNIQUE,
    
    -- Información básica
    titulo TEXT NOT NULL,
    descripcion TEXT,
    
    -- Entidades
    entidad_compradora VARCHAR(500),
    unidad_compradora VARCHAR(500),
    
    -- Clasificación
    tipo_procedimiento VARCHAR(50),
    tipo_contratacion VARCHAR(50),
    estado VARCHAR(50),
    caracter VARCHAR(50),
    
    -- Fechas
    fecha_publicacion DATE,
    fecha_apertura DATE,
    fecha_fallo DATE,
    fecha_junta_aclaraciones DATE,
    
    -- Montos
    monto_estimado DECIMAL(15,2),
    moneda VARCHAR(10) DEFAULT 'MXN',
    
    -- Proveedor
    proveedor_ganador TEXT,
    
    -- Metadata
    fuente VARCHAR(50) NOT NULL,
    url_original TEXT,
    fecha_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    datos_originales JSONB,
    
    -- Constraints
    CONSTRAINT uk_licitacion UNIQUE(numero_procedimiento, entidad_compradora, fuente)
);

-- Índices para búsquedas rápidas
CREATE INDEX idx_numero_procedimiento ON licitaciones(numero_procedimiento);
CREATE INDEX idx_entidad ON licitaciones(entidad_compradora);
CREATE INDEX idx_fecha_pub ON licitaciones(fecha_publicacion);
CREATE INDEX idx_fuente ON licitaciones(fuente);
CREATE INDEX idx_estado ON licitaciones(estado);
CREATE INDEX idx_tipo_procedimiento ON licitaciones(tipo_procedimiento);
CREATE INDEX idx_tipo_contratacion ON licitaciones(tipo_contratacion);
CREATE INDEX idx_uuid ON licitaciones(uuid_procedimiento);
CREATE INDEX idx_hash ON licitaciones(hash_contenido);

-- Verificar que se creó correctamente
\d licitaciones
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Esquema creado correctamente${NC}"
else
    echo -e "${RED}❌ Error creando esquema${NC}"
    exit 1
fi

# Paso 3: Verificar la estructura
echo ""
echo "3. Verificando estructura de la tabla..."
psql -h localhost -U postgres -d paloma_licitera -c "\d licitaciones" > /tmp/tabla_estructura.txt 2>&1

if grep -q "monto_estimado" /tmp/tabla_estructura.txt; then
    echo -e "${GREEN}✅ Campo monto_estimado existe${NC}"
else
    echo -e "${RED}❌ Campo monto_estimado NO existe${NC}"
    cat /tmp/tabla_estructura.txt
    exit 1
fi

# Paso 4: Test de inserción
echo ""
echo "4. Probando inserción de datos..."
psql -h localhost -U postgres -d paloma_licitera << EOF
INSERT INTO licitaciones (
    numero_procedimiento, titulo, entidad_compradora, 
    fuente, monto_estimado, moneda
) VALUES (
    'TEST-001', 'Licitación de prueba', 'Entidad de prueba',
    'test', 100000.00, 'MXN'
);
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Inserción de prueba exitosa${NC}"
    
    # Limpiar dato de prueba
    psql -h localhost -U postgres -d paloma_licitera -c "DELETE FROM licitaciones WHERE fuente='test';" > /dev/null 2>&1
else
    echo -e "${RED}❌ Error en inserción de prueba${NC}"
    exit 1
fi

# Resumen final
echo ""
echo "===================================="
echo -e "${GREEN}✅ BASE DE DATOS LISTA${NC}"
echo "===================================="
echo ""
echo "La base de datos ha sido recreada con el esquema correcto."
echo "Ahora puedes ejecutar:"
echo ""
echo "  1. Para procesar archivos existentes:"
echo "     python src/etl.py --fuente all --solo-procesamiento"
echo ""
echo "  2. Para descargar y procesar nuevos datos:"
echo "     python src/etl.py --fuente all"
echo ""
