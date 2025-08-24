#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descarga, parseo y extracción estructurada de licitaciones del DOF
- Descarga PDFs para fechas y ediciones especificadas
- Extrae texto por página a TXT
- Aplica parser avanzado (estructura_dof.py) para generar JSON estructurado

Dependencias requeridas:
    pip install requests pymupdf pdfminer.six
"""
import os
import re
import json
import sys
from datetime import date, timedelta
import requests
import logging
from typing import Optional

# Asegura que el directorio actual esté en sys.path para importar estructura_dof
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from estructura_dof import DOFLicitacionesExtractor

logging.getLogger("pdfminer").setLevel(logging.ERROR)

# ========= Config =========
OUT_DIR = "../../data/raw/dof"
OUT_JSON_DIR = "../../data/raw/dof"
# Fechas: martes y jueves de agosto 2025
AUG_DAYS = [d for d in range(1, 32)]
AUG_2025 = [date(2025, 8, d) for d in AUG_DAYS if date(2025, 8, d).weekday() in (1, 3)]  # 1=Martes, 3=Jueves
EDICIONES = ["MAT", "VES"]
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
HDRS = {"User-Agent": UA, "Accept-Language": "es-MX,es;q=0.9,en;q=0.8"}

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
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(OUT_JSON_DIR, exist_ok=True)
    resumen = {"period": "2025-08-martes-jueves", "pdfs": []}
    for d in AUG_2025:
        ddmmyyyy = f"{d.day:02d}{d.month:02d}{d.year}"
        for ed in EDICIONES:
            tag = f"{ddmmyyyy}_{ed}"
            print(f"==> {d.isoformat()} {ed}")
            pdf_path = download_pdf(ddmmyyyy, ed)
            entry = {"fecha": d.isoformat(), "edicion": ed, "pdf": pdf_path, "txt": None, "json": None}
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
                print(f"   [WARN] no se pudo escribir TXT: {e}")
                resumen["pdfs"].append(entry)
                continue
            # Extracción estructurada avanzada
            try:
                extractor = DOFLicitacionesExtractor(txt_path)
                ok = extractor.procesar()
                if ok:
                    json_out = os.path.join(OUT_JSON_DIR, f"{tag}_licitaciones.json")
                    # El extractor ya guarda el JSON, pero lo movemos a versiones-revisadas/dof
                    if os.path.exists(txt_path.replace('.txt', '_licitaciones.json')):
                        os.rename(txt_path.replace('.txt', '_licitaciones.json'), json_out)
                        print(f"   [JSON] {json_out}")
                        entry["json"] = json_out
                else:
                    print(f"   [ERROR] Extracción estructurada fallida")
            except Exception as e:
                print(f"   [ERROR] Estructuración: {e}")
            resumen["pdfs"].append(entry)
    # Guardar resumen
    resumen_path = os.path.join(OUT_JSON_DIR, "dof_extraccion_estructuracion_resumen.json")
    with open(resumen_path, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Resumen -> {resumen_path}")

if __name__ == "__main__":
    main()
