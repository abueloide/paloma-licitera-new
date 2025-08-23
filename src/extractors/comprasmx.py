#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor de ComprasMX - Portal de Compras del Gobierno Federal
Versión simplificada sin Playwright (usando archivos JSON descargados)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class ComprasMXExtractor(BaseExtractor):
    """Extractor para ComprasMX."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.data_dir = Path(config['paths']['data_raw']) / 'comprasmx'
        
    def extraer(self) -> List[Dict[str, Any]]:
        """Extraer licitaciones de archivos JSON de ComprasMX."""
        licitaciones = []
        
        # Buscar archivos JSON
        json_files = list(self.data_dir.glob("*.json"))
        logger.info(f"Encontrados {len(json_files)} archivos JSON en {self.data_dir}")
        
        for json_file in json_files:
            try:
                licitaciones.extend(self._procesar_json(json_file))
            except Exception as e:
                logger.error(f"Error procesando {json_file}: {e}")
                
        return licitaciones
    
    def _procesar_json(self, json_path: Path) -> List[Dict[str, Any]]:
        """Procesar un archivo JSON de ComprasMX."""
        logger.info(f"Procesando: {json_path.name}")
        licitaciones = []
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # El formato puede variar, intentar diferentes estructuras
        registros = []
        
        # Formato 1: Lista directa
        if isinstance(data, list):
            registros = data
            
        # Formato 2: Objeto con campo 'data'
        elif isinstance(data, dict):
            if 'data' in data:
                if isinstance(data['data'], list):
                    # Si data es lista, puede tener registros directos
                    if len(data['data']) > 0:
                        if 'registros' in data['data'][0]:
                            registros = data['data'][0]['registros']
                        else:
                            registros = data['data']
                            
            # Formato 3: Objeto con campo 'registros'
            elif 'registros' in data:
                registros = data['registros']
                
            # Formato 4: Objeto con campo 'licitaciones'
            elif 'licitaciones' in data:
                registros = data['licitaciones']
        
        # Procesar registros
        for registro in registros:
            licitacion = self._parsear_registro(registro)
            if licitacion:
                licitaciones.append(licitacion)
                
        logger.info(f"Extraídas {len(licitaciones)} licitaciones de {json_path.name}")
        return licitaciones
    
    def _parsear_registro(self, registro: Dict) -> Dict[str, Any]:
        """Parsear un registro de ComprasMX."""
        try:
            # Validar campos mínimos
            numero = registro.get('numero_procedimiento', '')
            if not numero:
                return None
            
            # Normalizar tipo de procedimiento
            tipo_proc_original = registro.get('tipo_procedimiento', '')
            tipo_proc = self._normalizar_tipo_procedimiento(tipo_proc_original)
            
            # Normalizar tipo de contratación
            tipo_cont_original = registro.get('tipo_contratacion', '')
            tipo_cont = self._normalizar_tipo_contratacion(tipo_cont_original)
            
            # Parsear fechas
            fecha_apertura = self._parsear_fecha(registro.get('fecha_apertura'))
            fecha_aclaraciones = self._parsear_fecha(registro.get('fecha_aclaraciones'))
            
            # Construir URL si existe UUID
            uuid = registro.get('uuid_procedimiento', '')
            url = f"https://comprasmx.buengobierno.gob.mx/procedimiento/{uuid}" if uuid else None
            
            # Crear licitación normalizada
            licitacion = self.normalizar_licitacion(registro)
            licitacion.update({
                'numero_procedimiento': numero,
                'titulo': registro.get('nombre_procedimiento', '')[:500],
                'entidad_compradora': registro.get('siglas', ''),
                'unidad_compradora': registro.get('unidad_compradora'),
                'tipo_procedimiento': tipo_proc,
                'tipo_contratacion': tipo_cont,
                'estado': registro.get('estatus_alterno', 'VIGENTE'),
                'fecha_publicacion': datetime.now().date(),  # ComprasMX no tiene fecha pub
                'fecha_apertura': fecha_apertura,
                'fecha_junta_aclaraciones': fecha_aclaraciones,
                'url_original': url
            })
            
            return licitacion
            
        except Exception as e:
            logger.debug(f"Error parseando registro: {e}")
            return None
    
    def _normalizar_tipo_procedimiento(self, tipo: str) -> str:
        """Normalizar tipo de procedimiento."""
        if not tipo:
            return 'LICITACION_PUBLICA'
            
        tipo_upper = tipo.upper()
        
        if 'LICITACIÓN PÚBLICA' in tipo_upper or 'LICITACION PUBLICA' in tipo_upper:
            return 'LICITACION_PUBLICA'
        elif 'INVITACIÓN' in tipo_upper or 'INVITACION' in tipo_upper:
            return 'INVITACION_3'
        elif 'ADJUDICACIÓN' in tipo_upper or 'ADJUDICACION' in tipo_upper:
            return 'ADJUDICACION_DIRECTA'
        else:
            return 'LICITACION_PUBLICA'
    
    def _normalizar_tipo_contratacion(self, tipo: str) -> str:
        """Normalizar tipo de contratación."""
        if not tipo:
            return 'ADQUISICIONES'
            
        tipo_upper = tipo.upper()
        
        if 'SERVICIO' in tipo_upper:
            return 'SERVICIOS'
        elif 'OBRA' in tipo_upper:
            return 'OBRA_PUBLICA'
        else:
            return 'ADQUISICIONES'
    
    def _parsear_fecha(self, fecha_str: str) -> datetime:
        """Parsear fecha desde diferentes formatos."""
        if not fecha_str:
            return None
            
        try:
            # Formato ISO con hora
            if 'T' in fecha_str:
                return datetime.fromisoformat(fecha_str.replace('Z', '+00:00')).date()
                
            # Formato DD/MM/YYYY, HH:MM horas
            if 'horas' in fecha_str:
                fecha_parte = fecha_str.split(',')[0].strip()
                return datetime.strptime(fecha_parte, '%d/%m/%Y').date()
                
            # Formato YYYY-MM-DD
            if '-' in fecha_str and len(fecha_str.split('-')[0]) == 4:
                return datetime.strptime(fecha_str.split(' ')[0], '%Y-%m-%d').date()
                
            # Formato DD/MM/YYYY
            if '/' in fecha_str:
                return datetime.strptime(fecha_str.split(' ')[0], '%d/%m/%Y').date()
                
        except Exception as e:
            logger.debug(f"Error parseando fecha '{fecha_str}': {e}")
            
        return None
