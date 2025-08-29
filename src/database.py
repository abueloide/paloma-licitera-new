#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestión de Base de Datos para Paloma Licitera
ACTUALIZADO: Manejo completo de detalles de ComprasMX extraídos por scraper v2
CORREGIDO: Usar UUID real como hash_contenido, no SHA256 artificial
"""

import psycopg2
import psycopg2.extras
import yaml
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib
import json

logger = logging.getLogger(__name__)

class Database:
    """Gestor de base de datos PostgreSQL con modelo híbrido y detalles completos."""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        self.db_config = config['database']
        
    @contextmanager
    def get_connection(self):
        """Context manager para conexiones a BD."""
        conn = None
        try:
            # Construir parámetros de conexión, omitiendo password si está vacío
            conn_params = {
                'host': self.db_config['host'],
                'port': self.db_config['port'],
                'database': self.db_config['name'],
                'user': self.db_config['user'],
                'cursor_factory': psycopg2.extras.RealDictCursor
            }
            
            # Solo agregar password si no está vacío
            if self.db_config.get('password') and self.db_config['password'].strip():
                conn_params['password'] = self.db_config['password']
            
            conn = psycopg2.connect(**conn_params)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error en BD: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def setup(self):
        """Crear esquema de base de datos con modelo híbrido."""
        schema = """
        CREATE TABLE IF NOT EXISTS licitaciones (
            id SERIAL PRIMARY KEY,
            numero_procedimiento VARCHAR(255) NOT NULL,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            entidad_compradora VARCHAR(500),
            unidad_compradora VARCHAR(500),
            tipo_procedimiento VARCHAR(50),
            tipo_contratacion VARCHAR(50),
            estado VARCHAR(50),
            fecha_publicacion DATE,
            fecha_apertura DATE,
            fecha_fallo DATE,
            fecha_junta_aclaraciones DATE,
            monto_estimado DECIMAL(15,2),
            moneda VARCHAR(10) DEFAULT 'MXN',
            proveedor_ganador TEXT,
            caracter VARCHAR(50),
            uuid_procedimiento VARCHAR(255),
            fuente VARCHAR(50) NOT NULL,
            url_original TEXT,
            fecha_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            hash_contenido VARCHAR(64) UNIQUE,
            datos_originales JSONB,
            -- Nuevos campos para modelo híbrido
            entidad_federativa VARCHAR(100),
            municipio VARCHAR(100),
            datos_especificos JSONB,
            CONSTRAINT uk_licitacion UNIQUE(numero_procedimiento, entidad_compradora, fuente)
        );
        
        -- Índices existentes
        CREATE INDEX IF NOT EXISTS idx_numero_procedimiento ON licitaciones(numero_procedimiento);
        CREATE INDEX IF NOT EXISTS idx_entidad ON licitaciones(entidad_compradora);
        CREATE INDEX IF NOT EXISTS idx_fecha_pub ON licitaciones(fecha_publicacion);
        CREATE INDEX IF NOT EXISTS idx_fuente ON licitaciones(fuente);
        CREATE INDEX IF NOT EXISTS idx_estado ON licitaciones(estado);
        CREATE INDEX IF NOT EXISTS idx_tipo_procedimiento ON licitaciones(tipo_procedimiento);
        CREATE INDEX IF NOT EXISTS idx_tipo_contratacion ON licitaciones(tipo_contratacion);
        CREATE INDEX IF NOT EXISTS idx_uuid ON licitaciones(uuid_procedimiento);
        
        -- Nuevos índices para modelo híbrido
        CREATE INDEX IF NOT EXISTS idx_entidad_federativa ON licitaciones(entidad_federativa);
        CREATE INDEX IF NOT EXISTS idx_municipio ON licitaciones(municipio);
        CREATE INDEX IF NOT EXISTS idx_entidad_municipio ON licitaciones(entidad_federativa, municipio);
        CREATE INDEX IF NOT EXISTS idx_datos_especificos_gin ON licitaciones USING GIN(datos_especificos);
        """
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(schema)
            logger.info("Esquema de BD creado/verificado con modelo híbrido")
    
    def insertar_licitacion(self, licitacion: Dict[str, Any]) -> bool:
        """
        CORREGIDO: Usar UUID real como hash_contenido para ComprasMX.
        """
        try:
            # Validaciones básicas
            if not licitacion.get('numero_procedimiento'):
                logger.warning(f"Licitación sin numero_procedimiento, saltando: {licitacion}")
                return False
            
            if not licitacion.get('titulo'):
                licitacion['titulo'] = licitacion.get('descripcion', 'Sin título')[:500]
            
            if not licitacion.get('entidad_compradora'):
                licitacion['entidad_compradora'] = 'No especificada'
            
            if not licitacion.get('fuente'):
                logger.error(f"Licitación sin fuente, no se puede insertar: {licitacion.get('numero_procedimiento')}")
                return False
            
            # CORRECCIÓN CRÍTICA: Normalizar fuente
            if licitacion['fuente'] == 'COMPRASMX':
                licitacion['fuente'] = 'ComprasMX'
            
            # Procesar campos geográficos según la fuente
            self._procesar_campos_geograficos(licitacion)
            
            # NUEVO: Procesar detalles específicos completos de ComprasMX
            self._procesar_datos_especificos_completos(licitacion)
            
            # CORRECCIÓN PRINCIPAL: Usar UUID real como hash_contenido
            fuente = licitacion.get('fuente', '')
            uuid_procedimiento = licitacion.get('uuid_procedimiento')
            
            if fuente == 'ComprasMX' and uuid_procedimiento:
                # Para ComprasMX: usar el UUID real directamente
                licitacion['hash_contenido'] = uuid_procedimiento
                logger.debug(f"Usando UUID real como hash: {uuid_procedimiento}")
            else:
                # Para otras fuentes: generar hash solo si no hay UUID
                hash_str = f"{licitacion['numero_procedimiento']}_{licitacion['entidad_compradora']}_{licitacion['fuente']}"
                licitacion['hash_contenido'] = hashlib.sha256(hash_str.encode()).hexdigest()
                logger.debug(f"Generando hash artificial para {fuente}: {hash_str}")
            
            # Serializar datos originales si existen
            if 'datos_originales' in licitacion and licitacion['datos_originales'] is not None:
                if isinstance(licitacion['datos_originales'], (dict, list)):
                    licitacion['datos_originales'] = json.dumps(licitacion['datos_originales'])
            else:
                licitacion['datos_originales'] = None
            
            # Serializar datos específicos si existen
            if 'datos_especificos' in licitacion and licitacion['datos_especificos'] is not None:
                if isinstance(licitacion['datos_especificos'], (dict, list)):
                    licitacion['datos_especificos'] = json.dumps(licitacion['datos_especificos'])
            else:
                licitacion['datos_especificos'] = None
            
            # Asegurar que los campos opcionales existen (con None si no están)
            campos_opcionales = [
                'descripcion', 'unidad_compradora', 'tipo_procedimiento', 
                'tipo_contratacion', 'estado', 'fecha_publicacion', 
                'fecha_apertura', 'fecha_fallo', 'fecha_junta_aclaraciones',
                'monto_estimado', 'moneda', 'proveedor_ganador', 
                'caracter', 'uuid_procedimiento', 'url_original',
                'entidad_federativa', 'municipio'
            ]
            
            for campo in campos_opcionales:
                if campo not in licitacion:
                    licitacion[campo] = None
            
            # Si moneda no está especificada, usar MXN por defecto
            if not licitacion.get('moneda'):
                licitacion['moneda'] = 'MXN'
            
            # SQL para inserción
            sql = """
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
            ON CONFLICT (hash_contenido) DO NOTHING
            RETURNING id;
            """
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, licitacion)
                result = cursor.fetchone()
                if result:
                    logger.debug(f"Licitación insertada: {licitacion['numero_procedimiento']} (ID: {result['id']})")
                    return True
                else:
                    logger.debug(f"Licitación duplicada (ya existe): {licitacion['numero_procedimiento']}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error insertando licitación {licitacion.get('numero_procedimiento', 'UNKNOWN')}: {e}")
            logger.debug(f"Datos que causaron el error: {licitacion}")
            return False
    
    def _procesar_campos_geograficos(self, licitacion: Dict[str, Any]):
        """Procesar campos geográficos según la fuente."""
        fuente = licitacion.get('fuente', '')
        datos_orig = licitacion.get('datos_originales', {})
        
        if isinstance(datos_orig, str):
            try:
                datos_orig = json.loads(datos_orig)
            except:
                datos_orig = {}
        
        if fuente == 'ComprasMX':
            # Buscar en datos específicos si existen
            datos_especificos = licitacion.get('datos_especificos', {})
            if isinstance(datos_especificos, str):
                try:
                    datos_especificos = json.loads(datos_especificos)
                except:
                    datos_especificos = {}
            
            # Buscar en detalle individual si existe
            detalle_individual = datos_especificos.get('detalle_individual', {})
            info_extraida = detalle_individual.get('informacion_extraida', {}) if detalle_individual else {}
            
            # Mapear entidad federativa
            entidad_fed = (
                info_extraida.get('entidad_federativa') or 
                datos_orig.get('entidad_federativa_contratacion') or
                datos_especificos.get('entidad_federativa')
            )
            if entidad_fed:
                licitacion['entidad_federativa'] = entidad_fed
            
            # Buscar municipio si existe
            municipio = (
                info_extraida.get('municipio') or
                datos_orig.get('municipio') or
                datos_especificos.get('municipio')
            )
            if municipio:
                licitacion['municipio'] = municipio
        
        elif fuente == 'DOF':
            # TODO: Usar el parser DOF para extraer ubicación
            pass
        
        elif fuente == 'Tianguis Digital':
            # Buscar información geográfica en OCDS
            if datos_orig.get('tender', {}).get('procuringEntity', {}).get('address'):
                address = datos_orig['tender']['procuringEntity']['address']
                if address.get('region'):
                    licitacion['entidad_federativa'] = address['region']
                if address.get('locality'):
                    licitacion['municipio'] = address['locality']
    
    def _procesar_datos_especificos_completos(self, licitacion: Dict[str, Any]):
        """
        NUEVO: Procesar datos específicos completos incluyendo detalles individuales de ComprasMX.
        """
        fuente = licitacion.get('fuente', '')
        datos_orig = licitacion.get('datos_originales', {})
        
        if isinstance(datos_orig, str):
            try:
                datos_orig = json.loads(datos_orig)
            except:
                datos_orig = {}
        
        # Obtener datos específicos existentes si ya fueron procesados
        datos_especificos = licitacion.get('datos_especificos', {})
        if isinstance(datos_especificos, str):
            try:
                datos_especificos = json.loads(datos_especificos)
            except:
                datos_especificos = {}
        
        if fuente == 'ComprasMX':
            # Datos básicos de ComprasMX
            datos_especificos.update({
                'tipo_procedimiento': datos_orig.get('tipo_procedimiento', licitacion.get('tipo_procedimiento')),
                'caracter': datos_orig.get('caracter', licitacion.get('caracter')),
                'forma_procedimiento': datos_orig.get('forma_procedimiento'),
                'medio_utilizado': datos_orig.get('medio_utilizado'),
                'codigo_contrato': datos_orig.get('codigo_contrato'),
                'plantilla_convenio': datos_orig.get('plantilla_convenio'),
                'fecha_inicio_contrato': datos_orig.get('fecha_inicio_contrato'),
                'fecha_fin_contrato': datos_orig.get('fecha_fin_contrato'),
                'convenio_modificatorio': datos_orig.get('convenio_modificatorio'),
                'ramo': datos_orig.get('ramo'),
                'clave_programa': datos_orig.get('clave_programa'),
                'aportacion_federal': datos_orig.get('aportacion_federal'),
                'fecha_celebracion': datos_orig.get('fecha_celebracion'),
                'contrato_marco': datos_orig.get('contrato_marco'),
                'compra_consolidada': datos_orig.get('compra_consolidada'),
                'plurianual': datos_orig.get('plurianual'),
                'clave_cartera_shcp': datos_orig.get('clave_cartera_shcp')
            })
            
            # NUEVO: Procesar detalles individuales si existen
            detalle_individual = datos_especificos.get('detalle_individual')
            if detalle_individual:
                logger.debug(f"Procesando detalle individual para {licitacion['numero_procedimiento']}")
                
                # Extraer información detallada
                info_extraida = detalle_individual.get('informacion_extraida', {})
                
                # Actualizar descripción con versión completa si está disponible
                if info_extraida.get('descripcion_completa'):
                    desc_actual = licitacion.get('descripcion', '')
                    desc_completa = info_extraida['descripcion_completa']
                    
                    # Usar la más larga y completa
                    if len(desc_completa) > len(desc_actual or ''):
                        licitacion['descripcion'] = desc_completa
                        logger.debug(f"Descripción enriquecida para {licitacion['numero_procedimiento']}")
                
                # Agregar información específica del detalle
                datos_especificos['detalle_individual'].update({
                    # Información de contacto
                    'email_unidad_compradora': info_extraida.get('email_unidad_compradora'),
                    'responsable_captura': info_extraida.get('responsable_captura'),
                    
                    # Información detallada del procedimiento
                    'descripcion_detallada': info_extraida.get('descripcion_detallada'),
                    'año_ejercicio': info_extraida.get('año_ejercicio'),
                    
                    # Cronograma detallado
                    'fechas_cronograma': info_extraida.get('fechas_cronograma', {}),
                    
                    # Información técnica
                    'partidas_especificas': info_extraida.get('partidas_especificas', []),
                    'requisitos_economicos': info_extraida.get('requisitos_economicos', []),
                    'documentos_anexos': info_extraida.get('documentos_anexos', []),
                    
                    # Datos adicionales específicos
                    'datos_especificos_detalle': info_extraida.get('datos_especificos', {}),
                    
                    # Metadata del procesamiento
                    'url_completa_hash': detalle_individual.get('url_completa_con_hash'),
                    'timestamp_procesamiento': detalle_individual.get('timestamp_procesamiento'),
                    'pagina_origen': detalle_individual.get('pagina_origen'),
                    'procesado_exitosamente': detalle_individual.get('procesado_exitosamente', False)
                })
                
                logger.debug(f"Detalle individual integrado para {licitacion['numero_procedimiento']}")
        
        elif fuente == 'DOF':
            datos_especificos.update({
                'titulo_original': licitacion.get('titulo'),
                'descripcion_original': licitacion.get('descripcion'),
                'fecha_ejemplar': datos_orig.get('fecha_ejemplar'),
                'seccion': datos_orig.get('seccion'),
                'organismo': datos_orig.get('organismo'),
                'notas': datos_orig.get('notas'),
                'procesado_parser': False
            })
        
        elif fuente == 'Tianguis Digital':
            datos_especificos.update({
                'ocds_data': datos_orig if datos_orig.get('ocid') else None,
                'classification': datos_orig.get('tender', {}).get('classification'),
                'procuring_entity': datos_orig.get('tender', {}).get('procuringEntity'),
                'items': datos_orig.get('tender', {}).get('items'),
                'documents': datos_orig.get('tender', {}).get('documents'),
                'milestones': datos_orig.get('tender', {}).get('milestones')
            })
        
        # Actualizar datos específicos en la licitación
        licitacion['datos_especificos'] = datos_especificos
    
    def obtener_licitaciones(self, filtros: Dict = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Obtener licitaciones con filtros opcionales incluyendo campos geográficos."""
        sql = "SELECT * FROM licitaciones WHERE 1=1"
        params = {}
        
        if filtros:
            if 'fuente' in filtros:
                sql += " AND fuente = %(fuente)s"
                params['fuente'] = filtros['fuente']
            if 'estado' in filtros:
                sql += " AND estado = %(estado)s"
                params['estado'] = filtros['estado']
            if 'entidad' in filtros:
                sql += " AND entidad_compradora ILIKE %(entidad)s"
                params['entidad'] = f"%{filtros['entidad']}%"
            if 'entidad_federativa' in filtros:
                sql += " AND entidad_federativa = %(entidad_federativa)s"
                params['entidad_federativa'] = filtros['entidad_federativa']
            if 'municipio' in filtros:
                sql += " AND municipio = %(municipio)s"
                params['municipio'] = filtros['municipio']
            if 'q' in filtros:
                sql += " AND (titulo ILIKE %(q)s OR descripcion ILIKE %(q)s)"
                params['q'] = f"%{filtros['q']}%"
        
        sql += " ORDER BY fecha_publicacion DESC LIMIT %(limit)s OFFSET %(offset)s"
        params['limit'] = limit
        params['offset'] = offset
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    def obtener_estadisticas(self) -> Dict:
        """Obtener estadísticas de la BD incluyendo datos geográficos."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total de licitaciones
            cursor.execute("SELECT COUNT(*) as total FROM licitaciones")
            total = cursor.fetchone()['total']
            
            # Por fuente
            cursor.execute("""
                SELECT fuente, COUNT(*) as cantidad 
                FROM licitaciones 
                GROUP BY fuente
            """)
            por_fuente = {row['fuente']: row['cantidad'] for row in cursor.fetchall()}
            
            # Por estado
            cursor.execute("""
                SELECT estado, COUNT(*) as cantidad 
                FROM licitaciones 
                WHERE estado IS NOT NULL
                GROUP BY estado
            """)
            por_estado = {row['estado']: row['cantidad'] for row in cursor.fetchall()}
            
            # Por entidad federativa
            cursor.execute("""
                SELECT entidad_federativa, COUNT(*) as cantidad 
                FROM licitaciones 
                WHERE entidad_federativa IS NOT NULL
                GROUP BY entidad_federativa
                ORDER BY cantidad DESC
                LIMIT 10
            """)
            por_entidad_federativa = {row['entidad_federativa']: row['cantidad'] for row in cursor.fetchall()}
            
            # Estadísticas de detalles de ComprasMX
            cursor.execute("""
                SELECT COUNT(*) as con_detalles
                FROM licitaciones 
                WHERE fuente = 'ComprasMX' 
                AND datos_especificos IS NOT NULL
                AND datos_especificos::text LIKE '%detalle_individual%'
            """)
            comprasmx_con_detalles = cursor.fetchone()['con_detalles']
            
            cursor.execute("""
                SELECT COUNT(*) as total_comprasmx
                FROM licitaciones 
                WHERE fuente = 'ComprasMX'
            """)
            total_comprasmx = cursor.fetchone()['total_comprasmx']
            
            return {
                'total': total,
                'por_fuente': por_fuente,
                'por_estado': por_estado,
                'por_entidad_federativa': por_entidad_federativa,
                'comprasmx_con_detalles': comprasmx_con_detalles,
                'comprasmx_total': total_comprasmx,
                'porcentaje_detalles_comprasmx': (comprasmx_con_detalles / total_comprasmx * 100) if total_comprasmx > 0 else 0,
                'ultima_actualizacion': datetime.now().isoformat()
            }

if __name__ == "__main__":
    import sys
    
    db = Database()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        db.setup()
        print("Base de datos configurada con modelo híbrido y soporte completo para detalles")
    else:
        stats = db.obtener_estadisticas()
        print(f"Estadísticas: {stats}")
