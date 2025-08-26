#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API REST para Paloma Licitera
API principal que se conecta a PostgreSQL con los datos reales
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
import psycopg2
import psycopg2.extras
import yaml
import logging
from contextlib import contextmanager
from decimal import Decimal
import json
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

# Cargar configuración - buscar en el directorio padre (raíz del proyecto)
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)
db_config = config['database']

@contextmanager
def get_db_connection():
    """Context manager para conexiones a BD."""
    conn = None
    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['name'],
            user=db_config['user'],
            password=db_config['password'],
            cursor_factory=psycopg2.extras.RealDictCursor
        )
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
            "/analisis/temporal-acumulado",
            "/detalle/{id}",
            "/busqueda-rapida",
            "/top-entidad",
            "/top-tipo-contratacion"
        ]
    }

@app.get("/stats")
def get_statistics():
    """Obtener estadísticas generales."""
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
        por_fuente = cursor.fetchall()
        
        # Por estado
        cursor.execute("""
            SELECT estado, COUNT(*) as cantidad 
            FROM licitaciones 
            WHERE estado IS NOT NULL
            GROUP BY estado
            ORDER BY cantidad DESC
        """)
        por_estado = cursor.fetchall()
        
        # Por tipo de contratación
        cursor.execute("""
            SELECT tipo_contratacion, COUNT(*) as cantidad 
            FROM licitaciones 
            WHERE tipo_contratacion IS NOT NULL
            GROUP BY tipo_contratacion
            ORDER BY cantidad DESC
        """)
        por_tipo_contratacion = cursor.fetchall()
        
        # Top entidad compradora con más licitaciones
        cursor.execute("""
            SELECT entidad_compradora, COUNT(*) as cantidad
            FROM licitaciones
            WHERE entidad_compradora IS NOT NULL
            GROUP BY entidad_compradora
            ORDER BY cantidad DESC
            LIMIT 1
        """)
        top_entidad = cursor.fetchone()
        
        # Top tipo de contratación con más licitaciones
        cursor.execute("""
            SELECT tipo_contratacion, COUNT(*) as cantidad
            FROM licitaciones
            WHERE tipo_contratacion IS NOT NULL
            GROUP BY tipo_contratacion
            ORDER BY cantidad DESC
            LIMIT 1
        """)
        top_tipo = cursor.fetchone()
        
        # Últimas actualizaciones
        cursor.execute("""
            SELECT fuente, MAX(fecha_captura) as ultima_actualizacion
            FROM licitaciones
            GROUP BY fuente
        """)
        actualizaciones = cursor.fetchall()
        
        return serialize_result({
            'total': total,
            'por_fuente': por_fuente,
            'por_estado': por_estado,
            'por_tipo_contratacion': por_tipo_contratacion,
            'top_entidad': top_entidad,
            'top_tipo_contratacion': top_tipo,
            'ultimas_actualizaciones': actualizaciones,
            'fecha_consulta': datetime.now()
        })

@app.get("/top-entidad")
def get_top_entidad():
    """Obtener la entidad con más licitaciones."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT entidad_compradora, COUNT(*) as cantidad
            FROM licitaciones
            WHERE entidad_compradora IS NOT NULL
            GROUP BY entidad_compradora
            ORDER BY cantidad DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        return serialize_result(result if result else {"entidad_compradora": "No disponible", "cantidad": 0})

@app.get("/top-tipo-contratacion")
def get_top_tipo_contratacion():
    """Obtener el tipo de contratación con más licitaciones."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tipo_contratacion, COUNT(*) as cantidad
            FROM licitaciones
            WHERE tipo_contratacion IS NOT NULL
            GROUP BY tipo_contratacion
            ORDER BY cantidad DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        return serialize_result(result if result else {"tipo_contratacion": "No disponible", "cantidad": 0})

