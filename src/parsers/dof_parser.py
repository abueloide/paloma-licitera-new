#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser especializado para licitaciones del DOF
Extrae información estructurada del texto del DOF
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DOFParser:
    """Parser mejorado para textos del DOF."""
    
    def __init__(self):
        # Meses en español
        self.meses = {
            'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
            'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
            'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
        }
        
        # Mapeo de estados mexicanos
        self.estados_mexico = {
            'AGUASCALIENTES': 'Aguascalientes',
            'BAJA CALIFORNIA': 'Baja California',
            'BAJA CALIFORNIA SUR': 'Baja California Sur',
            'CAMPECHE': 'Campeche',
            'CHIAPAS': 'Chiapas',
            'CHIHUAHUA': 'Chihuahua',
            'CIUDAD DE MEXICO': 'Ciudad de México',
            'CDMX': 'Ciudad de México',
            'COAHUILA': 'Coahuila',
            'COLIMA': 'Colima',
            'DURANGO': 'Durango',
            'GUANAJUATO': 'Guanajuato',
            'GUERRERO': 'Guerrero',
            'HIDALGO': 'Hidalgo',
            'JALISCO': 'Jalisco',
            'MEXICO': 'Estado de México',
            'ESTADO DE MEXICO': 'Estado de México',
            'MICHOACAN': 'Michoacán',
            'MORELOS': 'Morelos',
            'NAYARIT': 'Nayarit',
            'NUEVO LEON': 'Nuevo León',
            'OAXACA': 'Oaxaca',
            'PUEBLA': 'Puebla',
            'QUERETARO': 'Querétaro',
            'QUINTANA ROO': 'Quintana Roo',
            'SAN LUIS POTOSI': 'San Luis Potosí',
            'SINALOA': 'Sinaloa',
            'SONORA': 'Sonora',
            'TABASCO': 'Tabasco',
            'TAMAULIPAS': 'Tamaulipas',
            'TLAXCALA': 'Tlaxcala',
            'VERACRUZ': 'Veracruz',
            'YUCATAN': 'Yucatán',
            'ZACATECAS': 'Zacatecas'
        }
        
        # Patrones mejorados para eventos
        self.evento_patterns = {
            'fecha_publicacion_compranet': [
                r'Fecha\s+de\s+publicación\s+en\s+Compranet\s+(\d{1,2}/\d{1,2}/\d{4})',
                r'Fecha\s+de\s+publicación\s+en\s+CompraNet\s+(\d{1,2}/\d{1,2}/\d{4})',
                r'Fecha\s+de\s+publicación\s+en\s+Compras?\s+MX\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
            ],
            'junta_aclaraciones': [
                r'Junta\s+de\s+aclaraciones\s+(\d{1,2}/\d{1,2}/\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?)',
                r'Junta\s+de\s+aclaraciones\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?)',
            ],
            'presentacion_apertura': [
                r'Presentación\s+y\s+apertura\s+de\s+proposiciones\s+(\d{1,2}/\d{1,2}/\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?)',
                r'Acto\s+de\s+presentación\s+y\s+apertura\s+de\s+proposiciones\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?)',
            ],
            'fallo': [
                r'Fallo\s+(\d{1,2}/\d{1,2}/\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?)',
                r'Emisión\s+del\s+Fallo\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
            ],
            'visita_sitio': [
                r'Visita\s+al\s+sitio\s+(?:de\s+los\s+trabajos?\s+)?(\d{1,2}/\d{1,2}/\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?|No\s+habrá\s+visita)',
            ]
        }
    
    def parse(self, licitacion_data: dict) -> dict:
        """
        Parser principal para una licitación del DOF.
        
        Args:
            licitacion_data: Diccionario con datos de la licitación
            
        Returns:
            Diccionario con datos parseados y estructurados
        """
        titulo = licitacion_data.get('titulo', '') or ''
        descripcion = licitacion_data.get('descripcion') or ''
        texto_completo = f"{titulo} {descripcion}"
        
        # Separar título de descripción si están concatenados
        titulo_limpio, descripcion_extraida = self._split_title_description(titulo)
        
        # Extraer todas las fechas
        fechas = self._extract_dates_from_text(texto_completo)
        
        # Extraer ubicación
        ubicacion = self._extract_location(texto_completo)
        
        # Extraer información técnica
        info_tecnica = self._extract_technical_info(texto_completo)
        
        # Determinar entidad federativa y municipio
        entidad_federativa, municipio = self._determinar_ubicacion_geografica(ubicacion, texto_completo)
        
        resultado = {
            'titulo_limpio': titulo_limpio or self._clean_title(titulo),
            'descripcion_completa': descripcion_extraida or descripcion,
            'fechas_parseadas': fechas,
            'ubicacion_extraida': ubicacion,
            'info_tecnica': info_tecnica,
            'entidad_federativa': entidad_federativa,
            'municipio': municipio,
            'procesado': True,
            'fecha_procesamiento': datetime.now().isoformat()
        }
        
        return resultado
    
    def _extract_dates_from_text(self, text: str) -> Dict[str, str]:
        """Extraer fechas específicas del texto."""
        fechas_encontradas = {}
        
        for evento, patterns in self.evento_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    fecha_texto = match.group(1)
                    if "No habrá" in fecha_texto:
                        fechas_encontradas[evento] = "No aplica"
                    else:
                        fecha_normalizada = self._normalize_date(fecha_texto)
                        if fecha_normalizada:
                            fechas_encontradas[evento] = fecha_normalizada
                            break
        
        return fechas_encontradas
    
    def _normalize_date(self, fecha_texto: str) -> Optional[str]:
        """Normalizar fecha a formato ISO."""
        fecha_texto = fecha_texto.strip()
        
        # Patrón 1: "20/08/2025, a las 10:00"
        match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})(?:,?\s*(?:a?\s*las?\s*)?(\d{1,2}):(\d{2}))?', fecha_texto)
        if match:
            dia = int(match.group(1))
            mes = int(match.group(2))
            año = int(match.group(3))
            hora = int(match.group(4)) if match.group(4) else 0
            minuto = int(match.group(5)) if match.group(5) else 0
            
            try:
                fecha = datetime(año, mes, dia, hora, minuto)
                return fecha.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        
        # Patrón 2: "12 de agosto de 2025"
        match = re.match(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})(?:,?\s*(?:a?\s*las?\s*)?(\d{1,2}):(\d{2}))?', fecha_texto, re.IGNORECASE)
        if match:
            dia = int(match.group(1))
            mes_texto = match.group(2).upper()
            año = int(match.group(3))
            hora = int(match.group(4)) if match.group(4) else 0
            minuto = int(match.group(5)) if match.group(5) else 0
            
            if mes_texto in self.meses:
                mes = self.meses[mes_texto]
                try:
                    fecha = datetime(año, mes, dia, hora, minuto)
                    return fecha.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
        
        return None
    
    def _extract_location(self, text: str) -> Dict[str, Optional[str]]:
        """Extraer información de ubicación."""
        location_info = {
            'localidad': None,
            'municipio': None,
            'estado': None,
            'ciudad': None,
            'direccion': None
        }
        
        # Buscar dirección completa
        direccion_pattern = r'(?:ubicad[oa]\s+en|sito\s+en|domicilio\s+en)\s+([^,.]+(?:,\s*[^,.]+)*)'
        match = re.search(direccion_pattern, text, re.IGNORECASE)
        if match:
            location_info['direccion'] = match.group(1).strip()
        
        # Patrones específicos
        patterns = [
            (r'(?:localidad de\s+|localidad\s+)([^,\.]+)', 'localidad'),
            (r'(?:municipio de\s+|municipio\s+)([^,\.]+)', 'municipio'),
            (r'(?:estado de\s+|estado\s+)([^,\.]+)', 'estado'),
            (r'(?:ciudad de\s+|ciudad\s+)([^,\.]+)', 'ciudad'),
        ]
        
        for pattern, tipo in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                valor = match.group(1).strip()
                if len(valor) > 2 and len(valor) < 100:
                    location_info[tipo] = valor
        
        return location_info
    
    def _determinar_ubicacion_geografica(self, ubicacion: dict, texto: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Determinar entidad federativa y municipio de la ubicación extraída.
        
        Returns:
            Tupla (entidad_federativa, municipio)
        """
        entidad_federativa = None
        municipio = None
        
        # Buscar estado en la ubicación extraída
        estado_texto = ubicacion.get('estado', '')
        if estado_texto:
            estado_upper = estado_texto.upper().strip()
            if estado_upper in self.estados_mexico:
                entidad_federativa = self.estados_mexico[estado_upper]
        
        # Si no se encontró, buscar en el texto completo
        if not entidad_federativa:
            texto_upper = texto.upper()
            for estado_key, estado_valor in self.estados_mexico.items():
                if estado_key in texto_upper:
                    entidad_federativa = estado_valor
                    break
        
        # Determinar municipio
        if ubicacion.get('municipio'):
            municipio = ubicacion['municipio'].title()
        elif ubicacion.get('ciudad'):
            municipio = ubicacion['ciudad'].title()
        elif ubicacion.get('localidad'):
            municipio = ubicacion['localidad'].title()
        
        return entidad_federativa, municipio
    
    def _extract_technical_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extraer información técnica del texto."""
        info = {
            'volumen_obra': None,
            'cantidad': None,
            'unidad': None,
            'especificaciones': None,
            'detalles_convocatoria': None,
            'visita_requerida': None,
            'caracter_procedimiento': None
        }
        
        # Volumen de obra
        volumen_patterns = [
            r'Volumen\s+a?\s*\w*\s*(.*?)(?:Los\s+detalles|Fecha\s+de|$)',
            r'Volumen\s+de\s+(?:la\s+)?(?:obra|licitación)\s+(.*?)(?:Fecha\s+de|$)',
        ]
        
        for pattern in volumen_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                volumen_texto = match.group(1).strip()
                if volumen_texto and len(volumen_texto) > 3:
                    info['volumen_obra'] = volumen_texto[:500]
                    break
        
        # Cantidad específica
        cantidad_match = re.search(r'(\d+)\s+(pieza|unidad|equipo|servicio|lote)(?:s)?', text, re.IGNORECASE)
        if cantidad_match:
            numero = int(cantidad_match.group(1))
            if numero > 31 or numero < 2000:  # No es día ni año
                info['cantidad'] = cantidad_match.group(1)
                info['unidad'] = cantidad_match.group(2)
        
        # Detalles en convocatoria
        if re.search(r'detalles\s+se\s+determinan\s+en\s+la\s+convocatoria', text, re.IGNORECASE):
            info['detalles_convocatoria'] = "Los detalles se determinan en la convocatoria"
        
        # Visita al sitio
        if re.search(r'No\s+habrá\s+visita', text, re.IGNORECASE):
            info['visita_requerida'] = False
        elif re.search(r'Visita\s+al\s+sitio', text, re.IGNORECASE):
            info['visita_requerida'] = True
        
        # Carácter del procedimiento
        if re.search(r'carácter\s+Internacional', text, re.IGNORECASE):
            info['caracter_procedimiento'] = "Internacional"
        elif re.search(r'Nacional', text, re.IGNORECASE):
            info['caracter_procedimiento'] = "Nacional"
        
        return info
    
    def _split_title_description(self, titulo: str) -> Tuple[str, str]:
        """Separar título de descripción cuando están concatenados."""
        if not titulo:
            return "", ""
        
        separators = [
            "Volumen a adquirir",
            "Volumen de la obra",
            "Volumen de licitación",
            "Los detalles se determinan",
            "Se detalla en la Convocatoria",
            "Fecha de publicación",
            "Visita al sitio"
        ]
        
        titulo_limpio = titulo
        descripcion_extraida = ""
        
        for separator in separators:
            if separator in titulo:
                partes = titulo.split(separator, 1)
                titulo_limpio = partes[0].strip()
                if len(partes) > 1:
                    descripcion_extraida = f"{separator}{partes[1]}".strip()
                break
        
        return titulo_limpio, descripcion_extraida
    
    def _clean_title(self, titulo: str) -> str:
        """Limpiar y mejorar el título."""
        if not titulo:
            return ""
        
        # Remover comillas innecesarias
        titulo = titulo.strip('"\'')
        
        # Si contiene "Volumen" como parte del título, separar
        if "Volumen" in titulo and len(titulo) > 100:
            partes = titulo.split("Volumen")
            titulo = partes[0].strip()
        
        # Otros separadores comunes
        separators = [
            ' Los detalles', ' Fecha de publicación', ' Visita al sitio',
            'Volumen de licitación', 'Volumen a adquirir'
        ]
        
        for separator in separators:
            if separator in titulo:
                titulo = titulo.split(separator)[0].strip()
                break
        
        return titulo.strip()
