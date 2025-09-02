#!/usr/bin/env python3
"""
Tianguis Digital Extractor - Cornerstone
Extractor de licitaciones del Tianguis Digital CDMX
"""

import os
import sys
import logging
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TianguisExtractor:
    """Extractor de licitaciones del Tianguis Digital CDMX"""
    
    def __init__(self):
        self.base_url = "https://tianguis.cdmx.gob.mx"
        self.api_url = f"{self.base_url}/api/licitaciones"
        self.data_dir = Path("data/raw/tianguis")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def fetch_licitaciones(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Obtiene licitaciones de una página específica"""
        try:
            params = {
                'page': page,
                'per_page': per_page,
                'status': 'active'
            }
            
            logger.info(f"Obteniendo página {page} del Tianguis Digital...")
            
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo página {page}: {e}")
            return {}
            
    def process_licitacion(self, licitacion: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa una licitación individual"""
        processed = {
            'numero_procedimiento': licitacion.get('numero_procedimiento', ''),
            'titulo': licitacion.get('titulo', licitacion.get('nombre', '')),
            'descripcion': licitacion.get('descripcion', licitacion.get('objeto', '')),
            'entidad_compradora': licitacion.get('unidad_compradora', 'CDMX'),
            'unidad_compradora': licitacion.get('unidad_compradora', ''),
            'tipo_procedimiento': licitacion.get('tipo_procedimiento', 'Licitación Pública'),
            'tipo_contratacion': licitacion.get('tipo_contratacion', ''),
            'estado': licitacion.get('estatus', licitacion.get('status', '')),
            'caracter': licitacion.get('caracter', ''),
            'monto_estimado': self._parse_monto(licitacion.get('monto_estimado', 0)),
            'moneda': 'MXN',
            'entidad_federativa': 'Ciudad de México',
            'municipio': 'Ciudad de México',
            'fuente': 'tianguis',
            'url_original': f"{self.base_url}/licitacion/{licitacion.get('id', '')}",
            'datos_originales': licitacion
        }
        
        # Procesar fechas
        processed.update(self._process_dates(licitacion))
        
        return processed
        
    def _parse_monto(self, monto) -> float:
        """Convierte monto a float"""
        try:
            if isinstance(monto, str):
                # Remover caracteres no numéricos excepto puntos
                monto = ''.join(c for c in monto if c.isdigit() or c == '.')
            return float(monto) if monto else 0.0
        except:
            return 0.0
            
    def _process_dates(self, licitacion: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa las fechas de una licitación"""
        date_fields = {
            'fecha_publicacion': ['fecha_publicacion', 'published_at', 'created_at'],
            'fecha_apertura': ['fecha_apertura', 'fecha_apertura_proposiciones'],
            'fecha_fallo': ['fecha_fallo', 'fecha_fallo_tecnico'],
            'fecha_junta_aclaraciones': ['fecha_junta_aclaraciones']
        }
        
        processed_dates = {}
        
        for field, possible_keys in date_fields.items():
            for key in possible_keys:
                if key in licitacion and licitacion[key]:
                    processed_dates[field] = self._parse_date(licitacion[key])
                    break
                    
        return processed_dates
        
    def _parse_date(self, date_str: str) -> str:
        """Convierte fecha a formato YYYY-MM-DD"""
        if not date_str:
            return None
            
        try:
            # Intentar varios formatos
            formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%d/%m/%Y',
                '%d-%m-%Y'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str[:len(fmt)], fmt)
                    return dt.strftime('%Y-%m-%d')
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"No se pudo parsear fecha: {date_str}")
            
        return None
        
    def run_extraction(self, max_pages: int = 50):
        """Ejecuta la extracción completa"""
        logger.info(f"🚀 Iniciando extracción Tianguis Digital (máximo {max_pages} páginas)")
        
        all_licitaciones = []
        page = 1
        
        while page <= max_pages:
            data = self.fetch_licitaciones(page)
            
            if not data or 'data' not in data:
                logger.warning(f"No hay más datos en página {page}")
                break
                
            licitaciones = data.get('data', [])
            
            if not licitaciones:
                logger.info(f"Página {page} vacía, terminando")
                break
                
            # Procesar licitaciones
            for licitacion in licitaciones:
                processed = self.process_licitacion(licitacion)
                all_licitaciones.append(processed)
                
            logger.info(f"📄 Página {page}: {len(licitaciones)} licitaciones")
            
            # Verificar si hay más páginas
            if data.get('current_page', page) >= data.get('last_page', page):
                logger.info(f"Última página alcanzada: {page}")
                break
                
            page += 1
            time.sleep(1)  # Rate limiting
            
        # Guardar resultados
        if all_licitaciones:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tianguis_{timestamp}.json"
            filepath = self.data_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(all_licitaciones, f, ensure_ascii=False, indent=2, default=str)
                
            logger.info(f"✅ Guardadas {len(all_licitaciones)} licitaciones en {filename}")
            
        logger.info(f"🎯 Extracción completada: {len(all_licitaciones)} licitaciones totales")
        return len(all_licitaciones)

def main():
    """Función principal"""
    extractor = TianguisExtractor()
    
    # Permitir parámetros de línea de comandos
    max_pages = 50
    
    if len(sys.argv) > 1:
        max_pages = int(sys.argv[1])
        
    extractor.run_extraction(max_pages)

if __name__ == "__main__":
    main()
