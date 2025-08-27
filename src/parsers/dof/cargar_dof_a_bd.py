#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cargador de Datos DOF a Base de Datos PostgreSQL
================================================

Script para cargar los JSON mejorados del DOF a la base de datos PostgreSQL
con mapeo completo de campos y manejo de datos JSONB.
"""

import os
import sys
import json
import glob
import psycopg2
import psycopg2.extras
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('carga_dof_bd.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CargadorDOFBD:
    """Carga licitaciones del DOF procesadas a PostgreSQL"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Inicializa el cargador con la configuración de BD
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        # Cargar configuración
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.db_config = config.get('database', {})
        else:
            # Configuración por defecto
            self.db_config = {
                'host': 'localhost',
                'port': 5432,
                'name': 'paloma_licitera',
                'user': 'postgres',
                'password': ''
            }
            logger.warning(f"Archivo {config_path} no encontrado, usando configuración por defecto")
        
        self.conn = None
        self.cursor = None
        self.estadisticas = {
            'archivos_procesados': 0,
            'licitaciones_insertadas': 0,
            'licitaciones_actualizadas': 0,
            'licitaciones_duplicadas': 0,
            'errores': 0
        }
    
    def conectar(self) -> bool:
        """
        Establece conexión con la base de datos
        
        Returns:
            True si la conexión fue exitosa
        """
        try:
            # Construir parámetros de conexión
            conn_params = {
                'host': self.db_config['host'],
                'port': self.db_config['port'],
                'database': self.db_config['name'],
                'user': self.db_config['user']
            }
            
            # Solo agregar password si no está vacío
            if self.db_config.get('password') and self.db_config['password'].strip():
                conn_params['password'] = self.db_config['password']
            
            self.conn = psycopg2.connect(**conn_params)
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            logger.info(f"✅ Conectado a PostgreSQL: {self.db_config['name']}@{self.db_config['host']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando a BD: {e}")
            return False
    
    def desconectar(self):
        """Cierra la conexión con la base de datos"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Desconectado de la base de datos")
    
    def verificar_esquema(self) -> bool:
        """
        Verifica que el esquema de BD tenga los campos necesarios
        
        Returns:
            True si el esquema es válido
        """
        try:
            # Verificar que la tabla existe
            self.cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'licitaciones'
                ORDER BY ordinal_position
            """)
            
            columnas = self.cursor.fetchall()
            
            if not columnas:
                logger.error("❌ La tabla 'licitaciones' no existe")
                return False
            
            # Verificar campos requeridos
            campos_requeridos = ['entidad_federativa', 'municipio', 'datos_especificos']
            columnas_dict = {col['column_name']: col['data_type'] for col in columnas}
            
            faltantes = []
            for campo in campos_requeridos:
                if campo not in columnas_dict:
                    faltantes.append(campo)
            
            if faltantes:
                logger.error(f"❌ Faltan campos en la tabla: {', '.join(faltantes)}")
                logger.info("Ejecute las migraciones necesarias para actualizar el esquema")
                return False
            
            # Verificar tipo de datos_especificos
            if columnas_dict.get('datos_especificos') != 'jsonb':
                logger.warning(f"⚠️ El campo 'datos_especificos' no es JSONB, es {columnas_dict.get('datos_especificos')}")
            
            logger.info("✅ Esquema de BD verificado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error verificando esquema: {e}")
            return False
    
    def cargar_archivo_json(self, archivo_json: str) -> Dict[str, int]:
        """
        Carga un archivo JSON mejorado a la base de datos
        
        Args:
            archivo_json: Ruta al archivo JSON
        
        Returns:
            Diccionario con estadísticas de carga
        """
        stats = {
            'total': 0,
            'insertadas': 0,
            'actualizadas': 0,
            'duplicadas': 0,
            'errores': 0
        }
        
        try:
            with open(archivo_json, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            
            licitaciones = datos.get('licitaciones', [])
            stats['total'] = len(licitaciones)
            
            logger.info(f"📄 Procesando {archivo_json}: {stats['total']} licitaciones")
            
            for lic in licitaciones:
                resultado = self.insertar_licitacion(lic)
                if resultado == 'insertada':
                    stats['insertadas'] += 1
                elif resultado == 'actualizada':
                    stats['actualizadas'] += 1
                elif resultado == 'duplicada':
                    stats['duplicadas'] += 1
                else:
                    stats['errores'] += 1
            
            # Hacer commit después de cada archivo
            self.conn.commit()
            
            logger.info(f"   ✅ Insertadas: {stats['insertadas']}, "
                       f"Actualizadas: {stats['actualizadas']}, "
                       f"Duplicadas: {stats['duplicadas']}, "
                       f"Errores: {stats['errores']}")
            
        except Exception as e:
            logger.error(f"Error cargando {archivo_json}: {e}")
            self.conn.rollback()
            stats['errores'] = stats['total']
        
        return stats
    
    def insertar_licitacion(self, licitacion: Dict[str, Any]) -> str:
        """
        Inserta o actualiza una licitación en la BD
        
        Args:
            licitacion: Diccionario con datos de la licitación
        
        Returns:
            Estado de la operación: 'insertada', 'actualizada', 'duplicada', 'error'
        """
        try:
            # Mapear campos del JSON mejorado a campos de BD
            datos_bd = self._mapear_campos(licitacion)
            
            # Generar hash para deduplicación
            hash_str = f"{datos_bd['numero_procedimiento']}_{datos_bd['entidad_compradora']}_{datos_bd['fuente']}"
            datos_bd['hash_contenido'] = hashlib.sha256(hash_str.encode()).hexdigest()
            
            # Intentar insertar
            sql_insert = """
                INSERT INTO licitaciones (
                    numero_procedimiento, titulo, descripcion, entidad_compradora,
                    unidad_compradora, tipo_procedimiento, tipo_contratacion, estado,
                    fecha_publicacion, fecha_apertura, fecha_fallo, fecha_junta_aclaraciones,
                    monto_estimado, moneda, proveedor_ganador, caracter, uuid_procedimiento,
                    fuente, url_original, hash_contenido, datos_originales,
                    entidad_federativa, municipio, datos_especificos
                ) VALUES (
                    %(numero_procedimiento)s, %(titulo)s, %(descripcion)s, %(entidad_compradora)s,
                    %(unidad_compradora)s, %(tipo_procedimiento)s, %(tipo_contratacion)s, %(estado)s,
                    %(fecha_publicacion)s, %(fecha_apertura)s, %(fecha_fallo)s, %(fecha_junta_aclaraciones)s,
                    %(monto_estimado)s, %(moneda)s, %(proveedor_ganador)s, %(caracter)s, %(uuid_procedimiento)s,
                    %(fuente)s, %(url_original)s, %(hash_contenido)s, %(datos_originales)s,
                    %(entidad_federativa)s, %(municipio)s, %(datos_especificos)s
                )
                ON CONFLICT (hash_contenido) 
                DO UPDATE SET
                    entidad_federativa = EXCLUDED.entidad_federativa,
                    municipio = EXCLUDED.municipio,
                    datos_especificos = EXCLUDED.datos_especificos,
                    fecha_publicacion = EXCLUDED.fecha_publicacion,
                    fecha_apertura = EXCLUDED.fecha_apertura,
                    fecha_fallo = EXCLUDED.fecha_fallo,
                    fecha_junta_aclaraciones = EXCLUDED.fecha_junta_aclaraciones
                RETURNING id, 
                    CASE 
                        WHEN xmax = 0 THEN 'insertada'
                        ELSE 'actualizada'
                    END as operacion;
            """
            
            self.cursor.execute(sql_insert, datos_bd)
            resultado = self.cursor.fetchone()
            
            if resultado:
                return resultado['operacion']
            else:
                return 'duplicada'
            
        except Exception as e:
            logger.error(f"Error insertando licitación: {e}")
            logger.debug(f"Datos: {licitacion.get('numero_licitacion', 'SIN NUMERO')}")
            return 'error'
    
    def _mapear_campos(self, licitacion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapea campos del JSON mejorado a campos de la BD
        
        Args:
            licitacion: Datos de la licitación del JSON
        
        Returns:
            Diccionario con campos mapeados para BD
        """
        # Mapeo básico
        datos_bd = {
            'numero_procedimiento': licitacion.get('numero_licitacion_completo') or 
                                   licitacion.get('numero_licitacion', ''),
            'titulo': licitacion.get('titulo', '')[:500],
            'descripcion': licitacion.get('descripcion', ''),
            'entidad_compradora': licitacion.get('dependencia', 'No especificada'),
            'unidad_compradora': licitacion.get('subdependencia'),
            'tipo_procedimiento': licitacion.get('tipo_procedimiento', 'Licitación Pública'),
            'tipo_contratacion': licitacion.get('tipo_contratacion', 'No especificado'),
            'estado': 'Publicada',  # Estado por defecto para DOF
            'caracter': licitacion.get('caracter_procedimiento', 'Nacional'),
            'fuente': 'DOF',
            'moneda': 'MXN',
            
            # Campos geográficos
            'entidad_federativa': licitacion.get('entidad_federativa'),
            'municipio': licitacion.get('municipio'),
            
            # Campos opcionales
            'proveedor_ganador': None,
            'uuid_procedimiento': None,
            'url_original': None,
            'monto_estimado': None
        }
        
        # Procesar fechas (convertir de formato ISO si es necesario)
        fecha_campos = {
            'fecha_publicacion': 'fecha_publicacion',
            'fecha_apertura': 'fecha_presentacion_apertura',
            'fecha_fallo': 'fecha_fallo',
            'fecha_junta_aclaraciones': 'fecha_junta_aclaraciones'
        }
        
        for campo_bd, campo_json in fecha_campos.items():
            fecha_valor = licitacion.get(campo_json)
            if fecha_valor:
                # Si tiene hora, tomar solo la fecha
                if ' ' in str(fecha_valor):
                    fecha_valor = str(fecha_valor).split(' ')[0]
                datos_bd[campo_bd] = fecha_valor
            else:
                datos_bd[campo_bd] = None
        
        # Preparar datos_originales
        datos_originales = {
            'fecha_ejemplar': licitacion.get('fecha_ejemplar'),
            'edicion_ejemplar': licitacion.get('edicion_ejemplar'),
            'archivo_origen': licitacion.get('archivo_origen'),
            'pagina': licitacion.get('pagina'),
            'referencia': licitacion.get('referencia'),
            'reduccion_plazos': licitacion.get('reduccion_plazos'),
            'autoridad_reduccion': licitacion.get('autoridad_reduccion'),
            'fecha_visita_instalaciones': licitacion.get('fecha_visita_instalaciones'),
            'raw_text': licitacion.get('raw_text', '')[:1000]
        }
        
        datos_bd['datos_originales'] = json.dumps(datos_originales, ensure_ascii=False)
        
        # Preparar datos_especificos
        datos_especificos = {
            'tipo_contratacion_detectado': licitacion.get('tipo_contratacion'),
            'confianza_extraccion': licitacion.get('confianza_extraccion', 0),
            'campos_extraidos': licitacion.get('campos_extraidos', 0),
            'volumen_obra': licitacion.get('volumen_obra'),
            'cantidad': licitacion.get('cantidad'),
            'unidad_medida': licitacion.get('unidad_medida'),
            'especificaciones_tecnicas': licitacion.get('especificaciones_tecnicas'),
            'localidad': licitacion.get('localidad'),
            'direccion_completa': licitacion.get('direccion_completa'),
            'lugar_eventos': licitacion.get('lugar_eventos'),
            'observaciones': licitacion.get('observaciones'),
            'procesado_parser_mejorado': True,
            'fecha_procesamiento': licitacion.get('fecha_procesamiento')
        }
        
        datos_bd['datos_especificos'] = json.dumps(datos_especificos, ensure_ascii=False)
        
        return datos_bd
    
    def procesar_directorio(self, directorio: str, patron: str = "*_mejorado.json") -> bool:
        """
        Procesa todos los archivos JSON mejorados en un directorio
        
        Args:
            directorio: Directorio con archivos JSON
            patron: Patrón de archivos a buscar
        
        Returns:
            True si el proceso fue exitoso
        """
        # Buscar archivos
        patron_busqueda = os.path.join(directorio, patron)
        archivos = glob.glob(patron_busqueda)
        
        if not archivos:
            logger.warning(f"No se encontraron archivos con patrón {patron} en {directorio}")
            return False
        
        logger.info(f"\n📁 Encontrados {len(archivos)} archivos para cargar")
        
        # Procesar cada archivo
        for i, archivo in enumerate(archivos, 1):
            logger.info(f"\n[{i}/{len(archivos)}] Procesando...")
            stats = self.cargar_archivo_json(archivo)
            
            # Actualizar estadísticas globales
            self.estadisticas['archivos_procesados'] += 1
            self.estadisticas['licitaciones_insertadas'] += stats['insertadas']
            self.estadisticas['licitaciones_actualizadas'] += stats['actualizadas']
            self.estadisticas['licitaciones_duplicadas'] += stats['duplicadas']
            self.estadisticas['errores'] += stats['errores']
        
        return True
    
    def generar_reporte_carga(self):
        """Genera y muestra un reporte de la carga a BD"""
        print("\n" + "="*80)
        print("REPORTE DE CARGA A BASE DE DATOS")
        print("="*80)
        
        print(f"\n📊 ESTADÍSTICAS DE CARGA:")
        print(f"   • Archivos procesados: {self.estadisticas['archivos_procesados']}")
        print(f"   • Licitaciones insertadas: {self.estadisticas['licitaciones_insertadas']}")
        print(f"   • Licitaciones actualizadas: {self.estadisticas['licitaciones_actualizadas']}")
        print(f"   • Licitaciones duplicadas: {self.estadisticas['licitaciones_duplicadas']}")
        print(f"   • Errores: {self.estadisticas['errores']}")
        
        total_procesadas = (self.estadisticas['licitaciones_insertadas'] + 
                          self.estadisticas['licitaciones_actualizadas'] + 
                          self.estadisticas['licitaciones_duplicadas'])
        
        if total_procesadas > 0:
            tasa_exito = ((self.estadisticas['licitaciones_insertadas'] + 
                         self.estadisticas['licitaciones_actualizadas']) / 
                         total_procesadas * 100)
            print(f"\n📈 TASA DE ÉXITO: {tasa_exito:.1f}%")
        
        # Consultar estadísticas de la BD
        try:
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT entidad_federativa) as entidades,
                    COUNT(DISTINCT municipio) as municipios,
                    COUNT(CASE WHEN entidad_federativa IS NOT NULL THEN 1 END) as con_entidad,
                    COUNT(CASE WHEN municipio IS NOT NULL THEN 1 END) as con_municipio
                FROM licitaciones
                WHERE fuente = 'DOF'
            """)
            
            stats_bd = self.cursor.fetchone()
            
            print(f"\n🗄️ ESTADO ACTUAL EN BD (fuente DOF):")
            print(f"   • Total licitaciones: {stats_bd['total']}")
            print(f"   • Entidades federativas: {stats_bd['entidades']}")
            print(f"   • Municipios únicos: {stats_bd['municipios']}")
            print(f"   • Con entidad federativa: {stats_bd['con_entidad']} ({stats_bd['con_entidad']/stats_bd['total']*100:.1f}%)")
            print(f"   • Con municipio: {stats_bd['con_municipio']} ({stats_bd['con_municipio']/stats_bd['total']*100:.1f}%)")
            
            # Top 5 entidades
            self.cursor.execute("""
                SELECT entidad_federativa, COUNT(*) as cantidad
                FROM licitaciones
                WHERE fuente = 'DOF' AND entidad_federativa IS NOT NULL
                GROUP BY entidad_federativa
                ORDER BY cantidad DESC
                LIMIT 5
            """)
            
            top_entidades = self.cursor.fetchall()
            
            if top_entidades:
                print(f"\n🏆 TOP 5 ENTIDADES FEDERATIVAS:")
                for entidad in top_entidades:
                    print(f"   • {entidad['entidad_federativa']}: {entidad['cantidad']} licitaciones")
        
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de BD: {e}")
        
        print("\n" + "="*80)


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Cargador de datos DOF mejorados a PostgreSQL'
    )
    parser.add_argument(
        'directorio',
        nargs='?',
        default='.',
        help='Directorio con archivos JSON mejorados (por defecto: directorio actual)'
    )
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Archivo de configuración (por defecto: config.yaml)'
    )
    parser.add_argument(
        '-p', '--patron',
        default='*_mejorado.json',
        help='Patrón de archivos a cargar (por defecto: *_mejorado.json)'
    )
    parser.add_argument(
        '--verificar',
        action='store_true',
        help='Solo verificar el esquema de BD sin cargar datos'
    )
    
    args = parser.parse_args()
    
    # Crear cargador
    cargador = CargadorDOFBD(config_path=args.config)
    
    # Conectar a BD
    if not cargador.conectar():
        print("❌ No se pudo conectar a la base de datos")
        sys.exit(1)
    
    try:
        # Verificar esquema
        if not cargador.verificar_esquema():
            print("❌ El esquema de BD no es válido")
            print("   Ejecute las migraciones necesarias antes de cargar datos")
            sys.exit(1)
        
        if args.verificar:
            print("✅ Esquema de BD verificado correctamente")
            sys.exit(0)
        
        # Validar directorio
        if not os.path.exists(args.directorio):
            print(f"❌ El directorio {args.directorio} no existe")
            sys.exit(1)
        
        print("\n🚀 Iniciando carga de datos DOF a PostgreSQL...")
        print("="*80)
        print(f"📂 Directorio: {args.directorio}")
        print(f"🔍 Patrón: {args.patron}")
        print(f"🗄️ Base de datos: {cargador.db_config['name']}@{cargador.db_config['host']}")
        print("="*80)
        
        # Procesar directorio
        exito = cargador.procesar_directorio(args.directorio, args.patron)
        
        if exito:
            # Generar reporte
            cargador.generar_reporte_carga()
            print("\n✅ Carga completada exitosamente")
        else:
            print("\n⚠️ No se encontraron archivos para cargar")
        
    finally:
        cargador.desconectar()
    
    return 0 if exito else 1


if __name__ == "__main__":
    sys.exit(main())
