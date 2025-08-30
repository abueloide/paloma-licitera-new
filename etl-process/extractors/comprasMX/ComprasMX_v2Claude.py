#!/usr/bin/env python3
"""
Scraper ComprasMX corregido para capturar hash real y descripción completa
MODIFICADO: Capturar window.location.href para obtener hash UUID real de cada licitación
MEJORADO: Extraer descripción detallada completa de cada licitación individual
CORREGIDO: Eliminar límite artificial de 5 páginas - procesar TODAS las páginas disponibles
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
    def __init__(self, salida_dir: Path = SALIDA, max_paginas_procesar: int = None):
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
        
        # NUEVO: Control de límite de páginas (None = sin límite)
        self.max_paginas_procesar = max_paginas_procesar
        
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
                
                # Guardar respuesta para análisis
                self.respuestas_capturadas.append({
                    "url": url,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            print(f"[ERROR] No se pudo procesar {url}: {e}")
    
    async def procesar_licitaciones_en_pagina_actual(self, page):
        """CORREGIDO: Procesa cada licitación individual usando selectores PrimeNG específicos"""
        if not self.extraer_detalles:
            return
            
        print(f"\n=== EXTRAYENDO DETALLES CON HASH REAL - PÁGINA {self.pagina_actual} ===")
        
        try:
            # NUEVO: Esperar tabla PrimeNG específica
            await page.wait_for_selector("table.p-datatable-table", timeout=15000)
            print(f"  ✅ Tabla PrimeNG detectada")
            
            # NUEVO: Obtener filas usando selectores PrimeNG específicos
            filas_tabla = await page.query_selector_all("table.p-datatable-table tbody tr")
            
            if not filas_tabla:
                print(f"  ❌ No se encontraron filas en la tabla PrimeNG")
                return
            
            print(f"  └─ Encontradas {len(filas_tabla)} filas de licitaciones")
            
        except Exception as e:
            print(f"  ❌ Error localizando tabla PrimeNG: {e}")
            return
        
        # Procesar cada fila individual - UNA POR UNA COMPLETAMENTE
        for i, fila in enumerate(filas_tabla, 1):
            try:
                # NUEVO: Extraer información usando selectores específicos de columna
                segunda_columna = await fila.query_selector("td:nth-child(2)")
                tercera_columna = await fila.query_selector("td:nth-child(3)")
                cuarta_columna = await fila.query_selector("td:nth-child(4)")
                
                if not segunda_columna:
                    continue
                
                # Extraer código de expediente de la segunda columna
                codigo_expediente = await segunda_columna.inner_text()
                codigo_expediente = codigo_expediente.strip()
                
                if not codigo_expediente or len(codigo_expediente) < 5:
                    continue
                
                # Extraer título de la tercera o cuarta columna
                titulo_preliminar = ""
                if cuarta_columna:
                    titulo_preliminar = await cuarta_columna.inner_text()
                elif tercera_columna:
                    titulo_preliminar = await tercera_columna.inner_text()
                
                titulo_preliminar = titulo_preliminar.strip()
                
                print(f"\n[{i}/{len(filas_tabla)}] Procesando: {codigo_expediente}")
                print(f"    └─ {titulo_preliminar[:60]}...")
                
                # Verificar si ya procesamos este detalle
                if codigo_expediente in self.detalles_extraidos:
                    print(f"    ✓ Ya procesado: {codigo_expediente}")
                    continue
                
                # NUEVO: Click específico en la segunda columna donde está el código
                print(f"    🔄 Haciendo click en código de expediente...")
                
                # Buscar enlace específico dentro de la segunda columna
                enlace_codigo = await segunda_columna.query_selector("a, span[role='button'], div[role='button']")
                
                if not enlace_codigo:
                    # Si no hay enlace específico, hacer click en la celda completa
                    enlace_codigo = segunda_columna
                    print(f"    ⚠️ No se encontró enlace específico, usando celda completa")
                else:
                    print(f"    ✓ Encontrado enlace en código de expediente")
                
                # Ejecutar click en el código de expediente
                click_exitoso = False
                try:
                    # Hacer click con JavaScript (más confiable para PrimeNG)
                    await enlace_codigo.click()
                    print(f"    🔄 Click ejecutado, esperando navegación...")
                    click_exitoso = True
                except Exception as e:
                    print(f"    ❌ Error en click directo: {e}")
                    
                    # Método alternativo: usar JavaScript
                    try:
                        await page.evaluate("(element) => element.click()", enlace_codigo)
                        print(f"    🔄 Click por JavaScript ejecutado")
                        click_exitoso = True
                    except:
                        print(f"    ❌ Todos los métodos de click fallaron")
                
                if not click_exitoso:
                    # Si no se pudo hacer click, guardar información básica y continuar
                    print(f"    ⚠️ No se pudo hacer click - guardando información básica")
                    detalle = {
                        "codigo_expediente": codigo_expediente,
                        "url_completa_con_hash": "https://comprasmx.buengobierno.gob.mx/sitiopublico/#/",
                        "hash_uuid_real": None,
                        "descripcion_completa": "",
                        "informacion_extraida": {"titulo": titulo_preliminar},
                        "timestamp_procesamiento": datetime.now().isoformat(),
                        "procesado_exitosamente": False,
                        "pagina_origen": self.pagina_actual,
                        "error": "No se pudo hacer click en la licitación"
                    }
                    await self.guardar_detalle_individual(codigo_expediente, detalle)
                    self.detalles_extraidos[codigo_expediente] = detalle
                    continue
                
                print(f"    ⏳ Esperando navegación...")
                
                # 2. ESPERAR QUE CAMBIE LA URL (máximo 15 segundos)
                url_cambio = False
                try:
                    await page.wait_for_function(
                        "window.location.href.includes('/detalle/') && window.location.href.includes('/procedimiento')",
                        timeout=15000
                    )
                    url_cambio = True
                    print(f"    ✅ URL cambió a página de detalle")
                except:
                    print(f"    ❌ URL NO CAMBIÓ - El click no navegó correctamente")
                
                # 3. SI LA URL CAMBIÓ, PROCESAR; SI NO, SALTAR
                if url_cambio:
                    # CORREGIDO: Esperar carga completa del detalle con timeouts más largos
                    print(f"    ⏳ Esperando carga completa de la página de detalle...")
                    await page.wait_for_load_state("networkidle", timeout=20000)  # Aumentado a 20 segundos
                    await page.wait_for_timeout(8000)  # Aumentado a 8 segundos para cargas dinámicas
                    print(f"    ✅ Página de detalle completamente cargada")
                    
                    # CAPTURAR INFORMACIÓN CON TIEMPO SUFICIENTE
                    url_completa_real = await page.evaluate("window.location.href")
                    print(f"    🌐 URL capturada: {url_completa_real}")
                    
                    hash_uuid = self.extraer_hash_de_url(url_completa_real)
                    if hash_uuid:
                        print(f"    🔑 Hash UUID: {hash_uuid}")
                    
                    print(f"    📝 Extrayendo descripción completa...")
                    descripcion_completa = await self.extraer_descripcion_completa(page)
                    print(f"    📝 Descripción extraída: {len(descripcion_completa)} caracteres")
                    
                    print(f"    📋 Extrayendo información estructurada...")
                    informacion_extraida = await self.extraer_informacion_detalle_comprasmx(page)
                    
                    if hash_uuid:
                        informacion_extraida["hash_uuid_real"] = hash_uuid
                    if descripcion_completa:
                        informacion_extraida["descripcion_completa"] = descripcion_completa
                    
                    # Guardar detalle
                    detalle = {
                        "codigo_expediente": codigo_expediente,
                        "url_completa_con_hash": url_completa_real,
                        "hash_uuid_real": hash_uuid,
                        "descripcion_completa": descripcion_completa,
                        "informacion_extraida": informacion_extraida,
                        "timestamp_procesamiento": datetime.now().isoformat(),
                        "procesado_exitosamente": True,
                        "pagina_origen": self.pagina_actual
                    }
                    
                    await self.guardar_detalle_individual(codigo_expediente, detalle)
                    self.detalles_extraidos[codigo_expediente] = detalle
                    print(f"    ✅ Detalle completo guardado: {codigo_expediente}")
                    
                    # 4. VOLVER AL LISTADO CON TIEMPO SUFICIENTE
                    print(f"    ⬅️ Volviendo al listado...")
                    await page.go_back()
                    await page.wait_for_load_state("networkidle", timeout=15000)  # Tiempo suficiente para volver
                    await page.wait_for_timeout(3000)  # Pausa extra para estabilizar
                    print(f"    ✅ De vuelta en el listado")
                    
                else:
                    # El click no funcionó, crear detalle básico sin información adicional
                    print(f"    ⚠️ No se pudo acceder al detalle - guardando información básica")
                    detalle = {
                        "codigo_expediente": codigo_expediente,
                        "url_completa_con_hash": "https://comprasmx.buengobierno.gob.mx/sitiopublico/#/",
                        "hash_uuid_real": None,
                        "descripcion_completa": "",
                        "informacion_extraida": {},
                        "timestamp_procesamiento": datetime.now().isoformat(),
                        "procesado_exitosamente": False,
                        "pagina_origen": self.pagina_actual,
                        "error": "No se pudo hacer click en la licitación"
                    }
                    
                    await self.guardar_detalle_individual(codigo_expediente, detalle)
                    self.detalles_extraidos[codigo_expediente] = detalle
                
            except Exception as e:
                print(f"    ❌ Error procesando licitación {i}: {e}")
                
                # Recuperación: volver al listado si es posible
                try:
                    current_url = await page.evaluate("window.location.href")
                    if "/detalle/" in current_url:
                        print(f"    🔄 Intentando volver al listado...")
                        await page.go_back()
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(2000)
                except:
                    # Si todo falla, navegar directamente al listado
                    print(f"    🔄 Navegando directamente al listado...")
                    await page.goto(
                        "https://comprasmx.buengobierno.gob.mx/sitiopublico/#/",
                        wait_until="domcontentloaded"
                    )
                    await page.wait_for_timeout(5000)
                
        print(f"\n✅ Página {self.pagina_actual} completada. Detalles extraídos: {len(self.detalles_extraidos)}")
    
    async def navegar_todas_las_paginas(self, page):
        """🚀 CORREGIDO: Navega por las páginas según límite especificado"""
        # Determinar cuántas páginas procesar ANTES de mostrar mensajes
        if self.total_paginas and self.total_paginas > 1:
            paginas_a_procesar = self.max_paginas_procesar or self.total_paginas
            limite_real = min(paginas_a_procesar, self.total_paginas)
            
            if self.max_paginas_procesar:
                print(f"\n=== PROCESANDO {limite_real} PÁGINA(S) - LÍMITE: {self.max_paginas_procesar} ===")
            else:
                print(f"\n=== PROCESANDO TODAS LAS {limite_real} PÁGINAS (SIN LÍMITE) ===")
                
            print(f"📊 Total páginas detectadas: {self.total_paginas}")
            print(f"📊 Total registros en sistema: {self.total_registros}")
            print(f"🎯 Páginas que se procesarán: {limite_real}")
        else:
            print(f"\n=== PROCESANDO 1 PÁGINA - PÁGINA ÚNICA ===")
        
        # Esperar a que se cargue la primera página
        await page.wait_for_timeout(5000)
        
        # Procesar licitaciones de la primera página
        if self.extraer_detalles:
            await self.procesar_licitaciones_en_pagina_actual(page)
        
        # Navegar por páginas adicionales SOLO si hay más de 1 página Y no estamos limitando a 1
        if self.total_paginas and self.total_paginas > 1 and (not self.max_paginas_procesar or self.max_paginas_procesar > 1):
            paginas_a_procesar = self.max_paginas_procesar or self.total_paginas
            limite_paginas = min(paginas_a_procesar, self.total_paginas)
            
            for pagina in range(2, limite_paginas + 1):
                print(f"\n[Navegando a página {pagina}/{limite_paginas}]")
                
                # Método de navegación usando selectores PrimeNG
                exito = False
                try:
                    # Buscar botón "Siguiente" usando selector PrimeNG específico
                    boton_siguiente = await page.query_selector("button.p-paginator-next:not(.p-disabled)")
                    if boton_siguiente:
                        await boton_siguiente.click()
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(5000)
                        print(f"  ✓ Navegado con botón PrimeNG siguiente")
                        exito = True
                    else:
                        print(f"  ⚠️ Botón siguiente PrimeNG no disponible o deshabilitado")
                except Exception as e:
                    print(f"  ❌ Error con botón PrimeNG siguiente: {e}")
                
                # Método alternativo: botón de página específica
                if not exito:
                    try:
                        # Buscar botón de página específica
                        boton_pagina = await page.query_selector(f"button.p-paginator-page[aria-label='Page {pagina}']")
                        if not boton_pagina:
                            # Fallback: buscar por texto
                            boton_pagina = await page.query_selector(f"button:has-text('{pagina}')")
                        
                        if boton_pagina:
                            await boton_pagina.click()
                            await page.wait_for_load_state("networkidle")
                            await page.wait_for_timeout(5000)
                            print(f"  ✓ Navegado a página {pagina} con botón específico")
                            exito = True
                    except Exception as e:
                        print(f"  ❌ Error con botón de página específica: {e}")
                
                if not exito:
                    print(f"  ❌ No se pudo navegar a página {pagina}")
                    continue
                
                # Procesar licitaciones de esta página
                if self.extraer_detalles:
                    await self.procesar_licitaciones_en_pagina_actual(page)
                
                # Verificar progreso
                print(f"  └─ Detalles extraídos hasta ahora: {len(self.detalles_extraidos)}")
                print(f"  └─ Expedientes totales hasta ahora: {len(self.expedientes_ids)}")
                
                # Pausa entre páginas para no sobrecargar el servidor
                await page.wait_for_timeout(3000)
        else:
            print("\n🎯 Solo hay 1 página de resultados - procesamiento completo")
    
    async def cambiar_cantidad_resultados(self, page):
        """🚀 MEJORADO: Maximizar resultados por página para capturar más datos."""
        print("\n=== MAXIMIZANDO RESULTADOS POR PÁGINA ===")
        
        selectores = [
            "select",
            "[class*='per-page']",
            "[class*='page-size']",
            "[class*='items-per']",
            "[class*='pageSize']",
            "select[name*='size']",
            "select[name*='page']"
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
                                print(f"  🎯 Maximizando a {max_valor} resultados por página")
                                await elemento.select_option(str(max_valor))
                                await page.wait_for_timeout(5000)
                                print(f"  ✅ Configurado para mostrar {max_valor} resultados por página")
                                return True
            except:
                pass
        
        print("  ⚠️ No se pudo cambiar cantidad de resultados - usando valor por defecto")
        return False
    
    async def ejecutar(self, headless: bool = True, extraer_detalles: bool = True, max_paginas: int = None):
        """🚀 MEJORADO: Ejecuta el scraper completo sin límites artificiales"""
        self.extraer_detalles = extraer_detalles
        self.max_paginas_procesar = max_paginas
        
        print(f"\n{'='*70}")
        print(f"SCRAPER COMPRASMX - CAPTURA COMPLETA SIN LÍMITES")
        print(f"Hora: {datetime.now()}")
        print(f"Modo: {'Headless' if headless else 'Visible'}")
        print(f"Extraer detalles con hash real: {'Sí' if extraer_detalles else 'No'}")
        print(f"Límite de páginas: {'Sin límite' if not max_paginas else str(max_paginas)}")
        print(f"{'='*70}\n")
        
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
            print("\n[2/4] Maximizando resultados por página...")
            await self.cambiar_cantidad_resultados(page)
            
            # 3. Navegar por TODAS las páginas extrayendo detalles
            print("\n[3/4] Navegando por TODAS las páginas (sin límites)...")
            await self.navegar_todas_las_paginas(page)
            
            # 4. Guardar resultados
            print("\n[4/4] Guardando resultados...")
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
            "paginas_procesadas": self.pagina_actual,
            "cobertura_sistema": (len(self.expedientes_ids) / self.total_registros * 100) if self.total_registros else 0,
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
                        "archivo": f"detalle_{re.sub(r'[^\w\-_.]', '_', codigo)}.json",
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
        """🚀 MEJORADO: Muestra estadísticas completas de captura"""
        print(f"\n{'='*70}")
        print("ESTADÍSTICAS FINALES - CAPTURA COMPLETA")
        print(f"{'='*70}")
        print(f"✓ Expedientes capturados: {len(self.expedientes_ids):,}")
        print(f"✓ Total en el sistema: {self.total_registros:,}")
        print(f"✓ Páginas procesadas: {self.pagina_actual}")
        if self.total_registros:
            cobertura = (len(self.expedientes_ids) / self.total_registros * 100)
            print(f"✓ Cobertura del sistema: {cobertura:.1f}%")
            if cobertura < 90:
                print(f"⚠️ COBERTURA INCOMPLETA - Considera aumentar límite de páginas")
        
        # Estadísticas de hash real
        if self.extraer_detalles:
            expedientes_con_hash = len([e for e in self.expedientes_totales if e.get("hash_uuid_real")])
            print(f"✓ Detalles individuales extraídos: {len(self.detalles_extraidos):,}")
            print(f"✓ Expedientes con hash UUID real: {expedientes_con_hash:,}")
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
        
        # Recomendación final
        if self.total_registros and len(self.expedientes_ids) < self.total_registros:
            faltantes = self.total_registros - len(self.expedientes_ids)
            print(f"\n📋 RECOMENDACIÓN:")
            print(f"   - Faltan {faltantes:,} expedientes por capturar")
            print(f"   - Ejecutar sin límite de páginas para captura completa")
        
        print(f"\n{'='*70}")
        print(f"CAPTURA COMPLETADA: {datetime.now()}")
        print(f"{'='*70}\n")


async def main():
    """Función principal mejorada con opciones flexibles"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scraper ComprasMX sin límites')
    parser.add_argument('--headless', action='store_true', help='Ejecutar en modo headless')
    parser.add_argument('--no-detalles', action='store_true', help='No extraer detalles individuales')
    parser.add_argument('--max-paginas', type=int, help='Límite máximo de páginas a procesar')
    
    args = parser.parse_args()
    
    scraper = ComprasMXScraper()
    
    # Ejecutar con parámetros especificados
    await scraper.ejecutar(
        headless=args.headless,
        extraer_detalles=not args.no_detalles,
        max_paginas=args.max_paginas
    )


if __name__ == "__main__":
    asyncio.run(main())