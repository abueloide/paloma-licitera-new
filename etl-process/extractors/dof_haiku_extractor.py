#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descarga, parseo y extracción con Haiku de licitaciones del DOF
- Descarga PDFs para fechas y ediciones especificadas
- Extrae texto por página a TXT
- IDENTIFICA PÁGINAS DE CONVOCATORIAS usando el índice del DOF
- Envía SOLO páginas de convocatorias a Claude Haiku para extraer licitaciones
- BATCHING OPTIMIZADO: Procesa múltiples páginas por llamada API (75% menos costos)

Dependencias requeridas:
    pip install requests pymupdf pdfminer.six anthropic python-dotenv
"""
import os
import re
import json
import sys
import uuid
from datetime import date, timedelta, datetime
import requests
import logging
from typing import Optional, List, Dict, Tuple
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar Anthropic
try:
    import anthropic
except ImportError:
    print("[ERROR] anthropic no instalado. Ejecuta: pip install anthropic")
    sys.exit(1)

logging.getLogger("pdfminer").setLevel(logging.ERROR)

# ========= Config =========
OUT_DIR = "../../data/raw/dof"
OUT_JSON_DIR = "../../data/processed/dof"
# Fechas: martes y jueves de agosto 2025
AUG_DAYS = [d for d in range(1, 32)]
AUG_2025 = [date(2025, 8, d) for d in AUG_DAYS if date(2025, 8, d).weekday() in (1, 3)]  # 1=Martes, 3=Jueves
EDICIONES = ["MAT", "VES"]
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
HDRS = {"User-Agent": UA, "Accept-Language": "es-MX,es;q=0.9,en;q=0.8"}

# Configuración de batching
BATCH_SIZE = 4  # Páginas por llamada API (balance entre costo y calidad)

class HaikuExtractor:
    """Extractor que usa Claude Haiku para procesar páginas del DOF con batching optimizado"""
    
    def __init__(self):
        # Configurar API key de Anthropic
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key or api_key == 'your_api_key_here':
            raise ValueError(
                "ANTHROPIC_API_KEY no configurada en .env\n"
                "Crea un archivo .env en la raíz del proyecto con:\n"
                "ANTHROPIC_API_KEY=tu_api_key_aqui"
            )
            
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def encontrar_paginas_convocatorias(self, txt_path: str) -> Tuple[int, int]:
        """
        Encuentra las páginas que contienen convocatorias leyendo el ÍNDICE del DOF
        
        Returns:
            (inicio, fin) - números de página donde están las convocatorias
        """
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
        except Exception as e:
            print(f"[ERROR] No se pudo leer {txt_path}: {e}")
            return 0, 0
        
        # Buscar en las primeras páginas (típicamente primeras 10 páginas tienen el índice)
        patron_pagina = re.compile(r'=====\s*\[PÁGINA\s+(\d+)\]\s*=====', re.IGNORECASE)
        marcadores = list(patron_pagina.finditer(contenido))
        
        if len(marcadores) < 5:
            print("[WARN] Muy pocas páginas encontradas para buscar índice")
            return 0, len(marcadores)
        
        # Extraer texto de las primeras 10 páginas para buscar el índice
        texto_indice = ""
        for i in range(min(10, len(marcadores))):
            inicio = marcadores[i].start()
            if i + 1 < len(marcadores):
                fin = marcadores[i + 1].start()
            else:
                fin = len(contenido)
            
            texto_indice += contenido[inicio:fin]
        
        print("[INFO] Buscando páginas de convocatorias en el índice del DOF...")
        
        # PATRONES ESPECÍFICOS DEL ÍNDICE DEL DOF
        # Buscar: "Licitaciones Públicas Nacionales e Internacionales. ........ 171"
        patron_licitaciones = re.compile(
            r'Licitaciones\s+Públicas\s+Nacionales\s+e\s+Internacionales\.\s*[.\s]*(\d+)',
            re.IGNORECASE | re.DOTALL
        )
        
        # Buscar: "Judiciales y generales. ........ 221"
        patron_avisos = re.compile(
            r'Judiciales\s+y\s+generales\.\s*[.\s]*(\d+)',
            re.IGNORECASE | re.DOTALL
        )
        
        inicio_convocatorias = None
        fin_convocatorias = None
        
        # Buscar números de página en el índice
        match_licitaciones = patron_licitaciones.search(texto_indice)
        if match_licitaciones:
            try:
                inicio_convocatorias = int(match_licitaciones.group(1))
                print(f"[INFO] Licitaciones inician en página {inicio_convocatorias}")
            except ValueError:
                pass
        
        match_avisos = patron_avisos.search(texto_indice)
        if match_avisos:
            try:
                fin_convocatorias = int(match_avisos.group(1)) - 1  # Antes de avisos
                print(f"[INFO] Avisos inician en página {int(match_avisos.group(1))}, convocatorias terminan en página {fin_convocatorias}")
            except ValueError:
                pass
        
        # Fallback: buscar patrones más genéricos si los específicos fallan
        if inicio_convocatorias is None:
            print("[INFO] Patrones específicos no encontrados, probando genéricos...")
            
            # Buscar variaciones del patrón
            patron_conv_fallback = re.compile(
                r'(?:CONVOCATORIAS|Convocatorias).*?(?:CONCURSOS|LICITACIONES|Licitaciones).*?(\d+)',
                re.IGNORECASE | re.DOTALL
            )
            
            match_fallback = patron_conv_fallback.search(texto_indice)
            if match_fallback:
                try:
                    inicio_convocatorias = int(match_fallback.group(1))
                    print(f"[INFO] Convocatorias encontradas (fallback) en página {inicio_convocatorias}")
                except ValueError:
                    pass
        
        if fin_convocatorias is None and inicio_convocatorias:
            print("[INFO] Buscando fin de convocatorias con patrón genérico...")
            
            patron_avisos_fallback = re.compile(
                r'(?:AVISOS|Avisos).*?(?:JUDICIALES|Judiciales|GENERALES|generales).*?(\d+)',
                re.IGNORECASE | re.DOTALL
            )
            
            match_avisos_fallback = patron_avisos_fallback.search(texto_indice)
            if match_avisos_fallback:
                try:
                    fin_convocatorias = int(match_avisos_fallback.group(1)) - 1
                    print(f"[INFO] Avisos encontrados (fallback) en página {int(match_avisos_fallback.group(1))}, convocatorias terminan en {fin_convocatorias}")
                except ValueError:
                    pass
        
        # Validación y valores por defecto
        if inicio_convocatorias is None:
            print("[WARN] No se pudo determinar inicio de convocatorias")
            # Como último recurso, buscar en contenido directo
            return self._buscar_en_contenido_directo(contenido, marcadores)
        
        if fin_convocatorias is None:
            # Si encontramos inicio pero no fin, asumir que van hasta cerca del final
            fin_convocatorias = min(inicio_convocatorias + 100, len(marcadores))
            print(f"[WARN] No se pudo determinar fin de convocatorias, usando página {fin_convocatorias}")
        
        # Validar que el rango tenga sentido
        if inicio_convocatorias >= fin_convocatorias:
            print(f"[ERROR] Rango inválido: inicio={inicio_convocatorias}, fin={fin_convocatorias}")
            return self._buscar_en_contenido_directo(contenido, marcadores)
        
        # Limitar rangos muy grandes (más de 150 páginas probablemente es un error)
        if fin_convocatorias - inicio_convocatorias > 150:
            print(f"[WARN] Rango muy grande ({fin_convocatorias - inicio_convocatorias + 1} páginas), limitando a 100")
            fin_convocatorias = inicio_convocatorias + 99
        
        print(f"[INFO] Procesando páginas {inicio_convocatorias} a {fin_convocatorias} ({fin_convocatorias - inicio_convocatorias + 1} páginas)")
        return inicio_convocatorias, fin_convocatorias
    
    def _buscar_en_contenido_directo(self, contenido: str, marcadores: List) -> Tuple[int, int]:
        """Fallback: buscar convocatorias directamente en el contenido de las páginas"""
        print("[INFO] Fallback: buscando convocatorias directamente en contenido...")
        
        inicio_encontrado = None
        fin_encontrado = None
        
        for i, marcador in enumerate(marcadores):
            numero_pagina = int(marcador.group(1))
            inicio_pagina = marcador.start()
            
            if i + 1 < len(marcadores):
                fin_pagina = marcadores[i + 1].start()
            else:
                fin_pagina = len(contenido)
            
            contenido_pagina = contenido[inicio_pagina:fin_pagina]
            
            # Buscar inicio de convocatorias
            if inicio_encontrado is None:
                if re.search(r'(?:CONVOCATORIAS|Convocatorias).*?(?:CONCURSOS|LICITACIONES)', contenido_pagina, re.IGNORECASE):
                    inicio_encontrado = numero_pagina
                    print(f"[INFO] Convocatorias encontradas directamente en página {numero_pagina}")
            
            # Buscar fin (inicio de avisos)
            if inicio_encontrado and fin_encontrado is None:
                if re.search(r'(?:AVISOS|Avisos).*?(?:JUDICIALES|GENERALES)', contenido_pagina, re.IGNORECASE):
                    fin_encontrado = numero_pagina - 1
                    print(f"[INFO] Avisos encontrados en página {numero_pagina}, convocatorias terminan en {fin_encontrado}")
                    break
        
        if inicio_encontrado is None:
            print("[ERROR] No se pudieron encontrar convocatorias en ningún lado")
            return 0, 0
        
        if fin_encontrado is None:
            fin_encontrado = min(inicio_encontrado + 50, len(marcadores))
            print(f"[WARN] No se encontró fin, usando página {fin_encontrado}")
        
        return inicio_encontrado, fin_encontrado
    
    def dividir_por_paginas_convocatorias(self, txt_path: str) -> List[Dict]:
        """
        Lee el archivo TXT y divide SOLO las páginas de convocatorias
        """
        # Primero encontrar el rango de páginas de convocatorias
        inicio_conv, fin_conv = self.encontrar_paginas_convocatorias(txt_path)
        
        if inicio_conv == 0 and fin_conv == 0:
            return []
        
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
        except Exception as e:
            print(f"[ERROR] No se pudo leer {txt_path}: {e}")
            return []
        
        # Buscar marcadores de página: ===== [PÁGINA 123] =====
        patron_pagina = re.compile(r'=====\s*\[PÁGINA\s+(\d+)\]\s*=====', re.IGNORECASE)
        marcadores = list(patron_pagina.finditer(contenido))
        
        if not marcadores:
            print(f"[WARN] No se encontraron marcadores de página en {txt_path}")
            return []
        
        chunks_convocatorias = []
        
        for i, marcador in enumerate(marcadores):
            numero_pagina = int(marcador.group(1))
            
            # FILTRO CRÍTICO: Solo procesar páginas en el rango de convocatorias
            if not (inicio_conv <= numero_pagina <= fin_conv):
                continue
            
            inicio_pagina = marcador.start()
            
            # Determinar fin de página
            if i + 1 < len(marcadores):
                fin_pagina = marcadores[i + 1].start()
            else:
                fin_pagina = len(contenido)
            
            contenido_pagina = contenido[inicio_pagina:fin_pagina].strip()
            
            # Solo incluir páginas con contenido sustancial
            if len(contenido_pagina) > 200:
                chunks_convocatorias.append({
                    'numero_pagina': numero_pagina,
                    'contenido': contenido_pagina,
                    'caracteres': len(contenido_pagina)
                })
        
        print(f"[INFO] Encontradas {len(chunks_convocatorias)} páginas de convocatorias para procesar")
        return chunks_convocatorias
    
    def procesar_batch_paginas(self, batch_paginas: List[Dict], archivo_origen: str) -> List[Dict]:
        """
        Procesa un batch de múltiples páginas en una sola llamada API para reducir costos
        """
        if not batch_paginas:
            return []
        
        # Preparar contenido del batch con separadores claros
        contenido_batch = ""
        numeros_paginas = []
        
        for i, info_pagina in enumerate(batch_paginas):
            numero_pagina = info_pagina['numero_pagina']
            contenido = info_pagina['contenido']
            numeros_paginas.append(numero_pagina)
            
            contenido_batch += f"\n\n{'='*60}\n"
            contenido_batch += f"PÁGINA DOF #{numero_pagina}\n"
            contenido_batch += f"{'='*60}\n"
            contenido_batch += contenido
            
            if i < len(batch_paginas) - 1:
                contenido_batch += f"\n\n{'='*60}\n"
                contenido_batch += f"FIN PÁGINA {numero_pagina} - INICIO SIGUIENTE PÁGINA\n"
        
        # Crear prompt optimizado para batch
        prompt = f"""Analiza estas {len(batch_paginas)} PÁGINAS del Diario Oficial de la Federación mexicano que contienen CONVOCATORIAS DE LICITACIONES.

