#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para procesar licitaciones DOF con el parser especializado
Actualiza datos_especificos con información estructurada
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras
import yaml
import json
from datetime import datetime
from src.parsers.dof_parser import DOFParser

def load_config():
    """Cargar configuración de BD."""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config['database']
    except Exception as e:
        print(f"❌ Error cargando config.yaml: {e}")
        return None

def procesar_licitaciones_dof(limite=None, solo_pendientes=True):
    """
    Procesar licitaciones DOF con el parser especializado.
    
    Args:
        limite: Número máximo de licitaciones a procesar (None = todas)
        solo_pendientes: Si True, solo procesa las no procesadas anteriormente
    """
    db_config = load_config()
    if not db_config:
        return
    
    print("\n" + "=" * 60)
    print("   PROCESAMIENTO DE LICITACIONES DOF CON PARSER")
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
        
        # Construir query según parámetros
        if solo_pendientes:
            sql = """
                SELECT id, numero_procedimiento, titulo, descripcion, 
                       entidad_compradora, datos_originales, datos_especificos,
                       fecha_publicacion, fecha_apertura
                FROM licitaciones 
                WHERE fuente = 'DOF'
                  AND (
                    datos_especificos IS NULL 
                    OR (datos_especificos->>'procesado')::boolean IS FALSE
                    OR datos_especificos->>'procesado' IS NULL
                  )
                ORDER BY fecha_captura DESC
            """
        else:
            sql = """
                SELECT id, numero_procedimiento, titulo, descripcion, 
                       entidad_compradora, datos_originales, datos_especificos,
                       fecha_publicacion, fecha_apertura
                FROM licitaciones 
                WHERE fuente = 'DOF'
                ORDER BY fecha_captura DESC
            """
        
        if limite:
            sql += f" LIMIT {limite}"
        
        cursor.execute(sql)
        licitaciones = cursor.fetchall()
        
        if not licitaciones:
            print("\n✅ No hay licitaciones DOF pendientes de procesar")
            return
        
        print(f"\n📊 Encontradas {len(licitaciones)} licitaciones DOF para procesar")
        
        # Inicializar parser
        parser = DOFParser()
        
        # Contadores
        procesadas = 0
        con_estado = 0
        con_municipio = 0
        con_fechas = 0
        errores = 0
        
        print("\n🔄 Procesando licitaciones...")
        print("-" * 60)
        
        for lic in licitaciones:
            try:
                # Parsear licitación
                resultado = parser.parse(lic)
                
                # Preparar datos_especificos actualizados
                datos_especificos_actuales = lic.get('datos_especificos') or {}
                if isinstance(datos_especificos_actuales, str):
                    try:
                        datos_especificos_actuales = json.loads(datos_especificos_actuales)
                    except:
                        datos_especificos_actuales = {}
                
                # Combinar con resultados del parser
                datos_especificos_nuevos = {
                    **datos_especificos_actuales,
                    **resultado,
                    'procesado': True,
                    'procesado_fecha': datetime.now().isoformat()
                }
                
                # Actualizar registro
                update_sql = """
                    UPDATE licitaciones 
                    SET 
                        datos_especificos = %s,
                        entidad_federativa = COALESCE(entidad_federativa, %s),
                        municipio = COALESCE(municipio, %s)
                    WHERE id = %s
                """
                
                cursor.execute(update_sql, (
                    json.dumps(datos_especificos_nuevos),
                    resultado.get('entidad_federativa'),
                    resultado.get('municipio'),
                    lic['id']
                ))
                
                procesadas += 1
                
                # Actualizar contadores
                if resultado.get('entidad_federativa'):
                    con_estado += 1
                if resultado.get('municipio'):
                    con_municipio += 1
                if resultado.get('fechas_parseadas'):
                    con_fechas += 1
                
                # Mostrar progreso cada 10 registros
                if procesadas % 10 == 0:
                    print(f"   Procesadas: {procesadas}/{len(licitaciones)}")
                
            except Exception as e:
                errores += 1
                print(f"   ❌ Error procesando ID {lic['id']}: {e}")
                continue
        
        # Confirmar cambios
        print("\n" + "-" * 60)
        print("📈 Resumen del procesamiento:")
        print(f"   Total procesadas: {procesadas}")
        print(f"   Con entidad federativa: {con_estado}")
        print(f"   Con municipio: {con_municipio}")
        print(f"   Con fechas extraídas: {con_fechas}")
        print(f"   Errores: {errores}")
        
        if procesadas > 0:
            print("\n" + "=" * 60)
            respuesta = input("¿Desea confirmar los cambios? (s/n): ")
            
            if respuesta.lower() == 's':
                conn.commit()
                print("\n✅ Cambios guardados exitosamente")
                
                # Mostrar estadísticas finales
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_dof,
                        SUM(CASE WHEN entidad_federativa IS NOT NULL THEN 1 ELSE 0 END) as con_estado,
                        SUM(CASE WHEN municipio IS NOT NULL THEN 1 ELSE 0 END) as con_municipio,
                        SUM(CASE WHEN (datos_especificos->>'procesado')::boolean IS TRUE THEN 1 ELSE 0 END) as procesadas
                    FROM licitaciones
                    WHERE fuente = 'DOF'
                """)
                
                stats = cursor.fetchone()
                print("\n📊 Estadísticas DOF actualizadas:")
                print(f"   Total DOF: {stats['total_dof']}")
                print(f"   Procesadas: {stats['procesadas']}")
                print(f"   Con estado: {stats['con_estado']} ({stats['con_estado']*100//stats['total_dof']}%)")
                print(f"   Con municipio: {stats['con_municipio']} ({stats['con_municipio']*100//stats['total_dof']}%)")
                
            else:
                conn.rollback()
                print("\n⚠️  Cambios revertidos")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error durante el procesamiento: {e}")
        if conn:
            conn.rollback()
            conn.close()

def mostrar_ejemplos():
    """Mostrar ejemplos de licitaciones procesadas."""
    db_config = load_config()
    if not db_config:
        return
    
    print("\n📋 Ejemplos de licitaciones DOF procesadas:")
    print("=" * 60)
    
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
        
        # Obtener ejemplos
        cursor.execute("""
            SELECT 
                id,
                numero_procedimiento,
                titulo,
                entidad_federativa,
                municipio,
                datos_especificos
            FROM licitaciones
            WHERE fuente = 'DOF'
              AND (datos_especificos->>'procesado')::boolean IS TRUE
              AND entidad_federativa IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 3
        """)
        
        ejemplos = cursor.fetchall()
        
        for i, ej in enumerate(ejemplos, 1):
            print(f"\nEjemplo {i}:")
            print(f"  ID: {ej['id']}")
            print(f"  Número: {ej['numero_procedimiento']}")
            
            # Mostrar título limpio si existe
            datos_esp = json.loads(ej['datos_especificos']) if ej['datos_especificos'] else {}
            if datos_esp.get('titulo_limpio'):
                print(f"  Título limpio: {datos_esp['titulo_limpio'][:80]}...")
            
            print(f"  Estado: {ej['entidad_federativa']}")
            print(f"  Municipio: {ej['municipio'] or 'No identificado'}")
            
            # Mostrar fechas parseadas
            if datos_esp.get('fechas_parseadas'):
                print("  Fechas extraídas:")
                for evento, fecha in datos_esp['fechas_parseadas'].items():
                    print(f"    - {evento}: {fecha}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error mostrando ejemplos: {e}")

def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Procesar licitaciones DOF con parser especializado'
    )
    parser.add_argument(
        '--limite', 
        type=int, 
        help='Número máximo de licitaciones a procesar'
    )
    parser.add_argument(
        '--todas', 
        action='store_true',
        help='Procesar todas las licitaciones (no solo pendientes)'
    )
    parser.add_argument(
        '--ejemplos',
        action='store_true',
        help='Mostrar ejemplos de licitaciones procesadas'
    )
    
    args = parser.parse_args()
    
    if args.ejemplos:
        mostrar_ejemplos()
    else:
        procesar_licitaciones_dof(
            limite=args.limite,
            solo_pendientes=not args.todas
        )

if __name__ == "__main__":
    main()
