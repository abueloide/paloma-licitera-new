#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOF Extractor con Integración Haiku - VERSIÓN MEJORADA
=====================================================
Toma el 70% del código de dof_extraccion_estructuracion.py que YA funciona bien
y le agrega envío directo de páginas a Haiku para extraer licitaciones.

FLUJO:
1. Descarga PDFs del DOF ✅ (reutilizado)  
2. Extrae texto por página ✅ (reutilizado)
3. 🆕 NUEVO: Envía cada página a Haiku directamente
4. 🆕 NUEVO: Consolida JSONs de licitaciones

NO usa archivos TXT intermedios - procesamiento directo página → Haiku → JSON
"""

import os
import re
import json
import sys
import time
import warnings
from datetime import date, timedelta, datetime
import requests
import logging
from typing import Optional, List, Dict
import ssl
import urllib3
from urllib.parse import quote
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Deshabilitar warnings de SSL para sitios gubernamentales
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# Importar Anthropic
try:
    import anthropic
except ImportError:
    logger.error("anthropic no instalado. Ejecuta: pip install anthropic")
    sys.exit(1)

# ========= Configuración =========
OUT_DIR = "../../../data/raw/dof"
OUT_JSON_DIR = "../../../data/processed/dof"

# Fechas: martes y jueves de agosto 2025
AUG_DAYS = [d for d in range(1, 32)]
AUG_2025 = [date(2025, 8, d) for d in AUG_DAYS if date(2025, 8, d).weekday() in (1, 3)]  # 1=Martes, 3=Jueves
EDICIONES = ["MAT", "VES"]

# Headers mejorados
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

class DOFDownloader:
    """Clase mejorada para descargar PDFs del DOF con manejo robusto de SSL"""
    
    def __init__(self, out_dir: str = OUT_DIR):
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)
        self.session = self._crear_sesion()
        
    def _crear_sesion(self) -> requests.Session:
        """Crea una sesión configurada para manejar problemas de SSL"""
        session = requests.Session()
        
        # Configurar adaptadores con reintentos
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=requests.adapters.Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504]
            )
        )
        
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # Headers por defecto
        session.headers.update(HEADERS)
        
        # Configuración SSL más permisiva para sitios gubernamentales
        session.verify = False  # Desactivar verificación SSL por defecto
        
        return session
    
    def _generar_urls(self, ddmmyyyy: str, edicion: str) -> list:
        """Genera múltiples variantes de URL para intentar la descarga"""
        año = ddmmyyyy[-4:]
        dia = ddmmyyyy[:2]
        mes = ddmmyyyy[2:4]
        
        urls = [
            # URLs principales conocidas
            f"https://www.dof.gob.mx/abrirPDF.php?archivo={ddmmyyyy}-{edicion}.pdf&anio={año}&repo=",
            f"https://dof.gob.mx/abrirPDF.php?archivo={ddmmyyyy}-{edicion}.pdf&anio={año}&repo=",
            f"https://www.diariooficial.gob.mx/nota_to_pdf.php?edicion={edicion}&fecha={dia}/{mes}/{año}",
            f"https://diariooficial.gob.mx/nota_to_pdf.php?edicion={edicion}&fecha={dia}/{mes}/{año}",
            
            # Variantes adicionales
            f"http://www.dof.gob.mx/abrirPDF.php?archivo={ddmmyyyy}-{edicion}.pdf&anio={año}&repo=",
            f"http://dof.gob.mx/abrirPDF.php?archivo={ddmmyyyy}-{edicion}.pdf&anio={año}&repo=",
            
            # Con diferentes formatos de fecha
            f"https://www.dof.gob.mx/nota_to_pdf.php?fecha={dia}/{mes}/{año}&edicion={edicion}",
            f"https://dof.gob.mx/index.php?year={año}&month={mes}&day={dia}&edicion={edicion}",
            
            # URLs directas al archivo
            f"https://www.dof.gob.mx/notas/{año}/{mes}/{ddmmyyyy}-{edicion}.pdf",
            f"https://dof.gob.mx/archivos/{año}/{mes}/{dia}/{ddmmyyyy}-{edicion}.pdf",
        ]
        
        return urls
    
    def _validar_pdf(self, content: bytes) -> bool:
        """Valida que el contenido sea un PDF válido"""
        if not content or len(content) < 1024:
            return False
        
        # Verificar header PDF
        if not content.startswith(b'%PDF'):
            return False
        
        # Verificar que no sea una página de error HTML
        if b'<!DOCTYPE' in content[:500] or b'<html' in content[:500]:
            return False
        
        return True
    
    def download_pdf(self, ddmmyyyy: str, edicion: str, max_reintentos: int = 3) -> Optional[str]:
        """
        Descarga un PDF del DOF con manejo robusto de errores y SSL
        
        Args:
            ddmmyyyy: Fecha en formato DDMMYYYY
            edicion: Edición (MAT o VES)
            max_reintentos: Número máximo de reintentos por URL
        
        Returns:
            Path al archivo descargado o None si falla
        """
        out_path = os.path.join(self.out_dir, f"{ddmmyyyy}_{edicion}.pdf")
        
        # Si ya existe, no descargar de nuevo
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
            logger.info(f"[EXISTS] {ddmmyyyy}-{edicion} ya descargado: {out_path}")
            return out_path
        
        urls = self._generar_urls(ddmmyyyy, edicion)
        
        for url_idx, url in enumerate(urls, 1):
            logger.debug(f"Intento {url_idx}/{len(urls)}: {url}")
            
            for intento in range(max_reintentos):
                try:
                    # Alternar entre verificación SSL activada y desactivada
                    verify_ssl = (intento == 0)  # Primer intento con SSL, luego sin
                    
                    # Configurar timeout progresivo
                    timeout = 30 + (intento * 15)
                    
                    # Headers adicionales para algunos sitios
                    headers = HEADERS.copy()
                    if 'diariooficial' in url:
                        headers['Referer'] = 'https://www.diariooficial.gob.mx/'
                    
                    # Realizar petición
                    response = self.session.get(
                        url,
                        headers=headers,
                        timeout=timeout,
                        verify=verify_ssl,
                        allow_redirects=True,
                        stream=True
                    )
                    
                    # Verificar respuesta
                    if response.status_code == 200:
                        content = response.content
                        
                        if self._validar_pdf(content):
                            # Guardar PDF
                            with open(out_path, 'wb') as f:
                                f.write(content)
                            
                            size_mb = len(content) / (1024 * 1024)
                            logger.info(f"[OK] DOF {ddmmyyyy}-{edicion} descargado ({size_mb:.2f} MB): {out_path}")
                            return out_path
                        else:
                            logger.debug(f"Contenido no es PDF válido desde {url}")
                    
                    elif response.status_code == 404:
                        logger.debug(f"404 Not Found: {url}")
                        break  # No reintentar si es 404
                    
                    else:
                        logger.debug(f"Status {response.status_code} desde {url}")
                
                except requests.exceptions.SSLError as e:
                    logger.debug(f"Error SSL en {url}: {e}")
                    if intento == 0:
                        logger.debug("Reintentando sin verificación SSL...")
                        continue
                
                except requests.exceptions.ConnectionError as e:
                    logger.debug(f"Error de conexión en {url}: {e}")
                    time.sleep(2)  # Esperar antes de reintentar
                
                except requests.exceptions.Timeout:
                    logger.debug(f"Timeout en {url} (timeout={timeout}s)")
                
                except Exception as e:
                    logger.debug(f"Error inesperado en {url}: {e}")
                
                # Esperar entre reintentos
                if intento < max_reintentos - 1:
                    time.sleep(1)
        
        logger.warning(f"[FAIL] No se pudo descargar DOF {ddmmyyyy}-{edicion} después de intentar todas las URLs")
        return None


class HaikuExtractor:
    """Extractor que envía páginas del DOF directamente a Haiku"""
    
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
        
    def encontrar_paginas_convocatorias(self, pages: List[str]) -> tuple[int, int]:
        """
        Encuentra el rango de páginas que contienen convocatorias
        
        Returns:
            (inicio, fin) - índices de páginas (0-based)
        """
        # Buscar en las primeras páginas el índice del DOF
        texto_inicial = "\n".join(pages[:10])  # Primeras 10 páginas para buscar índice
        
        # Patrones para encontrar donde empiezan y terminan las convocatorias
        patron_inicio = re.compile(
            r'CONVOCATORIAS?\s+(?:PARA\s+)?(?:CONCURSOS?|LICITACIONES?).*?(\d+)',
            re.IGNORECASE | re.DOTALL
        )
        
        patron_fin = re.compile(
            r'AVISOS?\s+(?:JUDICIALES?|GENERALES?)?.*?(\d+)',
            re.IGNORECASE | re.DOTALL
        )
        
        inicio_pagina = None
        fin_pagina = None
        
        # Buscar números de página en el índice
        match_inicio = patron_inicio.search(texto_inicial)
        if match_inicio:
            try:
                inicio_pagina = int(match_inicio.group(1)) - 1  # Convertir a 0-based
                logger.info(f"Convocatorias inician en página {inicio_pagina + 1}")
            except:
                pass
        
        match_fin = patron_fin.search(texto_inicial)
        if match_fin:
            try:
                fin_pagina = int(match_fin.group(1)) - 1  # Convertir a 0-based
                logger.info(f"Convocatorias terminan en página {fin_pagina}")
            except:
                pass
        
        # Si no encontramos en el índice, buscar directamente en el contenido
        if inicio_pagina is None:
            for i, page in enumerate(pages):
                if re.search(r'CONVOCATORIAS?\s+(?:PARA\s+)?CONCURSOS?', page, re.IGNORECASE):
                    inicio_pagina = i
                    logger.info(f"Convocatorias encontradas directamente en página {i + 1}")
                    break
            
            if inicio_pagina is None:
                inicio_pagina = 0  # Si no encontramos, empezar desde el inicio
        
        if fin_pagina is None:
            # Buscar donde empiezan los avisos
            for i, page in enumerate(pages[inicio_pagina:], inicio_pagina):
                if re.search(r'AVISOS?\s+(?:JUDICIALES?|GENERALES?)', page, re.IGNORECASE):
                    fin_pagina = i
                    logger.info(f"Avisos encontrados en página {i + 1}, convocatorias terminan ahí")
                    break
            
            if fin_pagina is None:
                fin_pagina = len(pages)  # Si no encontramos, hasta el final
        
        return inicio_pagina, fin_pagina
    
    def procesar_pagina_con_haiku(self, numero_pagina: int, contenido_pagina: str, archivo_origen: str) -> List[Dict]:
        """
        Envía una página completa a Haiku para extraer licitaciones
        
        Args:
            numero_pagina: Número de página (1-based)
            contenido_pagina: Texto completo de la página
            archivo_origen: Nombre del archivo PDF original
            
        Returns:
            Lista de licitaciones encontradas en formato JSON
        """
        
        prompt = f"""Analiza esta PÁGINA COMPLETA #{numero_pagina} del Diario Oficial de la Federación mexicano.