PÁGINAS A PROCESAR: {', '.join(map(str, numeros_paginas))}

CONTENIDO DE TODAS LAS PÁGINAS:
{contenido_batch}

INSTRUCCIONES CRÍTICAS:
1. Extrae TODAS las licitaciones/convocatorias que encuentres en TODAS las páginas
2. Cada página está separada por líneas de "====" con su número
3. Busca patrones como: "RESUMEN DE CONVOCATORIA", "Licitación Pública", "INVITACIÓN A CUANDO MENOS", convocatorias de organismos gubernamentales
4. Para cada licitación extraída, indica en "datos_originales.pagina_dof" de qué página proviene

FORMATO JSON REQUERIDO para cada licitación:
{{
  "uuid": "generar_uuid_unico_aqui",
  "numero_identificacion": "código único de la licitación",
  "titulo_basico": "objeto o título principal de la licitación", 
  "url_detalle": null,
  "numero_procedimiento_contratacion": "mismo código que numero_identificacion",
  "dependencia_entidad": "nombre completo del organismo gubernamental",
  "ramo": "ramo presupuestal si se especifica",
  "unidad_compradora": "dirección o unidad administrativa específica",
  "referencia_control_interno": "referencia interna si existe",
  "nombre_procedimiento_contratacion": "nombre completo del procedimiento",
  "descripcion_detallada": "descripción completa del servicio/bien a adquirir",
  "ley_soporte_normativo": "LEY DE ADQUISICIONES, ARRENDAMIENTOS Y SERVICIOS DEL SECTOR PÚBLICO",
  "tipo_procedimiento_contratacion": "LICITACIÓN PÚBLICA/INVITACIÓN A CUANDO MENOS TRES/etc",
  "entidad_federativa_contratacion": "estado donde se realizará",
  "fecha_publicacion": "DD/MM/YYYY HH:MM si disponible",
  "fecha_apertura_proposiciones": "DD/MM/YYYY HH:MM si disponible", 
  "fecha_junta_aclaraciones": "DD/MM/YYYY HH:MM si disponible",
  "fecha_scraping": "2025-09-01T23:50:00.000000",
  "procesado_haiku": true,
  "error_haiku": null,
  "datos_originales": {{
    "pagina_dof": [NÚMERO_DE_PÁGINA_DONDE_SE_ENCONTRÓ],
    "archivo_origen": "{archivo_origen}",
    "procesado_en_batch": true,
    "batch_size": {len(batch_paginas)}
  }}
}}

