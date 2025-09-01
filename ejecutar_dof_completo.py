#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para ejecutar flujo completo DOF:
1. Descargar PDFs del DOF (agosto 2025)
2. Convertir a TXT con marcadores de página
3. Extraer licitaciones con IA (Claude)

IMPORTANTE: Requiere ANTHROPIC_API_KEY en .env
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verificar_requisitos():
    """Verificar que estén los requisitos necesarios"""
    logger.info("🔍 Verificando requisitos...")
    
    # Verificar API key de Anthropic
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your_api_key_here':
        logger.error("❌ ANTHROPIC_API_KEY no configurada en .env")
        logger.info("   Crear archivo .env con: ANTHROPIC_API_KEY=tu_api_key_aqui")
        return False
    
    logger.info("✅ ANTHROPIC_API_KEY configurada")
    
    # Verificar directorios
    data_dir = Path("data/raw/dof")
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ Directorio creado: {data_dir}")
    
    # Verificar que existan los scripts
    dof_downloader = Path("etl-process/extractors/dof/dof_extraccion_estructuracion.py")
    dof_ai = Path("etl-process/extractors/dof_extractor_ai.py")
    
    if not dof_downloader.exists():
        logger.error(f"❌ No se encontró: {dof_downloader}")
        return False
    
    if not dof_ai.exists():
        logger.error(f"❌ No se encontró: {dof_ai}")
        return False
    
    logger.info("✅ Scripts encontrados")
    return True

