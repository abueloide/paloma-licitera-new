#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor DOF Mejorado - Integración con ETL
============================================

Extractor que usa el parser mejorado del DOF para procesar archivos TXT
y cargar directamente a la base de datos con campos geográficos.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import sys
import os

# Agregar el directorio de parsers al path
sys.path.append(str(Path(__file__).parent.parent / 'parsers' / 'dof'))

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class DOFMejoradoExtractor(BaseExtractor):
    """Extractor mejorado para el Diario Oficial de la Federación."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.data_dir = Path(config['paths']['data_raw']) / 'dof'
        self.procesados_dir = Path(config['paths']['data_processed']) / 'dof'
        
        # Crear directorio de procesados si no existe
        self.procesados_dir.mkdir(parents=True, exist_ok=True)
        
        # Importar el parser mejorado
        try:
            from estructura_dof_mejorado import ParserDOFMejorado, procesar_archivo_txt
            self.parser = ParserDOFMejorado()
            self.procesar_archivo_txt = procesar_archivo_txt
            logger.info("✅ Parser DOF mejorado cargado correctamente")
        except ImportError as e:
            logger.error(f"❌ Error importando parser mejorado: {e}")
            self.parser = None
            self.procesar_archivo_txt = None
    
    def extraer(self) -> List[Dict[str, Any]]:
        """
        Extraer licitaciones procesando archivos TXT del DOF con el parser mejorado.
        
        Returns:
            Lista de licitaciones procesadas y normalizadas para BD
        """
        if not self.parser:
            logger.error("Parser mejorado no disponible")
            return []
        
        licitaciones = []
        
        # Buscar archivos TXT para procesar
        txt_files = list(self.data_dir.glob("*.txt"))
        json_mejorados = list(self.procesados_dir.glob("*_mejorado.json"))
        
        logger.info(f"📁 Encontrados {len(txt_files)} archivos TXT en {self.data_dir}")
        logger.info(f"📋 JSONs mejorados existentes: {len(json_mejorados)}")
        
        # Procesar cada archivo TXT
        for txt_file in txt_files:
            try:
                # Verificar si ya fue procesado
                json_file = self.procesados_dir / f"{txt_file.stem}_mejorado.json"
                
                if json_file.exists():
                    logger.debug(f"⏭️ {txt_file.name} ya procesado, cargando JSON existente")
                    # Cargar JSON existente
                    licitaciones.extend(self._cargar_json_mejorado(json_file))
                else:
                    logger.info(f"🔄 Procesando {txt_file.name} con parser mejorado...")
                    # Procesar con parser mejorado
                    licitaciones_archivo = self._procesar_txt_mejorado(txt_file)
                    
                    if licitaciones_archivo:
                        # Guardar JSON mejorado
                        self._guardar_json_mejorado(licitaciones_archivo, json_file)
                        licitaciones.extend(licitaciones_archivo)
                        logger.info(f"   ✅ {len(licitaciones_archivo)} licitaciones extraídas")
                    else:
                        logger.warning(f"   ⚠️ No se encontraron licitaciones en {txt_file.name}")
                        
            except Exception as e:
                logger.error(f"❌ Error procesando {txt_file.name}: {e}")
        
        # También procesar JSONs mejorados que no tengan TXT correspondiente
        for json_file in json_mejorados:
            txt_correspondiente = self.data_dir / f"{json_file.stem.replace('_mejorado', '')}.txt"
            if not txt_correspondiente.exists():
                logger.info(f"📄 Cargando JSON mejorado sin TXT: {json_file.name}")
                licitaciones.extend(self._cargar_json_mejorado(json_file))
        
        logger.info(f"📊 Total licitaciones extraídas: {len(licitaciones)}")
        return licitaciones
    
    def _procesar_txt_mejorado(self, txt_file: Path) -> List[Dict[str, Any]]:
        """
        Procesar un archivo TXT con el parser mejorado.
        
        Args:
            txt_file: Ruta al archivo TXT
            
        Returns:
            Lista de licitaciones procesadas y normalizadas
        """
        try:
            # Usar la función del parser mejorado
            licitaciones_mejoradas = self.procesar_archivo_txt(str(txt_file))
            
            # Convertir a formato para BD
            licitaciones_bd = []
            for lic in licitaciones_mejoradas:
                licitacion_bd = self._convertir_a_formato_bd(lic)
                if licitacion_bd:
                    licitaciones_bd.append(licitacion_bd)
            
            return licitaciones_bd
            
        except Exception as e:
            logger.error(f"Error en parser mejorado: {e}")
            return []
    
    def _convertir_a_formato_bd(self, licitacion_mejorada) -> Dict[str, Any]:
        """
        Convertir una licitación del formato mejorado al formato de BD.
        
        Args:
            licitacion_mejorada: Objeto LicitacionMejorada del parser
            
        Returns:
            Diccionario con formato para insertar en BD
        """
        try:
            # Convertir objeto a diccionario si es necesario
            if hasattr(licitacion_mejorada, '__dict__'):
                lic_dict = vars(licitacion_mejorada)
            else:
                lic_dict = licitacion_mejorada
            
            # Mapear campos al formato de BD
            licitacion_bd = {
                'numero_procedimiento': lic_dict.get('numero_licitacion_completo') or 
                                       lic_dict.get('numero_licitacion', ''),
                'titulo': lic_dict.get('titulo', '')[:500],
                'descripcion': lic_dict.get('descripcion', ''),
                'entidad_compradora': lic_dict.get('dependencia', 'No especificada'),
                'unidad_compradora': lic_dict.get('subdependencia'),
                'tipo_procedimiento': lic_dict.get('tipo_procedimiento', 'Licitación Pública'),
                'tipo_contratacion': lic_dict.get('tipo_contratacion', 'No especificado'),
                'estado': 'Publicada',
                'caracter': lic_dict.get('caracter_procedimiento', 'Nacional'),
                'fuente': 'DOF',
                'moneda': 'MXN',
                
                # Campos geográficos - IMPORTANTES
                'entidad_federativa': lic_dict.get('entidad_federativa'),
                'municipio': lic_dict.get('municipio'),
                
                # Fechas (convertir si tienen hora)
                'fecha_publicacion': self._limpiar_fecha(lic_dict.get('fecha_publicacion')),
                'fecha_apertura': self._limpiar_fecha(lic_dict.get('fecha_presentacion_apertura')),
                'fecha_fallo': self._limpiar_fecha(lic_dict.get('fecha_fallo')),
                'fecha_junta_aclaraciones': self._limpiar_fecha(lic_dict.get('fecha_junta_aclaraciones')),
                
                # Datos originales para JSONB
                'datos_originales': {
                    'fecha_ejemplar': lic_dict.get('fecha_ejemplar'),
                    'edicion_ejemplar': lic_dict.get('edicion_ejemplar'),
                    'archivo_origen': lic_dict.get('archivo_origen'),
                    'pagina': lic_dict.get('pagina'),
                    'referencia': lic_dict.get('referencia'),
                    'reduccion_plazos': lic_dict.get('reduccion_plazos'),
                    'autoridad_reduccion': lic_dict.get('autoridad_reduccion'),
                    'fecha_visita_instalaciones': lic_dict.get('fecha_visita_instalaciones')
                },
                
                # Datos específicos para JSONB
                'datos_especificos': {
                    'tipo_contratacion_detectado': lic_dict.get('tipo_contratacion'),
                    'confianza_extraccion': lic_dict.get('confianza_extraccion', 0),
                    'campos_extraidos': lic_dict.get('campos_extraidos', 0),
                    'volumen_obra': lic_dict.get('volumen_obra'),
                    'cantidad': lic_dict.get('cantidad'),
                    'unidad_medida': lic_dict.get('unidad_medida'),
                    'especificaciones_tecnicas': lic_dict.get('especificaciones_tecnicas'),
                    'localidad': lic_dict.get('localidad'),
                    'direccion_completa': lic_dict.get('direccion_completa'),
                    'lugar_eventos': lic_dict.get('lugar_eventos'),
                    'observaciones': lic_dict.get('observaciones'),
                    'procesado_parser_mejorado': True,
                    'fecha_procesamiento': datetime.now().isoformat()
                }
            }
            
            # Validar que tenga información mínima
            if licitacion_bd['numero_procedimiento'] or licitacion_bd['titulo']:
                return licitacion_bd
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error convirtiendo licitación a formato BD: {e}")
            return None
    
    def _limpiar_fecha(self, fecha_str: str) -> str:
        """
        Limpiar fecha para dejar solo YYYY-MM-DD.
        
        Args:
            fecha_str: String con fecha posiblemente con hora
            
        Returns:
            String con fecha en formato YYYY-MM-DD o None
        """
        if not fecha_str:
            return None
        
        # Si tiene espacio (fecha y hora), tomar solo la fecha
        if ' ' in str(fecha_str):
            return str(fecha_str).split(' ')[0]
        
        return str(fecha_str)
    
    def _guardar_json_mejorado(self, licitaciones: List[Dict], json_file: Path):
        """
        Guardar licitaciones procesadas en JSON mejorado.
        
        Args:
            licitaciones: Lista de licitaciones procesadas
            json_file: Ruta donde guardar el JSON
        """
        try:
            datos = {
                'fecha_procesamiento': datetime.now().isoformat(),
                'total_licitaciones': len(licitaciones),
                'fuente': 'DOF',
                'parser': 'mejorado',
                'licitaciones': licitaciones
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"   💾 JSON guardado: {json_file.name}")
            
        except Exception as e:
            logger.error(f"Error guardando JSON: {e}")
    
    def _cargar_json_mejorado(self, json_file: Path) -> List[Dict[str, Any]]:
        """
        Cargar licitaciones desde un JSON mejorado existente.
        
        Args:
            json_file: Ruta al archivo JSON
            
        Returns:
            Lista de licitaciones en formato BD
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            
            licitaciones = datos.get('licitaciones', [])
            
            # Si las licitaciones ya están en formato BD, devolverlas directamente
            # Si no, convertirlas
            licitaciones_bd = []
            for lic in licitaciones:
                if 'numero_procedimiento' in lic:
                    # Ya está en formato BD
                    licitaciones_bd.append(lic)
                else:
                    # Convertir desde formato mejorado
                    lic_bd = self._convertir_a_formato_bd(lic)
                    if lic_bd:
                        licitaciones_bd.append(lic_bd)
            
            return licitaciones_bd
            
        except Exception as e:
            logger.error(f"Error cargando JSON {json_file}: {e}")
            return []