PÁGINA {numero_pagina} - CONTENIDO COMPLETO:
{contenido_pagina}

INSTRUCCIONES ESPECÍFICAS:
1. Esta página puede contener UNA o VARIAS licitaciones/convocatorias completas del gobierno mexicano
2. Extrae TODAS las licitaciones que encuentres en esta página
3. Busca patrones como: "RESUMEN DE CONVOCATORIA", "Licitación Pública", "INVITACIÓN A CUANDO MENOS", convocatorias de organismos gubernamentales
4. Cada licitación puede tener formato diferente pero generalmente incluye: organismo, objeto/descripción, fechas importantes, número de procedimiento

FORMATO JSON REQUERIDO para cada licitación encontrada:
{{
  "numero_procedimiento": "código único si existe, ej: LA-08-B00-008B00001-N-177-2025",
  "titulo": "objeto o descripción de la licitación",
  "descripcion": "descripción detallada del servicio/bien a adquirir",
  "entidad_compradora": "nombre del organismo gubernamental",
  "unidad_compradora": "dirección o unidad administrativa específica",
  "tipo_procedimiento": "LICITACIÓN PÚBLICA/INVITACIÓN/CONCURSO/etc",
  "tipo_contratacion": "SERVICIOS/ADQUISICIONES/OBRA PÚBLICA/ARRENDAMIENTO",
  "caracter": "NACIONAL/INTERNACIONAL si se especifica",
  "entidad_federativa": "estado de México donde se realizará",
  "municipio": "municipio si se especifica",
  "fecha_publicacion": "YYYY-MM-DD si está disponible",
  "fecha_apertura": "YYYY-MM-DD HH:MM:SS si está disponible",
  "fecha_fallo": "YYYY-MM-DD si está disponible", 
  "fecha_junta_aclaraciones": "YYYY-MM-DD si está disponible",
  "fecha_visita": "YYYY-MM-DD si aplica",
  "referencia": "número de referencia (R.- XXXXX) si existe"
}}

