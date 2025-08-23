#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestador ETL Principal - Paloma Licitera
"""

import logging
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import sys

# Agregar directorio de extractores al path
sys.path.insert(0, str(Path(__file__).parent))

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
        self.extractors = self._inicializar_extractores()
        self.zip_processor = ZipProcessor()
        
    def _inicializar_extractores(self) -> Dict[str, BaseExtractor]:
        """Inicializar extractores habilitados."""
        extractors = {}
        
        if self.config['sources']['comprasmx']['enabled']:
            extractors['comprasmx'] = ComprasMXExtractor(self.config)
            
        if self.config['sources']['dof']['enabled']:
            extractors['dof'] = DOFExtractor(self.config)
            
        if self.config['sources']['tianguis']['enabled']:
            extractors['tianguis'] = TianguisExtractor(self.config)
            
        return extractors
    
    def ejecutar(self, fuente: str = 'all') -> Dict:
        """
        Ejecutar ETL para una fuente o todas.
        
        Args:
            fuente: 'all', 'comprasmx', 'dof', 'tianguis', 'zip'
        """
        logger.info(f"Iniciando ETL para: {fuente}")
        resultados = {
            'inicio': datetime.now(),
            'fuentes': {},
            'totales': {'extraidos': 0, 'insertados': 0, 'errores': 0}
        }
        
        # Procesar archivos ZIP si se solicita
        if fuente in ['all', 'zip']:
            self._procesar_zips(resultados)
        
        # Procesar fuentes regulares
        fuentes_a_procesar = self.extractors.keys() if fuente == 'all' else [fuente]
        
        for nombre_fuente in fuentes_a_procesar:
            if nombre_fuente in self.extractors:
                resultado_fuente = self._procesar_fuente(nombre_fuente)
                resultados['fuentes'][nombre_fuente] = resultado_fuente
                resultados['totales']['extraidos'] += resultado_fuente['extraidos']
                resultados['totales']['insertados'] += resultado_fuente['insertados']
                resultados['totales']['errores'] += resultado_fuente['errores']
        
        resultados['fin'] = datetime.now()
        resultados['duracion'] = str(resultados['fin'] - resultados['inicio'])
        
        logger.info(f"ETL completado: {resultados['totales']}")
        return resultados
    
    def _procesar_fuente(self, nombre_fuente: str) -> Dict:
        """Procesar una fuente específica."""
        logger.info(f"Procesando fuente: {nombre_fuente}")
        extractor = self.extractors[nombre_fuente]
        
        resultado = {
            'extraidos': 0,
            'insertados': 0,
            'errores': 0
        }
        
        try:
            # Extraer datos
            licitaciones = extractor.extraer()
            resultado['extraidos'] = len(licitaciones)
            
            # Insertar en BD
            for licitacion in licitaciones:
                if self.db.insertar_licitacion(licitacion):
                    resultado['insertados'] += 1
                    
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
    
    args = parser.parse_args()
    
    etl = ETL()
    
    if args.setup:
        etl.db.setup()
        print("✅ Base de datos configurada")
    else:
        resultados = etl.ejecutar(args.fuente)
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
