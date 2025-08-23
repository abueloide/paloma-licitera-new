#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor del DOF - Diario Oficial de la Federación
Versión simplificada (procesa JSONs ya extraídos de PDFs)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import re

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class DOFExtractor(BaseExtractor):
    """Extractor para el Diario Oficial de la Federación."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.data_dir = Path(config['paths']['data_raw']) / 'dof'
        
    def extraer(self) -> List[Dict[str, Any]]:
        """Extraer licitaciones de archivos JSON del DOF."""
        licitaciones = []
        
        # Buscar archivos JSON de licitaciones
        json_files = list(self.data_dir.glob("*licitaciones.json"))
        logger.info(f"Encontrados {len(json_files)} archivos JSON en {self.data_dir}")
        
        for json_file in json_files:
            try:
                licitaciones.extend(self._procesar_json(json_file))
            except Exception as e:
                logger.error(f"Error procesando {json_file}: {e}")
                
        return licitaciones
    
    def _procesar_json(self, json_path: Path) -> List[Dict[str, Any]]:
        """Procesar un archivo JSON del DOF."""
        logger.info(f"Procesando: {json_path.name}")
        licitaciones = []
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # El formato puede variar
        if isinstance(data, list):
            registros = data
        elif isinstance(data, dict):
            registros = data.get('licitaciones', data.get('data', []))
        else:
            registros = []
        
        for registro in registros:
            licitacion = self._parsear_registro_dof(registro)
            if licitacion:
                licitaciones.append(licitacion)
                
        logger.info(f"Extraídas {len(licitaciones)} licitaciones de {json_path.name}")
        return licitaciones
    
    def _parsear_registro_dof(self, registro: Dict) -> Dict[str, Any]:
        """Parsear un registro del DOF."""
        try:
            # Campos principales
            numero = registro.get('numero_licitacion', '')
            if not numero:
                return None
            
            # Objeto de licitación (puede ser muy largo)
            objeto = registro.get('objeto_licitacion', '')
            titulo = objeto[:500] if objeto else ''
            descripcion = objeto if len(objeto) > 500 else None
            
            # Entidades
            entidad = registro.get('dependencia', '')
            if not entidad:
                return None
                
            unidad = registro.get('subdependencia')
            
            # Inferir tipo de procedimiento del número
            tipo_proc = self._inferir_tipo_procedimiento(numero)
            
            # Caracter de la licitación
            caracter_original = registro.get('caracter_licitacion', '')
            caracter = self._normalizar_caracter(caracter_original)
            
            # Fechas
            fecha_pub = self._parsear_fecha_dof(registro.get('fecha_publicacion'))
            fecha_aclaraciones = self._parsear_fecha_dof(registro.get('fecha_junta_aclaraciones'))
            fecha_apertura = self._parsear_fecha_dof(registro.get('fecha_presentacion_apertura'))
            fecha_fallo = self._parsear_fecha_dof(registro.get('fecha_fallo'))
            
            # Tipo de contratación (DOF no lo especifica, detectar por texto)
            tipo_cont = self.detectar_tipo_contratacion(objeto)
            
            # Crear licitación normalizada
            licitacion = self.normalizar_licitacion(registro)
            licitacion.update({
                'numero_procedimiento': numero,
                'titulo': titulo,
                'descripcion': descripcion,
                'entidad_compradora': entidad,
                'unidad_compradora': unidad,
                'tipo_procedimiento': tipo_proc,
                'tipo_contratacion': tipo_cont,
                'estado': 'VIGENTE',  # DOF siempre publica vigentes
                'fecha_publicacion': fecha_pub or datetime.now().date(),
                'fecha_junta_aclaraciones': fecha_aclaraciones,
                'fecha_apertura': fecha_apertura,
                'fecha_fallo': fecha_fallo
            })
            
            # Agregar caracter si no es estándar
            if caracter and caracter != 'NACIONAL':
                licitacion['caracter'] = caracter
            
            return licitacion
            
        except Exception as e:
            logger.debug(f"Error parseando registro DOF: {e}")
            return None
    
    def _inferir_tipo_procedimiento(self, numero: str) -> str:
        """Inferir tipo de procedimiento del número de licitación."""
        if not numero:
            return 'LICITACION_PUBLICA'
        
        numero_upper = numero.upper()
        
        # Patrones comunes en números de licitación
        if numero_upper.startswith('LA-') or 'LICITACI' in numero_upper:
            return 'LICITACION_PUBLICA'
        elif numero_upper.startswith('IA-') or numero_upper.startswith('I3P-'):
            return 'INVITACION_3'
        elif numero_upper.startswith('AD-') or 'ADJUDICACI' in numero_upper:
            return 'ADJUDICACION_DIRECTA'
        
        # Por defecto
        return 'LICITACION_PUBLICA'
    
    def _normalizar_caracter(self, caracter: str) -> str:
        """Normalizar caracter de licitación."""
        if not caracter:
            return 'NACIONAL'
        
        caracter_upper = caracter.upper()
        
        if 'INTERNACIONAL' in caracter_upper:
            return 'INTERNACIONAL'
        else:
            return 'NACIONAL'
    
    def _parsear_fecha_dof(self, fecha_str: str) -> datetime:
        """Parsear fecha en formato del DOF."""
        if not fecha_str:
            return None
        
        try:
            # Limpiar la fecha
            fecha_str = fecha_str.strip()
            
            # Formato: "DD/MM/YYYY, HH:MM horas"
            if ',' in fecha_str:
                fecha_parte = fecha_str.split(',')[0].strip()
                return datetime.strptime(fecha_parte, '%d/%m/%Y').date()
            
            # Formato: "DD de MES de YYYY"
            if ' de ' in fecha_str:
                # Mapeo de meses en español
                meses = {
                    'enero': '01', 'febrero': '02', 'marzo': '03',
                    'abril': '04', 'mayo': '05', 'junio': '06',
                    'julio': '07', 'agosto': '08', 'septiembre': '09',
                    'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                }
                
                partes = fecha_str.lower().split(' de ')
                if len(partes) == 3:
                    dia = partes[0].strip()
                    mes = meses.get(partes[1].strip(), '01')
                    año = partes[2].strip()
                    
                    fecha_formateada = f"{dia.zfill(2)}/{mes}/{año}"
                    return datetime.strptime(fecha_formateada, '%d/%m/%Y').date()
            
            # Formato ISO
            if '-' in fecha_str:
                return datetime.strptime(fecha_str.split(' ')[0], '%Y-%m-%d').date()
            
            # Formato DD/MM/YYYY simple
            if '/' in fecha_str:
                return datetime.strptime(fecha_str, '%d/%m/%Y').date()
                
        except Exception as e:
            logger.debug(f"Error parseando fecha DOF '{fecha_str}': {e}")
            
        return None
