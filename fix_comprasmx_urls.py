#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para obtener las URLs correctas de ComprasMX mediante búsqueda por número de procedimiento
Actualiza la base de datos con las URLs reales obtenidas del sitio

PROBLEMA:
- ComprasMX usa hashes únicos para cada procedimiento en sus URLs
- Formato: https://comprasmx.buengobierno.gob.mx/sitiopublico/#/sitiopublico/detalle/{hash}/procedimiento
- El hash no es predecible y no viene en los datos descargados

SOLUCIÓN:
- Este script busca cada procedimiento por su número en el sitio de ComprasMX
- Obtiene la URL real con el hash correcto
- Actualiza la base de datos

USO:
python fix_comprasmx_urls.py
"""

import asyncio
import psycopg2
import yaml
import logging
from pathlib import Path
from playwright.async_api import async_playwright
import re
import json
from typing import Dict, Optional, List
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar configuración
config_path = Path(__file__).parent / 'config.yaml'
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)
db_config = config['database']

def obtener_procedimientos_sin_url_valida():
    """Obtener procedimientos de ComprasMX que necesitan URL válida."""
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        # Obtener procedimientos con URL incorrecta o sin hash válido
        query = """
            SELECT id, numero_procedimiento, titulo
            FROM licitaciones
            WHERE fuente = 'COMPRASMX'
              AND (url_original IS NULL 
                   OR url_original = 'https://comprasmx.buengobierno.gob.mx/'
                   OR url_original LIKE '%/procedimiento/%'
                   OR url_original NOT LIKE '%/sitiopublico/detalle/%')
            ORDER BY id
            LIMIT 100  -- Procesar en lotes
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
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        try:
            logger.info(f"Buscando procedimiento: {numero_procedimiento}")
            
            # Ir a la página principal
            await page.goto("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/", 
                           wait_until="networkidle", timeout=30000)
            
            # Esperar que cargue la aplicación Angular
            await page.wait_for_timeout(3000)
            
            # Buscar el campo de búsqueda
            search_selectors = [
                'input[placeholder*="Buscar"]',
                'input[type="search"]',
                'input[ng-model*="search"]',
                'input[ng-model*="busqueda"]',
                '#searchInput',
                '.search-input'
            ]
            
            search_field = None
            for selector in search_selectors:
                try:
                    search_field = await page.wait_for_selector(selector, timeout=5000)
                    if search_field:
                        break
                except:
                    continue
            
            if not search_field:
                logger.warning(f"No se encontró campo de búsqueda para {numero_procedimiento}")
                return None
            
            # Escribir el número de procedimiento
            await search_field.clear()
            await search_field.type(numero_procedimiento)
            
            # Presionar Enter o buscar botón de búsqueda
            await page.keyboard.press('Enter')
            
            # Esperar resultados
            await page.wait_for_timeout(5000)
            
            # Buscar enlaces a procedimientos en los resultados
            # Los resultados suelen tener enlaces con el formato del hash
            resultado_links = await page.locator('a[href*="/sitiopublico/detalle/"]').all()
            
            if not resultado_links:
                # Intentar hacer clic en el primer resultado si existe
                resultados = await page.locator('.resultado-item, .search-result, tr[ng-repeat]').all()
                
                if resultados:
                    await resultados[0].click()
                    await page.wait_for_timeout(3000)
                    
                    # Obtener la URL actual
                    current_url = page.url
                    if '/sitiopublico/detalle/' in current_url:
                        logger.info(f"URL encontrada para {numero_procedimiento}: {current_url}")
                        return current_url
            else:
                # Obtener el href del primer resultado
                href = await resultado_links[0].get_attribute('href')
                if href:
                    # Construir URL completa
                    if href.startswith('#'):
                        url_completa = f"https://comprasmx.buengobierno.gob.mx/sitiopublico/{href}"
                    elif href.startswith('/'):
                        url_completa = f"https://comprasmx.buengobierno.gob.mx{href}"
                    else:
                        url_completa = href
                    
                    logger.info(f"URL encontrada para {numero_procedimiento}: {url_completa}")
                    return url_completa
            
            logger.warning(f"No se encontró URL para {numero_procedimiento}")
            return None
            
        except Exception as e:
            logger.error(f"Error buscando {numero_procedimiento}: {e}")
            return None
            
        finally:
            await browser.close()

async def procesar_lote(procedimientos: List[tuple]):
    """Procesar un lote de procedimientos."""
    
    for id_licitacion, numero_proc, titulo in procedimientos:
        try:
            # Buscar la URL real
            url_real = await buscar_procedimiento_comprasmx(numero_proc, titulo)
            
            if url_real:
                # Actualizar en la base de datos
                actualizar_url_procedimiento(id_licitacion, url_real)
            else:
                logger.warning(f"No se pudo obtener URL para {numero_proc}")
            
            # Esperar entre búsquedas para no saturar el servidor
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Error procesando {numero_proc}: {e}")
            continue

async def main():
    """Proceso principal."""
    
    logger.info("Iniciando actualización de URLs de ComprasMX...")
    
    # Obtener procedimientos a actualizar
    procedimientos = obtener_procedimientos_sin_url_valida()
    
    if not procedimientos:
        logger.info("No hay procedimientos para actualizar")
        return
    
    # Procesar en lotes
    await procesar_lote(procedimientos)
    
    logger.info("Proceso completado")

if __name__ == "__main__":
    asyncio.run(main())