REGLAS IMPORTANTES:
- Extrae TODAS las licitaciones que encuentres en esta página
- Si un campo no existe o no está claro, usa null
- Las fechas deben ser del año 2025
- Si no hay numero_procedimiento claro, usa null pero sigue extrayendo la licitación
- Sé generoso extrayendo - es mejor tener información incompleta que perder licitaciones

Responde ÚNICAMENTE con un array JSON de licitaciones encontradas: [...]
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
            
            # Agregar metadatos a cada licitación
            for lic in licitaciones:
                lic['fuente'] = 'DOF'
                lic['estado'] = 'PUBLICADA'
                lic['moneda'] = 'MXN'
                lic['numero_pagina_dof'] = numero_pagina
                lic['datos_originales'] = {
                    'archivo_origen': archivo_origen,
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'procesado_con_ia': True,
                    'modelo': 'claude-3-5-haiku-20241022',
                    'pagina_dof': numero_pagina,
                    'caracteres_pagina': len(contenido_pagina)
                }
            
            logger.info(f"  Página {numero_pagina}: {len(licitaciones)} licitaciones encontradas")
            return licitaciones
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON en página {numero_pagina}: {e}")
            logger.debug(f"Respuesta: {respuesta_texto[:500]}...")
            return []
        except Exception as e:
            logger.error(f"Error con API Haiku en página {numero_pagina}: {e}")
            return []


