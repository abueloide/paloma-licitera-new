#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API REST para Paloma Licitera
"""

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from datetime import datetime
import yaml
import logging

from database import Database
from etl import ETL

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="Paloma Licitera API",
    description="API para consultar licitaciones gubernamentales de México",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar componentes
with open("config.yaml", 'r') as f:
    config = yaml.safe_load(f)

db = Database()
etl = ETL()

@app.get("/")
def root():
    """Endpoint raíz con información del sistema."""
    return {
        "nombre": "Paloma Licitera API",
        "version": "2.0.0",
        "descripcion": "Sistema ETL simplificado para licitaciones gubernamentales",
        "endpoints": {
            "licitaciones": "/licitaciones",
            "estadisticas": "/stats",
            "ejecutar_etl": "/etl/run"
        }
    }

@app.get("/health")
def health_check():
    """Verificar estado del sistema."""
    try:
        stats = db.obtener_estadisticas()
        return {
            "status": "healthy",
            "database": "connected",
            "total_licitaciones": stats['total'],
            "ultima_actualizacion": stats['ultima_actualizacion']
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }

@app.get("/licitaciones")
def obtener_licitaciones(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(50, ge=1, le=500, description="Registros por página"),
    fuente: Optional[str] = Query(None, description="Filtrar por fuente (COMPRASMX, DOF, TIANGUIS)"),
    entidad: Optional[str] = Query(None, description="Filtrar por entidad compradora"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    q: Optional[str] = Query(None, description="Búsqueda de texto")
):
    """
    Obtener licitaciones con filtros opcionales.
    
    - **page**: Número de página (default: 1)
    - **limit**: Registros por página (default: 50, max: 500)
    - **fuente**: COMPRASMX, DOF, TIANGUIS, TIANGUIS_ZIP
    - **entidad**: Nombre parcial de entidad compradora
    - **estado**: VIGENTE, CERRADO, CANCELADO
    - **q**: Búsqueda de texto en título y descripción
    """
    try:
        offset = (page - 1) * limit
        
        filtros = {}
        if fuente:
            filtros['fuente'] = fuente.upper()
        if entidad:
            filtros['entidad'] = entidad
        if estado:
            filtros['estado'] = estado.upper()
        if q:
            filtros['q'] = q
            
        licitaciones = db.obtener_licitaciones(filtros, limit, offset)
        
        # Convertir fechas a string para JSON
        for lic in licitaciones:
            for campo in ['fecha_publicacion', 'fecha_apertura', 'fecha_fallo', 'fecha_captura']:
                if campo in lic and lic[campo]:
                    lic[campo] = str(lic[campo])
                    
        return {
            "page": page,
            "limit": limit,
            "total": len(licitaciones),
            "data": licitaciones
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo licitaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def obtener_estadisticas():
    """Obtener estadísticas generales del sistema."""
    try:
        stats = db.obtener_estadisticas()
        return stats
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/filters")
def obtener_filtros():
    """Obtener valores únicos para filtros."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Fuentes
            cursor.execute("SELECT DISTINCT fuente FROM licitaciones ORDER BY fuente")
            fuentes = [row['fuente'] for row in cursor.fetchall()]
            
            # Estados
            cursor.execute("SELECT DISTINCT estado FROM licitaciones WHERE estado IS NOT NULL ORDER BY estado")
            estados = [row['estado'] for row in cursor.fetchall()]
            
            # Top entidades
            cursor.execute("""
                SELECT entidad_compradora, COUNT(*) as total
                FROM licitaciones
                WHERE entidad_compradora IS NOT NULL
                GROUP BY entidad_compradora
                ORDER BY total DESC
                LIMIT 50
            """)
            entidades = [row['entidad_compradora'] for row in cursor.fetchall()]
            
            return {
                "fuentes": fuentes,
                "estados": estados,
                "entidades": entidades
            }
            
    except Exception as e:
        logger.error(f"Error obteniendo filtros: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/etl/run")
async def ejecutar_etl(
    background_tasks: BackgroundTasks,
    fuente: str = Query("all", description="Fuente a procesar: all, comprasmx, dof, tianguis, zip")
):
    """
    Ejecutar proceso ETL en background.
    
    - **fuente**: all (todas), comprasmx, dof, tianguis, zip
    """
    if fuente not in ["all", "comprasmx", "dof", "tianguis", "zip"]:
        raise HTTPException(status_code=400, detail="Fuente inválida")
    
    # Ejecutar en background
    background_tasks.add_task(etl.ejecutar, fuente)
    
    return {
        "message": f"ETL iniciado para fuente: {fuente}",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/licitaciones/{id}")
def obtener_licitacion(id: int):
    """Obtener una licitación específica por ID."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM licitaciones WHERE id = %s", (id,))
            licitacion = cursor.fetchone()
            
            if not licitacion:
                raise HTTPException(status_code=404, detail="Licitación no encontrada")
            
            # Convertir fechas
            for campo in ['fecha_publicacion', 'fecha_apertura', 'fecha_fallo', 'fecha_captura']:
                if campo in licitacion and licitacion[campo]:
                    licitacion[campo] = str(licitacion[campo])
                    
            return licitacion
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo licitación {id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    # Leer configuración
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Iniciar servidor
    uvicorn.run(
        app,
        host=config['api']['host'],
        port=config['api']['port'],
        log_level="info"
    )
