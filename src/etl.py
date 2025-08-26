#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestador ETL Principal - Paloma Licitera
Integra scrapers de etl-process/extractors/ como fuentes principales
"""

import logging
import yaml
import subprocess
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Agregar directorios al path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "etl-process"))

from database import Database
from extractors.base import BaseExtractor
from extractors.comprasmx import ComprasMXExtractor
from extractors.dof import DOFExtractor
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
        """Inicializar procesadores de archivos (para post-procesamiento)."""
        processors = {}
        
        if self.config['sources']['comprasmx']['enabled']:
            processors['comprasmx'] = ComprasMXExtractor(self.config)
            
        if self.config['sources']['dof']['enabled']:
            processors['dof'] = DOFExtractor(self.config)
            
        if self.config['sources']['tianguis']['enabled']:
            processors['tianguis'] = TianguisExtractor(self.config)
            
        return processors
    
    def ejecutar(self, fuente: str = 'all', solo_procesamiento: bool = False) -> Dict:
        """
        Ejecutar ETL completo: scraping + procesamiento + carga.
        
        Args:
            fuente: 'all', 'comprasmx', 'dof', 'tianguis', 'zip'
            solo_procesamiento: Si True, omite la fase de scraping
        """
        logger.info(f"Iniciando ETL para: {fuente}")
        if solo_procesamiento:
            logger.info("🚫 MODO SOLO PROCESAMIENTO - Omitiendo scrapers")
        
        resultados = {
            'inicio': datetime.now(),
            'fuentes': {},
            'totales': {'extraidos': 0, 'insertados': 0, 'errores': 0}
        }
        
        # 1. FASE DE SCRAPING - Solo si no es solo procesamiento
        if not solo_procesamiento:
            if fuente == 'all':
                self._ejecutar_todos_scrapers(resultados)
            else:
                self._ejecutar_scraper(fuente, resultados)
        else:
            logger.info("⏭️ Saltando fase de scraping...")
        
        # 2. FASE DE PROCESAMIENTO - Procesar archivos generados
        self._procesar_archivos_generados(fuente, resultados)
        
        # 3. PROCESAR ZIPs si se solicita
        if fuente in ['all', 'zip']:
            self._procesar_zips(resultados)
        
        resultados['fin'] = datetime.now()
        resultados['duracion'] = str(resultados['fin'] - resultados['inicio'])
        
        logger.info(f"ETL terminado: {resultados['totales']}")
        return resultados
    
    def _ejecutar_todos_scrapers(self, resultados: Dict):
        """Ejecutar todos los scrapers disponibles en orden de prioridad."""
        # ORDEN DE PRIORIDAD:
        # 1. ComprasMX (máxima prioridad) - Portal Federal de Compras
        # 2. DOF (alta prioridad) - Diario Oficial de la Federación  
        # 3. Tianguis Digital (media prioridad) - CDMX
        scrapers = ['comprasmx', 'dof', 'tianguis']
        
        for scraper in scrapers:
            if self._scraper_habilitado(scraper):
                logger.info(f"🎯 Ejecutando scraper prioritario: {scraper}")
                self._ejecutar_scraper(scraper, resultados)
    
    def _scraper_habilitado(self, scraper: str) -> bool:
        """Verificar si un scraper está habilitado en la configuración."""
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
                self._ejecutar_dof_scraper(resultado_scraping)
            elif fuente == 'tianguis':
                self._ejecutar_tianguis_scraper(resultado_scraping)
                
        except Exception as e:
            logger.error(f"Error ejecutando scraper {fuente}: {e}")
            resultado_scraping['error_scraping'] = str(e)
        
        resultados['fuentes'][f'{fuente}_scraping'] = resultado_scraping
    
    def _ejecutar_comprasmx_scraper(self, resultado: Dict):
        """Ejecutar scraper de ComprasMX."""
        # Usar el nuevo scraper avanzado ComprasMX_v2Claude.py
        scraper_path = self.scrapers_dir / "comprasMX" / "ComprasMX_v2Claude.py"
        
        if scraper_path.exists():
            logger.info("🕷️ Ejecutando scraper ComprasMX v2 (captura completa)...")
            
            # Ejecutar el scraper avanzado
            process = subprocess.run([
                sys.executable, str(scraper_path)
            ], capture_output=True, text=True, cwd=str(scraper_path.parent))
            
            if process.returncode == 0:
                resultado['scraping_exitoso'] = True
                logger.info("✅ Scraper ComprasMX v2 ejecutado exitosamente")
                # Contar archivos generados
                data_dir = self.data_dir / "comprasmx"
                json_files = list(data_dir.glob("*.json")) if data_dir.exists() else []
                resultado['archivos_generados'] = len(json_files)
                logger.info(f"📁 Archivos JSON generados: {len(json_files)}")
            else:
                logger.error(f"❌ Error en scraper ComprasMX v2: {process.stderr}")
                resultado['error_scraping'] = process.stderr
        else:
            logger.warning(f"Scraper no encontrado: {scraper_path}")
            resultado['error_scraping'] = f"Scraper no encontrado: {scraper_path}"
    
    def _ejecutar_dof_scraper(self, resultado: Dict):
        """Ejecutar scraper del DOF - COMPLETO con procesamiento."""
        # Paso 1: Descargar PDFs
        scraper_path = self.scrapers_dir / "dof" / "dof_extraccion_estructuracion.py"
        
        if scraper_path.exists():
            logger.info("📥 Descargando PDFs del DOF...")
            
            process = subprocess.run([
                sys.executable, str(scraper_path)
            ], capture_output=True, text=True, cwd=str(scraper_path.parent))
            
            if process.returncode == 0:
                resultado['scraping_exitoso'] = True
                logger.info("✅ PDFs del DOF descargados")
            else:
                logger.error(f"❌ Error descargando DOF: {process.stderr}")
                resultado['error_scraping'] = process.stderr
                return
        else:
            logger.warning(f"Scraper no encontrado: {scraper_path}")
            return
        
        # Paso 2: Procesar PDFs a TXT y luego a JSON
        estructura_path = self.scrapers_dir / "dof" / "estructura_dof.py"
        
        if estructura_path.exists():
            logger.info("🔄 Procesando archivos del DOF (PDF -> TXT -> JSON)...")
            
            # Obtener todos los TXTs en el directorio
            dof_dir = self.data_dir / "dof"
            txt_files = list(dof_dir.glob("*.txt")) if dof_dir.exists() else []
            
            if txt_files:
                logger.info(f"📝 Procesando {len(txt_files)} archivos TXT...")
                
                for txt_file in txt_files:
                    # Verificar si ya existe el JSON
                    json_file = txt_file.with_suffix('').with_name(txt_file.stem + '_licitaciones.json')
                    if not json_file.exists():
                        logger.info(f"   Procesando: {txt_file.name}")
                        
                        process = subprocess.run([
                            sys.executable, str(estructura_path), str(txt_file)
                        ], capture_output=True, text=True, cwd=str(estructura_path.parent))
                        
                        if process.returncode == 0:
                            logger.info(f"   ✅ {txt_file.name} procesado")
                        else:
                            logger.error(f"   ❌ Error procesando {txt_file.name}")
                
                # Contar JSONs generados
                json_files = list(dof_dir.glob("*_licitaciones.json"))
                resultado['archivos_generados'] = len(json_files)
                logger.info(f"📁 JSONs generados: {len(json_files)}")
            else:
                logger.warning("No se encontraron archivos TXT para procesar")
        else:
            logger.error(f"No se encontró el procesador: {estructura_path}")
    
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
                logger.info("✅ Scraper Tianguis Digital ejecutado exitosamente")
                
                # Contar archivos generados
                tianguis_dir = self.data_dir / "tianguis"
                if tianguis_dir.exists():
                    archivos = list(tianguis_dir.glob("*"))
                    resultado['archivos_generados'] = len(archivos)
                    logger.info(f"📁 Archivos generados: {len(archivos)}")
            else:
                logger.error(f"❌ Error en scraper Tianguis: {process.stderr}")
                resultado['error_scraping'] = process.stderr
        else:
            logger.warning(f"Scraper no encontrado: {scraper_path}")
    
    def _procesar_archivos_generados(self, fuente: str, resultados: Dict):
        """Procesar archivos generados por los scrapers e insertar en BD."""
        logger.info("📁 Procesando archivos generados e insertando en BD...")
        
        # Mapear fuentes a procesadores
        fuentes_procesamiento = []
        if fuente == 'all':
            fuentes_procesamiento = list(self.file_processors.keys())
        elif fuente in self.file_processors:
            fuentes_procesamiento = [fuente]
        
        for nombre_fuente in fuentes_procesamiento:
            if nombre_fuente in self.file_processors:
                logger.info(f"💾 Procesando e insertando: {nombre_fuente}")
                resultado_fuente = self._procesar_fuente(nombre_fuente)
                resultados['fuentes'][f'{nombre_fuente}_procesamiento'] = resultado_fuente
                resultados['totales']['extraidos'] += resultado_fuente['extraidos']
                resultados['totales']['insertados'] += resultado_fuente['insertados']
                resultados['totales']['errores'] += resultado_fuente['errores']
    
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
            # Extraer datos
            licitaciones = extractor.extraer()
            resultado['extraidos'] = len(licitaciones)
            logger.info(f"   📊 Extraídas {len(licitaciones)} licitaciones")
            
            # Insertar en BD
            for licitacion in licitaciones:
                try:
                    if self.db.insertar_licitacion(licitacion):
                        resultado['insertados'] += 1
                except Exception as e:
                    logger.debug(f"Error insertando licitación: {e}")
                    resultado['errores'] += 1
            
            logger.info(f"   💾 Insertadas {resultado['insertados']} licitaciones en BD")
                    
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
    
    parser = argparse.ArgumentParser(description='ETL Paloma Licitera')
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
    
    etl = ETL()
    
    if args.setup:
        etl.db.setup()
        print("✅ Base de datos configurada")
    else:
        resultados = etl.ejecutar(args.fuente, solo_procesamiento=getattr(args, 'solo_procesamiento', False))
        print(f"""
🎯 ETL Completado
═══════════════
📊 Extraídos: {resultados['totales']['extraidos']}
💾 Insertados: {resultados['totales']['insertados']}
❌ Errores: {resultados['totales']['errores']}
⏱️ Duración: {resultados['duracion']}
        """)

if __name__ == "__main__":
    main()
