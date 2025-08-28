#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestador ETL Principal - Paloma Licitera
Integra scrapers con extracción DOF usando IA (Claude Haiku)
"""

import logging
import yaml
import subprocess
import asyncio
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# IMPORTANTE: Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()  # Esto carga el archivo .env con ANTHROPIC_API_KEY y otras variables

# Agregar directorios al path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "etl-process"))

from database import Database
from extractors.base import BaseExtractor
from extractors.comprasmx import ComprasMXExtractor
from extractors.tianguis import TianguisExtractor
from extractors.zip_processor import ZipProcessor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ETL:
    """Orquestador principal del ETL."""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.db = Database(config_path)
        self.file_processors = self._inicializar_procesadores()
        self.zip_processor = ZipProcessor()
        
        # Rutas de scrapers
        self.scrapers_dir = Path(__file__).parent.parent / "etl-process" / "extractors"
        self.data_dir = Path(self.config['paths']['data_raw'])
        
    def _inicializar_procesadores(self) -> Dict[str, BaseExtractor]:
        """Inicializar procesadores de archivos."""
        processors = {}
        
        if self.config['sources']['comprasmx']['enabled']:
            processors['comprasmx'] = ComprasMXExtractor(self.config)
            
        # NO incluimos DOF aquí porque usaremos el extractor con IA directamente
            
        if self.config['sources']['tianguis']['enabled']:
            processors['tianguis'] = TianguisExtractor(self.config)
            
        return processors
    
    def ejecutar(self, fuente: str = 'all', solo_procesamiento: bool = False) -> Dict:
        """
        Ejecutar ETL completo: scraping + procesamiento + carga.
        """
        logger.info(f"🚀 Iniciando ETL para: {fuente}")
        if solo_procesamiento:
            logger.info("🚫 MODO SOLO PROCESAMIENTO - Omitiendo scrapers")
        
        resultados = {
            'inicio': datetime.now(),
            'fuentes': {},
            'totales': {'extraidos': 0, 'insertados': 0, 'errores': 0}
        }
        
        # 1. FASE DE SCRAPING
        if not solo_procesamiento:
            if fuente == 'all':
                self._ejecutar_todos_scrapers(resultados)
            else:
                self._ejecutar_scraper(fuente, resultados)
        
        # 2. FASE DE PROCESAMIENTO
        self._procesar_archivos_generados(fuente, resultados)
        
        # 3. PROCESAR ZIPs si se solicita
        if fuente in ['all', 'zip']:
            self._procesar_zips(resultados)
        
        resultados['fin'] = datetime.now()
        resultados['duracion'] = str(resultados['fin'] - resultados['inicio'])
        
        logger.info(f"✅ ETL terminado: {resultados['totales']}")
        return resultados
    
    def _ejecutar_todos_scrapers(self, resultados: Dict):
        """Ejecutar todos los scrapers disponibles."""
        scrapers = ['comprasmx', 'dof', 'tianguis']
        
        for scraper in scrapers:
            if self._scraper_habilitado(scraper):
                logger.info(f"🎯 Ejecutando scraper: {scraper}")
                self._ejecutar_scraper(scraper, resultados)
    
    def _scraper_habilitado(self, scraper: str) -> bool:
        """Verificar si un scraper está habilitado."""
        config_map = {
            'comprasmx': self.config['sources']['comprasmx']['enabled'],
            'dof': self.config['sources']['dof']['enabled'],
            'tianguis': self.config['sources']['tianguis']['enabled']
        }
        return config_map.get(scraper, False)
    
    def _ejecutar_scraper(self, fuente: str, resultados: Dict):
        """Ejecutar un scraper específico."""
        logger.info(f"🕷️ Ejecutando scraper: {fuente}")
        
        resultado_scraping = {
            'scraping_exitoso': False,
            'archivos_generados': 0,
            'error_scraping': None
        }
        
        try:
            if fuente == 'comprasmx':
                self._ejecutar_comprasmx_scraper(resultado_scraping)
            elif fuente == 'dof':
                self._ejecutar_dof_con_ia(resultado_scraping)  # CAMBIO AQUÍ
            elif fuente == 'tianguis':
                self._ejecutar_tianguis_scraper(resultado_scraping)
                
        except Exception as e:
            logger.error(f"Error ejecutando scraper {fuente}: {e}")
            resultado_scraping['error_scraping'] = str(e)
        
        resultados['fuentes'][f'{fuente}_scraping'] = resultado_scraping
    
    def _ejecutar_dof_con_ia(self, resultado: Dict):
        """
        Ejecutar procesamiento DOF con IA (Claude Haiku).
        ESTE ES EL CAMBIO PRINCIPAL - USA EXTRACTOR CON IA
        """
        logger.info("🤖 Ejecutando extracción DOF con IA (Claude Haiku)...")
        
        # Verificar API key
        if not os.getenv('ANTHROPIC_API_KEY'):
            logger.warning("⚠️ ANTHROPIC_API_KEY no configurada en .env")
            logger.info("📝 Intentando con extractor DOF tradicional...")
            self._ejecutar_dof_scraper(resultado)
            return
        
        # Primero descargar PDFs si no existen
        dof_dir = self.data_dir / "dof"
        txt_files = list(dof_dir.glob("*.txt")) if dof_dir.exists() else []
        
        if not txt_files:
            logger.info("📥 Descargando PDFs del DOF primero...")
            self._descargar_pdfs_dof(resultado)
        
        # Ahora usar el extractor con IA
        extractor_ai_path = self.scrapers_dir.parent / "extractors" / "dof_extractor_ai.py"
        
        if extractor_ai_path.exists():
            logger.info("🧠 Procesando con Claude Haiku 3.5...")
            
            process = subprocess.run([
                sys.executable, str(extractor_ai_path)
            ], capture_output=True, text=True, env={**os.environ})
            
            if process.returncode == 0:
                resultado['scraping_exitoso'] = True
                logger.info("✅ Extracción DOF con IA completada")
                
                # Contar archivos generados
                processed_dir = Path("data/processed/dof")
                if processed_dir.exists():
                    json_files = list(processed_dir.glob("*_ai.json"))
                    resultado['archivos_generados'] = len(json_files)
                    logger.info(f"📁 JSONs generados con IA: {len(json_files)}")
            else:
                logger.error(f"❌ Error en extractor con IA: {process.stderr}")
                logger.info("📝 Intentando con extractor tradicional...")
                self._ejecutar_dof_scraper(resultado)
        else:
            logger.warning(f"No se encontró extractor con IA: {extractor_ai_path}")
            self._ejecutar_dof_scraper(resultado)
    
    def _descargar_pdfs_dof(self, resultado: Dict):
        """Descargar PDFs del DOF."""
        scraper_path = self.scrapers_dir / "dof" / "dof_extraccion_estructuracion.py"
        
        if scraper_path.exists():
            logger.info("📥 Descargando PDFs del DOF...")
            
            process = subprocess.run([
                sys.executable, str(scraper_path)
            ], capture_output=True, text=True, cwd=str(scraper_path.parent))
            
            if process.returncode == 0:
                logger.info("✅ PDFs del DOF descargados")
            else:
                logger.error(f"❌ Error descargando DOF: {process.stderr}")
    
    def _ejecutar_dof_scraper(self, resultado: Dict):
        """Ejecutar scraper del DOF tradicional (fallback)."""
        scraper_path = self.scrapers_dir / "dof" / "dof_extraccion_estructuracion.py"
        
        if scraper_path.exists():
            logger.info("📥 Ejecutando extractor DOF tradicional...")
            
            process = subprocess.run([
                sys.executable, str(scraper_path)
            ], capture_output=True, text=True, cwd=str(scraper_path.parent))
            
            if process.returncode == 0:
                resultado['scraping_exitoso'] = True
                logger.info("✅ DOF tradicional ejecutado")
            else:
                logger.error(f"❌ Error en DOF tradicional: {process.stderr}")
    
    def _ejecutar_comprasmx_scraper(self, resultado: Dict):
        """Ejecutar scraper de ComprasMX."""
        scraper_path = self.scrapers_dir / "comprasMX" / "ComprasMX_v2Claude.py"
        
        if scraper_path.exists():
            logger.info("🕷️ Ejecutando scraper ComprasMX v2...")
            
            process = subprocess.run([
                sys.executable, str(scraper_path)
            ], capture_output=True, text=True, cwd=str(scraper_path.parent))
            
            if process.returncode == 0:
                resultado['scraping_exitoso'] = True
                logger.info("✅ Scraper ComprasMX v2 ejecutado")
                
                data_dir = self.data_dir / "comprasmx"
                json_files = list(data_dir.glob("*.json")) if data_dir.exists() else []
                resultado['archivos_generados'] = len(json_files)
                logger.info(f"📁 Archivos JSON generados: {len(json_files)}")
            else:
                logger.error(f"❌ Error en ComprasMX: {process.stderr}")
    
    def _ejecutar_tianguis_scraper(self, resultado: Dict):
        """Ejecutar scraper de Tianguis Digital."""
        scraper_path = self.scrapers_dir / "tianguis-digital" / "extractor-tianguis.py"
        
        if scraper_path.exists():
            logger.info("🕷️ Ejecutando scraper Tianguis Digital...")
            
            process = subprocess.run([
                sys.executable, str(scraper_path)
            ], capture_output=True, text=True, cwd=str(scraper_path.parent))
            
            if process.returncode == 0:
                resultado['scraping_exitoso'] = True
                logger.info("✅ Scraper Tianguis Digital ejecutado")
                
                tianguis_dir = self.data_dir / "tianguis"
                if tianguis_dir.exists():
                    archivos = list(tianguis_dir.glob("*"))
                    resultado['archivos_generados'] = len(archivos)
                    logger.info(f"📁 Archivos generados: {len(archivos)}")
            else:
                logger.error(f"❌ Error en Tianguis: {process.stderr}")
    
    def _procesar_archivos_generados(self, fuente: str, resultados: Dict):
        """Procesar archivos generados e insertar en BD."""
        logger.info("📁 Procesando archivos e insertando en BD...")
        
        # Para DOF, procesar los archivos generados por IA
        if fuente in ['all', 'dof']:
            self._procesar_dof_ai_files(resultados)
        
        # Procesar otras fuentes normalmente
        fuentes_procesamiento = []
        if fuente == 'all':
            fuentes_procesamiento = list(self.file_processors.keys())
        elif fuente in self.file_processors:
            fuentes_procesamiento = [fuente]
        
        for nombre_fuente in fuentes_procesamiento:
            if nombre_fuente in self.file_processors:
                logger.info(f"💾 Procesando: {nombre_fuente}")
                resultado_fuente = self._procesar_fuente(nombre_fuente)
                resultados['fuentes'][f'{nombre_fuente}_procesamiento'] = resultado_fuente
                resultados['totales']['extraidos'] += resultado_fuente['extraidos']
                resultados['totales']['insertados'] += resultado_fuente['insertados']
                resultados['totales']['errores'] += resultado_fuente['errores']
    
    def _procesar_dof_ai_files(self, resultados: Dict):
        """Procesar archivos JSON generados por el extractor DOF con IA."""
        logger.info("🤖 Procesando archivos DOF generados con IA...")
        
        processed_dir = Path("data/processed/dof")
        if not processed_dir.exists():
            logger.warning("No existe directorio de procesados DOF")
            return
        
        # Buscar el archivo consolidado más reciente
        consolidados = list(processed_dir.glob("dof_consolidado_*.json"))
        
        if not consolidados:
            # Si no hay consolidado, buscar archivos individuales
            json_files = list(processed_dir.glob("*_ai.json"))
        else:
            # Usar el más reciente
            json_files = [max(consolidados, key=lambda x: x.stat().st_mtime)]
        
        resultado_dof = {
            'extraidos': 0,
            'insertados': 0,
            'errores': 0
        }
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                licitaciones = data.get('licitaciones', [])
                resultado_dof['extraidos'] += len(licitaciones)
                
                for lic in licitaciones:
                    try:
                        if self.db.insertar_licitacion(lic):
                            resultado_dof['insertados'] += 1
                    except Exception as e:
                        logger.debug(f"Error insertando: {e}")
                        resultado_dof['errores'] += 1
                
            except Exception as e:
                logger.error(f"Error procesando {json_file}: {e}")
        
        logger.info(f"   💾 DOF con IA: {resultado_dof['insertados']} insertadas de {resultado_dof['extraidos']}")
        
        resultados['fuentes']['dof_ai_procesamiento'] = resultado_dof
        resultados['totales']['extraidos'] += resultado_dof['extraidos']
        resultados['totales']['insertados'] += resultado_dof['insertados']
        resultados['totales']['errores'] += resultado_dof['errores']
    
    def _procesar_fuente(self, nombre_fuente: str) -> Dict:
        """Procesar una fuente específica e insertar en BD."""
        logger.info(f"🔄 Procesando fuente: {nombre_fuente}")
        extractor = self.file_processors[nombre_fuente]
        
        resultado = {
            'extraidos': 0,
            'insertados': 0,
            'errores': 0
        }
        
        try:
            licitaciones = extractor.extraer()
            resultado['extraidos'] = len(licitaciones)
            logger.info(f"   📊 Extraídas {len(licitaciones)} licitaciones")
            
            for licitacion in licitaciones:
                try:
                    if self.db.insertar_licitacion(licitacion):
                        resultado['insertados'] += 1
                except Exception as e:
                    logger.debug(f"Error insertando: {e}")
                    resultado['errores'] += 1
            
            logger.info(f"   💾 Insertadas {resultado['insertados']} licitaciones")
                    
        except Exception as e:
            logger.error(f"Error procesando {nombre_fuente}: {e}")
            resultado['errores'] += 1
            
        return resultado
    
    def _procesar_zips(self, resultados: Dict):
        """Procesar archivos ZIP de PAAAPS."""
        zip_dir = Path(self.config['paths']['data_processed']) / 'tianguis'
        
        if not zip_dir.exists():
            logger.warning(f"Directorio de ZIPs no existe: {zip_dir}")
            return
            
        zip_files = list(zip_dir.glob("*.zip"))
        logger.info(f"Encontrados {len(zip_files)} archivos ZIP")
        
        resultado_zip = {
            'extraidos': 0,
            'insertados': 0,
            'errores': 0
        }
        
        for zip_file in zip_files:
            try:
                licitaciones = self.zip_processor.procesar(zip_file)
                resultado_zip['extraidos'] += len(licitaciones)
                
                for licitacion in licitaciones:
                    if self.db.insertar_licitacion(licitacion):
                        resultado_zip['insertados'] += 1
                        
            except Exception as e:
                logger.error(f"Error procesando ZIP {zip_file}: {e}")
                resultado_zip['errores'] += 1
        
        resultados['fuentes']['zip'] = resultado_zip
        resultados['totales']['extraidos'] += resultado_zip['extraidos']
        resultados['totales']['insertados'] += resultado_zip['insertados']
        resultados['totales']['errores'] += resultado_zip['errores']


def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='ETL Paloma Licitera con IA')
    parser.add_argument(
        '--fuente',
        choices=['all', 'comprasmx', 'dof', 'tianguis', 'zip'],
        default='all',
        help='Fuente de datos a procesar'
    )
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Configurar base de datos'
    )
    parser.add_argument(
        '--solo-procesamiento',
        action='store_true',
        help='Solo procesar archivos existentes, sin ejecutar scrapers'
    )
    
    args = parser.parse_args()
    
    # Verificar API key para DOF
    if args.fuente in ['all', 'dof']:
        if not os.getenv('ANTHROPIC_API_KEY'):
            print("⚠️ ADVERTENCIA: ANTHROPIC_API_KEY no configurada")
            print("   El DOF usará extractor tradicional (menos preciso)")
            print("   Configura tu API key en .env para usar IA")
    
    etl = ETL()
    
    if args.setup:
        etl.db.setup()
        print("✅ Base de datos configurada")
    else:
        resultados = etl.ejecutar(
            args.fuente, 
            solo_procesamiento=args.solo_procesamiento
        )
        
        print(f"""
🎯 ETL Completado
═══════════════
📊 Extraídos: {resultados['totales']['extraidos']}
💾 Insertados: {resultados['totales']['insertados']}
❌ Errores: {resultados['totales']['errores']}
⏱️ Duración: {resultados['duracion']}
        """)
        
        # Mostrar info de DOF con IA si se usó
        if 'dof_ai_procesamiento' in resultados['fuentes']:
            dof_stats = resultados['fuentes']['dof_ai_procesamiento']
            print(f"🤖 DOF con IA: {dof_stats['insertados']} licitaciones procesadas")


if __name__ == "__main__":
    main()
