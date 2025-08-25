-- Script de inicialización de BD
-- Crear base de datos solo si no existe
CREATE DATABASE paloma_licitera;

-- Conectar a la base de datos
\c paloma_licitera;

-- Crear tabla licitaciones si no existe
CREATE TABLE IF NOT EXISTS licitaciones (
    id SERIAL PRIMARY KEY,
    numero_procedimiento VARCHAR(255),
    titulo TEXT,
    descripcion TEXT,
    entidad_compradora VARCHAR(500),
    unidad_compradora VARCHAR(500),
    tipo_procedimiento VARCHAR(100),
    tipo_contratacion VARCHAR(100),
    estado VARCHAR(50),
    fecha_publicacion TIMESTAMP,
    fecha_apertura TIMESTAMP,
    fecha_fallo TIMESTAMP,
    fecha_junta_aclaraciones TIMESTAMP,
    monto_estimado DECIMAL(20,2),
    moneda VARCHAR(10),
    proveedor_ganador VARCHAR(500),
    caracter VARCHAR(100),
    uuid_procedimiento VARCHAR(255),
    fuente VARCHAR(50),
    url_original TEXT,
    datos_originales JSONB,
    hash_unico VARCHAR(64) UNIQUE,
    fecha_captura TIMESTAMP DEFAULT NOW()
);

-- Crear índices solo si no existen (PostgreSQL maneja esto automáticamente)
CREATE INDEX IF NOT EXISTS idx_fuente ON licitaciones(fuente);
CREATE INDEX IF NOT EXISTS idx_fecha_publicacion ON licitaciones(fecha_publicacion);
CREATE INDEX IF NOT EXISTS idx_estado ON licitaciones(estado);
CREATE INDEX IF NOT EXISTS idx_entidad_compradora ON licitaciones(entidad_compradora);