@app.get("/licitaciones")
def get_licitaciones(
    fuente: Optional[str] = None,
    estado: Optional[str] = None,
    tipo_contratacion: Optional[List[str]] = Query(None),
    tipo_procedimiento: Optional[List[str]] = Query(None),
    entidad_compradora: Optional[List[str]] = Query(None),
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    monto_min: Optional[float] = None,
    monto_max: Optional[float] = None,
    dias_apertura: Optional[int] = None,
    busqueda: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    """Obtener licitaciones con filtros avanzados."""
    offset = (page - 1) * page_size
    
    # Construir query SQL dinámicamente
    sql = """
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
    
    params = {}
    
    if fuente:
        sql += " AND fuente = %(fuente)s"
        params['fuente'] = fuente
    
    if estado:
        sql += " AND estado = %(estado)s"
        params['estado'] = estado
    
    if tipo_contratacion:
        sql += " AND tipo_contratacion = ANY(%(tipo_contratacion)s)"
        params['tipo_contratacion'] = tipo_contratacion
    
    if tipo_procedimiento:
        sql += " AND tipo_procedimiento = ANY(%(tipo_procedimiento)s)"
        params['tipo_procedimiento'] = tipo_procedimiento
    
    if entidad_compradora:
        sql += " AND entidad_compradora = ANY(%(entidad_compradora)s)"
        params['entidad_compradora'] = entidad_compradora
    
    if fecha_desde:
        sql += " AND fecha_publicacion >= %(fecha_desde)s"
        params['fecha_desde'] = fecha_desde
    
    if fecha_hasta:
        sql += " AND fecha_publicacion <= %(fecha_hasta)s"
        params['fecha_hasta'] = fecha_hasta
    
    if monto_min:
        sql += " AND monto_estimado >= %(monto_min)s"
        params['monto_min'] = monto_min
    
    if monto_max:
        sql += " AND monto_estimado <= %(monto_max)s"
        params['monto_max'] = monto_max
    
    if dias_apertura is not None:
        fecha_limite = date.today() + timedelta(days=dias_apertura)
        sql += " AND fecha_apertura IS NOT NULL AND fecha_apertura <= %(fecha_limite)s AND fecha_apertura >= %(fecha_hoy)s"
        params['fecha_limite'] = fecha_limite
        params['fecha_hoy'] = date.today()
    
    if busqueda:
        sql += """ 
            AND (
                titulo ILIKE %(busqueda)s 
                OR descripcion ILIKE %(busqueda)s
                OR numero_procedimiento ILIKE %(busqueda)s
            )
        """
        params['busqueda'] = f"%{busqueda}%"
    
    # Contar total para paginación
    count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as subquery"
    
    # Agregar orden y límites
    sql += " ORDER BY fecha_publicacion DESC, id DESC LIMIT %(limit)s OFFSET %(offset)s"
    params['limit'] = page_size
    params['offset'] = offset
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Obtener total
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # Obtener datos
        cursor.execute(sql, params)
        licitaciones = cursor.fetchall()
        
        return serialize_result({
            'data': licitaciones,
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        })

@app.get("/filtros")
def get_filtros():
    """Obtener valores únicos para filtros."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Fuentes
        cursor.execute("""
            SELECT DISTINCT fuente, COUNT(*) as cantidad
            FROM licitaciones
            WHERE fuente IS NOT NULL
            GROUP BY fuente
            ORDER BY cantidad DESC
        """)
        fuentes = cursor.fetchall()
        
        # Estados
        cursor.execute("""
            SELECT DISTINCT estado, COUNT(*) as cantidad
            FROM licitaciones
            WHERE estado IS NOT NULL
            GROUP BY estado
            ORDER BY cantidad DESC
        """)
        estados = cursor.fetchall()
        
        # Tipos de contratación
        cursor.execute("""
            SELECT DISTINCT tipo_contratacion, COUNT(*) as cantidad
            FROM licitaciones
            WHERE tipo_contratacion IS NOT NULL
            GROUP BY tipo_contratacion
            ORDER BY cantidad DESC
        """)
        tipos_contratacion = cursor.fetchall()
        
        # Tipos de procedimiento
        cursor.execute("""
            SELECT DISTINCT tipo_procedimiento, COUNT(*) as cantidad
            FROM licitaciones
            WHERE tipo_procedimiento IS NOT NULL
            GROUP BY tipo_procedimiento
            ORDER BY cantidad DESC
        """)
        tipos_procedimiento = cursor.fetchall()
        
        # Top entidades compradoras
        cursor.execute("""
            SELECT entidad_compradora, COUNT(*) as cantidad
            FROM licitaciones
            WHERE entidad_compradora IS NOT NULL
            GROUP BY entidad_compradora
            ORDER BY cantidad DESC
            LIMIT 100
        """)
        entidades = cursor.fetchall()
        
        return serialize_result({
            'fuentes': fuentes,
            'estados': estados,
            'tipos_contratacion': tipos_contratacion,
            'tipos_procedimiento': tipos_procedimiento,
            'top_entidades': entidades
        })

@app.get("/analisis/por-tipo-contratacion")
def analisis_por_tipo_contratacion():
    """Análisis detallado por tipo de contratación."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                tipo_contratacion,
                COUNT(*) as cantidad,
                SUM(monto_estimado) as monto_total,
                AVG(monto_estimado) as monto_promedio,
                MAX(monto_estimado) as monto_maximo,
                MIN(monto_estimado) as monto_minimo,
                COUNT(DISTINCT entidad_compradora) as entidades_unicas
            FROM licitaciones
            WHERE tipo_contratacion IS NOT NULL
            GROUP BY tipo_contratacion
            ORDER BY cantidad DESC
        """)
        
        return serialize_result(cursor.fetchall())