REGLAS CRÍTICAS:
- Extrae TODAS las licitaciones de TODAS las páginas del batch
- Si un campo no existe, usa null
- El uuid debe ser único (32 caracteres hexadecimales)
- OBLIGATORIO: En datos_originales.pagina_dof pon el número exacto de la página donde encontraste cada licitación
- Si no hay licitaciones en alguna página, no incluyas entradas vacías

Responde ÚNICAMENTE con un array JSON de licitaciones: [...]
NO incluyas texto adicional, solo el JSON válido."""

        try:
            message = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=6000,  # Aumentado para manejar múltiples páginas
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parsear respuesta
            respuesta_texto = message.content[0].text.strip()
            
            # Buscar el JSON en la respuesta
            inicio_json = respuesta_texto.find('[')
            if inicio_json >= 0:
                respuesta_texto = respuesta_texto[inicio_json:]
            
            fin_json = respuesta_texto.rfind(']')
            if fin_json > 0:
                respuesta_texto = respuesta_texto[:fin_json + 1]
            
            # Limpiar markdown si existe
            respuesta_texto = respuesta_texto.replace("```json", "").replace("```", "").strip()
            
            licitaciones = json.loads(respuesta_texto)
            
            if not isinstance(licitaciones, list):
                licitaciones = [licitaciones] if licitaciones else []
            
            # Validar y limpiar cada licitación
            licitaciones_validas = []
            for lic in licitaciones:
                # Generar UUID si no existe o es inválido
                if not lic.get('uuid') or len(str(lic.get('uuid'))) != 32:
                    lic['uuid'] = uuid.uuid4().hex
                
                # Asegurar campos obligatorios
                lic.setdefault('procesado_haiku', True)
                lic.setdefault('error_haiku', None)
                lic.setdefault('fecha_scraping', datetime.now().isoformat())
                
                # Completar metadatos si faltan
                if 'datos_originales' not in lic:
                    lic['datos_originales'] = {
                        'pagina_dof': numeros_paginas[0],  # Primera página como fallback
                        'archivo_origen': archivo_origen,
                        'procesado_en_batch': True,
                        'batch_size': len(batch_paginas)
                    }
                elif not lic['datos_originales'].get('pagina_dof'):
                    lic['datos_originales']['pagina_dof'] = numeros_paginas[0]
                
                # Agregar metadatos de procesamiento
                lic['datos_originales'].update({
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'modelo': 'claude-3-5-haiku-20241022',
                    'batch_paginas': numeros_paginas
                })
                
                licitaciones_validas.append(lic)
            
            paginas_str = ', '.join(map(str, numeros_paginas))
            print(f"   [HAIKU-BATCH] Páginas {paginas_str}: {len(licitaciones_validas)} licitaciones extraídas")
            return licitaciones_validas
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON inválido en batch {numeros_paginas}: {e}")
            print(f"[DEBUG] Respuesta: {respuesta_texto[:200]}...")
            return []
        except Exception as e:
            print(f"[ERROR] Error con Haiku en batch {numeros_paginas}: {e}")
            return []
    
    def procesar_txt_completo(self, txt_path: str, archivo_origen: str) -> List[Dict]:
        """
        Procesa un archivo TXT completo usando BATCHING para enviar múltiples páginas por llamada API
        """
        print(f"[INFO] Procesando con Haiku (BATCHING): {txt_path}")
        
        # Dividir por páginas DE CONVOCATORIAS únicamente
        chunks_convocatorias = self.dividir_por_paginas_convocatorias(txt_path)
        
        if not chunks_convocatorias:
            print(f"[WARN] No se encontraron páginas de convocatorias en {txt_path}")
            return []
        
        # Crear batches de páginas
        batches = []
        for i in range(0, len(chunks_convocatorias), BATCH_SIZE):
            batch = chunks_convocatorias[i:i + BATCH_SIZE]
            batches.append(batch)
        
        print(f"[INFO] Procesando {len(chunks_convocatorias)} páginas en {len(batches)} batches (tamaño: {BATCH_SIZE})")
        
        # Procesar cada batch
        todas_licitaciones = []
        for i, batch in enumerate(batches, 1):
            numeros_paginas = [p['numero_pagina'] for p in batch]
            total_chars = sum(p['caracteres'] for p in batch)
            
            print(f"   [BATCH {i}/{len(batches)}] Procesando páginas {numeros_paginas} ({total_chars:,} chars)")
            
            licitaciones = self.procesar_batch_paginas(batch, archivo_origen)
            todas_licitaciones.extend(licitaciones)
            
            # Pausa entre batches para no saturar la API
            import time
            time.sleep(0.8)
        
        print(f"[INFO] Total extraído de {txt_path}: {len(todas_licitaciones)} licitaciones usando {len(batches)} llamadas API")
        return todas_licitaciones


def download_pdf(ddmmyyyy: str, edicion: str) -> Optional[str]:
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"{ddmmyyyy}_{edicion}.pdf")
    tries = [
        f"https://www.dof.gob.mx/abrirPDF.php?archivo={ddmmyyyy}-{edicion}.pdf&anio={ddmmyyyy[-4:]}&repo=",
        f"https://dof.gob.mx/abrirPDF.php?archivo={ddmmyyyy}-{edicion}.pdf&anio={ddmmyyyy[-4:]}&repo=",
        f"https://diariooficial.gob.mx/nota_to_pdf.php?edicion={edicion}&fecha={ddmmyyyy[:2]}/{ddmmyyyy[2:4]}/{ddmmyyyy[-4:]}"
    ]
    for url in tries:
        for verify in (True, False):
            try:
                r = requests.get(url, headers=HDRS, timeout=45, verify=verify, allow_redirects=True)
                ctype = r.headers.get("Content-Type", "").lower()
                if r.status_code == 200 and "pdf" in ctype and r.content and len(r.content) > 1024:
                    with open(out_path, "wb") as f:
                        f.write(r.content)
                    print(f"[OK] DOF {ddmmyyyy}-{edicion} -> {out_path}")
                    return out_path
            except Exception as e:
                print(f"[WARN] {ddmmyyyy}-{edicion} fallo {url}: {e}")
    return None

def extract_text_per_page(pdf_path: str) -> list[str]:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        pages = [p.get_text("text") or "" for p in doc]
        doc.close()
        return pages
    except Exception as e:
        print(f"[WARN] PyMuPDF falló, intento pdfminer: {e}")
        try:
            from pdfminer.high_level import extract_text
            txt = extract_text(pdf_path) or ""
            return [txt]
        except Exception as e2:
            print(f"[ERROR] No se pudo extraer texto: {e2}")
            return []

def main():
    # Verificar API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("[ERROR] ANTHROPIC_API_KEY no configurada en .env")
        print("Crea archivo .env con: ANTHROPIC_API_KEY=tu_api_key_aqui")
        return False
    
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(OUT_JSON_DIR, exist_ok=True)
    
    # Inicializar extractor Haiku
    try:
        haiku_extractor = HaikuExtractor()
    except Exception as e:
        print(f"[ERROR] No se pudo inicializar Haiku: {e}")
        return False
    
    resumen = {"period": "2025-08-martes-jueves", "pdfs": []}
    estadisticas = {
        "pdfs_procesados": 0,
        "pdfs_exitosos": 0,
        "total_licitaciones": 0,
        "total_paginas_procesadas": 0,
        "total_llamadas_api": 0,
        "ahorro_batching": "~75% menos llamadas API vs procesamiento individual"
    }
    
    todas_licitaciones_consolidadas = []
    
    print("=== DOF HAIKU EXTRACTOR - AGOSTO 2025 ===")
    print(f"PROCESANDO SOLO PÁGINAS DE CONVOCATORIAS CON BATCHING (tamaño: {BATCH_SIZE})")
    print("OPTIMIZACIÓN: 75% menos costos API vs procesamiento individual")
    
    for d in AUG_2025:
        ddmmyyyy = f"{d.day:02d}{d.month:02d}{d.year}"
        for ed in EDICIONES:
            tag = f"{ddmmyyyy}_{ed}"
            print(f"\n==> {d.isoformat()} {ed}")
            
            pdf_path = download_pdf(ddmmyyyy, ed)
            entry = {
                "fecha": d.isoformat(), 
                "edicion": ed, 
                "pdf": pdf_path, 
                "txt": None, 
                "json": None,
                "licitaciones_extraidas": 0,
                "paginas_procesadas": 0,
                "llamadas_api": 0
            }
            
            estadisticas["pdfs_procesados"] += 1
            
            if not pdf_path:
                resumen["pdfs"].append(entry)
                continue
            
            # Extraer texto por página
            pages = extract_text_per_page(pdf_path)
            txt_path = os.path.join(OUT_DIR, f"{tag}.txt")
            
            try:
                with open(txt_path, "w", encoding="utf-8", errors="ignore") as f:
                    for i, t in enumerate(pages, start=1):
                        f.write(f"\n\n===== [PÁGINA {i}] =====\n")
                        f.write(t)
                print(f"   [TXT] {txt_path}")
                entry["txt"] = txt_path
            except Exception as e:
                print(f"   [ERROR] no se pudo escribir TXT: {e}")
                resumen["pdfs"].append(entry)
                continue
            
            # Procesamiento con Haiku - SOLO PÁGINAS DE CONVOCATORIAS CON BATCHING
            try:
                licitaciones = haiku_extractor.procesar_txt_completo(txt_path, f"{tag}.pdf")
                
                if licitaciones:
                    # Calcular llamadas API usadas (páginas / batch_size)
                    chunks = haiku_extractor.dividir_por_paginas_convocatorias(txt_path)
                    llamadas_api = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE  # Ceiling division
                    
                    # Guardar JSON individual
                    json_out = os.path.join(OUT_JSON_DIR, f"{tag}_haiku_licitaciones.json")
                    with open(json_out, "w", encoding="utf-8") as f:
                        json.dump({
                            "fecha_procesamiento": datetime.now().isoformat(),
                            "archivo_origen": f"{tag}.pdf",
                            "fecha_dof": d.isoformat(),
                            "edicion": ed,
                            "total_licitaciones": len(licitaciones),
                            "procesado_con_haiku": True,
                            "modelo": "claude-3-5-haiku-20241022",
                            "optimizacion_batching": {
                                "batch_size": BATCH_SIZE,
                                "paginas_procesadas": len(chunks),
                                "llamadas_api_usadas": llamadas_api,
                                "ahorro_vs_individual": f"{((len(chunks) - llamadas_api) / len(chunks) * 100):.1f}%" if len(chunks) > 0 else "0%"
                            },
                            "licitaciones": licitaciones
                        }, f, ensure_ascii=False, indent=2)
                    
                    print(f"   [JSON] {json_out} ({len(licitaciones)} licitaciones)")
                    if len(chunks) > 0:
                        print(f"   [AHORRO] {llamadas_api} llamadas API vs {len(chunks)} individuales ({((len(chunks) - llamadas_api) / len(chunks) * 100):.1f}% menos)")
                    
                    entry["json"] = json_out
                    entry["licitaciones_extraidas"] = len(licitaciones)
                    entry["paginas_procesadas"] = len(chunks)
                    entry["llamadas_api"] = llamadas_api
                    
                    # Agregar a consolidado
                    todas_licitaciones_consolidadas.extend(licitaciones)
                    estadisticas["total_licitaciones"] += len(licitaciones)
                    estadisticas["total_paginas_procesadas"] += len(chunks)
                    estadisticas["total_llamadas_api"] += llamadas_api
                    estadisticas["pdfs_exitosos"] += 1
                
            except Exception as e:
                print(f"   [ERROR] Procesamiento Haiku: {e}")
                import traceback
                traceback.print_exc()
            
            resumen["pdfs"].append(entry)
    
    # Guardar consolidado final
    if todas_licitaciones_consolidadas:
        consolidado_path = os.path.join(OUT_JSON_DIR, f"dof_haiku_consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(consolidado_path, "w", encoding="utf-8") as f:
            json.dump({
                "fecha_procesamiento": datetime.now().isoformat(),
                "periodo": "2025-08-martes-jueves",
                "estadisticas": estadisticas,
                "total_licitaciones": len(todas_licitaciones_consolidadas),
                "procesado_con_haiku": True,
                "modelo": "claude-3-5-haiku-20241022",
                "optimizacion_batching": {
                    "batch_size": BATCH_SIZE,
                    "total_llamadas_api": estadisticas["total_llamadas_api"],
                    "total_paginas": estadisticas["total_paginas_procesadas"],
                    "ahorro_estimado": f"{((estadisticas['total_paginas_procesadas'] - estadisticas['total_llamadas_api']) / estadisticas['total_paginas_procesadas'] * 100):.1f}%" if estadisticas['total_paginas_procesadas'] > 0 else "0%"
                },
                "licitaciones": todas_licitaciones_consolidadas
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n[CONSOLIDADO] {consolidado_path}")
    
    # Guardar resumen
    resumen["estadisticas"] = estadisticas
    resumen_path = os.path.join(OUT_JSON_DIR, "dof_haiku_resumen.json")
    with open(resumen_path, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    
    # Estadísticas finales
    print(f"\n=== ESTADÍSTICAS FINALES ===")
    print(f"PDFs procesados: {estadisticas['pdfs_procesados']}")
    print(f"PDFs exitosos: {estadisticas['pdfs_exitosos']}")
    print(f"TOTAL LICITACIONES EXTRAÍDAS: {estadisticas['total_licitaciones']}")
    print(f"PÁGINAS PROCESADAS: {estadisticas['total_paginas_procesadas']}")
    print(f"LLAMADAS API USADAS: {estadisticas['total_llamadas_api']}")
    if estadisticas['total_paginas_procesadas'] > 0:
        ahorro = (estadisticas['total_paginas_procesadas'] - estadisticas['total_llamadas_api']) / estadisticas['total_paginas_procesadas'] * 100
        print(f"AHORRO CON BATCHING: {ahorro:.1f}% menos llamadas API")
    print(f"[DONE] Resumen -> {resumen_path}")
    
    return estadisticas['total_licitaciones'] > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
