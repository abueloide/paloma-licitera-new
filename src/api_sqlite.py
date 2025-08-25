#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API REST Compatible para Paloma Licitera
Version simplificada que funciona con SQLite y es compatible con el frontend existente
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
from datetime import datetime, date
import sqlite3
import logging
from contextlib import contextmanager
from decimal import Decimal
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="Paloma Licitera API",
    description="API para consulta y análisis de licitaciones gubernamentales",
    version="2.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de base de datos
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "licitaciones.db")

@contextmanager
def get_db_connection():
    """Context manager para conexiones a BD."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        logger.error(f"Error conectando a BD: {e}")
        raise
    finally:
        if conn:
            conn.close()

def serialize_result(result):
    """Serializar resultados para JSON."""
    if isinstance(result, list):
        return [serialize_result(item) for item in result]
    elif isinstance(result, sqlite3.Row):
        return dict(result)
    elif isinstance(result, dict):
        return {
            key: (
                value.isoformat() if isinstance(value, (datetime, date)) else
                float(value) if isinstance(value, Decimal) else
                value
            )
            for key, value in result.items()
        }
    return result

@app.get("/")
def root():
    """Endpoint raíz."""
    return {
        "mensaje": "API Paloma Licitera",
        "version": "2.0.0",
        "endpoints": [
            "/stats",
            "/licitaciones", 
            "/filtros",
            "/analisis/por-tipo-contratacion",
            "/analisis/por-dependencia", 
            "/analisis/por-fuente",
            "/analisis/temporal",
            "/detalle/{id}",
            "/busqueda-rapida"
        ]
    }

@app.get("/stats")
def get_statistics():
    """Obtener estadísticas generales con el formato que espera el frontend."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Total de licitaciones
            cursor.execute("SELECT COUNT(*) as total FROM licitaciones")
            total = cursor.fetchone()['total']
            
            # Por fuente
            cursor.execute("""
                SELECT fuente, COUNT(*) as cantidad 
                FROM licitaciones 
                GROUP BY fuente
                ORDER BY cantidad DESC
            """)
            por_fuente = [dict(row) for row in cursor.fetchall()]
            
            # Por estado
            cursor.execute("""
                SELECT estado, COUNT(*) as cantidad 
                FROM licitaciones 
                WHERE estado IS NOT NULL
                GROUP BY estado
                ORDER BY cantidad DESC
            """)
            por_estado = [dict(row) for row in cursor.fetchall()]
            
            # Por tipo de contratación
            cursor.execute("""
                SELECT tipo_contratacion, COUNT(*) as cantidad 
                FROM licitaciones 
                WHERE tipo_contratacion IS NOT NULL
                GROUP BY tipo_contratacion
                ORDER BY cantidad DESC
            """)
            por_tipo_contratacion = [dict(row) for row in cursor.fetchall()]
            
            # Montos
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE 0 END) as monto_total,
                    AVG(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE NULL END) as monto_promedio,
                    MAX(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE 0 END) as monto_maximo,
                    MIN(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE 0 END) as monto_minimo
                FROM licitaciones 
                WHERE monto_estimado IS NOT NULL
            """)
            montos_row = cursor.fetchone()
            
            # Crear objeto montos con valores por defecto si no hay datos
            montos = {
                'monto_total': float(montos_row['monto_total'] or 0),
                'monto_promedio': float(montos_row['monto_promedio'] or 0),
                'monto_maximo': float(montos_row['monto_maximo'] or 0),
                'monto_minimo': float(montos_row['monto_minimo'] or 0)
            }
            
            # Últimas actualizaciones
            cursor.execute("""
                SELECT fuente, MAX(fecha_captura) as ultima_actualizacion
                FROM licitaciones
                WHERE fecha_captura IS NOT NULL
                GROUP BY fuente
            """)
            actualizaciones = [dict(row) for row in cursor.fetchall()]
            
            # Si no hay actualizaciones, crear datos por defecto
            if not actualizaciones:
                fecha_actual = datetime.now().isoformat()
                actualizaciones = [
                    {'fuente': fuente['fuente'], 'ultima_actualizacion': fecha_actual}
                    for fuente in por_fuente
                ]
            
            return {
                'total': total,
                'por_fuente': por_fuente,
                'por_estado': por_estado,
                'por_tipo_contratacion': por_tipo_contratacion,
                'montos': montos,
                'ultimas_actualizaciones': actualizaciones,
                'fecha_consulta': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        # Devolver estructura mínima en caso de error
        return {
            'total': 0,
            'por_fuente': [],
            'por_estado': [],
            'por_tipo_contratacion': [],
            'montos': {
                'monto_total': 0,
                'monto_promedio': 0,
                'monto_maximo': 0,
                'monto_minimo': 0
            },
            'ultimas_actualizaciones': [],
            'fecha_consulta': datetime.now().isoformat()
        }

@app.get("/licitaciones")
def get_licitaciones(
    fuente: Optional[str] = None,
    estado: Optional[str] = None,
    tipo_contratacion: Optional[str] = None,
    tipo_procedimiento: Optional[str] = None,
    entidad_compradora: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    monto_min: Optional[float] = None,
    monto_max: Optional[float] = None,
    busqueda: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    """Obtener licitaciones con filtros avanzados."""
    try:
        offset = (page - 1) * page_size
        
        # Construir query SQL dinámicamente
        base_sql = """
            SELECT 
                id,
                numero_procedimiento,
                titulo,
                descripcion,
                entidad_compradora,
                unidad_compradora,
                tipo_procedimiento,
                tipo_contratacion,
                estado,
                fecha_publicacion,
                fecha_apertura,
                fecha_fallo,
                monto_estimado,
                moneda,
                fuente,
                url_original
            FROM licitaciones 
            WHERE 1=1
        """
        
        conditions = []
        params = []
        
        if fuente:
            conditions.append(" AND fuente = ?")
            params.append(fuente)
        
        if estado:
            conditions.append(" AND estado = ?")
            params.append(estado)
        
        if tipo_contratacion:
            conditions.append(" AND tipo_contratacion = ?")
            params.append(tipo_contratacion)
        
        if tipo_procedimiento:
            conditions.append(" AND tipo_procedimiento = ?")
            params.append(tipo_procedimiento)
        
        if entidad_compradora:
            conditions.append(" AND entidad_compradora LIKE ?")
            params.append(f"%{entidad_compradora}%")
        
        if fecha_desde:
            conditions.append(" AND fecha_publicacion >= ?")
            params.append(fecha_desde)
        
        if fecha_hasta:
            conditions.append(" AND fecha_publicacion <= ?")
            params.append(fecha_hasta)
        
        if monto_min:
            conditions.append(" AND monto_estimado >= ?")
            params.append(monto_min)
        
        if monto_max:
            conditions.append(" AND monto_estimado <= ?")
            params.append(monto_max)
        
        if busqueda:
            conditions.append("""
                AND (
                    titulo LIKE ? 
                    OR descripcion LIKE ?
                    OR numero_procedimiento LIKE ?
                )
            """)
            search_term = f"%{busqueda}%"
            params.extend([search_term, search_term, search_term])
        
        # Query completo
        full_conditions = "".join(conditions)
        data_sql = base_sql + full_conditions + " ORDER BY fecha_publicacion DESC, id DESC LIMIT ? OFFSET ?"
        count_sql = f"SELECT COUNT(*) as total FROM licitaciones WHERE 1=1{full_conditions}"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener total
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']
            
            # Obtener datos
            data_params = params + [page_size, offset]
            cursor.execute(data_sql, data_params)
            licitaciones = [dict(row) for row in cursor.fetchall()]
            
            return {
                'data': licitaciones,
                'pagination': {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total + page_size - 1) // page_size
                }
            }
    except Exception as e:
        logger.error(f"Error obteniendo licitaciones: {e}")
        return {
            'data': [],
            'pagination': {
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }
        }

@app.get("/filtros")
def get_filtros():
    """Obtener valores únicos para filtros."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Fuentes
            cursor.execute("""
                SELECT fuente, COUNT(*) as cantidad
                FROM licitaciones
                WHERE fuente IS NOT NULL
                GROUP BY fuente
                ORDER BY cantidad DESC
            """)
            fuentes = [dict(row) for row in cursor.fetchall()]
            
            # Estados
            cursor.execute("""
                SELECT estado, COUNT(*) as cantidad
                FROM licitaciones
                WHERE estado IS NOT NULL
                GROUP BY estado
                ORDER BY cantidad DESC
            """)
            estados = [dict(row) for row in cursor.fetchall()]
            
            # Tipos de contratación
            cursor.execute("""
                SELECT tipo_contratacion, COUNT(*) as cantidad
                FROM licitaciones
                WHERE tipo_contratacion IS NOT NULL
                GROUP BY tipo_contratacion
                ORDER BY cantidad DESC
            """)
            tipos_contratacion = [dict(row) for row in cursor.fetchall()]
            
            # Tipos de procedimiento
            cursor.execute("""
                SELECT tipo_procedimiento, COUNT(*) as cantidad
                FROM licitaciones
                WHERE tipo_procedimiento IS NOT NULL
                GROUP BY tipo_procedimiento
                ORDER BY cantidad DESC
            """)
            tipos_procedimiento = [dict(row) for row in cursor.fetchall()]
            
            # Top entidades compradoras
            cursor.execute("""
                SELECT entidad_compradora, COUNT(*) as cantidad
                FROM licitaciones
                WHERE entidad_compradora IS NOT NULL
                GROUP BY entidad_compradora
                ORDER BY cantidad DESC
                LIMIT 100
            """)
            entidades = [dict(row) for row in cursor.fetchall()]
            
            return {
                'fuentes': fuentes,
                'estados': estados,
                'tipos_contratacion': tipos_contratacion,
                'tipos_procedimiento': tipos_procedimiento,
                'top_entidades': entidades
            }
    except Exception as e:
        logger.error(f"Error obteniendo filtros: {e}")
        return {
            'fuentes': [],
            'estados': [],
            'tipos_contratacion': [],
            'tipos_procedimiento': [],
            'top_entidades': []
        }

