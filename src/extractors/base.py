#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor Base - Clase abstracta para todos los extractores
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """Clase base para todos los extractores de licitaciones."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.fuente = self.__class__.__name__.replace('Extractor', '').upper()
        
    @abstractmethod
    def extraer(self) -> List[Dict[str, Any]]:
        """
        Extraer licitaciones de la fuente.
        
        Returns:
            Lista de diccionarios con los datos de licitaciones
        """
        pass
    
    def normalizar_licitacion(self, datos_crudos: Dict) -> Dict[str, Any]:
        """
        Normalizar datos crudos a formato estándar.
        
        Args:
            datos_crudos: Datos en formato original de la fuente
            
        Returns:
            Diccionario con formato estándar de licitación
        """
        return {
            'numero_procedimiento': '',
            'titulo': '',
            'descripcion': None,
            'entidad_compradora': '',
            'unidad_compradora': None,
            'tipo_procedimiento': None,
            'tipo_contratacion': None,
            'estado': 'VIGENTE',
            'fecha_publicacion': None,
            'fecha_apertura': None,
            'fecha_fallo': None,
            'monto_estimado': None,
            'moneda': 'MXN',
            'proveedor_ganador': None,
            'fuente': self.fuente,
            'url_original': None,
            'datos_originales': datos_crudos
        }
    
    def detectar_tipo_procedimiento(self, texto: str) -> str:
        """Detectar tipo de procedimiento desde texto."""
        texto_lower = texto.lower()
        
        if any(p in texto_lower for p in ['licitación pública', 'licitacion publica', 'art.30']):
            return 'LICITACION_PUBLICA'
        elif any(p in texto_lower for p in ['invitación', 'invitacion', 'art.54']):
            return 'INVITACION_3'
        else:
            return 'ADJUDICACION_DIRECTA'
    
    def detectar_tipo_contratacion(self, texto: str) -> str:
        """Detectar tipo de contratación desde texto."""
        texto_lower = texto.lower()
        
        if any(k in texto_lower for k in ['servicio', 'mantenimiento', 'consultoría']):
            return 'SERVICIOS'
        elif any(k in texto_lower for k in ['obra', 'construcción', 'infraestructura']):
            return 'OBRA_PUBLICA'
        else:
            return 'ADQUISICIONES'