def extract_text_per_page(pdf_path: str) -> list[str]:
    """Extrae texto de cada página del PDF con instalación automática de PyMuPDF si es necesario"""
    try:
        # Intentar importar PyMuPDF
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.info("PyMuPDF no encontrado, intentando instalación automática...")
            import subprocess
            import sys
            try:
                # Intentar instalar PyMuPDF automáticamente
                subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF==1.23.14"])
                import fitz  # Importar después de la instalación
                logger.info("✅ PyMuPDF instalado exitosamente")
            except Exception as install_error:
                logger.warning(f"No se pudo instalar PyMuPDF automáticamente: {install_error}")
                raise ImportError("PyMuPDF no disponible")
        
        doc = fitz.open(pdf_path)
        pages = []
        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text") or ""
            pages.append(text)
            logger.debug(f"Página {page_num}: {len(text)} caracteres extraídos")
        doc.close()
        logger.info(f"Extraídas {len(pages)} páginas de {pdf_path}")
        return pages
    
    except ImportError:
        logger.warning("PyMuPDF no disponible, usando pdfminer como alternativa")
        try:
            from pdfminer.high_level import extract_text
            txt = extract_text(pdf_path) or ""
            logger.info(f"Extraído texto completo con pdfminer: {len(txt)} caracteres")
            return [txt]
        except Exception as e:
            logger.error(f"Error extrayendo texto con pdfminer: {e}")
            return []
    
    except Exception as e:
        logger.error(f"Error extrayendo texto con PyMuPDF: {e}")
        return []


