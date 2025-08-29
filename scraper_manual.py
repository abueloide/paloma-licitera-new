#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRAPER MANUAL COMPRASMX
Extrae información de la página actual cuando presionas ENTER
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScraperManual:
    def __init__(self):
        self.data_dir = Path("data/raw/comprasmx")
        self.detalles_dir = self.data_dir / "detalles"
        self.detalles_dir.mkdir(parents=True, exist_ok=True)
        self.detalles_extraidos = {}
        
    async def inicializar(self):
        """Inicializar navegador visible"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        self.context = await self.browser.new_context(viewport=None)
        self.page = await self.context.new_page()
        
        logger.info("Navegador iniciado - Abriendo ComprasMX...")
        
    async def extraer_pagina_actual(self):
        """Extraer información de cualquier página actual"""
        url = self.page.url
        logger.info(f"Extrayendo información de: {url}")
        
        try:
            # Esperar a que la página cargue
            await self.page.wait_for_load_state('networkidle', timeout=5000)
            
            # Obtener todo el texto de la página
            contenido = await self.page.text_content('body')
            titulo_pagina = await self.page.title()
            
            print(f"\n=== INFORMACIÓN DE LA PÁGINA ACTUAL ===")
            print(f"URL: {url}")
            print(f"Título: {titulo_pagina}")
            print(f"Contenido (primeros 500 chars): {contenido[:500] if contenido else 'Sin contenido'}...")
            
            # Si parece ser una página de detalle, extraer información específica
            if self.parece_pagina_detalle(url, contenido):
                detalle = await self.extraer_detalle_licitacion()
                if detalle:
                    await self.guardar_detalle(detalle)
                    codigo = detalle.get('codigo_expediente', 'UNKNOWN')
                    logger.info(f"✅ Detalle guardado: {codigo}")
                    return True
            else:
                print("No parece ser una página de detalle de licitación")
                
        except Exception as e:
            logger.error(f"Error extrayendo página: {e}")
            
        return False
    
    def parece_pagina_detalle(self, url, contenido):
        """Verificar si parece una página de detalle"""
        # Buscar indicadores en URL
        indicadores_url = [
            'detalle', 'expediente', 'procedimiento', 
            'contratacion', 'licitacion'
        ]
        
        # Buscar indicadores en contenido
        indicadores_contenido = [
            'Código del expediente', 'Número de procedimiento',
            'DATOS GENERALES', 'Descripción detallada',
            'INVITACIÓN A CUANDO MENOS', 'LICITACIÓN PÚBLICA'
        ]
        
        url_match = any(ind in url.lower() for ind in indicadores_url)
        contenido_match = any(ind in contenido for ind in indicadores_contenido) if contenido else False
        
        es_detalle = url_match or contenido_match
        print(f"¿Es página de detalle? {es_detalle} (URL: {url_match}, Contenido: {contenido_match})")
        
        return es_detalle
    
    async def extraer_detalle_licitacion(self):
        """Extraer información específica de licitación"""
        try:
            # Buscar elementos específicos usando múltiples estrategias
            info = {}
            
            # Estrategia 1: Buscar por texto específico
            campos_texto = {
                'codigo_expediente': ['Código del expediente:', 'código del expediente'],
                'numero_procedimiento': ['Número de procedimiento', 'número de procedimiento'],
                'estatus': ['Estatus del procedimiento', 'estatus del procedimiento'],
                'descripcion_completa': ['Descripción detallada', 'descripción detallada'],
                'dependencia': ['Dependencia o Entidad:', 'dependencia o entidad'],
                'ramo': ['Ramo:', 'ramo'],
                'unidad_compradora': ['Unidad compradora:', 'unidad compradora'],
                'nombre_procedimiento': ['Nombre del procedimiento', 'nombre del procedimiento']
            }
            
            for campo, textos_buscar in campos_texto.items():
                for texto in textos_buscar:
                    try:
                        # Buscar elemento que contenga el texto
                        elemento = self.page.locator(f"text={texto}").first
                        if await elemento.count() > 0:
                            # Obtener el contenedor padre
                            parent = elemento.locator('..')
                            texto_completo = await parent.text_content()
                            
                            # Extraer valor después del label
                            if texto in texto_completo:
                                valor = texto_completo.split(texto)[-1].strip()
                                if valor and valor != '-':
                                    info[campo] = valor[:200]  # Limitar longitud
                                    print(f"✓ {campo}: {valor[:50]}...")
                                    break
                    except Exception as e:
                        continue
            
            # Estrategia 2: Si no encontró nada, buscar en todo el contenido
            if not info:
                print("Estrategia 1 falló, probando estrategia 2...")
                contenido_completo = await self.page.text_content('body')
                
                # Buscar patrones específicos
                patrones = {
                    'codigo_expediente': r'(?:Código del expediente:|código del expediente)[:\s]*([A-Z0-9\-]+)',
                    'numero_procedimiento': r'(?:IA-|LA-|AD-)[0-9A-Z\-]+',
                    'estatus': r'(?:VIGENTE|CERRADO|CANCELADO|EN PROCESO)'
                }
                
                for campo, patron in patrones.items():
                    match = re.search(patron, contenido_completo, re.IGNORECASE)
                    if match:
                        info[campo] = match.group(1) if match.groups() else match.group(0)
                        print(f"✓ {campo} (regex): {info[campo]}")
            
            # Si encontró algo, construir detalle completo
            if info:
                detalle = {
                    'codigo_expediente': info.get('codigo_expediente', f'AUTO_{datetime.now().strftime("%Y%m%d_%H%M%S")}'),
                    'url_completa_con_hash': self.page.url,
                    'timestamp_procesamiento': datetime.now().isoformat(),
                    'pagina_origen': 'Scraper Manual ComprasMX',
                    'procesado_exitosamente': True,
                    'informacion_extraida': {
                        'numero_procedimiento': info.get('numero_procedimiento'),
                        'estatus': info.get('estatus'),
                        'descripcion_completa': info.get('descripcion_completa'),
                        'nombre_procedimiento': info.get('nombre_procedimiento'),
                        'dependencia_entidad': info.get('dependencia'),
                        'ramo': info.get('ramo'),
                        'unidad_compradora': info.get('unidad_compradora'),
                        'metodo_extraccion': 'manual_playwright'
                    },
                    'contenido_bruto': await self.page.text_content('body')
                }
                
                return detalle
            else:
                print("No se pudo extraer información específica")
                return None
                
        except Exception as e:
            logger.error(f"Error extrayendo detalle: {e}")
            return None
    
    async def guardar_detalle(self, detalle):
        """Guardar detalle como archivo JSON"""
        codigo = detalle.get('codigo_expediente', 'UNKNOWN')
        filename = f"detalle_{codigo}.json"
        filepath = self.detalles_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(detalle, f, ensure_ascii=False, indent=2)
        
        self.detalles_extraidos[codigo] = detalle
        logger.info(f"Guardado: {filepath}")
    
    async def mostrar_estadisticas(self):
        """Mostrar estadísticas de extracción"""
        print(f"\n=== ESTADÍSTICAS ===")
        print(f"Detalles extraídos: {len(self.detalles_extraidos)}")
        print(f"Carpeta: {self.detalles_dir}")
        
        if self.detalles_extraidos:
            print("\nArchivos creados:")
            for codigo in self.detalles_extraidos.keys():
                print(f"  - detalle_{codigo}.json")
    
    async def ejecutar(self):
        """Ejecutar scraper manual"""
        try:
            await self.inicializar()
            await self.page.goto('https://comprasmx.buengobierno.gob.mx/sitiopublico/#/')
            
            print("\n" + "="*60)
            print("SCRAPER MANUAL COMPRASMX")
            print("="*60)
            print("INSTRUCCIONES:")
            print("1. Navega manualmente a cualquier página")
            print("2. Presiona ENTER para extraer información de la página actual")
            print("3. Escribe 'stats' para ver estadísticas")
            print("4. Escribe 'quit' para salir")
            print("="*60)
            
            while True:
                comando = input("\nPresiona ENTER para extraer, 'stats' para estadísticas, 'quit' para salir: ").strip()
                
                if comando.lower() == 'quit':
                    break
                elif comando.lower() == 'stats':
                    await self.mostrar_estadisticas()
                else:
                    # Extraer página actual
                    exito = await self.extraer_pagina_actual()
                    if exito:
                        print("✅ Información extraída y guardada")
                    else:
                        print("⚠️ No se extrajo información específica")
            
            await self.mostrar_estadisticas()
            
        except KeyboardInterrupt:
            print("\nSaliendo...")
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await self.cerrar()
    
    async def cerrar(self):
        """Cerrar recursos"""
        try:
            if hasattr(self, 'browser'):
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error cerrando: {e}")

async def main():
    scraper = ScraperManual()
    await scraper.ejecutar()

if __name__ == "__main__":
    asyncio.run(main())