@app.get("/analisis/por-dependencia")
def analisis_por_dependencia(
    limit: int = Query(20, ge=1, le=100)
):
    """Análisis detallado por dependencia."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                entidad_compradora,
                COUNT(*) as cantidad_licitaciones,
                SUM(monto_estimado) as monto_total,
                AVG(monto_estimado) as monto_promedio,
                COUNT(DISTINCT tipo_contratacion) as tipos_contratacion,
                COUNT(DISTINCT tipo_procedimiento) as tipos_procedimiento,
                MIN(fecha_publicacion) as primera_licitacion,
                MAX(fecha_publicacion) as ultima_licitacion
            FROM licitaciones
            WHERE entidad_compradora IS NOT NULL
            GROUP BY entidad_compradora
            ORDER BY cantidad_licitaciones DESC
            LIMIT %(limit)s
        """, {'limit': limit})
        
        return serialize_result(cursor.fetchall())

@app.get("/analisis/por-fuente")
def analisis_por_fuente():
    """Análisis comparativo por fuente de datos."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                fuente,
                COUNT(*) as total_licitaciones,
                COUNT(DISTINCT entidad_compradora) as entidades_unicas,
                COUNT(DISTINCT tipo_contratacion) as tipos_contratacion,
                SUM(CASE WHEN monto_estimado > 0 THEN 1 ELSE 0 END) as con_monto,
                SUM(monto_estimado) as monto_total,
                AVG(monto_estimado) as monto_promedio,
                MIN(fecha_publicacion) as fecha_mas_antigua,
                MAX(fecha_publicacion) as fecha_mas_reciente,
                MAX(fecha_captura) as ultima_actualizacion
            FROM licitaciones
            GROUP BY fuente
            ORDER BY total_licitaciones DESC
        """)
        
        return serialize_result(cursor.fetchall())

@app.get("/analisis/temporal")
def analisis_temporal(
    granularidad: str = Query("mes", regex="^(dia|semana|mes|año)$")
):
    """Análisis temporal de licitaciones."""
    
    # Mapear granularidad a formato de fecha SQL
    date_formats = {
        'dia': 'YYYY-MM-DD',
        'semana': 'YYYY-IW',
        'mes': 'YYYY-MM',
        'año': 'YYYY'
    }
    
    date_format = date_formats[granularidad]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT 
                TO_CHAR(fecha_publicacion, '{date_format}') as periodo,
                COUNT(*) as cantidad,
                SUM(monto_estimado) as monto_total,
                COUNT(DISTINCT entidad_compradora) as entidades_unicas,
                COUNT(DISTINCT fuente) as fuentes
            FROM licitaciones
            WHERE fecha_publicacion IS NOT NULL
                AND fecha_publicacion >= CURRENT_DATE - INTERVAL '1 year'
            GROUP BY periodo
            ORDER BY periodo DESC
        """)
        
        return serialize_result(cursor.fetchall())

@app.get("/analisis/temporal-acumulado")
def analisis_temporal_acumulado():
    """Análisis temporal acumulado del año actual."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Obtener datos mensuales del año actual
        cursor.execute("""
            SELECT 
                TO_CHAR(fecha_publicacion, 'YYYY-MM') as mes,
                COUNT(*) as cantidad
            FROM licitaciones
            WHERE fecha_publicacion IS NOT NULL
                AND EXTRACT(YEAR FROM fecha_publicacion) = EXTRACT(YEAR FROM CURRENT_DATE)
            GROUP BY mes
            ORDER BY mes
        """)
        
        datos = cursor.fetchall()
        
        # Calcular acumulado
        acumulado = 0
        resultado = []
        for row in datos:
            acumulado += row['cantidad']
            resultado.append({
                'mes': row['mes'],
                'cantidad': row['cantidad'],
                'acumulado': acumulado
            })
        
        return serialize_result(resultado)

@app.get("/detalle/{licitacion_id}")
def get_detalle_licitacion(licitacion_id: int):
    """Obtener detalles completos de una licitación."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM licitaciones WHERE id = %(id)s
        """, {'id': licitacion_id})
        
        licitacion = cursor.fetchone()
        
        if not licitacion:
            raise HTTPException(status_code=404, detail="Licitación no encontrada")
        
        return serialize_result(licitacion)

@app.get("/busqueda-rapida")
def busqueda_rapida(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50)
):
    """Búsqueda rápida para autocompletado."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
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
                numero_procedimiento ILIKE %(q)s
                OR titulo ILIKE %(q)s
                OR entidad_compradora ILIKE %(q)s
            ORDER BY fecha_publicacion DESC
            LIMIT %(limit)s
        """, {'q': f"%{q}%", 'limit': limit})
        
        return serialize_result(cursor.fetchall())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
