#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestador ETL Principal - Paloma Licitera
Integra scrapers de etl-process/extractors/ como fuentes principales
Incluye el parser DOF mejorado con extracción de ubicación geográfica
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
from extractors.dof_mejorado import DOFMejoradoExtractor  # NUEVO: Extractor mejorado
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
            # NUEVO: Usar extractor DOF mejorado si está disponible
            try:
                processors['dof'] = DOFMejoradoExtractor(self.config)
                logger.info("✅ Usando extractor DOF MEJORADO con parser de ubicación geográfica")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo cargar extractor DOF mejorado: {e}")
                logger.info("📋 Usando extractor DOF estándar")
                processors['dof'] = DOFExtractor(self.config)
            
        if self.config['sources']['tianguis']['enabled']:
            processors['tianguis'] = TianguisExtractor(self.config)
            
        return processors
    
    def ejecutar(self, fuente: str = 'all', solo_procesamiento: bool = False, 
                 usar_parser_mejorado: bool = True) -> Dict:
        """
        Ejecutar ETL completo: scraping + procesamiento + carga.
        
        Args:
            fuente: 'all', 'comprasmx', 'dof', 'tianguis', 'zip'
            solo_procesamiento: Si True, omite la fase de scraping
            usar_parser_mejorado: Si True, usa el parser DOF mejorado (default: True)
        """
        logger.info(f"🚀 Iniciando ETL para: {fuente}")
        if solo_procesamiento:
            logger.info("🚫 MODO SOLO PROCESAMIENTO - Omitiendo scrapers")
        if usar_parser_mejorado and fuente in ['all', 'dof']:
            logger.info("🔍 Parser DOF mejorado ACTIVADO - Extracción de ubicación geográfica")
        
        resultados = {
            'inicio': datetime.now(),
            'fuentes': {},
            'totales': {'extraidos': 0, 'insertados': 0, 'errores': 0}
        }
        
        # 1. FASE DE SCRAPING - Solo si no es solo procesamiento
        if not solo_procesamiento:
            if fuente == 'all':
                self._ejecutar_todos_scrapers(resultados, usar_parser_mejorado)
            else:
                self._ejecutar_scraper(fuente, resultados, usar_parser_mejorado)
        else:
            logger.info("⏭️ Saltando fase de scraping...")
        
        # 2. FASE DE PROCESAMIENTO - Procesar archivos generados
        self._procesar_archivos_generados(fuente, resultados)
        
        # 3. PROCESAR ZIPs si se solicita
        if fuente in ['all', 'zip']:
            self._procesar_zips(resultados)
        
        # 4. Mostrar estadísticas de ubicación si es DOF mejorado
        if usar_parser_mejorado and fuente in ['all', 'dof']:
            self._mostrar_estadisticas_geograficas()
        
        resultados['fin'] = datetime.now()
        resultados['duracion'] = str(resultados['fin'] - resultados['inicio'])
        
        logger.info(f"✅ ETL terminado: {resultados['totales']}")
        return resultados
    
    def _ejecutar_todos_scrapers(self, resultados: Dict, usar_parser_mejorado: bool = True):
        """Ejecutar todos los scrapers disponibles en orden de prioridad."""
        # ORDEN DE PRIORIDAD:
        # 1. ComprasMX (máxima prioridad) - Portal Federal de Compras
        # 2. DOF (alta prioridad) - Diario Oficial de la Federación  
        # 3. Tianguis Digital (media prioridad) - CDMX
        scrapers = ['comprasmx', 'dof', 'tianguis']
        
        for scraper in scrapers:
            if self._scraper_habilitado(scraper):
                logger.info(f"🎯 Ejecutando scraper prioritario: {scraper}")
                self._ejecutar_scraper(scraper, resultados, usar_parser_mejorado)
    
    def _scraper_habilitado(self, scraper: str) -> bool:
        """Verificar si un scraper está habilitado en la configuración."""
        config_map = {
            'comprasmx': self.config['sources']['comprasmx']['enabled'],
            'dof': self.config['sources']['dof']['enabled'],
            'tianguis': self.config['sources']['tianguis']['enabled']
        }
        return config_map.get(scraper, False)
    
    def _ejecutar_scraper(self, fuente: str, resultados: Dict, usar_parser_mejorado: bool = True):
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
                if usar_parser_mejorado:
                    self._ejecutar_dof_scraper_mejorado(resultado_scraping)
                else:
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
    
    def _ejecutar_dof_scraper_mejorado(self, resultado: Dict):
        """
        Ejecutar scraper del DOF con parser mejorado.
        Procesa TXTs existentes con extracción de ubicación geográfica.
        """
        logger.info("🔍 Ejecutando procesamiento DOF MEJORADO...")
        
        # Usar el procesador mejorado directamente
        procesar_script = Path(__file__).parent / "parsers" / "dof" / "procesar_dof_mejorado.py"
        
        if procesar_script.exists():
            logger.info("📝 Procesando archivos TXT con parser mejorado...")
            
            # Directorio con archivos TXT
            dof_dir = self.data_dir / "dof"
            
            if dof_dir.exists():
                process = subprocess.run([
                    sys.executable, str(procesar_script), str(dof_dir)
                ], capture_output=True, text=True)
                
                if process.returncode == 0:
                    resultado['scraping_exitoso'] = True
                    logger.info("✅ Parser DOF mejorado ejecutado exitosamente")
                    
                    # Contar JSONs mejorados generados
                    json_files = list(dof_dir.glob("*_mejorado.json"))
                    resultado['archivos_generados'] = len(json_files)
                    logger.info(f"📁 JSONs mejorados generados: {len(json_files)}")
                    
                    # Mostrar estadísticas de ubicación
                    self._analizar_ubicaciones_dof(json_files)
                else:
                    logger.error(f"❌ Error en parser DOF mejorado: {process.stderr}")
                    # Si falla, intentar con el parser estándar
                    logger.info("⚠️ Intentando con parser DOF estándar...")
                    self._ejecutar_dof_scraper(resultado)
            else:
                logger.warning(f"No existe el directorio {dof_dir}")
                resultado['error_scraping'] = f"Directorio no encontrado: {dof_dir}"
        else:
            logger.warning("Parser mejorado no encontrado, usando estándar")
            self._ejecutar_dof_scraper(resultado)
    
    def _ejecutar_dof_scraper(self, resultado: Dict):
        """Ejecutar scraper del DOF - COMPLETO con procesamiento estándar."""
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
            'errores': 0,
            'con_ubicacion': 0  # NUEVO: Contador de licitaciones con ubicación
        }
        
        try:
            # Extraer datos
            licitaciones = extractor.extraer()
            resultado['extraidos'] = len(licitaciones)
            logger.info(f"   📊 Extraídas {len(licitaciones)} licitaciones")
            
            # Insertar en BD
            for licitacion in licitaciones:
                try:
                    # Contar licitaciones con ubicación geográfica
                    if licitacion.get('entidad_federativa'):
                        resultado['con_ubicacion'] += 1
                    
                    if self.db.insertar_licitacion(licitacion):
                        resultado['insertados'] += 1
                except Exception as e:
                    logger.debug(f"Error insertando licitación: {e}")
                    resultado['errores'] += 1
            
            logger.info(f"   💾 Insertadas {resultado['insertados']} licitaciones en BD")
            
            # Mostrar estadísticas de ubicación si es DOF
            if nombre_fuente == 'dof' and resultado['con_ubicacion'] > 0:
                logger.info(f"   🗺️ Con ubicación geográfica: {resultado['con_ubicacion']}/{resultado['extraidos']}")
                    
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
    
    def _analizar_ubicaciones_dof(self, json_files: List[Path]):
        """Analizar y mostrar estadísticas de ubicación de JSONs DOF mejorados."""
        total_con_estado = 0
        total_con_municipio = 0
        estados_contador = {}
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                
                for lic in datos.get('licitaciones', []):
                    if lic.get('entidad_federativa'):
                        total_con_estado += 1
                        estado = lic['entidad_federativa']
                        estados_contador[estado] = estados_contador.get(estado, 0) + 1
                    if lic.get('municipio'):
                        total_con_municipio += 1
            except:
                pass
        
        if total_con_estado > 0:
            logger.info(f"🗺️ Estadísticas de ubicación DOF:")
            logger.info(f"   • Con entidad federativa: {total_con_estado}")
            logger.info(f"   • Con municipio: {total_con_municipio}")
            
            # Top 3 estados
            if estados_contador:
                top_estados = sorted(estados_contador.items(), key=lambda x: x[1], reverse=True)[:3]
                logger.info(f"   • Top estados: {', '.join([f'{e[0]} ({e[1]})' for e in top_estados])}")
    
    def _mostrar_estadisticas_geograficas(self):
        """Mostrar estadísticas geográficas de la BD."""
        try:
            stats = self.db.obtener_estadisticas()
            
            if stats.get('por_entidad_federativa'):
                logger.info("\n🗺️ DISTRIBUCIÓN GEOGRÁFICA (DOF):")
                for entidad, cantidad in list(stats['por_entidad_federativa'].items())[:5]:
                    logger.info(f"   • {entidad}: {cantidad} licitaciones")
        except Exception as e:
            logger.debug(f"No se pudieron obtener estadísticas geográficas: {e}")