def main():
    """Función principal del procesador DOF integrado con Haiku"""
    logger.info("="*60)
    logger.info("DOF EXTRACTOR INTEGRADO CON HAIKU")
    logger.info(f"Período: Martes y Jueves de Agosto 2025")
    logger.info(f"Total de fechas: {len(AUG_2025)}")
    logger.info(f"Ediciones: {', '.join(EDICIONES)}")
    logger.info("🧠 Procesamiento DIRECTO con Haiku (sin TXT intermedios)")
    logger.info("="*60)
    
    # Verificar API key de Anthropic
    if not os.getenv('ANTHROPIC_API_KEY'):
        logger.error("❌ ANTHROPIC_API_KEY no configurada en .env")
        return False
    
    # Crear directorios
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(OUT_JSON_DIR, exist_ok=True)
    
    # Inicializar componentes
    downloader = DOFDownloader(OUT_DIR)
    haiku_extractor = HaikuExtractor()
    
    # Estadísticas
    stats = {
        "pdfs_descargados": 0,
        "pdfs_fallidos": 0,
        "total_paginas_analizadas": 0,
        "total_licitaciones_extraidas": 0,
        "archivos_json_generados": 0
    }
    
    todas_licitaciones = []
    
    # Procesar cada fecha y edición
    for fecha in AUG_2025:
        ddmmyyyy = f"{fecha.day:02d}{fecha.month:02d}{fecha.year}"
        
        for edicion in EDICIONES:
            tag = f"{ddmmyyyy}_{edicion}"
            logger.info(f"\n{'='*40}")
            logger.info(f"Procesando: {fecha.isoformat()} - Edición {edicion}")
            
            # Descargar PDF
            pdf_path = downloader.download_pdf(ddmmyyyy, edicion)
            
            if not pdf_path:
                stats["pdfs_fallidos"] += 1
                continue
            
            stats["pdfs_descargados"] += 1
            
            # Extraer texto por página
            pages = extract_text_per_page(pdf_path)
            
            if not pages:
                logger.warning(f"No se pudo extraer texto de {pdf_path}")
                continue
            
            # Encontrar páginas con convocatorias
            inicio, fin = haiku_extractor.encontrar_paginas_convocatorias(pages)
            
            # Procesar solo las páginas de convocatorias
            paginas_convocatorias = pages[inicio:fin]
            logger.info(f"  Procesando páginas {inicio + 1} a {fin} ({len(paginas_convocatorias)} páginas de convocatorias)")
            
            licitaciones_archivo = []
            
            # Enviar cada página a Haiku
            for i, contenido_pagina in enumerate(paginas_convocatorias):
                numero_pagina_real = inicio + i + 1
                
                if len(contenido_pagina.strip()) < 100:  # Saltar páginas muy cortas
                    continue
                
                logger.info(f"  🧠 Procesando página {numero_pagina_real} con Haiku...")
                licitaciones = haiku_extractor.procesar_pagina_con_haiku(
                    numero_pagina_real, contenido_pagina, f"{tag}.pdf"
                )
                
                if licitaciones:
                    licitaciones_archivo.extend(licitaciones)
                    stats["total_licitaciones_extraidas"] += len(licitaciones)
                
                stats["total_paginas_analizadas"] += 1
                
                # Pequeña pausa para no saturar la API
                time.sleep(0.5)
            
            # Guardar resultados del archivo
            if licitaciones_archivo:
                archivo_json = os.path.join(OUT_JSON_DIR, f"{tag}_haiku.json")
                with open(archivo_json, 'w', encoding='utf-8') as f:
                    json.dump({
                        'fecha_procesamiento': datetime.now().isoformat(),
                        'archivo_origen': f"{tag}.pdf",
                        'fecha_dof': fecha.isoformat(),
                        'edicion': edicion,
                        'total_licitaciones': len(licitaciones_archivo),
                        'paginas_procesadas': len(paginas_convocatorias),
                        'procesado_con_haiku': True,
                        'modelo': 'claude-3-5-haiku-20241022',
                        'licitaciones': licitaciones_archivo
                    }, f, ensure_ascii=False, indent=2)
                
                logger.info(f"  💾 Guardado: {archivo_json} ({len(licitaciones_archivo)} licitaciones)")
                todas_licitaciones.extend(licitaciones_archivo)
                stats["archivos_json_generados"] += 1
    
    # Guardar consolidado final
    if todas_licitaciones:
        consolidado_json = os.path.join(OUT_JSON_DIR, f"dof_haiku_consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(consolidado_json, 'w', encoding='utf-8') as f:
            json.dump({
                'fecha_procesamiento': datetime.now().isoformat(),
                'periodo': '2025-08-martes-jueves',
                'estadisticas': stats,
                'total_licitaciones': len(todas_licitaciones),
                'procesado_con_haiku_integrado': True,
                'modelo': 'claude-3-5-haiku-20241022',
                'licitaciones': todas_licitaciones
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📁 Consolidado guardado en: {consolidado_json}")
    
    # Mostrar estadísticas finales
    logger.info("\n" + "="*60)
    logger.info("🎉 PROCESAMIENTO COMPLETADO")
    logger.info("="*60)
    logger.info(f"✓ PDFs descargados: {stats['pdfs_descargados']}")
    logger.info(f"✗ PDFs fallidos: {stats['pdfs_fallidos']}")
    logger.info(f"🔍 Páginas analizadas con Haiku: {stats['total_paginas_analizadas']}")
    logger.info(f"🎯 TOTAL LICITACIONES EXTRAÍDAS: {stats['total_licitaciones_extraidas']}")
    logger.info(f"📊 Archivos JSON generados: {stats['archivos_json_generados']}")
    logger.info(f"📁 Archivos guardados en: {os.path.abspath(OUT_JSON_DIR)}")
    logger.info("="*60)
    
    return stats['total_licitaciones_extraidas'] > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
