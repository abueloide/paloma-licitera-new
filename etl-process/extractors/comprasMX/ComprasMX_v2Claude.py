#!/usr/bin/env python3
"""
Scraper ComprasMX corregido para la estructura real de la API
Captura TODOS los 1490+ expedientes navegando por las 15 páginas
+ FUNCIONALIDAD CORREGIDA: Extracción de detalles individuales usando estructura real de tabla
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
        """FUNCIÓN CORREGIDA: Procesa cada licitación individual usando la estructura real de tabla"""
        if not self.extraer_detalles:
            return
            
        print(f"\n=== EXTRAYENDO DETALLES INDIVIDUALES - PÁGINA {self.pagina_actual} ===")
        
        # CORREGIDO: ComprasMX usa una tabla con filas clickeables
        # Buscar todas las filas de la tabla de licitaciones
        try:
            # Esperar a que la tabla se cargue
            await page.wait_for_selector("table", timeout=10000)
            
            # Obtener todas las filas de la tabla (excluyendo header)
            filas_tabla = await page.locator("table tbody tr, table tr:not(:first-child)").all()
            
            if not filas_tabla:
                # Fallback: buscar cualquier fila de tabla
                filas_tabla = await page.locator("tr").all()
                # Filtrar header si existe
                filas_filtradas = []
                for fila in filas_tabla:
                    texto = await fila.text_content()
                    if texto and not ("Núm." in texto and "Número de identificación" in texto):
                        filas_filtradas.append(fila)
                filas_tabla = filas_filtradas
            
            print(f"  └─ Encontradas {len(filas_tabla)} filas de licitaciones en la tabla")
            
        except Exception as e:
            print(f"  ❌ Error localizando tabla de licitaciones: {e}")
            return
        
        # Procesar cada fila de licitación individual
        for i, fila in enumerate(filas_tabla, 1):
            try:
                # Extraer texto de la fila para identificación
                texto_fila = await fila.text_content()
                if not texto_fila or len(texto_fila.strip()) < 10:
                    continue
                
                # Extraer código de expediente de la segunda columna (índice 1)
                celdas = await fila.locator("td").all()
                codigo_expediente = ""
                nombre_procedimiento = ""
                
                if len(celdas) >= 4:  # Asegurarse que tiene suficientes columnas
                    # Segunda columna: Número de identificación
                    codigo_expediente = (await celdas[1].text_content()).strip()
                    # Cuarta columna: Nombre del procedimiento
                    nombre_procedimiento = (await celdas[3].text_content()).strip()
                
                if not codigo_expediente:
                    print(f"  ⚠️ No se pudo extraer código de expediente de la fila {i}")
                    continue
                
                print(f"  \n[{i}/{len(filas_tabla)}] Procesando: {codigo_expediente}")
                print(f"    └─ {nombre_procedimiento[:80]}{'...' if len(nombre_procedimiento) > 80 else ''}")
                
                # Verificar si ya procesamos este detalle
                if codigo_expediente in self.detalles_extraidos:
                    print(f"    ✓ Detalle ya procesado: {codigo_expediente}")
                    continue
                
                # Hacer click en la fila para abrir el detalle
                await fila.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(4000)
                
                # Capturar información de la página de detalle
                url_completa = page.url
                contenido_html = await page.content()
                
                # Extraer información estructurada de la página
                informacion_extraida = await self.extraer_informacion_detalle_comprasmx(page)
                
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
    
    async def extraer_informacion_detalle_comprasmx(self, page) -> Dict:
        """
        NUEVA FUNCIÓN: Extrae información estructurada específica de ComprasMX
        Basada en la estructura HTML real analizada
        """
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
            
            print("    🔍 Extrayendo información detallada...")
            
            # Obtener todo el contenido HTML
            contenido = await page.content()
            
            # CÓDIGO DEL EXPEDIENTE
            try:
                codigo_patterns = [
                    r'Código del expediente:\s*([^\n]+)',
                    r'E-\d{4}-\d{8}'
                ]
                
                for pattern in codigo_patterns:
                    match = re.search(pattern, contenido)
                    if match:
                        informacion["codigo_expediente"] = match.group(1).strip()
                        break
            except:
                pass
            
            # NÚMERO DE PROCEDIMIENTO
            try:
                numero_patterns = [
                    r'Número de procedimiento de contratación:\s*([^\n]+)',
                    r'[A-Z]{2}-\d{2}-[A-Z0-9]{3}-\d{9}-[A-Z]-\d+-\d{4}'
                ]
                
                for pattern in numero_patterns:
                    match = re.search(pattern, contenido)
                    if match:
                        informacion["numero_procedimiento"] = match.group(1).strip()
                        break
            except:
                pass
            
            # ESTATUS
            try:
                estatus_patterns = [
                    r'Estatus del procedimiento de contratación:\s*([^\n]+)',
                    r'(VIGENTE|CERRADO|CANCELADO|DESIERTO)'
                ]
                
                for pattern in estatus_patterns:
                    match = re.search(pattern, contenido)
                    if match:
                        estatus = match.group(1).strip()
                        if estatus in ['VIGENTE', 'CERRADO', 'CANCELADO', 'DESIERTO']:
                            informacion["estatus"] = estatus
                            break
            except:
                pass
            
            # DEPENDENCIA O ENTIDAD
            try:
                dep_pattern = r'Dependencia o Entidad:\s*([^\n]+)'
                match = re.search(dep_pattern, contenido)
                if match:
                    informacion["dependencia_entidad"] = match.group(1).strip()
            except:
                pass
            
            # UNIDAD COMPRADORA
            try:
                unidad_pattern = r'Unidad compradora:\s*([^\n]+)'
                match = re.search(unidad_pattern, contenido)
                if match:
                    informacion["unidad_compradora"] = match.group(1).strip()
            except:
                pass
            
            # RESPONSABLE DE LA CAPTURA
            try:
                resp_pattern = r'Responsable de la captura:\s*([^\n]+)'
                match = re.search(resp_pattern, contenido)
                if match:
                    informacion["responsable_captura"] = match.group(1).strip()
            except:
                pass
            
            # EMAIL UNIDAD COMPRADORA
            try:
                email_pattern = r'Correo electrónico unidad compradora:\s*([^\n]+)'
                match = re.search(email_pattern, contenido)
                if match:
                    informacion["email_unidad_compradora"] = match.group(1).strip()
            except:
                pass
            
            # DESCRIPCIÓN DETALLADA
            try:
                desc_pattern = r'Descripción detallada del procedimiento de contratación:\s*([^\n]+)'
                match = re.search(desc_pattern, contenido)
                if match:
                    informacion["descripcion_detallada"] = match.group(1).strip()
            except:
                pass
            
            # TIPO DE PROCEDIMIENTO
            try:
                tipo_pattern = r'Tipo de procedimiento de contratación:\s*([^\n]+)'
                match = re.search(tipo_pattern, contenido)
                if match:
                    informacion["tipo_procedimiento"] = match.group(1).strip()
            except:
                pass
            
            # ENTIDAD FEDERATIVA
            try:
                entidad_pattern = r'Entidad Federativa donde se llevará a cabo la contratación:\s*([^\n]+)'
                match = re.search(entidad_pattern, contenido)
                if match:
                    informacion["entidad_federativa"] = match.group(1).strip()
            except:
                pass
            
            # AÑO DEL EJERCICIO
            try:
                año_pattern = r'Año del ejercicio presupuestal:\s*([^\n]+)'
                match = re.search(año_pattern, contenido)
                if match:
                    informacion["año_ejercicio"] = match.group(1).strip()
            except:
                pass
            
            # FECHAS DEL CRONOGRAMA
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
                        informacion["fechas_cronograma"][clave] = match.group(1).strip()
            except:
                pass
            
            # PARTIDAS ESPECÍFICAS
            try:
                # Buscar tabla de partidas específicas en el HTML
                if 'Partidas específicas' in contenido:
                    # Extraer partidas usando patrones
                    partidas_matches = re.findall(r'(\d+)\s+([A-Z0-9\s]+)', contenido)
                    for clave, desc in partidas_matches:
                        if len(clave.strip()) == 5:  # Códigos de partida son de 5 dígitos
                            informacion["partidas_especificas"].append({
                                "clave": clave.strip(),
                                "descripcion": desc.strip()
                            })
            except:
                pass
            
            # DATOS ESPECÍFICOS
            try:
                datos_campos = [
                    ("tipo_contratacion", r'Tipo de contratación:\s*([^\n]+)'),
                    ("criterio_evaluacion", r'Criterio de evaluación:\s*([^\n]+)'),
                    ("caracter", r'Carácter:\s*([^\n]+)'),
                    ("moneda", r'Moneda:\s*([^\n]+)'),
                    ("anticipo", r'Anticipo:\s*([^\n]+)'),
                    ("forma_pago", r'Forma de pago:\s*([^\n]+)'),
                    ("garantia_cumplimiento", r'Garantía de cumplimiento:\s*([^\n]+)'),
                    ("porcentaje_garantia", r'Porcentaje del monto del contrato a garantizar:\s*([^\n]+)'),
                    ("participacion_conjunta", r'¿Permite participación conjunta\?\s*([^\n]+)'),
                    ("contrato_abierto", r'Contrato Abierto:\s*([^\n]+)'),
                    ("plurianual", r'Es plurianual:\s*([^\n]+)')
                ]
                
                for clave, pattern in datos_campos:
                    match = re.search(pattern, contenido)
                    if match:
                        informacion["datos_especificos"][clave] = match.group(1).strip()
            except:
                pass
            
            # DOCUMENTOS ANEXOS
            try:
                if 'ANEXOS' in contenido:
                    # Extraer información de documentos
                    doc_patterns = [
                        r'CONVOCATORIA\s+CONVOCATORIA',
                        r'ANEXO TÉCNICO\s+ANEXO TÉCNICO', 
                        r'MODELO DE CONTRATO\s+MODELO DE CONTRATO',
                        r'ACTA JUNTA DE ACLARACIONES\s+ACTA JUNTA DE ACLARACIONES'
                    ]
                    
                    for pattern in doc_patterns:
                        if re.search(pattern, contenido):
                            doc_tipo = pattern.split('\\s+')[0]
                            informacion["documentos_anexos"].append({
                                "tipo": doc_tipo,
                                "descripcion": doc_tipo
                            })
            except:
                pass
            
            # REQUISITOS ECONÓMICOS (tabla de partidas con montos)
            try:
                if 'REQUISITOS' in contenido and 'ECONÓMICOS' in contenido:
                    # Buscar patrones de partidas con detalles económicos
                    req_matches = re.findall(r'(\d{5})\s+([^\\n]+)\\s+(PIEZA|SERVICIO|LOTE)', contenido)
                    for partida, desc, unidad in req_matches:
                        informacion["requisitos_economicos"].append({
                            "partida_especifica": partida,
                            "descripcion": desc.strip(),
                            "unidad_medida": unidad
                        })
            except:
                pass
            
            campos_con_datos = len([k for k, v in informacion.items() if v])
            print(f"    ✓ Extracción completada - {campos_con_datos} campos con datos")
            return informacion
            
        except Exception as e:
            print(f"    ❌ Error en extracción de detalle: {e}")
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
        print(f"SCRAPER COMPRASMX - CAPTURA COMPLETA + DETALLES CORREGIDOS")
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
