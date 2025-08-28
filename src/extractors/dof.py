#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor del DOF - Diario Oficial de la Federación
Versión mejorada para manejar JSONs con estructura mejorada
Actualización: 28/12/2024
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, date
import re

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class DOFExtractor(BaseExtractor):
    """Extractor mejorado para el Diario Oficial de la Federación."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.data_dir = Path(config['paths']['data_raw']) / 'dof'
        
    def extraer(self) -> List[Dict[str, Any]]:
        """Extraer licitaciones de archivos JSON del DOF."""
        licitaciones = []
        
        # Buscar archivos JSON de licitaciones (normal y mejorado)
        json_patterns = ["*licitaciones.json", "*licitaciones_mejorado.json"]
        json_files = []
        
        for pattern in json_patterns:
            json_files.extend(list(self.data_dir.glob(pattern)))
        
        # Eliminar duplicados si existe versión mejorada
        json_files = self._filtrar_archivos_json(json_files)
        
        logger.info(f"Encontrados {len(json_files)} archivos JSON en {self.data_dir}")
        
        for json_file in json_files:
            try:
                licitaciones.extend(self._procesar_json(json_file))
            except Exception as e:
                logger.error(f"Error procesando {json_file}: {e}")
                
        return licitaciones
    
    def _filtrar_archivos_json(self, archivos: List[Path]) -> List[Path]:
        """Filtra archivos JSON, prefiriendo versión mejorada si existe"""
        archivos_filtrados = {}
        
        for archivo in archivos:
            # Extraer fecha base del nombre (e.g., "05082025_MAT")
            nombre = archivo.stem
            if '_licitaciones_mejorado' in nombre:
                base = nombre.replace('_licitaciones_mejorado', '')
                archivos_filtrados[base] = archivo
            elif '_licitaciones' in nombre:
                base = nombre.replace('_licitaciones', '')
                # Solo agregar si no existe versión mejorada
                if base not in archivos_filtrados:
                    archivos_filtrados[base] = archivo
        
        return list(archivos_filtrados.values())
    
    def _procesar_json(self, json_path: Path) -> List[Dict[str, Any]]:
        """Procesar un archivo JSON del DOF (formato normal o mejorado)."""
        logger.info(f"Procesando: {json_path.name}")
        licitaciones = []
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Detectar formato del JSON
        es_formato_mejorado = data.get('version_extractor') == '2.0'
        
        # Extraer información del ejemplar si existe
        fecha_ejemplar = data.get('fecha_ejemplar', '')
        edicion_ejemplar = data.get('edicion_ejemplar', '')
        archivo_origen = data.get('archivo_origen', '')
        
        # El formato puede variar
        if isinstance(data, list):
            registros = data
        elif isinstance(data, dict):
            registros = data.get('licitaciones', data.get('data', []))
        else:
            registros = []
        
        for registro in registros:
            if es_formato_mejorado:
                licitacion = self._parsear_registro_dof_mejorado(
                    registro, fecha_ejemplar, edicion_ejemplar, archivo_origen
                )
            else:
                licitacion = self._parsear_registro_dof(registro)
            
            if licitacion:
                licitaciones.append(licitacion)
                
        logger.info(f"Extraídas {len(licitaciones)} licitaciones de {json_path.name}")
        return licitaciones
    
    def _parsear_registro_dof_mejorado(self, registro: Dict, fecha_ejemplar: str, 
                                       edicion_ejemplar: str, archivo_origen: str) -> Dict[str, Any]:
        """Parsear un registro del DOF con formato mejorado."""
        try:
            # Usar título limpio si existe, sino usar objeto_licitacion
            titulo = registro.get('titulo') or registro.get('objeto_licitacion', '')
            descripcion = registro.get('descripcion')
            
            # Si no hay título pero hay objeto_contratacion, usarlo
            if not titulo and registro.get('objeto_contratacion'):
                titulo = registro['objeto_contratacion'][:500]
            
            # Número de licitación
            numero = registro.get('numero_licitacion', '')
            if not numero:
                return None
            
            # Entidades
            entidad = registro.get('dependencia', '')
            if not entidad:
                return None
            
            unidad = registro.get('subdependencia') or registro.get('unidad_responsable')
            
            # Tipo de procedimiento
            tipo_proc = registro.get('tipo_procedimiento') or self._inferir_tipo_procedimiento(numero)
            
            # Caracter de la licitación  
            caracter_original = registro.get('caracter_licitacion', '')
            caracter = self._normalizar_caracter(caracter_original)
            
            # Parsear fechas (pueden venir estructuradas o como string)
            fecha_pub = self._parsear_fecha_estructurada(registro.get('fecha_publicacion'))
            fecha_aclaraciones = self._parsear_fecha_estructurada(registro.get('fecha_junta_aclaraciones'))
            fecha_apertura = self._parsear_fecha_estructurada(registro.get('fecha_presentacion_apertura'))
            fecha_fallo = self._parsear_fecha_estructurada(registro.get('fecha_fallo'))
            fecha_visita = self._parsear_fecha_estructurada(registro.get('fecha_visita_instalaciones'))
            
            # Tipo de contratación
            tipo_cont = self.detectar_tipo_contratacion(titulo)
            
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
                'estado': 'VIGENTE',
                'fecha_publicacion': fecha_pub or datetime.now().date(),
                'fecha_junta_aclaraciones': fecha_aclaraciones,
                'fecha_apertura': fecha_apertura,
                'fecha_fallo': fecha_fallo,
                'fecha_visita_lugar': fecha_visita
            })
            
            # Agregar caracter si no es estándar
            if caracter and caracter != 'NACIONAL':
                licitacion['caracter'] = caracter
            
            # Agregar información del ejemplar a datos_originales
            if not licitacion.get('datos_originales'):
                licitacion['datos_originales'] = {}
            
            licitacion['datos_originales'].update({
                'fecha_ejemplar': fecha_ejemplar or registro.get('fecha_ejemplar', ''),
                'edicion_ejemplar': edicion_ejemplar or registro.get('edicion_ejemplar', ''),
                'archivo_origen': archivo_origen or registro.get('archivo_origen', ''),
                'pagina': registro.get('pagina'),
                'referencia': registro.get('referencia'),
                'lugar_eventos': registro.get('lugar_eventos'),
                'autoridad_firmante': registro.get('autoridad_firmante'),
                'volumen_adquirir': registro.get('volumen_adquirir')
            })
            
            return licitacion
            
        except Exception as e:
            logger.debug(f"Error parseando registro DOF mejorado: {e}")
            return None
    
    def _parsear_fecha_estructurada(self, fecha_data: Any) -> date:
        """
        Parsea una fecha que puede venir en formato estructurado o string.
        
        Formato estructurado esperado:
        {
            'fecha': 'YYYY-MM-DD',
            'hora': 'HH:MM',
            'texto_original': 'texto original'
        }
        """
        if not fecha_data:
            return None
        
        # Si es un diccionario con estructura
        if isinstance(fecha_data, dict):
            fecha_str = fecha_data.get('fecha')
            if fecha_str:
                try:
                    return datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except:
                    pass
            
            # Intentar con texto_original si no hay fecha parseada
            texto = fecha_data.get('texto_original')
            if texto:
                return self._parsear_fecha_dof(texto)
        
        # Si es string directo
        elif isinstance(fecha_data, str):
            return self._parsear_fecha_dof(fecha_data)
        
        return None
    
    def _parsear_registro_dof(self, registro: Dict) -> Dict[str, Any]:
        """Parsear un registro del DOF (formato original)."""
        try:
            # Campos principales
            numero = registro.get('numero_licitacion', '')
            if not numero:
                return None
            
            # Objeto de licitación (puede ser muy largo)
            objeto = registro.get('objeto_licitacion', '')
            
            # Limpiar objeto - quitar información que no corresponde
            if objeto:
                # Buscar donde termina realmente el objeto
                # Patrones que indican fin del objeto
                patrones_fin = [
                    r'Volumen\s+a\s+[Aa]dquirir',
                    r'Fecha\s+de\s+[Pp]ublicaci',
                    r'Junta\s+de\s+[Aa]claraciones',
                    r'Visita\s+a\s+[Ii]nstalaciones',
                    r'Presentaci[óo]n\s+y\s+[Aa]pertura',
                    r'Fallo'
                ]
                
                for patron in patrones_fin:
                    match = re.search(patron, objeto, re.IGNORECASE)
                    if match:
                        objeto = objeto[:match.start()].strip()
                        break
            
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
            
            # Agregar información del ejemplar si existe
            if registro.get('fecha_ejemplar'):
                if not licitacion.get('datos_originales'):
                    licitacion['datos_originales'] = {}
                
                licitacion['datos_originales'].update({
                    'fecha_ejemplar': registro.get('fecha_ejemplar'),
                    'edicion_ejemplar': registro.get('edicion_ejemplar'),
                    'archivo_origen': registro.get('archivo_origen'),
                    'pagina': registro.get('pagina'),
                    'referencia': registro.get('referencia')
                })
            
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
    
    def _parsear_fecha_dof(self, fecha_str: str) -> date:
        """Parsear fecha en formato del DOF."""
        if not fecha_str:
            return None
        
        # Diccionario de meses en español
        meses_es = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12',
            'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'ago': '08', 'agos': '08',
            'sep': '09', 'sept': '09', 'oct': '10', 'nov': '11', 'dic': '12'
        }
        
        try:
            # Limpiar la fecha
            fecha_str = fecha_str.strip()
            
            # Quitar texto adicional común
            fecha_str = fecha_str.replace('en CompraNet', '').replace('en Compras Mx', '')
            fecha_str = fecha_str.replace('.', '').strip()
            
            # Formato: "DD/MM/YYYY, HH:MM horas"
            if ',' in fecha_str:
                fecha_parte = fecha_str.split(',')[0].strip()
                if '/' in fecha_parte:
                    partes = fecha_parte.split('/')
                    if len(partes) == 3:
                        dia, mes, año = partes
                        return datetime.strptime(f"{dia}/{mes}/{año}", '%d/%m/%Y').date()
            
            # Formato: "DD de MES de YYYY"
            if ' de ' in fecha_str:
                partes = fecha_str.lower().split(' de ')
                if len(partes) >= 3:
                    dia = partes[0].strip()
                    mes_str = partes[1].strip()
                    año = partes[2].strip()[:4]  # Tomar solo los primeros 4 caracteres del año
                    
                    mes = meses_es.get(mes_str, '01')
                    
                    try:
                        fecha_formateada = f"{dia.zfill(2)}/{mes}/{año}"
                        return datetime.strptime(fecha_formateada, '%d/%m/%Y').date()
                    except:
                        pass
            
            # Formato: "HH:MM horas, DD Mes. YYYY"
            match = re.search(r'(\d{1,2})\s+(\w{3,})\.?\s+(\d{4})', fecha_str)
            if match:
                dia, mes_str, año = match.groups()
                mes = meses_es.get(mes_str.lower(), '01')
                try:
                    return datetime.strptime(f"{dia}/{mes}/{año}", '%d/%m/%Y').date()
                except:
                    pass
            
            # Formato ISO
            if '-' in fecha_str:
                partes = fecha_str.split(' ')[0].split('-')
                if len(partes) == 3 and len(partes[0]) == 4:
                    return datetime.strptime(fecha_str.split(' ')[0], '%Y-%m-%d').date()
            
            # Formato DD/MM/YYYY simple
            if '/' in fecha_str:
                partes = fecha_str.split('/')
                if len(partes) == 3:
                    dia, mes, año = partes
                    # Limpiar año de texto adicional
                    año = re.search(r'\d{4}', año)
                    if año:
                        return datetime.strptime(f"{dia}/{mes}/{año.group()}", '%d/%m/%Y').date()
                
        except Exception as e:
            logger.debug(f"Error parseando fecha DOF '{fecha_str}': {e}")
            
        return None
