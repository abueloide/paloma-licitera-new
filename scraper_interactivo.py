#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRAPER INTERACTIVO COMPRASMX
Extrae detalles individuales con navegador visible
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
import logging
from playwright.async_api import async_playwright

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScraperInteractivo:
    def __init__(self):
        self.data_dir = Path("data/raw/comprasmx")
        self.detalles_dir = self.data_dir / "detalles"
        self.detalles_dir.mkdir(parents=True, exist_ok=True)
        
        self.detalles_extraidos = {}
        self.url_actual = ""
        self.procesando = False
        
    async def inicializar(self):
        """Inicializar navegador visible"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        self.context = await self.browser.new_context(
            viewport=None,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()
        
        # Configurar listener para detectar cambios de URL
        self.page.on("load", self.on_page_load)
        
        logger.info("🌐 Navegador iniciado - Abriendo ComprasMX...")
        
    async def on_page_load(self):
        """Se ejecuta cada vez que carga una nueva página"""
        if self.procesando:
            return
            
        url = self.page.url
        
        # Detectar si estamos en una página de detalle de licitación
        if self.es_pagina_detalle(url) and url != self.url_actual:
            self.url_actual = url
            await self.extraer_detalle_actual()
    
    def es_pagina_detalle(self, url):
        """Verificar si la URL es una página de detalle de licitación"""
        patrones = [
            r'/sitiopublico/detalle/',
            r'/expedientes/[a-f0-9-]+',
            r'id_proceso=procedimiento'
        ]
        return any(re.search(patron, url) for patron in patrones)
    
    async def extraer_detalle_actual(self):
        """Extraer información de la página de detalle actual"""
        if self.procesando:
            return
            
        self.procesando = True
        
        try:
            logger.info(f"📄 Extrayendo detalle de: {self.url_actual}")
            
            # Esperar a que la página cargue completamente
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Extraer información
            detalle = await self.extraer_informacion_pagina()
            
            if detalle and detalle.get('codigo_expediente'):
                # Guardar detalle
                await self.guardar_detalle(detalle)
                
                codigo = detalle['codigo_expediente']
                self.detalles_extraidos[codigo] = detalle
                
                logger.info(f"✅ Detalle guardado: {codigo}")
                logger.info(f"📊 Total detalles extraídos: {len(self.detalles_extraidos)}")
            else:
                logger.warning("⚠️ No se pudo extraer información válida")
                
        except Exception as e:
            logger.error(f"❌ Error extrayendo detalle: {e}")
        finally:
            self.procesando = False
    
    async def extraer_informacion_pagina(self):
        """Extraer toda la información de la página de detalle"""
        try:
            # Información básica
            codigo_expediente = await self.extraer_texto("text=Código del expediente:")
            numero_procedimiento = await self.extraer_texto("text=Número de procedimiento de contratación:")
            estatus = await self.extraer_texto("text=Estatus del procedimiento de contratación:")
            
            # Datos generales  
            dependencia = await self.extraer_texto("text=Dependencia o Entidad:")
            ramo = await self.extraer_texto("text=Ramo:")
            unidad_compradora = await self.extraer_texto("text=Unidad compradora:")
            responsable = await self.extraer_texto("text=Responsable de la captura:")
            correo = await self.extraer_texto("text=Correo electrónico unidad compradora:")
            
            # Descripción detallada
            descripcion_completa = await self.extraer_texto("text=Descripción detallada del procedimiento de contratación:")
            
            # Información de procedimiento
            referencia = await self.extraer_texto("text=Referencia / Número de control interno:")
            nombre_procedimiento = await self.extraer_texto("text=Nombre del procedimiento de contratación:")
            ley_soporte = await self.extraer_texto("text=Ley/Soporte normativo que rige la contratación:")
            tipo_procedimiento = await self.extraer_texto("text=Tipo de procedimiento de contratación:")
            fundamento_legal = await self.extraer_texto("text=Fundamento legal de la Contratación:")
            
            # Construir objeto detalle
            detalle = {
                'codigo_expediente': self.limpiar_texto(codigo_expediente),
                'url_completa_con_hash': self.url_actual,
                'timestamp_procesamiento': datetime.now().isoformat(),
                'pagina_origen': 'ComprasMX - Scraper Interactivo',
                'procesado_exitosamente': True,
                'informacion_extraida': {
                    'numero_procedimiento': self.limpiar_texto(numero_procedimiento),
                    'estatus': self.limpiar_texto(estatus),
                    'descripcion_completa': self.limpiar_texto(descripcion_completa),
                    'nombre_procedimiento': self.limpiar_texto(nombre_procedimiento),
                    'dependencia_entidad': self.limpiar_texto(dependencia),
                    'ramo': self.limpiar_texto(ramo),
                    'unidad_compradora': self.limpiar_texto(unidad_compradora),
                    'responsable_captura': self.limpiar_texto(responsable),
                    'correo_electronico': self.limpiar_texto(correo),
                    'referencia_control': self.limpiar_texto(referencia),
                    'ley_soporte': self.limpiar_texto(ley_soporte),
                    'tipo_procedimiento': self.limpiar_texto(tipo_procedimiento),
                    'fundamento_legal': self.limpiar_texto(fundamento_legal),
                    'contacto': {
                        'emails': [self.limpiar_texto(correo)] if correo else [],
                        'responsable': self.limpiar_texto(responsable)
                    }
                }
            }
            
            # Buscar documentos adjuntos si existen
            documentos = await self.extraer_documentos()
            if documentos:
                detalle['informacion_extraida']['documentos_adjuntos'] = documentos
            
            return detalle
            
        except Exception as e:
            logger.error(f"Error extrayendo información: {e}")
            return None
    
    async def extraer_texto(self, selector, siguiente=True):
        """Extraer texto después de un label específico"""
        try:
            # Buscar el elemento que contiene el texto del label
            elemento = self.page.locator(selector)
            
            if await elemento.count() > 0:
                if siguiente:
                    # Buscar el siguiente elemento que contenga el valor
                    parent = elemento.locator("xpath=..")
                    texto = await parent.text_content()
                    
                    # Extraer solo la parte después del label
                    label_texto = await elemento.text_content()
                    if label_texto in texto:
                        valor = texto.replace(label_texto, "").strip()
                        return valor if valor else None
                else:
                    return await elemento.text_content()
            
            return None
            
        except Exception as e:
            logger.debug(f"No se pudo extraer texto para '{selector}': {e}")
            return None
    
    async def extraer_documentos(self):
        """Extraer enlaces de documentos adjuntos"""
        try:
            documentos = []
            
            # Buscar enlaces de documentos
            enlaces = self.page.locator("a[href*='.pdf'], a[href*='.doc'], a[href*='.xls']")
            count = await enlaces.count()
            
            for i in range(count):
                enlace = enlaces.nth(i)
                href = await enlace.get_attribute('href')
                texto = await enlace.text_content()
                
                if href and texto:
                    documentos.append({
                        'nombre': texto.strip(),
                        'url': href,
                        'tipo': 'documento'
                    })
            
            return documentos
            
        except Exception as e:
            logger.debug(f"Error extrayendo documentos: {e}")
            return []
    
    def limpiar_texto(self, texto):
        """Limpiar y normalizar texto extraído"""
        if not texto:
            return None
            
        # Limpiar espacios extras y caracteres especiales
        texto = re.sub(r'\s+', ' ', str(texto).strip())
        texto = texto.replace('\n', ' ').replace('\t', ' ')
        
        return texto if texto and texto != '-' else None
    
    async def guardar_detalle(self, detalle):
        """Guardar detalle individual como archivo JSON"""
        codigo = detalle['codigo_expediente']
        if not codigo:
            return
            
        filename = f"detalle_{codigo}.json"
        filepath = self.detalles_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(detalle, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Guardado: {filepath}")
    
    async def guardar_indice_detalles(self):
        """Guardar índice de todos los detalles extraídos"""
        indice = {
            'fecha_creacion': datetime.now().isoformat(),
            'total_detalles': len(self.detalles_extraidos),
            'detalles': {
                codigo: {
                    'archivo': f"detalle_{codigo}.json",
                    'url': detalle.get('url_completa_con_hash'),
                    'timestamp': detalle.get('timestamp_procesamiento')
                }
                for codigo, detalle in self.detalles_extraidos.items()
            }
        }
        
        indice_path = self.detalles_dir / "indice_detalles.json"
        with open(indice_path, 'w', encoding='utf-8') as f:
            json.dump(indice, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📋 Índice actualizado: {len(self.detalles_extraidos)} detalles")
    
    async def ejecutar(self):
        """Ejecutar scraper interactivo"""
        try:
            await self.inicializar()
            
            # Navegar a ComprasMX
            await self.page.goto('https://comprasmx.buengobierno.gob.mx/sitiopublico/#/')
            
            logger.info("🎯 ComprasMX abierto - Navega manualmente a las licitaciones")
            logger.info("📝 El script detectará automáticamente cuando entres a una página de detalle")
            logger.info("⚡ Presiona Ctrl+C para terminar y guardar el índice final")
            
            # Mantener el script corriendo
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("\n🛑 Deteniendo scraper...")
                
                # Guardar índice final
                await self.guardar_indice_detalles()
                
                logger.info(f"✅ Sesión completada:")
                logger.info(f"   📊 Detalles extraídos: {len(self.detalles_extraidos)}")
                logger.info(f"   📁 Guardados en: {self.detalles_dir}")
                
        except Exception as e:
            logger.error(f"Error en scraper interactivo: {e}")
        finally:
            await self.cerrar()
    
    async def cerrar(self):
        """Cerrar navegador y recursos"""
        try:
            if hasattr(self, 'browser'):
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error cerrando recursos: {e}")

async def main():
    print("""
🎯 SCRAPER INTERACTIVO COMPRASMX
================================

INSTRUCCIONES:
1. Se abrirá Chrome automáticamente
2. Navega manualmente a las licitaciones que te interesen
3. Cuando entres a una página de detalle, se extraerá automáticamente
4. Los archivos se guardan en data/raw/comprasmx/detalles/
5. Presiona Ctrl+C para terminar

COMENZANDO...
    """)
    
    scraper = ScraperInteractivo()
    await scraper.ejecutar()

if __name__ == "__main__":
    asyncio.run(main())
