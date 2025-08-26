#!/usr/bin/env python3
"""
Script para diagnosticar y arreglar problemas con los datos descargados
========================================================================
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Colores para output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_status(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def diagnosticar_dof():
    """Diagnostica y procesa archivos del DOF"""
    print("\n🔍 DIAGNOSTICANDO DOF...")
    print("-" * 50)
    
    dof_dir = Path("data/raw/dof")
    if not dof_dir.exists():
        print_error("No existe el directorio data/raw/dof")
        return False
    
    # Contar archivos
    pdfs = list(dof_dir.glob("*.pdf"))
    txts = list(dof_dir.glob("*.txt"))
    jsons = list(dof_dir.glob("*_licitaciones.json"))
    
    print(f"📁 Archivos encontrados:")
    print(f"   - PDFs: {len(pdfs)}")
    print(f"   - TXTs: {len(txts)}")
    print(f"   - JSONs procesados: {len(jsons)}")
    
    # Verificar si hay PDFs sin procesar
    pdfs_sin_txt = []
    txts_sin_json = []
    
    for pdf in pdfs:
        txt_file = pdf.with_suffix('.txt')
        json_file = pdf.with_suffix('').with_suffix('_licitaciones.json')
        
        if not txt_file.exists():
            pdfs_sin_txt.append(pdf)
        elif not json_file.exists():
            txts_sin_json.append(txt_file)
    
    if pdfs_sin_txt:
        print_warning(f"PDFs sin convertir a TXT: {len(pdfs_sin_txt)}")
        for pdf in pdfs_sin_txt[:3]:  # Mostrar máximo 3
            print(f"   - {pdf.name}")
    
    if txts_sin_json:
        print_warning(f"TXTs sin procesar a JSON: {len(txts_sin_json)}")
        for txt in txts_sin_json[:3]:  # Mostrar máximo 3
            print(f"   - {txt.name}")
    
    # Intentar procesar archivos faltantes
    if txts_sin_json:
        print_info("Intentando procesar TXTs faltantes...")
        
        # Buscar el script estructura_dof.py
        estructura_script = Path("etl-process/extractors/dof/estructura_dof.py")
        if estructura_script.exists():
            for txt in txts_sin_json:
                print(f"   Procesando: {txt.name}")
                try:
                    result = subprocess.run(
                        [sys.executable, str(estructura_script), str(txt)],
                        capture_output=True,
                        text=True,
                        cwd=estructura_script.parent
                    )
                    if result.returncode == 0:
                        print_status(f"   {txt.name} procesado")
                    else:
                        print_error(f"   Error procesando {txt.name}")
                except Exception as e:
                    print_error(f"   Error: {e}")
        else:
            print_error("No se encontró estructura_dof.py")
    
    # Verificar contenido de JSONs
    if jsons:
        print_info("Analizando JSONs procesados...")
        total_licitaciones = 0
        for json_file in jsons:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'licitaciones' in data:
                        count = len(data['licitaciones'])
                        total_licitaciones += count
                        if count > 0:
                            print(f"   ✓ {json_file.name}: {count} licitaciones")
            except Exception as e:
                print_error(f"   Error leyendo {json_file.name}: {e}")
        
        print_status(f"Total de licitaciones en JSONs: {total_licitaciones}")
    
    return True

def diagnosticar_comprasmx():
    """Diagnostica archivos de ComprasMX"""
    print("\n🔍 DIAGNOSTICANDO COMPRASMX...")
    print("-" * 50)
    
    compras_dir = Path("data/raw/comprasmx")
    if not compras_dir.exists():
        print_error("No existe el directorio data/raw/comprasmx")
        return False
    
    jsons = list(compras_dir.glob("*.json"))
    print(f"📁 Archivos JSON encontrados: {len(jsons)}")
    
    if jsons:
        total_licitaciones = 0
        for json_file in jsons[:3]:  # Revisar primeros 3
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Detectar formato
                    if isinstance(data, list):
                        count = len(data)
                    elif isinstance(data, dict) and 'data' in data:
                        count = len(data['data'])
                    else:
                        count = 1 if data else 0
                    
                    total_licitaciones += count
                    print(f"   ✓ {json_file.name}: {count} registros")
            except Exception as e:
                print_error(f"   Error leyendo {json_file.name}: {e}")
    else:
        print_warning("No hay archivos para procesar")
        print_info("Ejecuta: ./paloma.sh download y selecciona ComprasMX")
    
    return True

def diagnosticar_tianguis():
    """Diagnostica archivos de Tianguis"""
    print("\n🔍 DIAGNOSTICANDO TIANGUIS...")
    print("-" * 50)
    
    tianguis_dir = Path("data/raw/tianguis")
    if not tianguis_dir.exists():
        print_error("No existe el directorio data/raw/tianguis")
        tianguis_dir.mkdir(parents=True, exist_ok=True)
        print_status("Directorio creado")
    
    # Verificar si hay archivos mal ubicados
    old_dir = Path("etl-process/extractors/tianguis-digital/descargas")
    if old_dir.exists():
        print_warning(f"Encontrados archivos en ubicación incorrecta: {old_dir}")
        archivos_viejos = list(old_dir.glob("*"))
        if archivos_viejos:
            print_info(f"Moviendo {len(archivos_viejos)} archivos...")
            for archivo in archivos_viejos:
                destino = tianguis_dir / archivo.name
                archivo.rename(destino)
                print(f"   ✓ Movido: {archivo.name}")
    
    # Contar archivos
    csvs = list(tianguis_dir.glob("*.csv"))
    jsons = list(tianguis_dir.glob("*.json"))
    zips = list(tianguis_dir.glob("*.zip"))
    
    print(f"📁 Archivos encontrados:")
    print(f"   - CSVs: {len(csvs)}")
    print(f"   - JSONs: {len(jsons)}")
    print(f"   - ZIPs: {len(zips)}")
    
    if not (csvs or jsons or zips):
        print_warning("No hay archivos para procesar")
        print_info("Ejecuta: ./paloma.sh download y selecciona Tianguis")
    
    return True

def verificar_base_datos():
    """Verifica la conexión y contenido de la base de datos"""
    print("\n🔍 VERIFICANDO BASE DE DATOS...")
    print("-" * 50)
    
    try:
        import psycopg2
        import yaml
        
        # Cargar config
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        db_config = config['database']
        
        # Conectar
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['name'],
            user=db_config['user'],
            password=db_config['password']
        )
        
        cursor = conn.cursor()
        
        # Contar registros por fuente
        cursor.execute("""
            SELECT fuente, COUNT(*) as total
            FROM licitaciones
            GROUP BY fuente
            ORDER BY total DESC
        """)
        
        resultados = cursor.fetchall()
        
        if resultados:
            print_status("Registros en base de datos:")
            for fuente, total in resultados:
                print(f"   - {fuente}: {total}")
        else:
            print_warning("Base de datos vacía")
            print_info("Ejecuta: ./paloma.sh download-quick para procesar archivos existentes")
        
        conn.close()
        return True
        
    except Exception as e:
        print_error(f"Error conectando a la base de datos: {e}")
        print_info("Ejecuta: ./paloma.sh doctor")
        return False

def main():
    """Función principal"""
    print("=" * 60)
    print("🏥 DIAGNÓSTICO DE DATOS - PALOMA LICITERA")
    print("=" * 60)
    
    # Ejecutar diagnósticos
    diagnosticar_dof()
    diagnosticar_comprasmx()
    diagnosticar_tianguis()
    verificar_base_datos()
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN")
    print("=" * 60)
    
    print("\n🎯 PASOS RECOMENDADOS:")
    print("1. Si hay archivos sin procesar:")
    print("   ./paloma.sh download-quick")
    print("\n2. Si la BD está vacía:")
    print("   ./paloma.sh repopulate")
    print("\n3. Para descargar nuevos datos:")
    print("   ./paloma.sh download")
    print("\n4. Para ver el sistema funcionando:")
    print("   ./paloma.sh start")

if __name__ == "__main__":
    main()
