#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para ejecutar migración a modelo híbrido
Ejecuta el script SQL y verifica la migración
"""

import psycopg2
import psycopg2.extras
import yaml
import sys
import os
from datetime import datetime

def load_config():
    """Cargar configuración de BD."""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config['database']
    except Exception as e:
        print(f"❌ Error cargando config.yaml: {e}")
        return None

def ejecutar_migracion():
    """Ejecutar el script de migración SQL."""
    db_config = load_config()
    if not db_config:
        return False
    
    migration_file = 'migrations/001_hybrid_model.sql'
    if not os.path.exists(migration_file):
        print(f"❌ No se encontró el archivo de migración: {migration_file}")
        return False
    
    print("🚀 Iniciando migración a modelo híbrido...")
    print("=" * 60)
    
    try:
        # Conectar a BD
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['name'],
            user=db_config['user'],
            password=db_config.get('password', ''),
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        
        cursor = conn.cursor()
        
        # Verificar estado actual
        print("\n📊 Estado ANTES de la migración:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN datos_originales IS NOT NULL THEN 1 ELSE 0 END) as con_datos_originales
            FROM licitaciones
        """)
        estado_inicial = cursor.fetchone()
        print(f"   Total registros: {estado_inicial['total']}")
        print(f"   Con datos_originales: {estado_inicial['con_datos_originales']}")
        
        # Verificar si ya existe alguna columna nueva
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'licitaciones' 
              AND column_name IN ('entidad_federativa', 'municipio', 'datos_especificos')
        """)
        columnas_existentes = [row['column_name'] for row in cursor.fetchall()]
        
        if columnas_existentes:
            print(f"\n⚠️  Las siguientes columnas ya existen: {columnas_existentes}")
            respuesta = input("¿Desea continuar con la migración? (s/n): ")
            if respuesta.lower() != 's':
                print("Migración cancelada por el usuario.")
                return False
        
        # Leer y ejecutar script SQL
        print(f"\n📝 Ejecutando script de migración...")
        with open(migration_file, 'r') as f:
            sql_script = f.read()
        
        # Ejecutar script completo
        cursor.execute(sql_script)
        
        # Verificar resultados
        print("\n📊 Estado DESPUÉS de la migración:")
        
        # Verificar nuevas columnas
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'licitaciones' 
              AND column_name IN ('entidad_federativa', 'municipio', 'datos_especificos')
            ORDER BY column_name
        """)
        nuevas_columnas = cursor.fetchall()
        print("\n✅ Nuevas columnas creadas:")
        for col in nuevas_columnas:
            print(f"   - {col['column_name']}: {col['data_type']}")
        
        # Verificar índices
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'licitaciones' 
              AND indexname IN (
                  'idx_entidad_federativa', 
                  'idx_municipio', 
                  'idx_datos_especificos_gin',
                  'idx_entidad_municipio'
              )
        """)
        indices = [row['indexname'] for row in cursor.fetchall()]
        print(f"\n✅ Índices creados: {len(indices)}")
        for idx in indices:
            print(f"   - {idx}")
        
        # Estadísticas de migración de datos
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN datos_especificos IS NOT NULL THEN 1 ELSE 0 END) as con_datos_especificos,
                SUM(CASE WHEN entidad_federativa IS NOT NULL THEN 1 ELSE 0 END) as con_entidad,
                SUM(CASE WHEN municipio IS NOT NULL THEN 1 ELSE 0 END) as con_municipio
            FROM licitaciones
        """)
        estadisticas = cursor.fetchone()
        
        print("\n📈 Estadísticas de migración:")
        print(f"   Total registros: {estadisticas['total']}")
        print(f"   Con datos_especificos: {estadisticas['con_datos_especificos']}")
        print(f"   Con entidad_federativa: {estadisticas['con_entidad']}")
        print(f"   Con municipio: {estadisticas['con_municipio']}")
        
        # Estadísticas por fuente
        cursor.execute("""
            SELECT 
                fuente,
                COUNT(*) as total,
                SUM(CASE WHEN datos_especificos IS NOT NULL THEN 1 ELSE 0 END) as migrados,
                SUM(CASE WHEN entidad_federativa IS NOT NULL THEN 1 ELSE 0 END) as con_estado
            FROM licitaciones
            GROUP BY fuente
            ORDER BY fuente
        """)
        
        print("\n📊 Estadísticas por fuente:")
        for row in cursor.fetchall():
            print(f"\n   {row['fuente']}:")
            print(f"      Total: {row['total']}")
            print(f"      Migrados: {row['migrados']}")
            print(f"      Con estado: {row['con_estado']}")
        
        # Confirmar cambios
        print("\n" + "=" * 60)
        respuesta = input("¿Desea confirmar los cambios? (s/n): ")
        
        if respuesta.lower() == 's':
            conn.commit()
            print("\n✅ Migración completada exitosamente")
            
            # Crear archivo de registro
            with open('migrations/migration_001_log.txt', 'w') as log:
                log.write(f"Migración 001_hybrid_model ejecutada: {datetime.now()}\n")
                log.write(f"Total registros migrados: {estadisticas['con_datos_especificos']}\n")
                log.write(f"Registros con entidad_federativa: {estadisticas['con_entidad']}\n")
            
            return True
        else:
            conn.rollback()
            print("\n⚠️  Migración revertida (sin cambios)")
            return False
            
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def verificar_integridad():
    """Verificar integridad de datos después de migración."""
    db_config = load_config()
    if not db_config:
        return
    
    print("\n🔍 Verificando integridad de datos...")
    
    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['name'],
            user=db_config['user'],
            password=db_config.get('password', ''),
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        
        cursor = conn.cursor()
        
        # Verificar que no perdimos datos
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE 
                    WHEN datos_originales IS NOT NULL 
                     AND datos_especificos IS NULL 
                    THEN 1 ELSE 0 
                END) as sin_migrar
            FROM licitaciones
        """)
        
        resultado = cursor.fetchone()
        
        if resultado['sin_migrar'] > 0:
            print(f"⚠️  ADVERTENCIA: {resultado['sin_migrar']} registros no migrados")
        else:
            print(f"✅ Todos los datos migrados correctamente")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error verificando integridad: {e}")

def main():
    """Función principal."""
    print("\n" + "=" * 60)
    print("   MIGRACIÓN A MODELO HÍBRIDO - PALOMA LICITERA")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verificar_integridad()
    else:
        if ejecutar_migracion():
            verificar_integridad()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
