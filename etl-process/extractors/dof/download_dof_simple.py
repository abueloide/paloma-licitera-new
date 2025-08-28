#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simplificado para descargar PDFs del DOF y convertirlos a TXT
Descarga los últimos días disponibles del DOF
"""

import os
import requests
from datetime import date, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Desactivar warnings SSL
import urllib3
urllib3.disable_warnings()

def download_dof_simple():
    """Descarga PDFs recientes del DOF"""
    
    # Crear directorios
    base_dir = Path(__file__).parent.parent.parent.parent
    raw_dir = base_dir / "data" / "raw" / "dof"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    # Headers para la descarga
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/127.0.0.0"
    }
    
    # Descargar últimos 5 días hábiles
    fecha_actual = date.today()
    dias_descargados = 0
    dias_intentados = 0
    max_dias = 30  # Buscar hasta 30 días atrás
    
    logger.info("Iniciando descarga de PDFs del DOF...")
    
    while dias_descargados < 5 and dias_intentados < max_dias:
        fecha = fecha_actual - timedelta(days=dias_intentados)
        dias_intentados += 1
        
        # Solo días hábiles (lunes a viernes)
        if fecha.weekday() >= 5:  # 5=sábado, 6=domingo
            continue
            
        # Formato de fecha para URL
        ddmmyyyy = f"{fecha.day:02d}{fecha.month:02d}{fecha.year}"
        año = fecha.year
        
        for edicion in ["MAT", "VES"]:
            # Nombre del archivo
            filename = f"{ddmmyyyy}_{edicion}"
            pdf_path = raw_dir / f"{filename}.pdf"
            txt_path = raw_dir / f"{filename}.txt"
            
            # Si ya existe el TXT, saltar
            if txt_path.exists():
                logger.info(f"Ya existe: {txt_path.name}")
                continue
                
            # URL del DOF
            url = f"https://www.dof.gob.mx/abrirPDF.php?archivo={ddmmyyyy}-{edicion}.pdf&anio={año}&repo="
            
            try:
                # Descargar PDF
                logger.info(f"Descargando: {fecha} - {edicion}")
                response = requests.get(url, headers=headers, timeout=30, verify=False)
                
                if response.status_code == 200 and response.content.startswith(b'%PDF'):
                    # Guardar PDF
                    with open(pdf_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"✓ Descargado: {pdf_path.name}")
                    
                    # Convertir a TXT
                    try:
                        # Intentar con PyMuPDF
                        import fitz
                        doc = fitz.open(pdf_path)
                        text = ""
                        for page in doc:
                            text += page.get_text()
                        doc.close()
                    except ImportError:
                        # Usar pdfminer como fallback
                        try:
                            from pdfminer.high_level import extract_text
                            text = extract_text(str(pdf_path))
                        except:
                            logger.warning(f"No se pudo extraer texto de {pdf_path.name}")
                            continue
                    
                    # Guardar TXT
                    if text and len(text) > 100:
                        with open(txt_path, 'w', encoding='utf-8') as f:
                            f.write(text)
                        logger.info(f"✓ Convertido a TXT: {txt_path.name}")
                        dias_descargados += 1
                        
                        # Salir si ya tenemos suficientes
                        if dias_descargados >= 5:
                            break
                            
            except Exception as e:
                logger.debug(f"Error descargando {fecha} - {edicion}: {e}")
    
    # Resumen
    txt_files = list(raw_dir.glob("*.txt"))
    logger.info(f"\n{'='*50}")
    logger.info(f"Descarga completada")
    logger.info(f"Archivos TXT disponibles: {len(txt_files)}")
    
    if txt_files:
        logger.info("Archivos listos para procesar con IA:")
        for f in txt_files[:5]:
            logger.info(f"  - {f.name}")
    else:
        logger.warning("No hay archivos TXT. Verifica la conexión o las fechas.")
    
    return len(txt_files) > 0

if __name__ == "__main__":
    success = download_dof_simple()
    exit(0 if success else 1)
