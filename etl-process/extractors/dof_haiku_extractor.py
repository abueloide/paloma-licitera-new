#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descarga, parseo y extracción con Haiku de licitaciones del DOF
- Descarga PDFs para fechas y ediciones especificadas
- Extrae texto por página a TXT
- Envía cada página a Claude Haiku para extraer licitaciones en formato JSON estructurado

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
from typing import Optional, List, Dict
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

class HaikuExtractor:
    """Extractor que usa Claude Haiku para procesar páginas del DOF"""
    
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
    
    def dividir_por_paginas(self, txt_path: str) -> List[Dict]:
        """
        Lee el archivo TXT y divide por páginas usando marcadores
        ===== [PÁGINA X] =====
        """
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
        
        chunks_por_pagina = []
        
        for i, marcador in enumerate(marcadores):
            numero_pagina = int(marcador.group(1))
            inicio_pagina = marcador.start()
            
            # Determinar fin de página (inicio de siguiente o final del texto)
            if i + 1 < len(marcadores):
                fin_pagina = marcadores[i + 1].start()
            else:
                fin_pagina = len(contenido)
            
            contenido_pagina = contenido[inicio_pagina:fin_pagina].strip()
            
            # Solo incluir páginas con contenido sustancial y posibles licitaciones
            if len(contenido_pagina) > 200 and self._pagina_parece_tener_licitaciones(contenido_pagina):
                chunks_por_pagina.append({
                    'numero_pagina': numero_pagina,
                    'contenido': contenido_pagina,
                    'caracteres': len(contenido_pagina)
                })
        
        print(f"[INFO] Encontradas {len(chunks_por_pagina)} páginas con posibles licitaciones")
        return chunks_por_pagina
    
    def _pagina_parece_tener_licitaciones(self, contenido: str) -> bool:
        """
        Filtro básico para identificar páginas que podrían tener licitaciones
        """
        contenido_lower = contenido.lower()
        
        # Palabras clave que indican licitaciones
        palabras_clave = [
            'licitación', 'licitacion', 'convocatoria', 'procedimiento',
            'contratación', 'contratacion', 'adquisición', 'adquisicion',
            'servicio', 'obra', 'suministro', 'arrendamiento',
            'concurso', 'invitación', 'invitacion'
        ]
        
        # Si tiene al menos 2 palabras clave, probablemente tiene licitaciones
        count = sum(1 for palabra in palabras_clave if palabra in contenido_lower)
        return count >= 2
    
    def procesar_pagina_con_haiku(self, info_pagina: Dict, archivo_origen: str) -> List[Dict]:
        """
        Envía una página completa a Claude Haiku para extraer licitaciones
        """
        numero_pagina = info_pagina['numero_pagina']
        contenido = info_pagina['contenido']
        
        prompt = f"""Analiza esta PÁGINA COMPLETA #{numero_pagina} del Diario Oficial de la Federación mexicano.

PÁGINA {numero_pagina} - CONTENIDO COMPLETO:
{contenido}

INSTRUCCIONES:
1. Esta página puede contener UNA o VARIAS licitaciones/convocatorias del gobierno mexicano
2. Extrae TODAS las licitaciones que encuentres en esta página
3. Busca patrones como: "RESUMEN DE CONVOCATORIA", "Licitación Pública", "INVITACIÓN A CUANDO MENOS", convocatorias de organismos gubernamentales
4. Cada licitación debe seguir EXACTAMENTE el formato JSON especificado

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
  "error_haiku": null
}}

REGLAS CRÍTICAS:
- Extrae TODAS las licitaciones de esta página
- Si un campo no existe, usa null
- Las fechas deben estar en formato DD/MM/YYYY HH:MM
- El uuid debe ser único (32 caracteres hexadecimales)
- numero_identificacion es CRÍTICO - debe ser el código oficial de la licitación
- Si no hay código oficial claro, usa null pero sigue extrayendo la licitación

Responde ÚNICAMENTE con un array JSON de licitaciones: [...]
NO incluyas texto adicional, solo el JSON válido."""

        try:
            message = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=4000,
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
                
                # Agregar metadatos de trazabilidad
                if 'datos_originales' not in lic:
                    lic['datos_originales'] = {
                        'archivo_origen': archivo_origen,
                        'pagina_dof': numero_pagina,
                        'fecha_procesamiento': datetime.now().isoformat(),
                        'modelo': 'claude-3-5-haiku-20241022',
                        'caracteres_pagina': len(contenido)
                    }
                
                licitaciones_validas.append(lic)
            
            print(f"   [HAIKU] Página {numero_pagina}: {len(licitaciones_validas)} licitaciones extraídas")
            return licitaciones_validas
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON inválido en página {numero_pagina}: {e}")
            print(f"[DEBUG] Respuesta: {respuesta_texto[:200]}...")
            return []
        except Exception as e:
            print(f"[ERROR] Error con Haiku en página {numero_pagina}: {e}")
            return []
    
    def procesar_txt_completo(self, txt_path: str, archivo_origen: str) -> List[Dict]:
        """
        Procesa un archivo TXT completo enviando cada página a Haiku
        """
        print(f"[INFO] Procesando con Haiku: {txt_path}")
        
        # Dividir por páginas
        chunks_por_pagina = self.dividir_por_paginas(txt_path)
        
        if not chunks_por_pagina:
            print(f"[WARN] No se encontraron páginas válidas en {txt_path}")
            return []
        
        # Procesar cada página con Haiku
        todas_licitaciones = []
        for chunk_info in chunks_por_pagina:
            print(f"   [PROCESANDO] Página {chunk_info['numero_pagina']} ({chunk_info['caracteres']} chars)")
            
            licitaciones = self.procesar_pagina_con_haiku(chunk_info, archivo_origen)
            todas_licitaciones.extend(licitaciones)
            
            # Pequeña pausa para no saturar la API
            import time
            time.sleep(0.5)
        
        print(f"[INFO] Total extraído de {txt_path}: {len(todas_licitaciones)} licitaciones")
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
        "total_paginas_procesadas": 0
    }
    
    todas_licitaciones_consolidadas = []
    
    print("=== DOF HAIKU EXTRACTOR - AGOSTO 2025 ===")
    
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
                "paginas_procesadas": 0
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
            
            # Procesamiento con Haiku
            try:
                licitaciones = haiku_extractor.procesar_txt_completo(txt_path, f"{tag}.pdf")
                
                if licitaciones:
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
                            "licitaciones": licitaciones
                        }, f, ensure_ascii=False, indent=2)
                    
                    print(f"   [JSON] {json_out} ({len(licitaciones)} licitaciones)")
                    entry["json"] = json_out
                    entry["licitaciones_extraidas"] = len(licitaciones)
                    
                    # Agregar a consolidado
                    todas_licitaciones_consolidadas.extend(licitaciones)
                    estadisticas["total_licitaciones"] += len(licitaciones)
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
    print(f"[DONE] Resumen -> {resumen_path}")
    
    return estadisticas['total_licitaciones'] > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
