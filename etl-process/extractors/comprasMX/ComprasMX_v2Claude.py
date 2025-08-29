#!/usr/bin/env python3
"""
Scraper ComprasMX corregido para la estructura real de la API
Captura TODOS los 1490+ expedientes navegando por las 15 páginas
+ NUEVA FUNCIONALIDAD: Extracción de detalles individuales
"""

import asyncio
import os
import re
import json
import hashlib
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from playwright.async_api import async_playwright
from datetime import datetime
from typing import Dict, List, Set, Optional

# Configuración de directorios
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent  # ../../../
SALIDA = project_root / "data" / "raw" / "comprasmx"
SALIDA.mkdir(parents=True, exist_ok=True)

print(f"[INFO] Scraper ComprasMX - Guardando archivos en: {SALIDA.absolute()}")

class ComprasMXScraper:
    def __init__(self, salida_dir: Path = SALIDA):
        self.salida_dir = salida_dir
        self.respuestas_capturadas = []
        self.urls_procesadas = set()
        self.expedientes_totales = []
        self.expedientes_ids = set()
        self.pagina_actual = 1
        self.total_paginas = None
        self.total_registros = None
        
        # NUEVO: Para extracción de detalles individuales
        self.detalles_extraidos = {}
        self.carpeta_detalles = self.salida_dir / "detalles"
        self.carpeta_detalles.mkdir(parents=True, exist_ok=True)
        self.extraer_detalles = True  # Flag para habilitar/deshabilitar extracción de detalles
        
    def nombre_archivo(self, url: str, content_type: str, incluir_timestamp: bool = True) -> Path:
        """Genera un nombre estable y legible por URL + query."""
        u = urlparse(url)
        base = u.path.strip("/").replace("/", "_")
        if not base:
            base = "root"
        
        if u.query:
            q = "&".join(sorted([f"{k}={v}" for k, v in parse_qsl(u.query)]))
            h = hashlib.sha1(q.encode("utf-8")).hexdigest()[:10]
            base = f"{base}_{h}"
        
        ext = ".json"
        if "pdf" in content_type:
            ext = ".pdf"
        elif "html" in content_type:
            ext = ".html"
        
        if incluir_timestamp:
            ts = time.strftime("%Y%m%d-%H%M%S")
            return self.salida_dir / f"{ts}_{base}{ext}"
        else:
            return self.salida_dir / f"{base}{ext}"
    
    async def capturar_respuesta(self, response):
        """Captura y analiza respuestas de la API."""
        url = response.url
        
        # Solo procesar URLs de expedientes
        if "whitney/sitiopublico/expedientes" not in url:
            return
        
        ctype = (response.headers or {}).get("content-type", "").lower()
        
        try:
            if "application/json" in ctype or "json" in ctype:
                data = await response.json()
                
                # Guardar respuesta
                ruta = self.nombre_archivo(url, ctype)
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"\n[OK] JSON guardado: {ruta.name}")
                
                # Procesar datos según la estructura real
                if isinstance(data, dict) and "data" in data:
                    for item in data["data"]:
                        # Procesar registros (expedientes)
                        if "registros" in item and isinstance(item["registros"], list):
                            nuevos_expedientes = 0
                            for exp in item["registros"]:
                                # Usar cod_expediente como ID único
                                if "cod_expediente" in exp and exp["cod_expediente"] not in self.expedientes_ids:
                                    self.expedientes_ids.add(exp["cod_expediente"])
                                    self.expedientes_totales.append(exp)
                                    nuevos_expedientes += 1
                            
                            print(f"  └─ Nuevos expedientes en esta respuesta: {nuevos_expedientes}")
                            print(f"  └─ Total expedientes únicos capturados: {len(self.expedientes_ids)}")
                        
                        # Extraer información de paginación
                        if "paginacion" in item and isinstance(item["paginacion"], list):
                            for pag_info in item["paginacion"]:
                                self.pagina_actual = pag_info.get("pagina_actual", 1)
                                self.total_paginas = pag_info.get("total_paginas", 1)
                                self.total_registros = pag_info.get("total_registros", 0)
                                
                                print(f"  └─ Paginación: Página {self.pagina_actual}/{self.total_paginas}")
                                print(f"  └─ Total registros en el sistema: {self.total_registros}")
                                print(f"  └─ Registros en esta página: {pag_info.get('registros_pagina', 0)}")
                
                # Guardar respuesta para análisis
                self.respuestas_capturadas.append({
                    "url": url,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            print(f"[ERROR] No se pudo procesar {url}: {e}")
    
    async def procesar_licitaciones_en_pagina_actual(self, page):
        """NUEVA FUNCIÓN: Procesa cada licitación individual de la página actual"""
        if not self.extraer_detalles:
            return
            
        print(f"\n=== EXTRAYENDO DETALLES INDIVIDUALES - PÁGINA {self.pagina_actual} ===")
        
        # Selectores para encontrar enlaces/botones de licitaciones
        selectores_licitacion = [
            "a[href*='expediente']",
            "a[href*='procedimiento']",
            "button:has-text('Ver detalle')",
            "button:has-text('Ver')",
            "a:has-text('Ver detalle')",
            ".expediente-link",
            ".licitacion-item a",
            "tr[data-id] a",
            "[data-expediente] a"
        ]
        
        licitaciones_en_pagina = []
        
        # Buscar todos los posibles enlaces de licitaciones
        for selector in selectores_licitacion:
            try:
                elementos = await page.locator(selector).all()
                for elemento in elementos:
                    if await elemento.is_visible():
                        href = await elemento.get_attribute("href")
                        texto = await elemento.text_content()
                        
                        if href and (href not in [l.get("href") for l in licitaciones_en_pagina]):
                            licitaciones_en_pagina.append({
                                "elemento": elemento,
                                "href": href,
                                "texto": texto.strip() if texto else "",
                                "selector": selector
                            })
            except Exception as e:
                print(f"  ⚠️ Error con selector {selector}: {e}")
                continue
        
        print(f"  └─ Encontradas {len(licitaciones_en_pagina)} licitaciones potenciales en la página")
        
        # Procesar cada licitación individual
        for i, licitacion in enumerate(licitaciones_en_pagina, 1):
            try:
                print(f"  \n[{i}/{len(licitaciones_en_pagina)}] Procesando: {licitacion['texto']}")
                
                # Obtener el código de expediente del href
                codigo_expediente = self.extraer_codigo_expediente_de_url(licitacion['href'])
                if not codigo_expediente:
                    print(f"    ⚠️ No se pudo extraer código de expediente del URL: {licitacion['href']}")
                    continue
                
                # Verificar si ya procesamos este detalle
                if codigo_expediente in self.detalles_extraidos:
                    print(f"    ✓ Detalle ya procesado: {codigo_expediente}")
                    continue
                
                # Hacer click en la licitación
                await licitacion['elemento'].click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)
                
                # Capturar información de la página de detalle
                url_completa = page.url
                contenido_html = await page.content()
                
                # Extraer información estructurada de la página
                informacion_extraida = await self.extraer_informacion_detalle(page)
                
                # Crear objeto de detalle
                detalle = {
                    "codigo_expediente": codigo_expediente,
                    "url_completa_con_hash": url_completa,
                    "contenido_html": contenido_html,
                    "informacion_extraida": informacion_extraida,
                    "timestamp_procesamiento": datetime.now().isoformat(),
                    "procesado_exitosamente": True,
                    "pagina_origen": self.pagina_actual
                }
                
                # Guardar detalle individual
                await self.guardar_detalle_individual(codigo_expediente, detalle)
                self.detalles_extraidos[codigo_expediente] = detalle
                
                print(f"    ✓ Detalle extraído y guardado: {codigo_expediente}")
                
                # Volver al listado
                await page.go_back()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)
                
                print(f"    ✓ Regresado al listado")
                
            except Exception as e:
                print(f"    ❌ Error procesando licitación {i}: {e}")
                
                # Intentar volver al listado en caso de error
                try:
                    await page.go_back()
                    await page.wait_for_timeout(2000)
                except:
                    # Si falla go_back, navegar directamente al listado
                    await page.goto(
                        "https://comprasmx.buengobierno.gob.mx/sitiopublico/#/",
                        wait_until="domcontentloaded"
                    )
                    await page.wait_for_timeout(3000)
                
                continue
        
        print(f"  \n✓ Página {self.pagina_actual} completada. Detalles extraídos: {len(self.detalles_extraidos)}")
    
    def extraer_codigo_expediente_de_url(self, url: str) -> Optional[str]:
        """Extrae el código de expediente de una URL"""
        if not url:
            return None
        
        # Patrones comunes para extraer código de expediente
        patrones = [
            r'/expediente/([^/?#]+)',
            r'/procedimiento/([^/?#]+)', 
            r'expediente=([^&/#]+)',
            r'codigo=([^&/#]+)',
            r'id=([^&/#]+)'
        ]
        
        for patron in patrones:
            match = re.search(patron, url)
            if match:
                return match.group(1)
        
        return None
    
    async def extraer_informacion_detalle(self, page) -> Dict:
        """Extrae información estructurada de la página de detalle"""
        try:
            informacion = {
                "descripcion_completa": "",
                "documentos_adjuntos": [],
                "fechas_detalladas": {},
                "ubicacion_especifica": "",
                "contacto": {},
                "montos_detallados": {},
                "requisitos": [],
                "cronograma": []
            }
            
            # Extraer descripción completa
            try:
                desc_selectores = [
                    ".descripcion", ".description", 
                    ".detalle", ".detail",
                    ".contenido", ".content",
                    "p:has-text('Descripción')",
                    ".procedimiento-descripcion"
                ]
                
                for selector in desc_selectores:
                    elemento = page.locator(selector).first
                    if await elemento.is_visible():
                        texto = await elemento.text_content()
                        if texto and len(texto.strip()) > 50:
                            informacion["descripcion_completa"] = texto.strip()
                            break
            except:
                pass
            
            # Extraer documentos adjuntos
            try:
                doc_selectores = [
                    "a[href*='.pdf']",
                    "a[href*='.doc']", 
                    "a[href*='.xlsx']",
                    ".documentos a",
                    ".adjuntos a",
                    ".archivos a"
                ]
                
                for selector in doc_selectores:
                    elementos = await page.locator(selector).all()
                    for elemento in elementos:
                        href = await elemento.get_attribute("href")
                        texto = await elemento.text_content()
                        if href:
                            informacion["documentos_adjuntos"].append({
                                "nombre": texto.strip() if texto else "Documento",
                                "url": href
                            })
            except:
                pass
            
            # Extraer fechas detalladas
            try:
                fecha_selectores = [
                    ":has-text('Fecha')",
                    ":has-text('fecha')",
                    ".fecha", ".date",
                    ".cronograma", ".timeline"
                ]
                
                for selector in fecha_selectores:
                    elementos = await page.locator(selector).all()
                    for elemento in elementos:
                        texto = await elemento.text_content()
                        if texto and any(palabra in texto.lower() for palabra in ['fecha', 'plazo', 'vencimiento']):
                            # Extraer fechas del texto
                            fechas_encontradas = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', texto)
                            if fechas_encontradas:
                                informacion["fechas_detalladas"][texto[:50]] = fechas_encontradas
            except:
                pass
            
            # Extraer información de contacto
            try:
                contacto_selectores = [
                    ":has-text('Contacto')",
                    ":has-text('contacto')",
                    ":has-text('Email')",
                    ":has-text('Teléfono')",
                    ".contacto", ".contact"
                ]
                
                for selector in contacto_selectores:
                    elementos = await page.locator(selector).all()
                    for elemento in elementos:
                        texto = await elemento.text_content()
                        if texto:
                            # Extraer emails
                            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', texto)
                            if emails:
                                informacion["contacto"]["emails"] = emails
                            
                            # Extraer teléfonos
                            telefonos = re.findall(r'\b\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{4}\b', texto)
                            if telefonos:
                                informacion["contacto"]["telefonos"] = telefonos
            except:
                pass
            
            return informacion
            
        except Exception as e:
            print(f"    ⚠️ Error extrayendo información detallada: {e}")
            return {}
    
    async def guardar_detalle_individual(self, codigo_expediente: str, detalle: Dict):
        """Guarda el detalle individual en un archivo JSON"""
        try:
            # Limpiar código de expediente para nombre de archivo
            codigo_limpio = re.sub(r'[^\w\-_.]', '_', codigo_expediente)
            archivo_detalle = self.carpeta_detalles / f"detalle_{codigo_limpio}.json"
            
            with open(archivo_detalle, "w", encoding="utf-8") as f:
                json.dump(detalle, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"    ❌ Error guardando detalle {codigo_expediente}: {e}")
    
    async def navegar_todas_las_paginas(self, page):
        """Navega por todas las páginas usando la información de paginación."""
        print("\n=== NAVEGANDO POR TODAS LAS PÁGINAS ===")
        
        # Esperar a que se cargue la primera página
        await page.wait_for_timeout(5000)
        
        # NUEVO: Procesar licitaciones de la primera página
        if self.extraer_detalles:
            await self.procesar_licitaciones_en_pagina_actual(page)
        
        # Si conocemos el total de páginas, navegar por todas
        if self.total_paginas and self.total_paginas > 1:
            print(f"\nDetectadas {self.total_paginas} páginas con {self.total_registros} registros totales")
            
            for pagina in range(2, self.total_paginas + 1):
                print(f"\n[Navegando a página {pagina}/{self.total_paginas}]")
                
                # Método 1: Buscar botón de página específica
                exito = False
                
                # Intentar click en número de página
                try:
                    # Buscar botón con el número de página
                    boton_pagina = page.locator(f"button:has-text('{pagina}')").first
                    if await boton_pagina.is_visible():
                        await boton_pagina.click()
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(3000)
                        print(f"  ✓ Click en botón de página {pagina}")
                        exito = True
                except:
                    pass
                
                # Método 2: Buscar botón "Siguiente"
                if not exito:
                    botones_siguiente = [
                        "button:has-text('Siguiente')",
                        "button:has-text('>')",
                        "[aria-label*='next' i]",
                        "[aria-label*='siguiente' i]",
                        "button.next",
                        "button.btn-next",
                        "a:has-text('Siguiente')",
                        "a:has-text('>')"
                    ]
                    
                    for selector in botones_siguiente:
                        try:
                            boton = page.locator(selector).first
                            if await boton.is_visible() and await boton.is_enabled():
                                await boton.click()
                                await page.wait_for_load_state("networkidle")
                                await page.wait_for_timeout(3000)
                                print(f"  ✓ Click en botón siguiente")
                                exito = True
                                break
                        except:
                            pass
                
                # Método 3: Input de página
                if not exito:
                    try:
                        input_pagina = page.locator("input[type='number']").first
                        if await input_pagina.is_visible():
                            await input_pagina.fill(str(pagina))
                            await input_pagina.press("Enter")
                            await page.wait_for_load_state("networkidle")
                            await page.wait_for_timeout(3000)
                            print(f"  ✓ Navegado mediante input de página")
                            exito = True
                    except:
                        pass
                
                # Método 4: Modificar URL con parámetro de página
                if not exito:
                    try:
                        # Intentar navegar directamente modificando el hash
                        current_url = page.url
                        if "#" in current_url:
                            # Intentar agregar parámetro de página al URL
                            await page.evaluate(f"window.location.hash = window.location.hash + '&page={pagina}'")
                            await page.wait_for_timeout(3000)
                            print(f"  ✓ Navegado mediante modificación de URL")
                    except:
                        pass
                
                # NUEVO: Procesar licitaciones de esta página
                if self.extraer_detalles:
                    await self.procesar_licitaciones_en_pagina_actual(page)
                
                # Verificar progreso
                print(f"  └─ Expedientes capturados hasta ahora: {len(self.expedientes_ids)}/{self.total_registros}")
                
                # Si hemos capturado casi todos los registros, podemos parar
                if len(self.expedientes_ids) >= self.total_registros * 0.95:
                    print(f"\n✓ Capturados {len(self.expedientes_ids)} de {self.total_registros} registros (95%+)")
                    break
        
        else:
            # Si no hay información de paginación, intentar scroll y botones genéricos
            print("\nNo se detectó información de paginación, intentando métodos alternativos...")
            
            for intento in range(5):
                expedientes_antes = len(self.expedientes_ids)
                
                # Scroll
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                
                # Buscar botón siguiente
                try:
                    boton = page.locator("button:has-text('>')").first
                    if await boton.is_visible():
                        await boton.click()
                        await page.wait_for_timeout(3000)
                except:
                    pass
                
                if len(self.expedientes_ids) > expedientes_antes:
                    print(f"  ✓ Intento {intento + 1}: Nuevos expedientes cargados")
                    
                    # NUEVO: Procesar licitaciones si hay nuevos datos
                    if self.extraer_detalles:
                        await self.procesar_licitaciones_en_pagina_actual(page)
                        
                else:
                    print(f"  ✗ Intento {intento + 1}: Sin nuevos datos")
                    if intento >= 2:
                        break
    
    async def cambiar_cantidad_resultados(self, page):
        """Intenta cambiar la cantidad de resultados por página al máximo."""
        print("\n=== CAMBIANDO CANTIDAD DE RESULTADOS ===")
        
        selectores = [
            "select",
            "[class*='per-page']",
            "[class*='page-size']",
            "[class*='items-per']"
        ]
        
        for selector in selectores:
            try:
                elementos = await page.locator(selector).all()
                for elemento in elementos:
                    if await elemento.is_visible():
                        # Intentar seleccionar el valor máximo
                        opciones = await elemento.locator("option").all()
                        valores = []
                        for opcion in opciones:
                            texto = await opcion.text_content()
                            if texto and texto.strip().isdigit():
                                valores.append(int(texto.strip()))
                        
                        if valores:
                            max_valor = max(valores)
                            if max_valor > 10:  # Solo cambiar si hay opción mayor a 10
                                print(f"  └─ Cambiando a mostrar {max_valor} resultados por página")
                                await elemento.select_option(str(max_valor))
                                await page.wait_for_timeout(3000)
                                return True
            except:
                pass
        
        print("  └─ No se encontró selector de cantidad (usando valor por defecto)")
        return False
    
    async def ejecutar(self, headless: bool = True, extraer_detalles: bool = True):
        """Ejecuta el scraper completo."""
        self.extraer_detalles = extraer_detalles
        
        print(f"\n{'='*60}")
        print(f"SCRAPER COMPRASMX - CAPTURA COMPLETA")
        print(f"Hora: {datetime.now()}")
        print(f"Modo: {'Headless' if headless else 'Visible'}")
        print(f"Extraer detalles: {'Sí' if extraer_detalles else 'No'}")
        print(f"{'='*60}\n")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                locale="es-MX",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = await context.new_page()
            
            # Configurar interceptor de respuestas
            page.on("response", lambda r: asyncio.create_task(self.capturar_respuesta(r)))
            
            # 1. Cargar página principal
            print("[1/4] Abriendo ComprasMX...")
            await page.goto(
                "https://comprasmx.buengobierno.gob.mx/sitiopublico/#/",
                wait_until="domcontentloaded"
            )
            
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(10000)
            
            print(f"  └─ Primera carga: {len(self.expedientes_ids)} expedientes")
            
            # 2. Intentar maximizar resultados por página
            print("\n[2/4] Optimizando cantidad de resultados...")
            await self.cambiar_cantidad_resultados(page)
            await page.wait_for_timeout(3000)
            
            # 3. Navegar por todas las páginas
            print("\n[3/4] Navegando por todas las páginas...")
            await self.navegar_todas_las_paginas(page)
            
            # 4. Guardar resultados
            print("\n[4/4] Guardando resultados...")
            await self.guardar_resultados()
            
            await browser.close()
            
            # Mostrar estadísticas finales
            self.mostrar_estadisticas()
    
    async def guardar_resultados(self):
        """Guarda todos los expedientes capturados."""
        # Guardar todos los expedientes en un solo archivo
        archivo_expedientes = self.salida_dir / f"todos_expedientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(archivo_expedientes, "w", encoding="utf-8") as f:
            json.dump({
                "fecha_captura": datetime.now().isoformat(),
                "total_expedientes": len(self.expedientes_totales),
                "expedientes": self.expedientes_totales
            }, f, ensure_ascii=False, indent=2)
        print(f"  └─ Todos los expedientes guardados en: {archivo_expedientes.name}")
        
        # Guardar resumen
        resumen = {
            "fecha_captura": datetime.now().isoformat(),
            "total_expedientes_capturados": len(self.expedientes_ids),
            "total_registros_sistema": self.total_registros,
            "total_paginas_sistema": self.total_paginas,
            "porcentaje_capturado": (len(self.expedientes_ids) / self.total_registros * 100) if self.total_registros else 0,
            "codigos_expedientes": sorted(list(self.expedientes_ids)),
            # NUEVO: Información de detalles extraídos
            "detalles_extraidos": len(self.detalles_extraidos),
            "porcentaje_detalles": (len(self.detalles_extraidos) / len(self.expedientes_ids) * 100) if self.expedientes_ids else 0
        }
        
        archivo_resumen = self.salida_dir / f"resumen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(archivo_resumen, "w", encoding="utf-8") as f:
            json.dump(resumen, f, ensure_ascii=False, indent=2)
        print(f"  └─ Resumen guardado en: {archivo_resumen.name}")
        
        # NUEVO: Guardar índice de detalles extraídos
        if self.detalles_extraidos:
            indice_detalles = {
                "fecha_creacion": datetime.now().isoformat(),
                "total_detalles": len(self.detalles_extraidos),
                "detalles": {
                    codigo: {
                        "archivo": f"detalle_{re.sub(r'[^\\w\\-_.]', '_', codigo)}.json",
                        "url_completa": detalle.get("url_completa_con_hash", ""),
                        "procesado_en": detalle.get("timestamp_procesamiento", ""),
                        "pagina_origen": detalle.get("pagina_origen", 0)
                    }
                    for codigo, detalle in self.detalles_extraidos.items()
                }
            }
            
            archivo_indice = self.carpeta_detalles / "indice_detalles.json"
            with open(archivo_indice, "w", encoding="utf-8") as f:
                json.dump(indice_detalles, f, ensure_ascii=False, indent=2)
            print(f"  └─ Índice de detalles guardado en: {archivo_indice.name}")
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas finales."""
        print(f"\n{'='*60}")
        print("ESTADÍSTICAS FINALES")
        print(f"{'='*60}")
        print(f"✓ Expedientes capturados: {len(self.expedientes_ids)}")
        print(f"✓ Total en el sistema: {self.total_registros}")
        if self.total_registros:
            porcentaje = (len(self.expedientes_ids) / self.total_registros * 100)
            print(f"✓ Porcentaje capturado: {porcentaje:.1f}%")
        print(f"✓ Páginas procesadas: {self.pagina_actual}/{self.total_paginas}")
        
        # NUEVO: Estadísticas de detalles
        if self.extraer_detalles:
            print(f"✓ Detalles individuales extraídos: {len(self.detalles_extraidos)}")
            if self.expedientes_ids:
                porcentaje_detalles = (len(self.detalles_extraidos) / len(self.expedientes_ids) * 100)
                print(f"✓ Cobertura de detalles: {porcentaje_detalles:.1f}%")
            print(f"✓ Archivos de detalles en: {self.carpeta_detalles}")
        
        print(f"✓ Archivos guardados en: {self.salida_dir.absolute()}")
        
        if self.expedientes_totales:
            print(f"\nPrimeros 3 expedientes:")
            for i, exp in enumerate(self.expedientes_totales[:3], 1):
                print(f"  {i}. {exp.get('cod_expediente')} - {exp.get('nombre_procedimiento', 'Sin nombre')}")
        
        print(f"\n{'='*60}")
        print(f"Captura completada: {datetime.now()}")
        print(f"{'='*60}\n")


async def main():
    """Función principal."""
    scraper = ComprasMXScraper()
    
    # Ejecutar con headless=False para ver el navegador (debug)
    # extraer_detalles=True para activar la nueva funcionalidad
    await scraper.ejecutar(headless=True, extraer_detalles=True)


if __name__ == "__main__":
    asyncio.run(main())
