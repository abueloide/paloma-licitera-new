#!/usr/bin/env python3
"""
Scraper ComprasMX corregido para capturar hash real y descripción completa
MODIFICADO: Capturar window.location.href para obtener hash UUID real de cada licitación
MEJORADO: Extraer descripción detallada completa de cada licitación individual
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
        
        # Para extracción de detalles individuales con hash real
        self.detalles_extraidos = {}
        self.carpeta_detalles = self.salida_dir / "detalles"
        self.carpeta_detalles.mkdir(parents=True, exist_ok=True)
        self.extraer_detalles = True
        
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
                
                print(f"\\n[OK] JSON guardado: {ruta.name}")
                
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
                
                # Guardar respuesta para análisis
                self.respuestas_capturadas.append({
                    "url": url,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            print(f"[ERROR] No se pudo procesar {url}: {e}")
    
    async def procesar_licitaciones_en_pagina_actual(self, page):
        """CORREGIDO: Procesa cada licitación individual capturando hash real y descripción completa"""
        if not self.extraer_detalles:
            return
            
        print(f"\\n=== EXTRAYENDO DETALLES CON HASH REAL - PÁGINA {self.pagina_actual} ===")
        
        try:
            # Esperar a que la tabla se cargue
            await page.wait_for_selector("table", timeout=15000)
            
            # Obtener todas las filas de la tabla (excluyendo header)
            filas_tabla = await page.locator("table tbody tr, table tr:not(:first-child)").all()
            
            if not filas_tabla:
                # Fallback: buscar filas con contenido relevante
                filas_tabla = await page.locator("tr").all()
                filas_filtradas = []
                for fila in filas_tabla:
                    texto = await fila.text_content()
                    # Filtrar headers y filas vacías
                    if texto and not ("Núm." in texto and "Número de identificación" in texto) and len(texto.strip()) > 20:
                        filas_filtradas.append(fila)
                filas_tabla = filas_filtradas
            
            print(f"  └─ Encontradas {len(filas_tabla)} filas de licitaciones")
            
        except Exception as e:
            print(f"  ❌ Error localizando tabla: {e}")
            return
        
        # Procesar cada fila individual
        for i, fila in enumerate(filas_tabla, 1):
            try:
                # Extraer información básica de la fila
                celdas = await fila.locator("td").all()
                if len(celdas) < 3:
                    continue
                
                # Extraer código de expediente (segunda columna)
                codigo_expediente = (await celdas[1].text_content()).strip()
                if not codigo_expediente or len(codigo_expediente) < 5:
                    continue
                
                # Extraer título preliminar (tercera o cuarta columna)
                titulo_preliminar = ""
                if len(celdas) >= 4:
                    titulo_preliminar = (await celdas[3].text_content()).strip()
                elif len(celdas) >= 3:
                    titulo_preliminar = (await celdas[2].text_content()).strip()
                
                print(f"\\n[{i}/{len(filas_tabla)}] Procesando: {codigo_expediente}")
                print(f"    └─ {titulo_preliminar[:60]}...")
                
                # Verificar si ya procesamos este detalle
                if codigo_expediente in self.detalles_extraidos:
                    print(f"    ✓ Ya procesado: {codigo_expediente}")
                    continue
                
                # PASO CLAVE: Hacer click y navegar al detalle
                await fila.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(5000)  # Tiempo extra para carga completa
                
                # CAPTURAR HASH REAL DE LA URL usando window.location.href
                url_completa_real = await page.evaluate("window.location.href")
                print(f"    🌐 URL completa capturada: {url_completa_real}")
                
                # Extraer hash UUID de la URL
                hash_uuid = self.extraer_hash_de_url(url_completa_real)
                if hash_uuid:
                    print(f"    🔑 Hash UUID extraído: {hash_uuid}")
                else:
                    print(f"    ⚠️ No se pudo extraer hash UUID de la URL")
                
                # EXTRAER DESCRIPCIÓN DETALLADA COMPLETA
                descripcion_completa = await self.extraer_descripcion_completa(page)
                print(f"    📝 Descripción extraída: {len(descripcion_completa)} caracteres")
                
                # Extraer información estructurada completa
                informacion_extraida = await self.extraer_informacion_detalle_comprasmx(page)
                
                # INTEGRAR HASH REAL EN LA INFORMACIÓN
                if hash_uuid:
                    informacion_extraida["hash_uuid_real"] = hash_uuid
                
                if descripcion_completa:
                    informacion_extraida["descripcion_completa"] = descripcion_completa
                
                # Crear objeto de detalle con datos reales
                detalle = {
                    "codigo_expediente": codigo_expediente,
                    "url_completa_con_hash": url_completa_real,
                    "hash_uuid_real": hash_uuid,  # NUEVO: Hash real extraído
                    "descripcion_completa": descripcion_completa,  # NUEVO: Descripción completa
                    "informacion_extraida": informacion_extraida,
                    "timestamp_procesamiento": datetime.now().isoformat(),
                    "procesado_exitosamente": True,
                    "pagina_origen": self.pagina_actual
                }
                
                # Guardar detalle individual
                await self.guardar_detalle_individual(codigo_expediente, detalle)
                self.detalles_extraidos[codigo_expediente] = detalle
                
                print(f"    ✅ Detalle completo guardado: {codigo_expediente}")
                
                # Volver al listado
                await page.go_back()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)
                
            except Exception as e:
                print(f"    ❌ Error procesando licitación {i}: {e}")
                
                # Intentar recuperación volviendo al listado
                try:
                    await page.go_back()
                    await page.wait_for_timeout(3000)
                except:
                    # Si falla, navegar directamente al inicio
                    await page.goto(
                        "https://comprasmx.buengobierno.gob.mx/sitiopublico/#/",
                        wait_until="domcontentloaded"
                    )
                    await page.wait_for_timeout(5000)
                
        print(f"\\n✅ Página {self.pagina_actual} completada. Detalles extraídos: {len(self.detalles_extraidos)}")
    
    def extraer_hash_de_url(self, url_completa: str) -> str:
        """NUEVA FUNCIÓN: Extrae el hash UUID de la URL de ComprasMX"""
        try:
            # Patrón para URLs de ComprasMX con hash
            # Ejemplo: https://comprasmx.buengobierno.gob.mx/sitiopublico/#/sitiopublico/detalle/4b30105081ee4ce5b44aea1bf6eac6dc/procedimiento
            patron = r'\/detalle\/([a-f0-9]{32})\/procedimiento'
            
            match = re.search(patron, url_completa)
            if match:
                return match.group(1)
            
            # Patrón alternativo más general
            patron_alt = r'\/([a-f0-9]{32})\/'
            match_alt = re.search(patron_alt, url_completa)
            if match_alt:
                return match_alt.group(1)
                
            return None
            
        except Exception as e:
            print(f"    ❌ Error extrayendo hash: {e}")
            return None
    
    async def extraer_descripcion_completa(self, page) -> str:
        """NUEVA FUNCIÓN: Extrae la descripción detallada completa de la página"""
        try:
            # Buscar específicamente el campo de descripción detallada
            selectores_descripcion = [
                # Selector específico para el campo de descripción detallada
                "[contains(text(), 'Descripción detallada del procedimiento')]//following-sibling::*[1]",
                # Selector por texto visible
                "xpath=//text()[contains(., 'Descripción detallada')]/following::text()[1]",
                # Selectores de respaldo
                ".descripcion-detallada",
                "[data-field='descripcion_detallada']",
                ".detalle-descripcion"
            ]
            
            # También buscar por patrones de texto en el HTML
            contenido_html = await page.content()
            
            # Patrón para encontrar descripción detallada
            patron_descripcion = r'Descripción detallada del procedimiento de contratación:\s*([^\n]+(?:\n[^\n]+)*?)(?:\nLey/Soporte|$)'
            
            match = re.search(patron_descripcion, contenido_html, re.MULTILINE | re.DOTALL)
            if match:
                descripcion = match.group(1).strip()
                # Limpiar HTML tags si existen
                descripcion = re.sub(r'<[^>]+>', '', descripcion)
                # Limpiar espacios extra
                descripcion = re.sub(r'\s+', ' ', descripcion).strip()
                return descripcion
            
            # Método alternativo: buscar por selectores CSS
            for selector in selectores_descripcion:
                try:
                    if not selector.startswith("xpath="):
                        elemento = page.locator(selector).first
                        if await elemento.is_visible():
                            texto = await elemento.text_content()
                            if texto and len(texto.strip()) > 20:
                                return texto.strip()
                except:
                    continue
            
            return ""
            
        except Exception as e:
            print(f"    ❌ Error extrayendo descripción completa: {e}")
            return ""
    
    async def extraer_informacion_detalle_comprasmx(self, page) -> Dict:
        """Extrae información estructurada específica de ComprasMX con hash real incluido"""
        try:
            informacion = {
                "codigo_expediente": "",
                "numero_procedimiento": "",
                "estatus": "",
                "dependencia_entidad": "",
                "unidad_compradora": "",
                "responsable_captura": "",
                "email_unidad_compradora": "",
                "descripcion_detallada": "",
                "tipo_procedimiento": "",
                "entidad_federativa": "",
                "año_ejercicio": "",
                "fechas_cronograma": {},
                "partidas_especificas": [],
                "datos_especificos": {},
                "documentos_anexos": [],
                "requisitos_economicos": []
            }
            
            # Obtener todo el contenido HTML
            contenido = await page.content()
            
            # Extraer campos usando patrones mejorados
            campos_patrones = [
                ("codigo_expediente", r'Código del expediente:\s*([^\n]+)'),
                ("numero_procedimiento", r'Número de procedimiento de contratación:\s*([^\n]+)'),
                ("estatus", r'Estatus del procedimiento de contratación:\s*([^\n]+)'),
                ("dependencia_entidad", r'Dependencia o Entidad:\s*([^\n]+)'),
                ("unidad_compradora", r'Unidad compradora:\s*([^\n]+)'),
                ("responsable_captura", r'Responsable de la captura:\s*([^\n]+)'),
                ("email_unidad_compradora", r'Correo electrónico unidad compradora:\s*([^\n]+)'),
                ("descripcion_detallada", r'Descripción detallada del procedimiento de contratación:\s*([^\n]+(?:\n[^\n]+)*?)(?:\nLey|$)'),
                ("tipo_procedimiento", r'Tipo de procedimiento de contratación:\s*([^\n]+)'),
                ("entidad_federativa", r'Entidad Federativa donde se llevará a cabo la contratación:\s*([^\n]+)'),
                ("año_ejercicio", r'Año del ejercicio presupuestal:\s*([^\n]+)')
            ]
            
            for campo, patron in campos_patrones:
                try:
                    if campo == "descripcion_detallada":
                        match = re.search(patron, contenido, re.MULTILINE | re.DOTALL)
                    else:
                        match = re.search(patron, contenido)
                    
                    if match:
                        valor = match.group(1).strip()
                        # Limpiar HTML tags
                        valor = re.sub(r'<[^>]+>', '', valor)
                        # Limpiar espacios extra
                        valor = re.sub(r'\s+', ' ', valor).strip()
                        informacion[campo] = valor
                except:
                    pass
            
            # FECHAS DEL CRONOGRAMA (formato estandarizado)
            try:
                fechas_campos = [
                    ("fecha_publicacion", r'Fecha y hora de publicación:\s*([^\n]+)'),
                    ("fecha_apertura", r'Fecha y hora de presentación y apertura de proposiciones:\s*([^\n]+)'),
                    ("fecha_junta_aclaraciones", r'Fecha y hora de junta de aclaraciones:\s*([^\n]+)'),
                    ("fecha_fallo", r'Fecha y hora del acto del Fallo:\s*([^\n]+)'),
                    ("fecha_inicio_estimada", r'Fecha estimada del inicio del contrato:\s*([^\n]+)'),
                    ("lugar_apertura", r'Lugar de apertura de proposiciones:\s*([^\n]+)'),
                    ("lugar_junta_aclaraciones", r'Lugar de la junta de aclaraciones:\s*([^\n]+)'),
                    ("lugar_fallo", r'Lugar del acto del Fallo:\s*([^\n]+)')
                ]
                
                for clave, pattern in fechas_campos:
                    match = re.search(pattern, contenido)
                    if match:
                        valor = match.group(1).strip()
                        informacion["fechas_cronograma"][clave] = valor
            except:
                pass
            
            return informacion
            
        except Exception as e:
            print(f"    ❌ Error en extracción de detalle: {e}")
            return {}
    
    async def guardar_detalle_individual(self, codigo_expediente: str, detalle: Dict):
        """Guarda el detalle individual con hash real en archivo JSON"""
        try:
            # Limpiar código de expediente para nombre de archivo
            codigo_limpio = re.sub(r'[^\\w\\-_.]', '_', codigo_expediente)
            archivo_detalle = self.carpeta_detalles / f"detalle_{codigo_limpio}.json"
            
            with open(archivo_detalle, "w", encoding="utf-8") as f:
                json.dump(detalle, f, ensure_ascii=False, indent=2)
                
            print(f"    💾 Detalle guardado: {archivo_detalle.name}")
                
        except Exception as e:
            print(f"    ❌ Error guardando detalle {codigo_expediente}: {e}")
    
    async def navegar_todas_las_paginas(self, page):
        """Navega por todas las páginas procesando detalles en cada una"""
        print("\\n=== NAVEGANDO POR TODAS LAS PÁGINAS CON EXTRACCIÓN DE DETALLES ===")
        
        # Esperar a que se cargue la primera página
        await page.wait_for_timeout(5000)
        
        # Procesar licitaciones de la primera página
        if self.extraer_detalles:
            await self.procesar_licitaciones_en_pagina_actual(page)
        
        # Navegar por páginas adicionales si existen
        if self.total_paginas and self.total_paginas > 1:
            print(f"\\nDetectadas {self.total_paginas} páginas con {self.total_registros} registros totales")
            
            for pagina in range(2, min(self.total_paginas + 1, 6)):  # Limitar a 5 páginas para prueba
                print(f"\\n[Navegando a página {pagina}/{self.total_paginas}]")
                
                # Método de navegación por botones de página
                exito = False
                
                try:
                    # Buscar y hacer click en botón de página específica
                    boton_pagina = page.locator(f"button:has-text('{pagina}')").first
                    if await boton_pagina.is_visible():
                        await boton_pagina.click()
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(5000)
                        print(f"  ✓ Navegado a página {pagina}")
                        exito = True
                except:
                    pass
                
                # Método alternativo: botón "Siguiente"
                if not exito:
                    try:
                        boton_siguiente = page.locator("button:has-text('Siguiente'), button:has-text('>')").first
                        if await boton_siguiente.is_visible() and await boton_siguiente.is_enabled():
                            await boton_siguiente.click()
                            await page.wait_for_load_state("networkidle")
                            await page.wait_for_timeout(5000)
                            print(f"  ✓ Navegado con botón siguiente")
                            exito = True
                    except:
                        pass
                
                if not exito:
                    print(f"  ❌ No se pudo navegar a página {pagina}")
                    continue
                
                # Procesar licitaciones de esta página
                if self.extraer_detalles:
                    await self.procesar_licitaciones_en_pagina_actual(page)
                
                # Verificar progreso
                print(f"  └─ Detalles extraídos hasta ahora: {len(self.detalles_extraidos)}")
                
                # Pausa entre páginas para no sobrecargar el servidor
                await page.wait_for_timeout(3000)
    
    async def cambiar_cantidad_resultados(self, page):
        """Intenta cambiar la cantidad de resultados por página al máximo."""
        print("\\n=== CAMBIANDO CANTIDAD DE RESULTADOS ===")
        
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
                            if max_valor > 10:
                                print(f"  └─ Cambiando a mostrar {max_valor} resultados por página")
                                await elemento.select_option(str(max_valor))
                                await page.wait_for_timeout(3000)
                                return True
            except:
                pass
        
        print("  └─ Usando valor por defecto de resultados por página")
        return False
    
    async def ejecutar(self, headless: bool = True, extraer_detalles: bool = True):
        """Ejecuta el scraper completo con extracción de hash real y descripción"""
        self.extraer_detalles = extraer_detalles
        
        print(f"\\n{'='*70}")
        print(f"SCRAPER COMPRASMX - CAPTURA HASH REAL + DESCRIPCIÓN COMPLETA")
        print(f"Hora: {datetime.now()}")
        print(f"Modo: {'Headless' if headless else 'Visible'}")
        print(f"Extraer detalles con hash real: {'Sí' if extraer_detalles else 'No'}")
        print(f"{'='*70}\\n")
        
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
            
            # 2. Optimizar resultados por página
            print("\\n[2/4] Optimizando cantidad de resultados...")
            await self.cambiar_cantidad_resultados(page)
            
            # 3. Navegar por páginas extrayendo detalles
            print("\\n[3/4] Navegando y extrayendo detalles con hash real...")
            await self.navegar_todas_las_paginas(page)
            
            # 4. Guardar resultados
            print("\\n[4/4] Guardando resultados...")
            await self.guardar_resultados()
            
            await browser.close()
            
            # Mostrar estadísticas finales
            self.mostrar_estadisticas()
    
    async def guardar_resultados(self):
        """Guarda todos los expedientes capturados con hash real incluido"""
        # Guardar expedientes con información de hash real integrada
        for expediente in self.expedientes_totales:
            codigo = expediente.get("cod_expediente")
            if codigo in self.detalles_extraidos:
                detalle = self.detalles_extraidos[codigo]
                # Integrar hash real en el expediente
                expediente["hash_uuid_real"] = detalle.get("hash_uuid_real")
                expediente["url_completa_con_hash"] = detalle.get("url_completa_con_hash")
                expediente["descripcion_completa"] = detalle.get("descripcion_completa")
        
        # Guardar todos los expedientes con datos enriquecidos
        archivo_expedientes = self.salida_dir / f"todos_expedientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(archivo_expedientes, "w", encoding="utf-8") as f:
            json.dump({
                "fecha_captura": datetime.now().isoformat(),
                "total_expedientes": len(self.expedientes_totales),
                "expedientes_con_hash_real": len([e for e in self.expedientes_totales if e.get("hash_uuid_real")]),
                "expedientes": self.expedientes_totales
            }, f, ensure_ascii=False, indent=2)
        print(f"  └─ Expedientes con hash real guardados en: {archivo_expedientes.name}")
        
        # Guardar resumen completo
        resumen = {
            "fecha_captura": datetime.now().isoformat(),
            "total_expedientes_capturados": len(self.expedientes_ids),
            "total_registros_sistema": self.total_registros,
            "detalles_extraidos": len(self.detalles_extraidos),
            "expedientes_con_hash_real": len([e for e in self.expedientes_totales if e.get("hash_uuid_real")]),
            "porcentaje_hash_real": (len([e for e in self.expedientes_totales if e.get("hash_uuid_real")]) / len(self.expedientes_totales) * 100) if self.expedientes_totales else 0,
            "codigos_expedientes": sorted(list(self.expedientes_ids))
        }
        
        archivo_resumen = self.salida_dir / f"resumen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(archivo_resumen, "w", encoding="utf-8") as f:
            json.dump(resumen, f, ensure_ascii=False, indent=2)
        print(f"  └─ Resumen guardado en: {archivo_resumen.name}")
        
        # Índice de detalles con hash real
        if self.detalles_extraidos:
            indice_detalles = {
                "fecha_creacion": datetime.now().isoformat(),
                "total_detalles": len(self.detalles_extraidos),
                "detalles_con_hash": len([d for d in self.detalles_extraidos.values() if d.get("hash_uuid_real")]),
                "detalles": {
                    codigo: {
                        "archivo": f"detalle_{re.sub(r'[^\\\\w\\\\-_.]', '_', codigo)}.json",
                        "url_completa": detalle.get("url_completa_con_hash", ""),
                        "hash_uuid_real": detalle.get("hash_uuid_real", ""),
                        "descripcion_longitud": len(detalle.get("descripcion_completa", "")),
                        "procesado_en": detalle.get("timestamp_procesamiento", "")
                    }
                    for codigo, detalle in self.detalles_extraidos.items()
                }
            }
            
            archivo_indice = self.carpeta_detalles / "indice_detalles.json"
            with open(archivo_indice, "w", encoding="utf-8") as f:
                json.dump(indice_detalles, f, ensure_ascii=False, indent=2)
            print(f"  └─ Índice de detalles con hash real guardado en: {archivo_indice.name}")
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas finales incluyendo hash real capturado"""
        print(f"\\n{'='*70}")
        print("ESTADÍSTICAS FINALES - CAPTURA CON HASH REAL")
        print(f"{'='*70}")
        print(f"✓ Expedientes capturados: {len(self.expedientes_ids)}")
        print(f"✓ Total en el sistema: {self.total_registros}")
        if self.total_registros:
            porcentaje = (len(self.expedientes_ids) / self.total_registros * 100)
            print(f"✓ Porcentaje capturado: {porcentaje:.1f}%")
        
        # Estadísticas de hash real
        if self.extraer_detalles:
            expedientes_con_hash = len([e for e in self.expedientes_totales if e.get("hash_uuid_real")])
            print(f"✓ Detalles individuales extraídos: {len(self.detalles_extraidos)}")
            print(f"✓ Expedientes con hash UUID real: {expedientes_con_hash}")
            if self.expedientes_totales:
                porcentaje_hash = (expedientes_con_hash / len(self.expedientes_totales) * 100)
                print(f"✓ Cobertura hash real: {porcentaje_hash:.1f}%")
            
            # Mostrar algunos ejemplos de hash capturados
            ejemplos_hash = [e.get("hash_uuid_real") for e in self.expedientes_totales if e.get("hash_uuid_real")]
            if ejemplos_hash:
                print(f"✓ Ejemplos de hash UUID capturados:")
                for i, hash_ejemplo in enumerate(ejemplos_hash[:3], 1):
                    print(f"  {i}. {hash_ejemplo}")
        
        print(f"✓ Archivos guardados en: {self.salida_dir.absolute()}")
        print(f"\\n{'='*70}")
        print(f"CAPTURA CON HASH REAL COMPLETADA: {datetime.now()}")
        print(f"{'='*70}\\n")


async def main():
    """Función principal con extracción de hash real"""
    scraper = ComprasMXScraper()
    
    # Ejecutar con extracción de detalles habilitada para capturar hash real
    await scraper.ejecutar(headless=True, extraer_detalles=True)


if __name__ == "__main__":
    asyncio.run(main())
