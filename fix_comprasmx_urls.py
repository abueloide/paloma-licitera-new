#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para obtener las URLs correctas de ComprasMX mediante búsqueda por número de procedimiento
"""

import asyncio
import psycopg2
import yaml
import logging
from pathlib import Path
from playwright.async_api import async_playwright
from typing import Optional, List

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar configuración y ajustar para psycopg2
config_path = Path(__file__).parent / 'config.yaml'
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Ajustar configuración para psycopg2 (usa 'database' en lugar de 'name')
db_config = {
    'host': config['database']['host'],
    'port': config['database']['port'],
    'database': config['database']['name'],  # psycopg2 usa 'database', no 'name'
    'user': config['database']['user'],
    'password': config['database']['password']
}

def obtener_procedimientos_sin_url_valida():
    """Obtener procedimientos de ComprasMX que necesitan URL válida."""
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT id, numero_procedimiento, titulo
            FROM licitaciones
            WHERE fuente = 'COMPRASMX'
              AND (url_original IS NULL 
                   OR url_original = 'https://comprasmx.buengobierno.gob.mx/'
                   OR url_original LIKE '%/procedimiento/%'
                   OR url_original NOT LIKE '%/sitiopublico/detalle/%')
            ORDER BY id
            LIMIT 100
        """
        
        cursor.execute(query)
        procedimientos = cursor.fetchall()
        
        logger.info(f"Encontrados {len(procedimientos)} procedimientos para actualizar")
        return procedimientos
        
    finally:
        cursor.close()
        conn.close()

def actualizar_url_procedimiento(id_licitacion: int, url_real: str):
    """Actualizar la URL de un procedimiento en la base de datos."""
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        query = """
            UPDATE licitaciones
            SET url_original = %s
            WHERE id = %s
        """
        cursor.execute(query, (url_real, id_licitacion))
        conn.commit()
        logger.info(f"Actualizada URL para ID {id_licitacion}")
        
    except Exception as e:
        logger.error(f"Error actualizando ID {id_licitacion}: {e}")
        conn.rollback()
        
    finally:
        cursor.close()
        conn.close()

async def buscar_procedimiento_comprasmx(numero_procedimiento: str, titulo: str = "") -> Optional[str]:
    """Buscar un procedimiento en ComprasMX y obtener su URL real."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            logger.info(f"Buscando procedimiento: {numero_procedimiento}")
            
            # Ir a la página principal
            await page.goto("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/", 
                           wait_until="networkidle", timeout=30000)
            
            # Esperar que cargue
            await page.wait_for_timeout(3000)
            
            # Buscar campo de búsqueda
            search_field = await page.wait_for_selector('input[type="search"], input[placeholder*="Buscar"]', timeout=5000)
            
            if search_field:
                await search_field.clear()
                await search_field.type(numero_procedimiento)
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(5000)
                
                # Verificar si llegamos a una página de detalle
                current_url = page.url
                if '/sitiopublico/detalle/' in current_url:
                    logger.info(f"URL encontrada: {current_url}")
                    return current_url
            
            return None
            
        except Exception as e:
            logger.error(f"Error buscando {numero_procedimiento}: {e}")
            return None
            
        finally:
            await browser.close()

async def main():
    """Proceso principal."""
    
    logger.info("Iniciando actualización de URLs de ComprasMX...")
    
    procedimientos = obtener_procedimientos_sin_url_valida()
    
    if not procedimientos:
        logger.info("No hay procedimientos para actualizar")
        return
    
    for id_licitacion, numero_proc, titulo in procedimientos:
        try:
            url_real = await buscar_procedimiento_comprasmx(numero_proc, titulo)
            
            if url_real:
                actualizar_url_procedimiento(id_licitacion, url_real)
            else:
                logger.warning(f"No se pudo obtener URL para {numero_proc}")
            
            await asyncio.sleep(2)  # Esperar entre búsquedas
            
        except Exception as e:
            logger.error(f"Error procesando {numero_proc}: {e}")
            continue
    
    logger.info("Proceso completado")

if __name__ == "__main__":
    asyncio.run(main())