def ejecutar_paso1_descarga():
    """Ejecutar descarga de PDFs DOF"""
    logger.info("=" * 60)
    logger.info("PASO 1: DESCARGA DE PDFs DOF - AGOSTO 2025")
    logger.info("=" * 60)
    
    script_path = "etl-process/extractors/dof/dof_extraccion_estructuracion.py"
    
    try:
        # Cambiar al directorio del script para rutas relativas
        original_dir = os.getcwd()
        script_dir = Path(script_path).parent
        os.chdir(script_dir)
        
        logger.info(f"📂 Ejecutando desde: {script_dir}")
        logger.info("⏳ Descargando PDFs... (esto puede tomar 10-15 minutos)")
        
        # Ejecutar el script de descarga
        result = subprocess.run([
            sys.executable, "dof_extraccion_estructuracion.py"
        ], capture_output=True, text=True, timeout=1800)  # 30 minutos timeout
        
        # Restaurar directorio original
        os.chdir(original_dir)
        
        if result.returncode == 0:
            logger.info("✅ PASO 1 COMPLETADO: PDFs descargados y convertidos a TXT")
            logger.info("📋 Output:")
            for line in result.stdout.split('\n')[-10:]:  # Últimas 10 líneas
                if line.strip():
                    logger.info(f"   {line}")
            return True
        else:
            logger.error("❌ Error en descarga de PDFs:")
            logger.error(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Timeout: La descarga tomó más de 30 minutos")
        os.chdir(original_dir)
        return False
    except Exception as e:
        logger.error(f"❌ Error ejecutando descarga: {e}")
        os.chdir(original_dir)
        return False

def verificar_archivos_txt():
    """Verificar que se generaron archivos TXT"""
    logger.info("🔍 Verificando archivos TXT generados...")
    
    data_dir = Path("data/raw/dof")
    txt_files = list(data_dir.glob("*.txt"))
    
    if not txt_files:
        logger.error("❌ No se encontraron archivos TXT en data/raw/dof/")
        return False
    
    logger.info(f"✅ Encontrados {len(txt_files)} archivos TXT:")
    for txt_file in txt_files[:5]:  # Mostrar primeros 5
        size_mb = txt_file.stat().st_size / (1024 * 1024)
        logger.info(f"   📄 {txt_file.name} ({size_mb:.2f} MB)")
    
    if len(txt_files) > 5:
        logger.info(f"   ... y {len(txt_files) - 5} más")
    
    # Verificar que tengan marcadores de página
    sample_file = txt_files[0]
    with open(sample_file, 'r', encoding='utf-8') as f:
        content = f.read(2000)  # Primeros 2000 caracteres
    
    if "===== [PÁGINA" in content:
        logger.info("✅ Archivos TXT tienen marcadores de página correctos")
        return True
    else:
        logger.warning("⚠️  No se encontraron marcadores de página en el sample")
        return True  # Continuar de todos modos

def ejecutar_paso2_extraccion_ia():
    """Ejecutar extracción con IA"""
    logger.info("=" * 60)
    logger.info("PASO 2: EXTRACCIÓN CON IA - CLAUDE HAIKU")
    logger.info("=" * 60)
    
    script_path = "etl-process/extractors/dof_extractor_ai.py"
    
    try:
        # Cambiar al directorio del script
        original_dir = os.getcwd()
        script_dir = Path(script_path).parent
        os.chdir(script_dir)
        
        logger.info(f"📂 Ejecutando desde: {script_dir}")
        logger.info("🧠 Procesando con Claude Haiku...")
        
        # Ejecutar el extractor AI
        result = subprocess.run([
            sys.executable, "dof_extractor_ai.py"
        ], capture_output=True, text=True, timeout=1200)  # 20 minutos timeout
        
        # Restaurar directorio
        os.chdir(original_dir)
        
        if result.returncode == 0:
            logger.info("✅ PASO 2 COMPLETADO: Licitaciones extraídas con IA")
            
            # Buscar resultados en el output
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if "licitaciones extraídas" in line.lower() or "total:" in line.lower():
                    logger.info(f"📊 {line}")
            
            # Mostrar últimas líneas relevantes
            logger.info("📋 Resumen final:")
            for line in output_lines[-15:]:
                if line.strip() and any(palabra in line.lower() 
                                      for palabra in ['total', 'archivos', 'licitaciones', 'páginas']):
                    logger.info(f"   {line}")
            
            return True
        else:
            logger.error("❌ Error en extracción con IA:")
            logger.error(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Timeout: La extracción IA tomó más de 20 minutos")
        os.chdir(original_dir)
        return False
    except Exception as e:
        logger.error(f"❌ Error ejecutando extracción IA: {e}")
        os.chdir(original_dir)
        return False

def mostrar_resultados_finales():
    """Mostrar resultados finales"""
    logger.info("=" * 60)
    logger.info("🎉 RESULTADOS FINALES")
    logger.info("=" * 60)
    
    # Contar archivos generados
    data_dir = Path("data/raw/dof")
    processed_dir = Path("data/processed/dof")
    
    txt_files = list(data_dir.glob("*.txt"))
    json_files = list(processed_dir.glob("*.json")) if processed_dir.exists() else []
    
    logger.info(f"📄 Archivos TXT generados: {len(txt_files)}")
    logger.info(f"📊 Archivos JSON con licitaciones: {len(json_files)}")
    
    if json_files:
        # Contar licitaciones totales
        total_licitaciones = 0
        for json_file in json_files:
            try:
                import json
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'licitaciones' in data:
                        total_licitaciones += len(data['licitaciones'])
            except:
                pass
        
        logger.info(f"🎯 TOTAL LICITACIONES EXTRAÍDAS: {total_licitaciones}")
        logger.info(f"📁 Archivos guardados en: {processed_dir}")
    
    logger.info("✅ FLUJO COMPLETO DOF TERMINADO")

def main():
    """Función principal"""
    logger.info("🐦 PALOMA LICITERA - FLUJO COMPLETO DOF")
    logger.info("=" * 60)
    
    # Paso 0: Verificar requisitos
    if not verificar_requisitos():
        logger.error("❌ Faltan requisitos. Abortando.")
        return False
    
    # Paso 1: Descargar PDFs
    if not ejecutar_paso1_descarga():
        logger.error("❌ Fallo en descarga de PDFs. Abortando.")
        return False
    
    # Verificar archivos TXT
    if not verificar_archivos_txt():
        logger.error("❌ No se generaron archivos TXT correctamente. Abortando.")
        return False
    
    # Paso 2: Extracción con IA
    if not ejecutar_paso2_extraccion_ia():
        logger.error("❌ Fallo en extracción con IA.")
        return False
    
    # Mostrar resultados
    mostrar_resultados_finales()
    
    logger.info("🎉 ¡FLUJO COMPLETO EJECUTADO EXITOSAMENTE!")
    return True

if __name__ == "__main__":
    # Cargar variables de entorno
    from pathlib import Path
    env_file = Path(".env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv()
    
    success = main()
    sys.exit(0 if success else 1)
