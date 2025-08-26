#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para re-procesar archivos del DOF y actualizar URLs
============================================================

Este script:
1. Re-procesa los archivos TXT del DOF con el extractor actualizado
2. Actualiza la base de datos con las fechas correctas del ejemplar
3. Corrige las URLs para que apunten al día correcto del DOF
"""

import os
import sys
import json
import re
import psycopg2
import psycopg2.extras
import yaml
import logging
from datetime import datetime
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Agregar directorio al path
sys.path.insert(0, str(Path(__file__).parent / 'etl-process' / 'extractors' / 'dof'))

def cargar_configuracion():
    """Cargar configuración de la base de datos"""
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config['database']

def conectar_bd(db_config):
    """Crear conexión a la base de datos"""
    return psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['name'],
        user=db_config['user'],
        password=db_config['password'],
        cursor_factory=psycopg2.extras.RealDictCursor
    )

def procesar_archivos_txt(directorio_dof):
    """Re-procesar todos los archivos TXT del DOF con el extractor actualizado"""
    logger.info(f"Procesando archivos TXT en: {directorio_dof}")
    
    # Importar el extractor actualizado
    from estructura_dof_actualizado import DOFLicitacionesExtractor
    
    archivos_procesados = []
    
    # Buscar todos los archivos TXT del DOF
    for archivo in os.listdir(directorio_dof):
        if archivo.endswith('.txt') and ('MAT' in archivo or 'VES' in archivo):
            archivo_path = os.path.join(directorio_dof, archivo)
            logger.info(f"Procesando: {archivo}")
            
            # Ejecutar extractor
            extractor = DOFLicitacionesExtractor(archivo_path)
            if extractor.procesar():
                json_path = archivo_path.replace('.txt', '_licitaciones.json')
                archivos_procesados.append({
                    'archivo': archivo,
                    'json': json_path,
                    'fecha_ejemplar': extractor.fecha_ejemplar,
                    'edicion': extractor.edicion_ejemplar,
                    'licitaciones': len(extractor.licitaciones)
                })
                logger.info(f"✅ Procesado: {len(extractor.licitaciones)} licitaciones - Fecha: {extractor.fecha_ejemplar}")
            else:
                logger.error(f"❌ Error procesando: {archivo}")
    
    return archivos_procesados

def actualizar_base_datos(archivos_procesados, db_config):
    """Actualizar la base de datos con la información correcta del ejemplar"""
    logger.info("Actualizando base de datos con fechas correctas del DOF...")
    
    conn = conectar_bd(db_config)
    cursor = conn.cursor()
    
    actualizaciones = 0
    
    for archivo_info in archivos_procesados:
        # Leer JSON generado
        with open(archivo_info['json'], 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        fecha_ejemplar = datos['fecha_ejemplar']
        edicion = datos['edicion_ejemplar']
        
        for licitacion in datos['licitaciones']:
            try:
                # Preparar datos_originales actualizado con fecha del ejemplar
                datos_originales = {
                    'fecha_ejemplar': fecha_ejemplar,
                    'edicion_ejemplar': edicion,
                    'archivo_origen': archivo_info['archivo'],
                    'pagina': licitacion.get('pagina'),
                    'referencia': licitacion.get('referencia'),
                    'fecha_publicacion_comprasmx': licitacion.get('fecha_publicacion')
                }
                
                # Actualizar registros existentes basándose en el número de licitación
                if licitacion.get('numero_licitacion'):
                    sql_update = """
                        UPDATE licitaciones 
                        SET datos_originales = datos_originales || %s::jsonb
                        WHERE fuente = 'DOF' 
                        AND numero_procedimiento = %s
                        RETURNING id;
                    """
                    
                    cursor.execute(sql_update, (
                        json.dumps(datos_originales),
                        licitacion['numero_licitacion']
                    ))
                    
                    result = cursor.fetchone()
                    if result:
                        actualizaciones += 1
                        logger.debug(f"Actualizado ID {result['id']}: {licitacion['numero_licitacion']}")
                
                # Si no tiene número, intentar por dependencia y objeto
                elif licitacion.get('dependencia') and licitacion.get('objeto_licitacion'):
                    sql_update = """
                        UPDATE licitaciones 
                        SET datos_originales = datos_originales || %s::jsonb
                        WHERE fuente = 'DOF' 
                        AND entidad_compradora = %s
                        AND titulo LIKE %s
                        RETURNING id;
                    """
                    
                    cursor.execute(sql_update, (
                        json.dumps(datos_originales),
                        licitacion['dependencia'],
                        f"%{licitacion['objeto_licitacion'][:50]}%"
                    ))
                    
                    result = cursor.fetchone()
                    if result:
                        actualizaciones += 1
                        logger.debug(f"Actualizado ID {result['id']}: {licitacion['dependencia']}")
                        
            except Exception as e:
                logger.error(f"Error actualizando licitación: {e}")
                conn.rollback()
                continue
    
    conn.commit()
    logger.info(f"✅ Actualizaciones completadas: {actualizaciones} registros")
    
    # Verificar las URLs actualizadas
    verificar_urls(cursor)
    
    cursor.close()
    conn.close()
    
    return actualizaciones

def verificar_urls(cursor):
    """Verificar que las URLs del DOF se están construyendo correctamente"""
    logger.info("Verificando construcción de URLs del DOF...")
    
    # Obtener algunas licitaciones del DOF para verificar
    cursor.execute("""
        SELECT 
            id,
            numero_procedimiento,
            entidad_compradora,
            datos_originales,
            fecha_publicacion
        FROM licitaciones 
        WHERE fuente = 'DOF'
        AND datos_originales IS NOT NULL
        AND datos_originales::text LIKE '%fecha_ejemplar%'
        LIMIT 5
    """)
    
    ejemplos = cursor.fetchall()
    
    for ejemplo in ejemplos:
        datos_orig = ejemplo['datos_originales']
        if isinstance(datos_orig, str):
            datos_orig = json.loads(datos_orig)
        
        fecha_ejemplar = datos_orig.get('fecha_ejemplar', '')
        edicion = datos_orig.get('edicion_ejemplar', '')
        
        if fecha_ejemplar:
            # Construir URL correcta
            fecha_parts = fecha_ejemplar.split('-')
            if len(fecha_parts) == 3:
                año, mes, dia = fecha_parts
                url_correcta = f"https://dof.gob.mx/index_111.php?year={año}&month={mes}&day={dia}#gsc.tab=0"
                
                logger.info(f"📎 Licitación {ejemplo['numero_procedimiento']}")
                logger.info(f"   Fecha ejemplar: {fecha_ejemplar} - Edición: {edicion}")
                logger.info(f"   URL DOF: {url_correcta}")
                print()

def main():
    """Función principal"""
    logger.info("="*60)
    logger.info("INICIANDO RE-PROCESAMIENTO DE ARCHIVOS DOF")
    logger.info("="*60)
    
    # Cargar configuración
    db_config = cargar_configuracion()
    
    # Directorio de archivos DOF
    directorio_dof = Path("data/raw/dof")
    
    if not directorio_dof.exists():
        logger.error(f"El directorio {directorio_dof} no existe")
        return 1
    
    # 1. Re-procesar archivos TXT
    logger.info("\n📝 FASE 1: Re-procesando archivos TXT...")
    archivos_procesados = procesar_archivos_txt(directorio_dof)
    
    if not archivos_procesados:
        logger.error("No se encontraron archivos para procesar")
        return 1
    
    logger.info(f"✅ Procesados {len(archivos_procesados)} archivos")
    
    # 2. Actualizar base de datos
    logger.info("\n💾 FASE 2: Actualizando base de datos...")
    actualizaciones = actualizar_base_datos(archivos_procesados, db_config)
    
    # Resumen final
    logger.info("\n" + "="*60)
    logger.info("RESUMEN DEL PROCESO")
    logger.info("="*60)
    logger.info(f"📁 Archivos procesados: {len(archivos_procesados)}")
    logger.info(f"💾 Registros actualizados: {actualizaciones}")
    
    print("\nArchivos procesados:")
    for archivo in archivos_procesados:
        print(f"  - {archivo['archivo']}: {archivo['licitaciones']} licitaciones")
        print(f"    Fecha: {archivo['fecha_ejemplar']} - Edición: {archivo['edicion']}")
    
    logger.info("\n✅ Proceso completado. Las URLs del DOF ahora apuntan a las fechas correctas del ejemplar.")
    logger.info("📌 La API ya puede construir URLs correctas usando la información de datos_originales")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
