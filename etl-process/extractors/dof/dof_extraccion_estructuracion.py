#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descarga mejorada de PDFs del DOF con manejo robusto de SSL/certificados
- Maneja problemas de certificados SSL
- Múltiples métodos de descarga
- Reintentos automáticos
- Mejor logging y diagnóstico

Dependencias requeridas:
    pip install requests pymupdf pdfminer.six urllib3 certifi
"""
import os
import re
import json
import sys
import time
import warnings
from datetime import date, timedelta
import requests
import logging
from typing import Optional
import ssl
import urllib3
from urllib.parse import quote

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

# Asegura que el directorio actual esté en sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Intentar importar estructura_dof si existe
try:
    from estructura_dof import DOFLicitacionesExtractor
    ESTRUCTURA_DISPONIBLE = True
except ImportError:
    logger.warning("No se encontró estructura_dof.py - Se omitirá la extracción estructurada")
    ESTRUCTURA_DISPONIBLE = False

# ========= Configuración =========
OUT_DIR = "../../../data/raw/dof"
OUT_JSON_DIR = "../../../data/raw/dof"

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


def extract_text_per_page(pdf_path: str) -> list[str]:
    """Extrae texto de cada página del PDF"""
    try:
        import fitz  # PyMuPDF
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
        logger.warning("PyMuPDF no disponible, usando pdfminer")
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
    """Función principal del scraper DOF"""
    logger.info("="*60)
    logger.info("INICIANDO DESCARGA Y PROCESAMIENTO DOF")
    logger.info(f"Período: Martes y Jueves de Agosto 2025")
    logger.info(f"Total de fechas: {len(AUG_2025)}")
    logger.info(f"Ediciones: {', '.join(EDICIONES)}")
    logger.info("="*60)
    
    # Crear directorios
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(OUT_JSON_DIR, exist_ok=True)
    
    # Inicializar downloader
    downloader = DOFDownloader(OUT_DIR)
    
    # Estadísticas
    stats = {
        "exitosos": 0,
        "fallidos": 0,
        "txt_generados": 0,
        "json_generados": 0
    }
    
    # Resumen de procesamiento
    resumen = {
        "period": "2025-08-martes-jueves",
        "fecha_proceso": date.today().isoformat(),
        "pdfs": []
    }
    
    # Procesar cada fecha y edición
    for fecha in AUG_2025:
        ddmmyyyy = f"{fecha.day:02d}{fecha.month:02d}{fecha.year}"
        
        for edicion in EDICIONES:
            tag = f"{ddmmyyyy}_{edicion}"
            logger.info(f"\n{'='*40}")
            logger.info(f"Procesando: {fecha.isoformat()} - Edición {edicion}")
            
            entry = {
                "fecha": fecha.isoformat(),
                "dia_semana": fecha.strftime("%A"),
                "edicion": edicion,
                "pdf": None,
                "txt": None,
                "json": None,
                "status": "pending"
            }
            
            # Descargar PDF
            pdf_path = downloader.download_pdf(ddmmyyyy, edicion)
            
            if not pdf_path:
                entry["status"] = "download_failed"
                stats["fallidos"] += 1
                resumen["pdfs"].append(entry)
                continue
            
            entry["pdf"] = pdf_path
            entry["status"] = "downloaded"
            stats["exitosos"] += 1
            
            # Extraer texto por página
            pages = extract_text_per_page(pdf_path)
            
            if pages:
                txt_path = os.path.join(OUT_DIR, f"{tag}.txt")
                try:
                    with open(txt_path, "w", encoding="utf-8", errors="ignore") as f:
                        for i, text in enumerate(pages, start=1):
                            f.write(f"\n\n{'='*5} [PÁGINA {i}] {'='*5}\n")
                            f.write(text)
                    
                    logger.info(f"[TXT] Generado: {txt_path}")
                    entry["txt"] = txt_path
                    entry["status"] = "text_extracted"
                    stats["txt_generados"] += 1
                    
                    # Extracción estructurada si está disponible
                    if ESTRUCTURA_DISPONIBLE:
                        try:
                            extractor = DOFLicitacionesExtractor(txt_path)
                            if extractor.procesar():
                                json_src = txt_path.replace('.txt', '_licitaciones.json')
                                json_dst = os.path.join(OUT_JSON_DIR, f"{tag}_licitaciones.json")
                                
                                if os.path.exists(json_src):
                                    os.rename(json_src, json_dst)
                                    logger.info(f"[JSON] Generado: {json_dst}")
                                    entry["json"] = json_dst
                                    entry["status"] = "fully_processed"
                                    stats["json_generados"] += 1
                        except Exception as e:
                            logger.error(f"Error en extracción estructurada: {e}")
                
                except Exception as e:
                    logger.error(f"Error escribiendo TXT: {e}")
                    entry["status"] = "text_write_error"
            else:
                logger.warning("No se pudo extraer texto del PDF")
                entry["status"] = "text_extraction_failed"
            
            resumen["pdfs"].append(entry)
    
    # Guardar resumen
    resumen["estadisticas"] = stats
    resumen_path = os.path.join(OUT_JSON_DIR, "dof_procesamiento_resumen.json")
    
    with open(resumen_path, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    
    # Mostrar estadísticas finales
    logger.info("\n" + "="*60)
    logger.info("PROCESAMIENTO COMPLETADO")
    logger.info("="*60)
    logger.info(f"✓ PDFs descargados: {stats['exitosos']}")
    logger.info(f"✗ PDFs fallidos: {stats['fallidos']}")
    logger.info(f"✓ TXT generados: {stats['txt_generados']}")
    logger.info(f"✓ JSON generados: {stats['json_generados']}")
    logger.info(f"📁 Archivos guardados en: {os.path.abspath(OUT_DIR)}")
    logger.info(f"📊 Resumen guardado en: {resumen_path}")
    logger.info("="*60)


if __name__ == "__main__":
    main()