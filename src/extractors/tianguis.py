#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor de Tianguis Digital (CDMX) - Formato OCDS
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import re

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class TianguisExtractor(BaseExtractor):
    """Extractor para Tianguis Digital con formato OCDS."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.data_dir = Path(config['paths']['data_raw']) / 'tianguis'
        
    def extraer(self) -> List[Dict[str, Any]]:
        """Extraer licitaciones de archivos CSV de Tianguis."""
        licitaciones = []
        
        # Buscar archivos CSV
        csv_files = list(self.data_dir.glob("*.csv"))
        logger.info(f"Encontrados {len(csv_files)} archivos CSV en {self.data_dir}")
        
        for csv_file in csv_files:
            try:
                licitaciones.extend(self._procesar_csv(csv_file))
            except Exception as e:
                logger.error(f"Error procesando {csv_file}: {e}")
                
        return licitaciones
    
    def _procesar_csv(self, csv_path: Path) -> List[Dict[str, Any]]:
        """Procesar un archivo CSV con formato OCDS."""
        logger.info(f"Procesando: {csv_path.name}")
        licitaciones = []
        
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                licitacion = self._parsear_fila_ocds(row)
                if licitacion:
                    licitaciones.append(licitacion)
                    
        logger.info(f"Extraídas {len(licitaciones)} licitaciones de {csv_path.name}")
        return licitaciones
    
    def _parsear_fila_ocds(self, row: Dict) -> Dict[str, Any]:
        """Parsear una fila CSV en formato OCDS."""
        try:
            # Campos principales con múltiples opciones
            numero = (self._extraer_campo_json(row, 'planning/budget/projectID') or
                     self._extraer_campo_json(row, 'tender/id') or
                     row.get('ocid', ''))
            
            if not numero:
                return None
            
            # Información básica
            titulo = (self._extraer_campo_json(row, 'tender/title') or
                     self._extraer_campo_json(row, 'planning/budget/description', ''))
            
            descripcion = self._extraer_campo_json(row, 'tender/description')
            
            # Entidades
            entidad = self._extraer_campo_json(row, 'buyer/name')
            if not entidad:
                return None
                
            # Fechas
            fecha_pub = self._parsear_fecha(row.get('date'))
            fecha_apertura = self._parsear_fecha(
                self._extraer_campo_json(row, 'tender/tenderPeriod/startDate')
            )
            
            # Montos
            monto = self._extraer_monto(
                self._extraer_campo_json(row, 'tender/value/amount') or
                self._extraer_campo_json(row, 'planning/budget/amount')
            )
            
            # Tipo de procedimiento
            proc_method = self._extraer_campo_json(row, 'tender/procurementMethod')
            tipo_proc = self._mapear_tipo_procedimiento(proc_method)
            
            # Si no hay método OCDS, intentar detectar por texto
            if not tipo_proc:
                tipo_proc = self.detectar_tipo_procedimiento(f"{numero} {titulo}")
            
            # Tipo de contratación
            categoria = self._extraer_campo_json(row, 'tender/mainProcurementCategory')
            tipo_cont = self._mapear_tipo_contratacion(categoria)
            
            # Si no hay categoría OCDS, detectar por texto
            if not tipo_cont:
                tipo_cont = self.detectar_tipo_contratacion(f"{titulo} {descripcion or ''}")
            
            # Crear licitación normalizada
            licitacion = self.normalizar_licitacion(row)
            licitacion.update({
                'numero_procedimiento': numero,
                'titulo': titulo[:500] if titulo else '',
                'descripcion': descripcion,
                'entidad_compradora': entidad,
                'tipo_procedimiento': tipo_proc,
                'tipo_contratacion': tipo_cont,
                'fecha_publicacion': fecha_pub or datetime.now().date(),
                'fecha_apertura': fecha_apertura,
                'monto_estimado': monto,
                'url_original': f"https://tianguisdigital.cdmx.gob.mx/ocds/tender/{row.get('ocid', '')}"
            })
            
            return licitacion
            
        except Exception as e:
            logger.debug(f"Error parseando fila: {e}")
            return None
    
    def _extraer_campo_json(self, row: Dict, campo: str, default=None) -> Any:
        """Extraer y parsear campo que puede contener JSON."""
        valor = row.get(campo, '')
        
        if not valor or valor == 'null':
            return default
            
        # Si es JSON, parsearlo
        if valor.startswith('[') or valor.startswith('{'):
            try:
                parsed = json.loads(valor)
                
                # Si es lista con un elemento, extraerlo
                if isinstance(parsed, list) and len(parsed) == 1:
                    parsed = parsed[0]
                    
                # Si es dict, buscar campos comunes
                if isinstance(parsed, dict):
                    for field in ['name', 'title', 'value', 'amount']:
                        if field in parsed:
                            return parsed[field]
                            
                return parsed
                
            except json.JSONDecodeError:
                pass
                
        return valor or default
    
    def _parsear_fecha(self, fecha_str: str) -> datetime:
        """Parsear fecha desde string."""
        if not fecha_str or fecha_str == "fecha de publicacion":
            return None
            
        try:
            # Formato ISO
            if 'T' in fecha_str:
                return datetime.fromisoformat(fecha_str.split('T')[0]).date()
            # Formato YYYY-MM-DD
            elif '-' in fecha_str and len(fecha_str.split('-')[0]) == 4:
                return datetime.strptime(fecha_str, '%Y-%m-%d').date()
            # Formato DD/MM/YYYY
            elif '/' in fecha_str:
                return datetime.strptime(fecha_str, '%d/%m/%Y').date()
        except:
            pass
            
        return None
    
    def _extraer_monto(self, valor: Any) -> float:
        """Extraer monto numérico."""
        if not valor:
            return None
            
        try:
            if isinstance(valor, (int, float)):
                return float(valor)
            elif isinstance(valor, str):
                # Limpiar y convertir
                valor_limpio = re.sub(r'[^\d.]', '', valor)
                if valor_limpio:
                    return float(valor_limpio)
        except:
            pass
            
        return None
    
    def _mapear_tipo_procedimiento(self, metodo: str) -> str:
        """Mapear método OCDS a tipo de procedimiento."""
        if not metodo:
            return None
            
        metodo_lower = metodo.lower()
        
        if metodo_lower == 'open':
            return 'LICITACION_PUBLICA'
        elif metodo_lower == 'selective':
            return 'INVITACION_3'
        elif metodo_lower == 'limited':
            return 'ADJUDICACION_DIRECTA'
            
        return None
    
    def _mapear_tipo_contratacion(self, categoria: str) -> str:
        """Mapear categoría OCDS a tipo de contratación."""
        if not categoria:
            return None
            
        categoria_lower = categoria.lower()
        
        if categoria_lower == 'goods':
            return 'ADQUISICIONES'
        elif categoria_lower == 'works':
            return 'OBRA_PUBLICA'
        elif categoria_lower == 'services':
            return 'SERVICIOS'
            
        return None
