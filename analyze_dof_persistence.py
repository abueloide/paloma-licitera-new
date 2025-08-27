#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de persistencia de datos mejorados del DOF
Muestra cómo se guardarían los datos parseados en la BD
"""

import json
from test_dof_parser import DOFTextParser, get_dof_samples, load_config
import psycopg2
import psycopg2.extras
from datetime import datetime

def get_current_schema():
    """Obtener el esquema actual de la tabla licitaciones."""
    db_config = load_config()
    if not db_config:
        return None
    
    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['name'],
            user=db_config['user'],
            password=db_config['password'],
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'licitaciones'
            ORDER BY ordinal_position;
        """)
        
        schema = cursor.fetchall()
        conn.close()
        return schema
        
    except Exception as e:
        print(f"Error obteniendo esquema: {e}")
        return None

def create_enhanced_table_suggestion():
    """Sugerir estructura de tabla mejorada para datos parseados."""
    return """
-- Propuesta de tabla mejorada para licitaciones del DOF
CREATE TABLE IF NOT EXISTS licitaciones_dof_enhanced (
    id SERIAL PRIMARY KEY,
    
    -- Datos originales (mantener compatibilidad)
    numero_procedimiento TEXT,
    titulo_original TEXT,
    descripcion_original TEXT,
    entidad_compradora TEXT,
    fuente TEXT DEFAULT 'DOF',
    url_original TEXT,
    fecha_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Datos parseados mejorados
    titulo_limpio TEXT,
    descripcion_extraida TEXT,
    
    -- Fechas estructuradas
    fecha_publicacion_compranet TIMESTAMP,
    fecha_junta_aclaraciones TIMESTAMP,
    fecha_presentacion_apertura TIMESTAMP,
    fecha_fallo TIMESTAMP,
    fecha_visita_sitio TIMESTAMP,
    
    -- Ubicación estructurada
    ubicacion_ciudad TEXT,
    ubicacion_estado TEXT,
    ubicacion_localidad TEXT,
    ubicacion_municipio TEXT,
    
    -- Información técnica
    volumen_obra TEXT,
    cantidad INTEGER,
    unidad TEXT,
    caracter_procedimiento TEXT, -- Nacional/Internacional
    visita_requerida BOOLEAN,
    detalles_en_convocatoria BOOLEAN,
    
    -- Metadatos de procesamiento
    parsing_version TEXT DEFAULT '1.0',
    parsing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parsing_success BOOLEAN DEFAULT true,
    
    -- JSON para datos adicionales
    datos_parseados JSONB,
    datos_originales JSONB
);

-- Índices para búsquedas eficientes
CREATE INDEX IF NOT EXISTS idx_licitaciones_dof_enhanced_fecha_pub 
    ON licitaciones_dof_enhanced(fecha_publicacion_compranet);
CREATE INDEX IF NOT EXISTS idx_licitaciones_dof_enhanced_ubicacion 
    ON licitaciones_dof_enhanced(ubicacion_ciudad, ubicacion_estado);
CREATE INDEX IF NOT EXISTS idx_licitaciones_dof_enhanced_cantidad 
    ON licitaciones_dof_enhanced(cantidad, unidad);
CREATE INDEX IF NOT EXISTS idx_licitaciones_dof_enhanced_titulo 
    ON licitaciones_dof_enhanced USING gin(to_tsvector('spanish', titulo_limpio));
"""

