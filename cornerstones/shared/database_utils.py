#!/usr/bin/env python3
"""
Database Utils - Cornerstone Shared
Utilidades compartidas para conexión a base de datos
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestor de conexiones a la base de datos PostgreSQL"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.connection = None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Carga configuración desde archivo YAML"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"No se pudo cargar config.yaml: {e}")
            
        # Configuración por defecto
        return {
            'database': {
                'host': os.getenv('DATABASE_HOST', 'localhost'),
                'port': int(os.getenv('DATABASE_PORT', 5432)),
                'name': os.getenv('DATABASE_NAME', 'paloma_licitera'),
                'user': os.getenv('DATABASE_USER', 'postgres'),
                'password': os.getenv('DATABASE_PASSWORD', '')
            }
        }
        
    def connect(self) -> bool:
        """Establece conexión a la base de datos"""
        try:
            db_config = self.config['database']
            
            self.connection = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['name'],
                user=db_config['user'],
                password=db_config['password']
            )
            
            logger.info("✅ Conexión a PostgreSQL establecida")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            return False
            
    def disconnect(self):
        """Cierra la conexión a la base de datos"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("📊 Conexión a PostgreSQL cerrada")
            
    def execute_query(self, query: str, params: tuple = None) -> Optional[List[Dict[str, Any]]]:
        """Ejecuta una consulta SELECT"""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando consulta: {e}")
            return None
            
    def execute_insert(self, query: str, params: tuple = None) -> bool:
        """Ejecuta una consulta INSERT/UPDATE/DELETE"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                return True
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando insert: {e}")
            self.connection.rollback()
            return False
            
    def insert_licitacion(self, licitacion: Dict[str, Any]) -> bool:
        """Inserta una licitación en la base de datos"""
        try:
            # Generar hash único para evitar duplicados
            import hashlib
            content_hash = hashlib.md5(
                f"{licitacion.get('numero_procedimiento', '')}"
                f"{licitacion.get('entidad_compradora', '')}"
                f"{licitacion.get('fuente', '')}"
                .encode('utf-8')
            ).hexdigest()
            
            query = """
                INSERT INTO licitaciones (
                    numero_procedimiento, uuid_procedimiento, hash_contenido,
                    titulo, descripcion,
                    entidad_compradora, unidad_compradora,
                    tipo_procedimiento, tipo_contratacion, estado, caracter,
                    fecha_publicacion, fecha_apertura, fecha_fallo, fecha_junta_aclaraciones,
                    monto_estimado, moneda,
                    proveedor_ganador,
                    fuente, url_original, fecha_captura, datos_originales,
                    entidad_federativa, municipio, datos_especificos
                ) VALUES (
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    %s,
                    %s, %s, CURRENT_TIMESTAMP, %s,
                    %s, %s, %s
                )
                ON CONFLICT (hash_contenido) DO NOTHING
            """
            
            params = (
                licitacion.get('numero_procedimiento', ''),
                licitacion.get('uuid_procedimiento'),
                content_hash,
                licitacion.get('titulo', ''),
                licitacion.get('descripcion', ''),
                licitacion.get('entidad_compradora', ''),
                licitacion.get('unidad_compradora', ''),
                licitacion.get('tipo_procedimiento', ''),
                licitacion.get('tipo_contratacion', ''),
                licitacion.get('estado', ''),
                licitacion.get('caracter', ''),
                licitacion.get('fecha_publicacion'),
                licitacion.get('fecha_apertura'),
                licitacion.get('fecha_fallo'),
                licitacion.get('fecha_junta_aclaraciones'),
                licitacion.get('monto_estimado', 0),
                licitacion.get('moneda', 'MXN'),
                licitacion.get('proveedor_ganador', ''),
                licitacion.get('fuente', ''),
                licitacion.get('url_original', ''),
                licitacion.get('datos_originales', {}),
                licitacion.get('entidad_federativa', ''),
                licitacion.get('municipio', ''),
                licitacion.get('datos_especificos', {})
            )
            
            return self.execute_insert(query, params)
            
        except Exception as e:
            logger.error(f"❌ Error insertando licitación: {e}")
            return False
            
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la base de datos"""
        try:
            stats = {}
            
            # Total de licitaciones
            result = self.execute_query("SELECT COUNT(*) as total FROM licitaciones")
            stats['total_licitaciones'] = result[0]['total'] if result else 0
            
            # Por fuente
            result = self.execute_query("""
                SELECT fuente, COUNT(*) as cantidad 
                FROM licitaciones 
                GROUP BY fuente 
                ORDER BY cantidad DESC
            """)
            stats['por_fuente'] = {row['fuente']: row['cantidad'] for row in result} if result else {}
            
            # Por entidad federativa
            result = self.execute_query("""
                SELECT entidad_federativa, COUNT(*) as cantidad 
                FROM licitaciones 
                WHERE entidad_federativa IS NOT NULL 
                GROUP BY entidad_federativa 
                ORDER BY cantidad DESC 
                LIMIT 10
            """)
            stats['por_entidad'] = {row['entidad_federativa']: row['cantidad'] for row in result} if result else {}
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {}

# Instancia global del gestor de base de datos
db_manager = DatabaseManager()

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    if not db_manager.connection:
        db_manager.connect()
    return db_manager

def insert_licitaciones_batch(licitaciones: List[Dict[str, Any]]) -> Dict[str, int]:
    """Inserta un lote de licitaciones"""
    db = get_db_connection()
    
    if not db.connection:
        logger.error("❌ No hay conexión a la base de datos")
        return {'insertadas': 0, 'errores': len(licitaciones)}
        
    insertadas = 0
    errores = 0
    
    for licitacion in licitaciones:
        if db.insert_licitacion(licitacion):
            insertadas += 1
        else:
            errores += 1
            
    return {'insertadas': insertadas, 'errores': errores}