@app.get("/detalle/{licitacion_id}")
def get_detalle_licitacion(licitacion_id: int):
    """Obtener detalles completos de una licitación."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM licitaciones WHERE id = ?", (licitacion_id,))
            licitacion = cursor.fetchone()
            
            if not licitacion:
                raise HTTPException(status_code=404, detail="Licitación no encontrada")
            
            return dict(licitacion)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo licitación {licitacion_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/busqueda-rapida")
def busqueda_rapida(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50)
):
    """Búsqueda rápida para autocompletado."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            search_term = f"%{q}%"
            cursor.execute("""
                SELECT 
                    id,
                    numero_procedimiento,
                    titulo,
                    entidad_compradora,
                    fecha_publicacion,
                    monto_estimado,
                    fuente
                FROM licitaciones
                WHERE 
                    numero_procedimiento LIKE ?
                    OR titulo LIKE ?
                    OR entidad_compradora LIKE ?
                ORDER BY fecha_publicacion DESC
                LIMIT ?
            """, (search_term, search_term, search_term, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error en búsqueda rápida: {e}")
        return []

# Endpoints de análisis simplificados
@app.get("/analisis/por-tipo-contratacion")
def analisis_por_tipo_contratacion():
    """Análisis detallado por tipo de contratación."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    tipo_contratacion,
                    COUNT(*) as cantidad,
                    SUM(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE 0 END) as monto_total,
                    AVG(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE NULL END) as monto_promedio,
                    MAX(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE 0 END) as monto_maximo,
                    MIN(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE 0 END) as monto_minimo,
                    COUNT(DISTINCT entidad_compradora) as entidades_unicas
                FROM licitaciones
                WHERE tipo_contratacion IS NOT NULL
                GROUP BY tipo_contratacion
                ORDER BY cantidad DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                # Asegurar que los valores numéricos sean float
                for key in ['monto_total', 'monto_promedio', 'monto_maximo', 'monto_minimo']:
                    if row_dict[key] is not None:
                        row_dict[key] = float(row_dict[key])
                results.append(row_dict)
            
            return results
    except Exception as e:
        logger.error(f"Error en análisis por tipo: {e}")
        return []

@app.get("/analisis/por-dependencia")
def analisis_por_dependencia(limit: int = Query(20, ge=1, le=100)):
    """Análisis detallado por dependencia."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    entidad_compradora,
                    COUNT(*) as cantidad_licitaciones,
                    SUM(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE 0 END) as monto_total,
                    AVG(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE NULL END) as monto_promedio,
                    COUNT(DISTINCT tipo_contratacion) as tipos_contratacion,
                    COUNT(DISTINCT tipo_procedimiento) as tipos_procedimiento,
                    MIN(fecha_publicacion) as primera_licitacion,
                    MAX(fecha_publicacion) as ultima_licitacion
                FROM licitaciones
                WHERE entidad_compradora IS NOT NULL
                GROUP BY entidad_compradora
                ORDER BY cantidad_licitaciones DESC
                LIMIT ?
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                # Asegurar que los valores numéricos sean float
                for key in ['monto_total', 'monto_promedio']:
                    if row_dict[key] is not None:
                        row_dict[key] = float(row_dict[key])
                results.append(row_dict)
            
            return results
    except Exception as e:
        logger.error(f"Error en análisis por dependencia: {e}")
        return []

@app.get("/analisis/por-fuente")
def analisis_por_fuente():
    """Análisis comparativo por fuente de datos."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    fuente,
                    COUNT(*) as total_licitaciones,
                    COUNT(DISTINCT entidad_compradora) as entidades_unicas,
                    COUNT(DISTINCT tipo_contratacion) as tipos_contratacion,
                    SUM(CASE WHEN monto_estimado > 0 THEN 1 ELSE 0 END) as con_monto,
                    SUM(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE 0 END) as monto_total,
                    AVG(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE NULL END) as monto_promedio,
                    MIN(fecha_publicacion) as fecha_mas_antigua,
                    MAX(fecha_publicacion) as fecha_mas_reciente,
                    MAX(fecha_captura) as ultima_actualizacion
                FROM licitaciones
                GROUP BY fuente
                ORDER BY total_licitaciones DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                # Asegurar que los valores numéricos sean float
                for key in ['monto_total', 'monto_promedio']:
                    if row_dict[key] is not None:
                        row_dict[key] = float(row_dict[key])
                results.append(row_dict)
            
            return results
    except Exception as e:
        logger.error(f"Error en análisis por fuente: {e}")
        return []

@app.get("/analisis/temporal")
def analisis_temporal(granularidad: str = Query("mes")):
    """Análisis temporal de licitaciones."""
    try:
        # Mapear granularidad a formato de fecha SQLite
        date_formats = {
            'dia': '%Y-%m-%d',
            'semana': '%Y-W%W',
            'mes': '%Y-%m',
            'año': '%Y'
        }
        
        date_format = date_formats.get(granularidad, '%Y-%m')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT 
                    strftime('{date_format}', fecha_publicacion) as periodo,
                    COUNT(*) as cantidad,
                    SUM(CASE WHEN monto_estimado > 0 THEN monto_estimado ELSE 0 END) as monto_total,
                    COUNT(DISTINCT entidad_compradora) as entidades_unicas,
                    COUNT(DISTINCT fuente) as fuentes
                FROM licitaciones
                WHERE fecha_publicacion IS NOT NULL
                    AND fecha_publicacion >= date('now', '-1 year')
                GROUP BY periodo
                ORDER BY periodo DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                # Asegurar que monto_total sea float
                if row_dict['monto_total'] is not None:
                    row_dict['monto_total'] = float(row_dict['monto_total'])
                results.append(row_dict)
            
            return results
    except Exception as e:
        logger.error(f"Error en análisis temporal: {e}")
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)