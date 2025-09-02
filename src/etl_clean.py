#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestador ETL LIMPIO - Paloma Licitera
USA SOLAMENTE LOS CORNERSTONES - NO más references obsoletas
"""

import logging
import yaml
import subprocess
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

from database import Database

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ETLClean:
    """Orquestador ETL LIMPIO que usa SOLO los cornerstones."""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.db = Database(config_path)
        
        # Rutas de cornerstones
        self.cornerstones_dir = Path(__file__).parent.parent / "cornerstones"
        self.data_dir = Path(self.config['paths']['data_raw'])
        
    def ejecutar(self, fuente: str = 'all', solo_procesamiento: bool = False) -> Dict:
        """
        Ejecutar ETL LIMPIO: scraping con cornerstones + procesamiento + carga.
        """
        logger.info(f"🚀 INICIANDO ETL LIMPIO para: {fuente}")
        if solo_procesamiento:
            logger.info("😫 MODO SOLO PROCESAMIENTO - Omitiendo scrapers")
        
        resultados = {
            'inicio': datetime.now(),
            'fuentes': {},
            'totales': {'extraidos': 0, 'insertados': 0, 'errores': 0, 'duplicados': 0}
        }
        
        # 1. FASE DE SCRAPING CON CORNERSTONES
        if not solo_procesamiento:
            if fuente == 'all':
                self._ejecutar_todos_cornerstones(resultados)
            else:
                self._ejecutar_cornerstone(fuente, resultados)
        
        # 2. FASE DE PROCESAMIENTO
        self._procesar_archivos_cornerstones(fuente, resultados)
        
        resultados['fin'] = datetime.now()
        resultados['duracion'] = str(resultados['fin'] - resultados['inicio'])
        
        logger.info(f"✅ ETL LIMPIO terminado: {resultados['totales']}")
        return resultados
    
    def _ejecutar_todos_cornerstones(self, resultados: Dict):
        """Ejecutar todos los cornerstones disponibles."""
        cornerstones = ['dof', 'comprasmx']
        
        for cornerstone in cornerstones:
            if self._cornerstone_habilitado(cornerstone):
                logger.info(f"🎯 Ejecutando cornerstone: {cornerstone}")
                self._ejecutar_cornerstone(cornerstone, resultados)
    
    def _cornerstone_habilitado(self, cornerstone: str) -> bool:
        """Verificar si un cornerstone está habilitado."""
        config_map = {
            'comprasmx': self.config['sources']['comprasmx']['enabled'],
            'dof': self.config['sources']['dof']['enabled']
        }
        return config_map.get(cornerstone, False)
    
    def _ejecutar_cornerstone(self, fuente: str, resultados: Dict):
        """Ejecutar un cornerstone específico."""
        logger.info(f"🔥 Ejecutando CORNERSTONE: {fuente}")
        
        resultado_scraping = {
            'scraping_exitoso': False,
            'archivos_generados': 0,
            'error_scraping': None
        }
        
        try:
            if fuente == 'comprasmx':
                self._ejecutar_comprasmx_cornerstone(resultado_scraping)
            elif fuente == 'dof':
                self._ejecutar_dof_cornerstone(resultado_scraping)
                
        except Exception as e:
            logger.error(f"Error ejecutando cornerstone {fuente}: {e}")
            resultado_scraping['error_scraping'] = str(e)
        
        resultados['fuentes'][f'{fuente}_cornerstone'] = resultado_scraping
    
    def _ejecutar_dof_cornerstone(self, resultado: Dict):
        """
        Ejecutar cornerstone DOF con Claude Haiku.
        """
        logger.info("🤖 Ejecutando cornerstone DOF con Claude Haiku...")
        
        # Verificar API key
        if not os.getenv('ANTHROPIC_API_KEY'):
            logger.error("❌ ANTHROPIC_API_KEY no configurada en .env")
            resultado['error_scraping'] = "API key no configurada"
            return
        
        # Ejecutar cornerstone DOF
        cornerstone_path = self.cornerstones_dir / "dof" / "dof_haiku_extractor.py"
        
        if cornerstone_path.exists():
            logger.info("📚 Procesando DOF con cornerstone Claude Haiku...")
            
            process = subprocess.run([
                sys.executable, str(cornerstone_path)
            ], capture_output=True, text=True, env={**os.environ}, cwd=str(cornerstone_path.parent))
            
            if process.returncode == 0:
                resultado['scraping_exitoso'] = True
                logger.info("✅ Cornerstone DOF completado")
                
                # Contar archivos generados
                processed_dir = Path("data/processed/dof")
                if processed_dir.exists():
                    json_files = list(processed_dir.glob("*haiku*.json"))
                    resultado['archivos_generados'] = len(json_files)
                    logger.info(f"📁 JSONs generados con cornerstone: {len(json_files)}")
            else:
                logger.error(f"❌ Error en cornerstone DOF: {process.stderr}")
                resultado['error_scraping'] = process.stderr
        else:
            logger.error(f"Cornerstone DOF no encontrado: {cornerstone_path}")
            resultado['error_scraping'] = "Cornerstone no encontrado"
    
    def _ejecutar_comprasmx_cornerstone(self, resultado: Dict):
        """Ejecutar cornerstone ComprasMX."""
        cornerstone_path = self.cornerstones_dir / "comprasmx" / "comprasmx_scraper_consolidado.py"
        
        if cornerstone_path.exists():
            logger.info("🕷️ Ejecutando cornerstone ComprasMX...")
            
            process = subprocess.run([
                sys.executable, str(cornerstone_path)
            ], capture_output=True, text=True, cwd=str(cornerstone_path.parent))
            
            if process.returncode == 0:
                resultado['scraping_exitoso'] = True
                logger.info("✅ Cornerstone ComprasMX ejecutado")
                
                # Buscar archivos generados en el directorio actual
                json_files = list(cornerstone_path.parent.glob("comprasmx_funcional_*.json"))
                resultado['archivos_generados'] = len(json_files)
                logger.info(f"📁 Archivos JSON generados: {len(json_files)}")
            else:
                logger.error(f"❌ Error en cornerstone ComprasMX: {process.stderr}")
                resultado['error_scraping'] = process.stderr
        else:
            logger.error(f"Cornerstone ComprasMX no encontrado: {cornerstone_path}")
            resultado['error_scraping'] = "Cornerstone no encontrado"
    
    def _procesar_archivos_cornerstones(self, fuente: str, resultados: Dict):
        """Procesar archivos generados por cornerstones e insertar en BD."""
        logger.info("📁 Procesando archivos de cornerstones e insertando en BD...")
        
        # Procesar archivos de cada cornerstone
        if fuente in ['all', 'dof']:
            self._procesar_dof_cornerstone_files(resultados)
        
        if fuente in ['all', 'comprasmx']:
            self._procesar_comprasmx_cornerstone_files(resultados)
    
    def _procesar_dof_cornerstone_files(self, resultados: Dict):
        """Procesar archivos JSON generados por el cornerstone DOF."""
        logger.info("📚 Procesando archivos DOF generados por cornerstone...")
        
        processed_dir = Path("data/processed/dof")
        if not processed_dir.exists():
            logger.warning("No existe directorio de procesados DOF")
            return
        
        # Buscar archivos del cornerstone (con 'haiku' en el nombre)
        json_files = list(processed_dir.glob("*haiku*.json"))
        
        if not json_files:
            logger.warning("No se encontraron archivos del cornerstone DOF")
            return
        
        resultado_dof = {
            'extraidos': 0,
            'insertados': 0,
            'errores': 0,
            'duplicados': 0
        }
        
        # Procesar el archivo más reciente (consolidado si existe)
        archivo_mas_reciente = max(json_files, key=lambda x: x.stat().st_mtime)
        
        try:
            with open(archivo_mas_reciente, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            licitaciones = data.get('licitaciones', [])
            resultado_dof['extraidos'] = len(licitaciones)
            
            for lic in licitaciones:
                try:
                    # Normalizar datos para el modelo híbrido
                    lic_normalizada = self._normalizar_dof_cornerstone(lic)
                    
                    if self.db.insertar_licitacion(lic_normalizada):
                        resultado_dof['insertados'] += 1
                    else:
                        resultado_dof['duplicados'] += 1
                except Exception as e:
                    logger.error(f"Error insertando licitación DOF cornerstone: {e}")
                    resultado_dof['errores'] += 1
            
        except Exception as e:
            logger.error(f"Error procesando {archivo_mas_reciente}: {e}")
            resultado_dof['errores'] += 1
        
        logger.info(f"   💾 DOF cornerstone: {resultado_dof['insertados']} insertadas de {resultado_dof['extraidos']}")
        
        resultados['fuentes']['dof_cornerstone_procesamiento'] = resultado_dof
        resultados['totales']['extraidos'] += resultado_dof['extraidos']
        resultados['totales']['insertados'] += resultado_dof['insertados']
        resultados['totales']['errores'] += resultado_dof['errores']
        resultados['totales']['duplicados'] += resultado_dof['duplicados']
    
    def _procesar_comprasmx_cornerstone_files(self, resultados: Dict):
        """Procesar archivos JSON generados por el cornerstone ComprasMX."""
        logger.info("🕷️ Procesando archivos ComprasMX generados por cornerstone...")
        
        cornerstone_dir = self.cornerstones_dir / "comprasmx"
        
        # Buscar archivos del cornerstone
        json_files = list(cornerstone_dir.glob("comprasmx_funcional_*.json"))
        
        if not json_files:
            logger.warning("No se encontraron archivos del cornerstone ComprasMX")
            return
        
        resultado_comprasmx = {
            'extraidos': 0,
            'insertados': 0,
            'errores': 0,
            'duplicados': 0
        }
        
        # Procesar el archivo más reciente
        archivo_mas_reciente = max(json_files, key=lambda x: x.stat().st_mtime)
        
        try:
            with open(archivo_mas_reciente, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            licitaciones = data.get('licitaciones', [])
            resultado_comprasmx['extraidos'] = len(licitaciones)
            
            for lic in licitaciones:
                try:
                    # Normalizar datos para el modelo híbrido
                    lic_normalizada = self._normalizar_comprasmx_cornerstone(lic)
                    
                    if self.db.insertar_licitacion(lic_normalizada):
                        resultado_comprasmx['insertados'] += 1
                    else:
                        resultado_comprasmx['duplicados'] += 1
                except Exception as e:
                    logger.error(f"Error insertando licitación ComprasMX cornerstone: {e}")
                    resultado_comprasmx['errores'] += 1
            
        except Exception as e:
            logger.error(f"Error procesando {archivo_mas_reciente}: {e}")
            resultado_comprasmx['errores'] += 1
        
        logger.info(f"   💾 ComprasMX cornerstone: {resultado_comprasmx['insertados']} insertadas de {resultado_comprasmx['extraidos']}")
        
        resultados['fuentes']['comprasmx_cornerstone_procesamiento'] = resultado_comprasmx
        resultados['totales']['extraidos'] += resultado_comprasmx['extraidos']
        resultados['totales']['insertados'] += resultado_comprasmx['insertados']
        resultados['totales']['errores'] += resultado_comprasmx['errores']
        resultados['totales']['duplicados'] += resultado_comprasmx['duplicados']
    
    def _normalizar_dof_cornerstone(self, lic: Dict) -> Dict:
        """Normalizar licitación del cornerstone DOF para el modelo híbrido."""
        return {
            'numero_procedimiento': lic.get('numero_identificacion') or lic.get('numero_procedimiento_contratacion'),
            'titulo': lic.get('titulo_basico') or 'Sin título',
            'descripcion': lic.get('descripcion_detallada'),
            'entidad_compradora': lic.get('dependencia_entidad'),
            'unidad_compradora': lic.get('unidad_compradora'),
            'tipo_procedimiento': lic.get('tipo_procedimiento_contratacion'),
            'estado': 'Publicada',
            'fecha_publicacion': lic.get('fecha_publicacion'),
            'fecha_apertura': lic.get('fecha_apertura_proposiciones'),
            'fecha_junta_aclaraciones': lic.get('fecha_junta_aclaraciones'),
            'uuid_procedimiento': lic.get('uuid'),
            'fuente': 'DOF',
            'url_original': lic.get('url_detalle'),
            'datos_originales': lic.get('datos_originales'),
            'entidad_federativa': lic.get('entidad_federativa_contratacion'),
            'datos_especificos': {
                'procesado_haiku': lic.get('procesado_haiku', True),
                'modelo_ia': 'claude-3-5-haiku-20241022',
                'fecha_procesamiento': datetime.now().isoformat(),
                'cornerstone_dof': True
            }
        }
    
    def _normalizar_comprasmx_cornerstone(self, lic: Dict) -> Dict:
        """Normalizar licitación del cornerstone ComprasMX para el modelo híbrido."""
        return {
            'numero_procedimiento': lic.get('numero_identificacion'),
            'titulo': lic.get('titulo_basico') or 'Sin título',
            'descripcion': lic.get('descripcion_detallada'),
            'entidad_compradora': lic.get('dependencia') or lic.get('dependencia_entidad'),
            'unidad_compradora': lic.get('unidad_compradora'),
            'tipo_procedimiento': lic.get('tipo_procedimiento_contratacion'),
            'caracter': lic.get('caracter'),
            'estado': lic.get('estatus', 'Publicada'),
            'fecha_publicacion': lic.get('fecha_publicacion'),
            'fecha_apertura': lic.get('fecha_apertura_proposiciones'),
            'fecha_junta_aclaraciones': lic.get('fecha_junta_aclaraciones'),
            'uuid_procedimiento': lic.get('uuid'),
            'fuente': 'ComprasMX',
            'url_original': lic.get('url_detalle'),
            'entidad_federativa': lic.get('entidad_federativa_contratacion'),
            'datos_especificos': {
                'procesado_haiku': lic.get('procesado_haiku', False),
                'fecha_procesamiento': datetime.now().isoformat(),
                'cornerstone_comprasmx': True
            }
        }

def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='ETL LIMPIO Paloma Licitera con cornerstones')
    parser.add_argument(
        '--fuente',
        choices=['all', 'comprasmx', 'dof'],
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
        help='Solo procesar archivos existentes, sin ejecutar cornerstones'
    )
    
    args = parser.parse_args()
    
    # Verificar API key para DOF
    if args.fuente in ['all', 'dof']:
        if not os.getenv('ANTHROPIC_API_KEY'):
            print("⚠️ ADVERTENCIA: ANTHROPIC_API_KEY no configurada")
            print("   El cornerstone DOF requiere API key de Anthropic")
            print("   Configura tu API key en .env")
    
    etl = ETLClean()
    
    if args.setup:
        etl.db.setup()
        print("✅ Base de datos configurada")
    else:
        resultados = etl.ejecutar(
            args.fuente, 
            solo_procesamiento=args.solo_procesamiento
        )
        
        print(f"""
🎯 ETL LIMPIO Completado
═════════════════════
📊 Extraídos: {resultados['totales']['extraidos']}
💾 Insertados: {resultados['totales']['insertados']}
🔄 Duplicados: {resultados['totales']['duplicados']}
❌ Errores: {resultados['totales']['errores']}
⏱️ Duración: {resultados['duracion']}
        """)
        
        # Mostrar desglose por cornerstone
        for fuente_key, stats in resultados['fuentes'].items():
            if '_cornerstone_procesamiento' in fuente_key:
                fuente_name = fuente_key.replace('_cornerstone_procesamiento', '').upper()
                print(f"📋 CORNERSTONE {fuente_name}:")
                print(f"    Extraídas: {stats['extraidos']}")
                print(f"    Insertadas: {stats['insertados']}")
                print(f"    Duplicadas: {stats.get('duplicados', 0)}")
                print(f"    Errores: {stats['errores']}")

if __name__ == "__main__":
    main()