def simulate_data_persistence():
    """Simular cómo se persistirían los datos parseados."""
    print("🔍 Simulando persistencia de datos parseados del DOF...\n")
    
    # Obtener muestras y parsear
    samples = get_dof_samples(3)  # Solo 3 para el ejemplo
    if not samples:
        print("❌ No se pudieron obtener muestras")
        return
    
    parser = DOFTextParser()
    
    print("=" * 80)
    print("📊 ESQUEMA ACTUAL DE LA TABLA 'licitaciones'")
    print("=" * 80)
    
    schema = get_current_schema()
    if schema:
        print("Columnas existentes:")
        for col in schema:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            max_len = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
            print(f"  {col['column_name']:<25} {col['data_type']}{max_len:<15} {nullable}")
    
    print("\n" + "=" * 80)
    print("💾 SIMULACIÓN DE DATOS MEJORADOS")
    print("=" * 80)
    
    enhanced_records = []
    
    for i, sample in enumerate(samples, 1):
        print(f"\n--- REGISTRO {i} ---")
        resultado = parser.parse_licitacion(sample)
        
        # Convertir fechas parseadas a formato de BD
        fechas_bd = {}
        for evento, fecha_str in resultado['fechas_extraidas'].items():
            if fecha_str and fecha_str != "No aplica" and not fecha_str.startswith("Original:"):
                try:
                    fechas_bd[evento] = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')
                except:
                    fechas_bd[evento] = None
            else:
                fechas_bd[evento] = None
        
        # Crear registro mejorado
        enhanced_record = {
            # Datos originales (mantener compatibilidad)
            'id': resultado['id'],
            'numero_procedimiento': resultado['numero_procedimiento'],
            'titulo_original': resultado['titulo_original'],
            'descripcion_original': resultado['descripcion_original'],
            'entidad_compradora': resultado['entidad_original'],
            'fuente': 'DOF',
            
            # Datos parseados mejorados
            'titulo_limpio': resultado['titulo_separado'],
            'descripcion_extraida': resultado['descripcion_extraida'][:500] if resultado['descripcion_extraida'] else None,
            
            # Fechas estructuradas
            'fecha_publicacion_compranet': fechas_bd.get('fecha_publicacion_compranet'),
            'fecha_junta_aclaraciones': fechas_bd.get('junta_aclaraciones'),
            'fecha_presentacion_apertura': fechas_bd.get('presentacion_apertura'),
            'fecha_fallo': fechas_bd.get('fallo'),
            'fecha_visita_sitio': fechas_bd.get('visita_sitio'),
            
            # Ubicación estructurada
            'ubicacion_ciudad': resultado['ubicacion'].get('ciudad'),
            'ubicacion_estado': resultado['ubicacion'].get('estado'),
            'ubicacion_localidad': resultado['ubicacion'].get('localidad'),
            'ubicacion_municipio': resultado['ubicacion'].get('municipio'),
            
            # Información técnica
            'volumen_obra': resultado['info_tecnica'].get('volumen_obra'),
            'cantidad': int(resultado['info_tecnica']['cantidad']) if resultado['info_tecnica'].get('cantidad') and resultado['info_tecnica']['cantidad'].isdigit() else None,
            'unidad': resultado['info_tecnica'].get('unidad'),
            'caracter_procedimiento': resultado['info_tecnica'].get('caracter_procedimiento'),
            'visita_requerida': resultado['info_tecnica'].get('visita_requerida'),
            'detalles_en_convocatoria': bool(resultado['info_tecnica'].get('detalles_convocatoria')),
            
            # Metadatos
            'parsing_version': '1.0',
            'parsing_date': datetime.now(),
            'parsing_success': True,
            
            # JSON para datos adicionales
            'datos_parseados': {
                'fechas_originales': resultado['fechas_extraidas'],
                'info_tecnica_completa': resultado['info_tecnica'],
                'ubicacion_completa': resultado['ubicacion']
            }
        }
        
        enhanced_records.append(enhanced_record)
        
        # Mostrar comparación
        print(f"📝 TÍTULO:")
        print(f"   Original: {resultado['titulo_original'][:80]}...")
        print(f"   Limpio:   {enhanced_record['titulo_limpio'][:80]}")
        
        print(f"\n📅 FECHAS ESTRUCTURADAS:")
        fechas_importantes = ['fecha_publicacion_compranet', 'fecha_junta_aclaraciones', 'fecha_presentacion_apertura', 'fecha_fallo']
        for fecha_campo in fechas_importantes:
            valor = enhanced_record[fecha_campo]
            if valor:
                print(f"   {fecha_campo}: {valor}")
        
        print(f"\n📍 UBICACIÓN ESTRUCTURADA:")
        ubicacion_campos = ['ubicacion_ciudad', 'ubicacion_estado', 'ubicacion_localidad']
        for ubi_campo in ubicacion_campos:
            valor = enhanced_record[ubi_campo]
            if valor:
                print(f"   {ubi_campo}: {valor}")
        
        print(f"\n🔧 INFO TÉCNICA ESTRUCTURADA:")
        if enhanced_record['cantidad']:
            print(f"   cantidad: {enhanced_record['cantidad']} {enhanced_record['unidad'] or ''}")
        if enhanced_record['caracter_procedimiento']:
            print(f"   carácter: {enhanced_record['caracter_procedimiento']}")
        if enhanced_record['visita_requerida'] is not None:
            print(f"   visita_requerida: {enhanced_record['visita_requerida']}")
    
    print("\n" + "=" * 80)
    print("📋 PROPUESTA DE ESTRUCTURA DE TABLA MEJORADA")
    print("=" * 80)
    print(create_enhanced_table_suggestion())
    
    print("\n" + "=" * 80)
    print("💡 EJEMPLO DE QUERY INSERT")
    print("=" * 80)
    
    if enhanced_records:
        record = enhanced_records[0]  # Tomar el primer registro como ejemplo
        insert_query = f"""
INSERT INTO licitaciones_dof_enhanced (
    numero_procedimiento,
    titulo_original,
    titulo_limpio,
    descripcion_extraida,
    entidad_compradora,
    fecha_publicacion_compranet,
    fecha_junta_aclaraciones,
    fecha_presentacion_apertura,
    ubicacion_ciudad,
    ubicacion_estado,
    cantidad,
    unidad,
    caracter_procedimiento,
    visita_requerida,
    detalles_en_convocatoria,
    datos_parseados
) VALUES (
    {repr(record['numero_procedimiento'])},
    {repr(record['titulo_original'][:100] + '...')},
    {repr(record['titulo_limpio'])},
    {repr(record['descripcion_extraida'][:100] + '...' if record['descripcion_extraida'] else None)},
    {repr(record['entidad_compradora'])},
    {repr(record['fecha_publicacion_compranet'])},
    {repr(record['fecha_junta_aclaraciones'])},
    {repr(record['fecha_presentacion_apertura'])},
    {repr(record['ubicacion_ciudad'])},
    {repr(record['ubicacion_estado'])},
    {record['cantidad']},
    {repr(record['unidad'])},
    {repr(record['caracter_procedimiento'])},
    {record['visita_requerida']},
    {record['detalles_en_convocatoria']},
    {repr(json.dumps(record['datos_parseados'], ensure_ascii=False, default=str))}
);
        """.strip()
        print(insert_query)
    
    print("\n" + "=" * 80)
    print("📈 BENEFICIOS DE LA ESTRUCTURA MEJORADA")
    print("=" * 80)
    
    beneficios = [
        "✅ Fechas estructuradas permiten filtros y rangos eficientes",
        "✅ Ubicación normalizada facilita búsquedas geográficas",
        "✅ Información técnica separada (cantidad, unidad) permite análisis",
        "✅ Títulos limpios mejoran la experiencia de usuario",
        "✅ Metadatos de parsing para control de calidad",
        "✅ JSONB para flexibilidad sin perder estructura",
        "✅ Índices optimizados para consultas comunes",
        "✅ Mantiene compatibilidad con tabla actual"
    ]
    
    for beneficio in beneficios:
        print(f"  {beneficio}")
    
    print(f"\n📊 Resumen de procesamiento:")
    print(f"  - {len(enhanced_records)} registros procesados")
    print(f"  - {sum(1 for r in enhanced_records if r['fecha_publicacion_compranet'])} con fecha de publicación")
    print(f"  - {sum(1 for r in enhanced_records if r['ubicacion_ciudad'] or r['ubicacion_estado'])} con ubicación")
    print(f"  - {sum(1 for r in enhanced_records if r['cantidad'])} con cantidad específica")
    print(f"  - {sum(1 for r in enhanced_records if r['caracter_procedimiento'])} con carácter definido")

def main():
    simulate_data_persistence()

if __name__ == "__main__":
    main()