def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='ETL Paloma Licitera con Parser DOF Mejorado')
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
    parser.add_argument(
        '--parser-estandar',
        action='store_true',
        help='Usar parser DOF estándar en lugar del mejorado'
    )
    
    args = parser.parse_args()
    
    etl = ETL()
    
    if args.setup:
        etl.db.setup()
        print("✅ Base de datos configurada")
    else:
        # Determinar si usar parser mejorado
        usar_parser_mejorado = not args.parser_estandar
        
        resultados = etl.ejecutar(
            args.fuente, 
            solo_procesamiento=args.solo_procesamiento,
            usar_parser_mejorado=usar_parser_mejorado
        )
        
        print(f"""
🎯 ETL Completado
═══════════════
📊 Extraídos: {resultados['totales']['extraidos']}
💾 Insertados: {resultados['totales']['insertados']}
❌ Errores: {resultados['totales']['errores']}
⏱️ Duración: {resultados['duracion']}
        """)
        
        # Mostrar información adicional si se usó parser mejorado
        if usar_parser_mejorado and args.fuente in ['all', 'dof']:
            if 'dof_procesamiento' in resultados['fuentes']:
                dof_stats = resultados['fuentes']['dof_procesamiento']
                if dof_stats.get('con_ubicacion', 0) > 0:
                    print(f"🗺️ Licitaciones DOF con ubicación: {dof_stats['con_ubicacion']}/{dof_stats['extraidos']}")


if __name__ == "__main__":
    main()
