#!/usr/bin/env python3
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DatabaseQueries:
    def __init__(self, config: dict):
        self.config = config['database']
        
    def get_connection(self):
        return psycopg2.connect(
            host=self.config['host'],
            port=self.config['port'],
            database=self.config['name'],
            user=self.config['user'],
            password=self.config['password']
        )
    
    def get_last_comprasmx_expediente(self) -> Optional[str]:
        """Obtener el último cod_expediente de ComprasMX"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT cod_expediente 
                    FROM licitaciones 
                    WHERE fuente = 'comprasmx' 
                    AND cod_expediente IS NOT NULL 
                    ORDER BY fecha_captura DESC 
                    LIMIT 1
                """)
                result = cur.fetchone()
                return result[0] if result else None
    
    def get_last_dof_date(self) -> Optional[datetime]:
        """Obtener la última fecha de publicación DOF procesada"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT MAX(fecha_publicacion) 
                    FROM licitaciones 
                    WHERE fuente = 'dof'
                """)
                result = cur.fetchone()
                return result[0] if result and result[0] else None
    
    def get_last_tianguis_uuid(self) -> Optional[str]:
        """Obtener el último UUID de Tianguis Digital"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT uuid_procedimiento 
                    FROM licitaciones 
                    WHERE fuente = 'tianguis' 
                    AND uuid_procedimiento IS NOT NULL 
                    ORDER BY fecha_captura DESC 
                    LIMIT 1
                """)
                result = cur.fetchone()
                return result[0] if result else None
    
    def check_dof_processed_today(self) -> bool:
        """Verificar si ya procesamos DOF hoy"""
        today = datetime.now().date()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM licitaciones 
                    WHERE fuente = 'dof' 
                    AND DATE(fecha_captura) = %s
                """, (today,))
                result = cur.fetchone()
                return result[0] > 0 if result else False
    
    def get_last_processing_date(self, fuente: str) -> Optional[datetime]:
        """Obtener la última fecha de procesamiento por fuente"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT MAX(fecha_captura) 
                    FROM licitaciones 
                    WHERE fuente = %s
                """, (fuente,))
                result = cur.fetchone()
                return result[0] if result and result[0] else None
    
    def count_records_by_source(self) -> Dict[str, int]:
        """Contar registros por fuente"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT fuente, COUNT(*) 
                    FROM licitaciones 
                    GROUP BY fuente
                """)
                results = cur.fetchall()
                return {fuente: count for fuente, count in results}
    
    def get_records_added_since(self, fuente: str, since: datetime) -> int:
        """Contar registros añadidos desde una fecha"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM licitaciones 
                    WHERE fuente = %s 
                    AND fecha_captura >= %s
                """, (fuente, since))
                result = cur.fetchone()
                return result[0] if result else 0