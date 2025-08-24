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
        
        # Detectar formato específico del nuevo scraper v2
        if self._es_archivo_resumen(json_path.name, data):
            return self._procesar_archivo_resumen(data)
        elif self._es_archivo_todos_expedientes(json_path.name, data):
            return self._procesar_archivo_todos_expedientes(data)
        
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
                
            # Formato 5: Objeto con campo 'expedientes' (nuevo scraper)
            elif 'expedientes' in data:
                registros = data['expedientes']
        
        # Procesar registros
        for registro in registros:
            licitacion = self._parsear_registro(registro)
            if licitacion:
                licitaciones.append(licitacion)
                
        logger.info(f"Extraídas {len(licitaciones)} licitaciones de {json_path.name}")
        return licitaciones
    
    def _es_archivo_resumen(self, filename: str, data: dict) -> bool:
        """Detectar si es un archivo de resumen del scraper v2."""
        return (filename.startswith('resumen_') and 
                isinstance(data, dict) and 
                'total_expedientes_capturados' in data)
    
    def _es_archivo_todos_expedientes(self, filename: str, data: dict) -> bool:
        """Detectar si es un archivo con todos los expedientes del scraper v2."""
        return (filename.startswith('todos_expedientes_') and
                isinstance(data, dict) and 
                'expedientes' in data and 
                'total_expedientes' in data)
    
    def _procesar_archivo_resumen(self, data: dict) -> List[Dict[str, Any]]:
        """Procesar archivo de resumen (no contiene expedientes, solo estadísticas)."""
        logger.info(f"Archivo de resumen detectado: {data.get('total_expedientes_capturados', 0)} expedientes capturados")
        return []  # Los resúmenes no contienen expedientes para procesar
    
    def _procesar_archivo_todos_expedientes(self, data: dict) -> List[Dict[str, Any]]:
        """Procesar archivo con todos los expedientes consolidados."""
        logger.info(f"Archivo de expedientes consolidados detectado: {data.get('total_expedientes', 0)} expedientes")
        
        licitaciones = []
        expedientes = data.get('expedientes', [])
        
        for expediente in expedientes:
            licitacion = self._parsear_registro(expediente)
            if licitacion:
                licitaciones.append(licitacion)
        
        return licitaciones
    
    def _parsear_registro(self, registro: Dict) -> Dict[str, Any]:
        """Parsear un registro de ComprasMX."""
        try:
            # Validar campos mínimos - el nuevo scraper usa 'cod_expediente'
            numero = registro.get('numero_procedimiento') or registro.get('cod_expediente', '')
            if not numero:
                return None
            
            # Normalizar tipo de procedimiento
            tipo_proc_original = registro.get('tipo_procedimiento', '')
            tipo_proc = self._normalizar_tipo_procedimiento(tipo_proc_original)
            
            # Normalizar tipo de contratación
            tipo_cont_original = registro.get('tipo_contratacion', '')
            tipo_cont = self._normalizar_tipo_contratacion(tipo_cont_original)
            
            # Parsear fechas - el nuevo scraper puede tener más campos de fecha
            fecha_apertura = self._parsear_fecha(registro.get('fecha_apertura'))
            fecha_aclaraciones = self._parsear_fecha(registro.get('fecha_aclaraciones'))
            fecha_fallo = self._parsear_fecha(registro.get('fecha_fallo'))
            fecha_publicacion = self._parsear_fecha(registro.get('fecha_publicacion'))
            
            # Si no hay fecha de publicación, usar fecha actual
            if not fecha_publicacion:
                fecha_publicacion = datetime.now().date()
            
            # Construir URL - el nuevo scraper puede tener diferentes formatos
            uuid = registro.get('uuid_procedimiento', '')
            url_original = registro.get('url_original')
            if not url_original and uuid:
                url_original = f"https://comprasmx.buengobierno.gob.mx/procedimiento/{uuid}"
            elif not url_original:
                url_original = "https://comprasmx.buengobierno.gob.mx/"
            
            # Extraer monto si está disponible
            monto_estimado = None
            monto_str = registro.get('monto_estimado') or registro.get('presupuesto_estimado')
            if monto_str and isinstance(monto_str, (str, int, float)):
                try:
                    # Limpiar y convertir monto
                    if isinstance(monto_str, str):
                        monto_limpio = monto_str.replace('$', '').replace(',', '').replace(' ', '')
                        monto_estimado = float(monto_limpio) if monto_limpio.replace('.', '').isdigit() else None
                    else:
                        monto_estimado = float(monto_str)
                except:
                    monto_estimado = None
            
            # Crear licitación normalizada
            licitacion = self.normalizar_licitacion(registro)
            licitacion.update({
                'numero_procedimiento': numero,
                'titulo': (registro.get('nombre_procedimiento') or registro.get('titulo', ''))[:500],
                'descripcion': registro.get('descripcion'),
                'entidad_compradora': registro.get('siglas') or registro.get('entidad_compradora', ''),
                'unidad_compradora': registro.get('unidad_compradora'),
                'tipo_procedimiento': tipo_proc,
                'tipo_contratacion': tipo_cont,
                'estado': self._normalizar_estado(registro.get('estatus_alterno') or registro.get('estado', 'VIGENTE')),
                'fecha_publicacion': fecha_publicacion,
                'fecha_apertura': fecha_apertura,
                'fecha_fallo': fecha_fallo,
                'fecha_junta_aclaraciones': fecha_aclaraciones,
                'monto_estimado': monto_estimado,
                'moneda': 'MXN',
                'url_original': url_original,
                'caracter': registro.get('caracter'),
                'uuid_procedimiento': uuid
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
    
    def _normalizar_estado(self, estado: str) -> str:
        """Normalizar estado del procedimiento."""
        if not estado:
            return 'VIGENTE'
            
        estado_upper = estado.upper()
        
        if any(term in estado_upper for term in ['ACTIV', 'VIGENTE', 'ABIERTO', 'PUBLICADO']):
            return 'VIGENTE'
        elif any(term in estado_upper for term in ['CERRADO', 'FINALIZADO', 'CONCLUIDO']):
            return 'CERRADO'
        elif any(term in estado_upper for term in ['CANCELADO', 'ANULADO']):
            return 'CANCELADO'
        elif any(term in estado_upper for term in ['DESIERTO', 'SIN POSTORES']):
            return 'DESIERTO'
        else:
            return 'VIGENTE'
