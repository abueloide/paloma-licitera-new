#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestión de Base de Datos para Paloma Licitera
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
    """Gestor de base de datos PostgreSQL."""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        self.db_config = config['database']
        
    @contextmanager
    def get_connection(self):
        """Context manager para conexiones a BD."""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['name'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                cursor_factory=psycopg2.extras.RealDictCursor
            )
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
        """Crear esquema de base de datos."""
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
            monto_estimado DECIMAL(15,2),
            moneda VARCHAR(10),
            proveedor_ganador TEXT,
            fuente VARCHAR(50) NOT NULL,
            url_original TEXT,
            fecha_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            hash_contenido VARCHAR(64) UNIQUE,
            datos_originales JSONB,
            CONSTRAINT uk_licitacion UNIQUE(numero_procedimiento, entidad_compradora, fuente)
        );
        
        CREATE INDEX IF NOT EXISTS idx_numero_procedimiento ON licitaciones(numero_procedimiento);
        CREATE INDEX IF NOT EXISTS idx_entidad ON licitaciones(entidad_compradora);
        CREATE INDEX IF NOT EXISTS idx_fecha_pub ON licitaciones(fecha_publicacion);
        CREATE INDEX IF NOT EXISTS idx_fuente ON licitaciones(fuente);
        CREATE INDEX IF NOT EXISTS idx_estado ON licitaciones(estado);
        """
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(schema)
            logger.info("Esquema de BD creado/verificado")
    
    def insertar_licitacion(self, licitacion: Dict[str, Any]) -> bool:
        """Insertar una licitación en la BD."""
        # Generar hash para deduplicación
        hash_str = f"{licitacion['numero_procedimiento']}_{licitacion['entidad_compradora']}_{licitacion['fuente']}"
        licitacion['hash_contenido'] = hashlib.sha256(hash_str.encode()).hexdigest()
        
        # Serializar datos originales
        if 'datos_originales' in licitacion:
            licitacion['datos_originales'] = json.dumps(licitacion['datos_originales'])
        
        sql = """
        INSERT INTO licitaciones (
            numero_procedimiento, titulo, descripcion, entidad_compradora,
            unidad_compradora, tipo_procedimiento, tipo_contratacion, estado,
            fecha_publicacion, fecha_apertura, fecha_fallo, monto_estimado,
            moneda, proveedor_ganador, fuente, url_original, hash_contenido,
            datos_originales
        ) VALUES (
            %(numero_procedimiento)s, %(titulo)s, %(descripcion)s, %(entidad_compradora)s,
            %(unidad_compradora)s, %(tipo_procedimiento)s, %(tipo_contratacion)s, %(estado)s,
            %(fecha_publicacion)s, %(fecha_apertura)s, %(fecha_fallo)s, %(monto_estimado)s,
            %(moneda)s, %(proveedor_ganador)s, %(fuente)s, %(url_original)s, %(hash_contenido)s,
            %(datos_originales)s
        )
        ON CONFLICT (hash_contenido) DO NOTHING
        RETURNING id;
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, licitacion)
                result = cursor.fetchone()
                if result:
                    logger.debug(f"Licitación insertada: {licitacion['numero_procedimiento']}")
                    return True
                else:
                    logger.debug(f"Licitación duplicada: {licitacion['numero_procedimiento']}")
                    return False
        except Exception as e:
            logger.error(f"Error insertando licitación: {e}")
            return False
    
    def obtener_licitaciones(self, filtros: Dict = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Obtener licitaciones con filtros opcionales."""
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
        """Obtener estadísticas de la BD."""
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
            
            return {
                'total': total,
                'por_fuente': por_fuente,
                'por_estado': por_estado,
                'ultima_actualizacion': datetime.now().isoformat()
            }

if __name__ == "__main__":
    import sys
    
    db = Database()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        db.setup()
        print("✅ Base de datos configurada")
    else:
        stats = db.obtener_estadisticas()
        print(f"📊 Estadísticas: {stats}")
