#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor de Sitios Masivos - Procesa archivos JSONL generados por scrapers
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import re

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class SitiosMasivosExtractor(BaseExtractor):
    """Extractor para archivos JSONL de sitios masivos."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.data_dir = Path(config['paths']['data_raw']) / 'sitios-masivos'
        
    def extraer(self) -> List[Dict[str, Any]]:
        """Extraer licitaciones de archivos JSONL de sitios masivos."""
        licitaciones = []
        
        # Buscar archivos JSONL
        jsonl_files = list(self.data_dir.glob("*.jsonl"))
        logger.info(f"Encontrados {len(jsonl_files)} archivos JSONL en {self.data_dir}")
        
        for jsonl_file in jsonl_files:
            try:
                licitaciones.extend(self._procesar_jsonl(jsonl_file))
            except Exception as e:
                logger.error(f"Error procesando {jsonl_file}: {e}")
                
        return licitaciones
    
    def _procesar_jsonl(self, jsonl_path: Path) -> List[Dict[str, Any]]:
        """Procesar un archivo JSONL de sitios masivos."""
        logger.info(f"Procesando: {jsonl_path.name}")
        licitaciones = []
        
        with open(jsonl_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    record = json.loads(line)
                    licitacion = self._parsear_registro_sitio_masivo(record)
                    if licitacion:
                        licitaciones.append(licitacion)
                except json.JSONDecodeError as e:
                    logger.debug(f"Error JSON en línea {line_num}: {e}")
                except Exception as e:
                    logger.debug(f"Error procesando línea {line_num}: {e}")
                    
        logger.info(f"Extraídas {len(licitaciones)} licitaciones de {jsonl_path.name}")
        return licitaciones
    
    def _parsear_registro_sitio_masivo(self, registro: Dict) -> Dict[str, Any]:
        """Parsear un registro de sitio masivo."""
        try:
            # Validar campos mínimos
            titulo = registro.get('Proyecto', '') or registro.get('titulo', '')
            organismo = registro.get('Organismo', '') or registro.get('organismo', '')
            
            if not titulo or not organismo:
                return None
            
            # Extraer número de procedimiento si existe
            numero = self._extraer_numero_procedimiento(titulo)
            
            # Detectar tipo de procedimiento y contratación
            tipo_proc = self.detectar_tipo_procedimiento(titulo)
            tipo_cont = self.detectar_tipo_contratacion(titulo)
            
            # Parsear monto
            monto_str = registro.get('Monto', '') or registro.get('monto', '')
            monto = self._parsear_monto(monto_str)
            
            # URL original
            url = registro.get('Vínculo', '') or registro.get('url', '') or registro.get('vinculo', '')
            
            # Localidad/jurisdicción
            localidad = registro.get('localidad', '') or registro.get('jurisdiccion', '')
            
            # Crear licitación normalizada
            licitacion = self.normalizar_licitacion(registro)
            licitacion.update({
                'numero_procedimiento': numero or f"SM-{hash(titulo) % 100000:05d}",
                'titulo': titulo[:500],
                'descripcion': registro.get('descripcion'),
                'entidad_compradora': organismo,
                'unidad_compradora': localidad if localidad != organismo else None,
                'tipo_procedimiento': tipo_proc,
                'tipo_contratacion': tipo_cont,
                'estado': 'VIGENTE',
                'fecha_publicacion': datetime.now().date(),
                'monto_estimado': monto,
                'url_original': url if url and url.startswith('http') else None,
                'fuente': 'SITIOS_MASIVOS'
            })
            
            return licitacion
            
        except Exception as e:
            logger.debug(f"Error parseando registro de sitio masivo: {e}")
            return None
    
    def _extraer_numero_procedimiento(self, texto: str) -> str:
        """Extraer número de procedimiento del texto."""
        # Patrones comunes de números de licitación
        patrones = [
            r'\b(?:LP|LA|IA|AD|SPFA|LPN|LPE|LPI|ADQ)[A-Z0-9/\-\._]*\b',
            r'\b\d{3,}/\d{4}\b',
            r'\b[A-Z]{2,}-\d{3,}\b',
            r'\bNo\.\s*([A-Z0-9/\-\.]+)\b'
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _parsear_monto(self, monto_str: str) -> float:
        """Parsear monto desde string."""
        if not monto_str:
            return None
            
        try:
            # Limpiar el string
            monto_limpio = re.sub(r'[^\d.,]', '', str(monto_str))
            if not monto_limpio:
                return None
            
            # Reemplazar comas por puntos para decimales
            if ',' in monto_limpio and '.' in monto_limpio:
                # Si tiene ambos, asumir que la coma es separador de miles
                monto_limpio = monto_limpio.replace(',', '')
            elif ',' in monto_limpio:
                # Solo comas, pueden ser decimales o miles
                parts = monto_limpio.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # Probablemente decimal
                    monto_limpio = monto_limpio.replace(',', '.')
                else:
                    # Probablemente separador de miles
                    monto_limpio = monto_limpio.replace(',', '')
            
            return float(monto_limpio)
            
        except (ValueError, TypeError):
            return None