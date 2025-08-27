#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parser DOF Mejorado - Extractor de Licitaciones del Diario Oficial
===================================================================

Parser mejorado que extrae información estructurada del DOF con:
- Extracción completa de números de licitación (LA-XXX-XXX-XXX)
- Normalización de fechas a formato ISO
- Detección de ubicación geográfica (32 estados + municipios)
- Identificación de tipos de contratación
- Cálculo de confianza de extracción
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import hashlib

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LicitacionMejorada:
    """Estructura de datos mejorada para una licitación"""
    # Identificación
    numero_licitacion: str
    numero_licitacion_completo: Optional[str]  # Con todos los segmentos
    
    # Información básica
    titulo: str
    descripcion: str
    dependencia: str
    subdependencia: Optional[str]
    
    # Tipo y carácter
    tipo_contratacion: str  # Obra, Servicio, Adquisición
    caracter_procedimiento: str  # Nacional, Internacional
    tipo_procedimiento: str  # Licitación Pública, Invitación, Adjudicación
    
    # Ubicación geográfica
    entidad_federativa: Optional[str]
    municipio: Optional[str]
    localidad: Optional[str]
    direccion_completa: Optional[str]
    
    # Fechas en formato ISO
    fecha_publicacion: Optional[str]
    fecha_junta_aclaraciones: Optional[str]
    fecha_visita_instalaciones: Optional[str]
    fecha_presentacion_apertura: Optional[str]
    fecha_fallo: Optional[str]
    
    # Información técnica
    volumen_obra: Optional[str]
    cantidad: Optional[str]
    unidad_medida: Optional[str]
    especificaciones_tecnicas: Optional[str]
    
    # Información adicional
    reduccion_plazos: bool
    autoridad_reduccion: Optional[str]
    lugar_eventos: Optional[str]
    observaciones: Optional[str]
    
    # Metadatos
    pagina: int
    referencia: Optional[str]  # (R.- XXXXXX)
    confianza_extraccion: float  # 0.0 a 1.0
    campos_extraidos: int  # Número de campos con datos
    raw_text: str  # Texto original
    
    # Información del ejemplar
    fecha_ejemplar: str  # YYYY-MM-DD
    edicion_ejemplar: str  # MAT o VES
    archivo_origen: str
    fecha_procesamiento: str  # ISO timestamp


class ParserDOFMejorado:
    """Parser mejorado para textos del DOF con extracción completa"""
    
    def __init__(self):
        # Meses en español para conversión de fechas
        self.meses = {
            'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
            'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
            'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
        }
        
        # Mapeo completo de 32 estados de México
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
            'COAHUILA DE ZARAGOZA': 'Coahuila',
            'COLIMA': 'Colima',
            'DURANGO': 'Durango',
            'GUANAJUATO': 'Guanajuato',
            'GUERRERO': 'Guerrero',
            'HIDALGO': 'Hidalgo',
            'JALISCO': 'Jalisco',
            'MEXICO': 'Estado de México',
            'ESTADO DE MEXICO': 'Estado de México',
            'EDO MEX': 'Estado de México',
            'EDOMEX': 'Estado de México',
            'MICHOACAN': 'Michoacán',
            'MICHOACAN DE OCAMPO': 'Michoacán',
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
            'VERACRUZ DE IGNACIO DE LA LLAVE': 'Veracruz',
            'YUCATAN': 'Yucatán',
            'ZACATECAS': 'Zacatecas'
        }
        
        # Tipos de contratación
        self.tipos_contratacion = {
            'OBRA': ['obra', 'obras', 'construcción', 'construccion', 'edificación', 
                     'pavimentación', 'rehabilitación', 'mantenimiento de infraestructura'],
            'SERVICIO': ['servicio', 'servicios', 'consultoría', 'consultoria', 'asesoría',
                         'asesoria', 'mantenimiento', 'limpieza', 'vigilancia', 'seguridad'],
            'ADQUISICION': ['adquisición', 'adquisicion', 'compra', 'suministro', 
                           'abastecimiento', 'material', 'equipo', 'insumos']
        }
        
        # Patrones regex mejorados
        self._compilar_patrones()
    
    def _compilar_patrones(self):
        """Compila todos los patrones regex para mejor rendimiento"""
        
        # Patrón para número de licitación completo
        self.patron_numero_completo = re.compile(
            r'(L[AOSP][\-\s]*\d{1,3}[\-\s]*\w+[\-\s]*\d+[\-\s]*[NIT][\-\s]*\d+[\-\s]*\d{4})',
            re.IGNORECASE
        )
        
        # Patrón para detectar tipo de procedimiento
        self.patron_tipo_procedimiento = re.compile(
            r'(Licitaci[óo]n\s+P[úu]blica|Invitaci[óo]n\s+a\s+cuando\s+menos\s+tres|'
            r'Adjudicaci[óo]n\s+Directa)',
            re.IGNORECASE
        )
        
        # Patrón para carácter del procedimiento
        self.patron_caracter = re.compile(
            r'(Nacional|Internacional)(?:\s+(?:Abierta|Electr[óo]nica|Presencial))?',
            re.IGNORECASE
        )
        
        # Patrones para fechas
        self.patrones_fechas = {
            'publicacion': re.compile(
                r'Fecha\s+de\s+publicaci[óo]n(?:\s+en\s+Compras?\s*M[Xx])?[\s:]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}|\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
                re.IGNORECASE
            ),
            'junta_aclaraciones': re.compile(
                r'Junta\s+de\s+aclaraciones?[\s:]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}(?:[\s,]+(?:a\s+las\s+)?\d{1,2}:\d{2})?|\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
                re.IGNORECASE
            ),
            'visita': re.compile(
                r'Visita\s+(?:a\s+las?\s+)?(?:instalaciones?|sitio|lugar)(?:\s+de\s+(?:los\s+)?trabajos?)?[\s:]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}(?:[\s,]+(?:a\s+las\s+)?\d{1,2}:\d{2})?|No\s+(?:habrá|aplica))',
                re.IGNORECASE
            ),
            'apertura': re.compile(
                r'(?:Presentaci[óo]n\s+y\s+)?[Aa]pertura\s+de\s+(?:las\s+)?proposiciones?[\s:]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}(?:[\s,]+(?:a\s+las\s+)?\d{1,2}:\d{2})?|\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
                re.IGNORECASE
            ),
            'fallo': re.compile(
                r'(?:Emisi[óo]n\s+de(?:l)?\s+)?Fallo[\s:]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}(?:[\s,]+(?:a\s+las\s+)?\d{1,2}:\d{2})?|\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
                re.IGNORECASE
            )
        }
        
        # Patrón para referencia (R.- XXXXX)
        self.patron_referencia = re.compile(r'\(R\.\-?\s*(\d+)\)')
        
        # Patrón para reducción de plazos
        self.patron_reduccion = re.compile(
            r'reducci[óo]n\s+de\s+plazos.*?autorizada?\s+por\s+(?:el\s+|la\s+)?([^,\.\n]+)',
            re.IGNORECASE | re.DOTALL
        )
    
    def parsear_bloque(self, texto: str, num_pagina: int, fecha_ejemplar: str, 
                       edicion_ejemplar: str, archivo_origen: str) -> Optional[LicitacionMejorada]:
        """
        Parsea un bloque de texto y extrae toda la información de la licitación
        
        Args:
            texto: Bloque de texto con información de una licitación
            num_pagina: Número de página donde se encuentra
            fecha_ejemplar: Fecha del ejemplar del DOF (YYYY-MM-DD)
            edicion_ejemplar: Edición (MAT/VES)
            archivo_origen: Nombre del archivo de origen
        
        Returns:
            Objeto LicitacionMejorada o None si no se puede extraer información suficiente
        """
        # Inicializar datos
        datos = {
            'numero_licitacion': '',
            'numero_licitacion_completo': None,
            'titulo': '',
            'descripcion': '',
            'dependencia': '',
            'subdependencia': None,
            'tipo_contratacion': 'No especificado',
            'caracter_procedimiento': 'Nacional',
            'tipo_procedimiento': 'Licitación Pública',
            'entidad_federativa': None,
            'municipio': None,
            'localidad': None,
            'direccion_completa': None,
            'fecha_publicacion': None,
            'fecha_junta_aclaraciones': None,
            'fecha_visita_instalaciones': None,
            'fecha_presentacion_apertura': None,
            'fecha_fallo': None,
            'volumen_obra': None,
            'cantidad': None,
            'unidad_medida': None,
            'especificaciones_tecnicas': None,
            'reduccion_plazos': False,
            'autoridad_reduccion': None,
            'lugar_eventos': None,
            'observaciones': None,
            'pagina': num_pagina,
            'referencia': None,
            'confianza_extraccion': 0.0,
            'campos_extraidos': 0,
            'raw_text': texto[:1000],  # Primeros 1000 caracteres
            'fecha_ejemplar': fecha_ejemplar,
            'edicion_ejemplar': edicion_ejemplar,
            'archivo_origen': archivo_origen,
            'fecha_procesamiento': datetime.now().isoformat()
        }
        
        campos_criticos = 0
        campos_totales = 0
        
        # 1. Extraer número de licitación completo
        match_numero = self.patron_numero_completo.search(texto)
        if match_numero:
            numero_completo = match_numero.group(1)
            # Normalizar el número (quitar espacios extras, estandarizar guiones)
            numero_normalizado = re.sub(r'[\s]+', '', numero_completo.upper())
            numero_normalizado = re.sub(r'[\-]+', '-', numero_normalizado)
            datos['numero_licitacion_completo'] = numero_normalizado
            datos['numero_licitacion'] = numero_normalizado
            campos_criticos += 1
            datos['campos_extraidos'] += 1
        
        # 2. Extraer dependencia y subdependencia
        dependencia, subdependencia = self._extraer_dependencias(texto)
        if dependencia:
            datos['dependencia'] = dependencia
            datos['subdependencia'] = subdependencia
            campos_criticos += 1
            datos['campos_extraidos'] += 1
            if subdependencia:
                datos['campos_extraidos'] += 1
        
        # 3. Extraer título y descripción
        titulo, descripcion = self._extraer_titulo_descripcion(texto)
        if titulo:
            datos['titulo'] = titulo
            datos['descripcion'] = descripcion
            datos['campos_extraidos'] += 1
            if descripcion:
                datos['campos_extraidos'] += 1
        
        # 4. Determinar tipo de contratación
        tipo_contratacion = self._detectar_tipo_contratacion(texto)
        datos['tipo_contratacion'] = tipo_contratacion
        datos['campos_extraidos'] += 1
        
        # 5. Extraer tipo y carácter del procedimiento
        match_tipo = self.patron_tipo_procedimiento.search(texto)
        if match_tipo:
            datos['tipo_procedimiento'] = match_tipo.group(1).strip()
            datos['campos_extraidos'] += 1
        
        match_caracter = self.patron_caracter.search(texto)
        if match_caracter:
            datos['caracter_procedimiento'] = match_caracter.group(1).strip()
            datos['campos_extraidos'] += 1
        
        # 6. Extraer ubicación geográfica
        ubicacion = self._extraer_ubicacion_completa(texto)
        if ubicacion['entidad_federativa']:
            datos['entidad_federativa'] = ubicacion['entidad_federativa']
            datos['municipio'] = ubicacion['municipio']
            datos['localidad'] = ubicacion['localidad']
            datos['direccion_completa'] = ubicacion['direccion']
            campos_criticos += 1
            datos['campos_extraidos'] += sum(1 for v in ubicacion.values() if v)
        
        # 7. Extraer todas las fechas
        fechas_extraidas = self._extraer_fechas(texto)
        for campo_fecha, valor_fecha in fechas_extraidas.items():
            datos[f'fecha_{campo_fecha}'] = valor_fecha
            if valor_fecha:
                datos['campos_extraidos'] += 1
                campos_totales += 1
        
        # 8. Extraer información técnica
        info_tecnica = self._extraer_informacion_tecnica(texto)
        for campo, valor in info_tecnica.items():
            if valor:
                datos[campo] = valor
                datos['campos_extraidos'] += 1
                campos_totales += 1
        
        # 9. Buscar referencia
        match_ref = self.patron_referencia.search(texto)
        if match_ref:
            datos['referencia'] = f"(R.- {match_ref.group(1)})"
            datos['campos_extraidos'] += 1
        
        # 10. Detectar reducción de plazos
        match_reduccion = self.patron_reduccion.search(texto)
        if match_reduccion:
            datos['reduccion_plazos'] = True
            datos['autoridad_reduccion'] = match_reduccion.group(1).strip()
            datos['campos_extraidos'] += 2
        
        # Calcular confianza de extracción
        # Campos críticos: número, dependencia, ubicación (valen más)
        # Máximo: 3 críticos * 0.2 = 0.6, más otros campos * 0.04 (máx 10) = 0.4
        confianza = min(1.0, (campos_criticos * 0.2) + (min(campos_totales, 10) * 0.04))
        datos['confianza_extraccion'] = round(confianza, 2)
        
        # Validar que tenemos información mínima
        if datos['numero_licitacion'] or (datos['dependencia'] and datos['titulo']):
            return LicitacionMejorada(**datos)
        
        return None
    
    def _extraer_dependencias(self, texto: str) -> Tuple[str, Optional[str]]:
        """Extrae dependencia y subdependencia del texto"""
        dependencia = ""
        subdependencia = None
        
        # Buscar líneas en mayúsculas al inicio (típicamente las primeras 15 líneas)
        lineas = texto.split('\n')[:15]
        
        # Patrones de dependencias comunes
        patrones_dependencia = [
            r'^(SECRETAR[ÍI]A\s+DE\s+[\w\s]+)',
            r'^(INSTITUTO\s+[\w\s]+)',
            r'^(COMISI[ÓO]N\s+[\w\s]+)',
            r'^(HOSPITAL\s+[\w\s]+)',
            r'^(UNIVERSIDAD\s+[\w\s]+)',
            r'^(CENTRO\s+[\w\s]+)',
            r'^(ADMINISTRACI[ÓO]N\s+[\w\s]+)',
            r'^(SERVICIOS\s+[\w\s]+)',
            r'^(CONSEJO\s+[\w\s]+)',
            r'^(TRIBUNAL\s+[\w\s]+)',
            r'^(PROCURADUR[ÍI]A\s+[\w\s]+)'
        ]
        
        patron_combinado = '|'.join(patrones_dependencia)
        
        for i, linea in enumerate(lineas):
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue
            
            # Buscar dependencia principal
            if re.match(patron_combinado, linea_limpia, re.IGNORECASE):
                dependencia = linea_limpia
                # Buscar subdependencia en las siguientes líneas
                if i + 1 < len(lineas):
                    siguiente = lineas[i + 1].strip()
                    # Si la siguiente línea también está en mayúsculas y es larga
                    if siguiente and siguiente.isupper() and len(siguiente) > 10:
                        # Verificar que no sea otra dependencia principal
                        if not re.match(patron_combinado, siguiente, re.IGNORECASE):
                            subdependencia = siguiente
                break
        
        return dependencia, subdependencia
    
    def _extraer_titulo_descripcion(self, texto: str) -> Tuple[str, str]:
        """Extrae y separa título de descripción"""
        titulo = ""
        descripcion = ""
        
        # Buscar patrones de objeto/título
        patrones = [
            r'Objeto\s+de\s+la\s+[Ll]icitaci[óo]n[\s:]+([^\n]+(?:\n[^\n]+){0,2})',
            r'Descripci[óo]n\s+de\s+la\s+[Ll]icitaci[óo]n[\s:]+([^\n]+(?:\n[^\n]+){0,2})',
            r'Nombre\s+del\s+Procedimiento[\s:]+([^\n]+(?:\n[^\n]+){0,2})'
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                contenido = match.group(1).strip()
                # Limpiar múltiples espacios
                contenido = re.sub(r'\s+', ' ', contenido)
                
                # Separar título de descripción si está concatenado
                if 'Volumen' in contenido or 'Los detalles' in contenido:
                    partes = re.split(r'(?=Volumen|Los detalles)', contenido)
                    titulo = partes[0].strip()
                    if len(partes) > 1:
                        descripcion = ' '.join(partes[1:]).strip()
                else:
                    titulo = contenido
                break
        
        # Si no se encontró descripción, buscarla por separado
        if titulo and not descripcion:
            match_desc = re.search(r'Volumen\s+a?\s*\w*[\s:]+([^\.]+)', texto, re.IGNORECASE)
            if match_desc:
                descripcion = match_desc.group(1).strip()
        
        return titulo[:500], descripcion[:1000]  # Limitar longitud
    
    def _detectar_tipo_contratacion(self, texto: str) -> str:
        """Detecta el tipo de contratación basándose en palabras clave"""
        texto_lower = texto.lower()
        
        # Contar palabras clave de cada tipo
        puntuacion = {'OBRA': 0, 'SERVICIO': 0, 'ADQUISICION': 0}
        
        for tipo, palabras in self.tipos_contratacion.items():
            for palabra in palabras:
                if palabra in texto_lower:
                    puntuacion[tipo] += 1
        
        # Devolver el tipo con mayor puntuación
        if max(puntuacion.values()) > 0:
            return max(puntuacion, key=puntuacion.get)
        
        # Si no se detecta, intentar por el número de licitación
        if 'LO-' in texto or 'LO ' in texto:
            return 'OBRA'
        elif 'LA-' in texto or 'LA ' in texto:
            return 'ADQUISICION'
        elif 'LS-' in texto or 'LS ' in texto:
            return 'SERVICIO'
        
        return 'No especificado'
    
    def _extraer_ubicacion_completa(self, texto: str) -> Dict[str, Optional[str]]:
        """Extrae ubicación geográfica completa con entidad, municipio y localidad"""
        ubicacion = {
            'entidad_federativa': None,
            'municipio': None,
            'localidad': None,
            'direccion': None
        }
        
        texto_upper = texto.upper()
        
        # 1. Buscar estado explícitamente mencionado
        for estado_key, estado_valor in self.estados_mexico.items():
            # Buscar con diferentes contextos
            patrones_estado = [
                rf'\b{estado_key}\b',
                rf'ESTADO\s+DE\s+{estado_key}',
                rf'EDO\.\s*DE\s+{estado_key}',
                rf'{estado_key},?\s+M[ÉE]XICO'
            ]
            
            for patron in patrones_estado:
                if re.search(patron, texto_upper):
                    ubicacion['entidad_federativa'] = estado_valor
                    break
            
            if ubicacion['entidad_federativa']:
                break
        
        # 2. Buscar municipio
        patrones_municipio = [
            r'[Mm]unicipio\s+de\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)(?:[,\.]|\s+del?\s+[Ee]stado)',
            r'[Mm]unicipio\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)(?:[,\.])',
            r'en\s+el\s+[Mm]unicipio\s+de\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)(?:[,\.])'
        ]
        
        for patron in patrones_municipio:
            match = re.search(patron, texto)
            if match:
                municipio = match.group(1).strip()
                # Capitalizar correctamente
                ubicacion['municipio'] = ' '.join(word.capitalize() for word in municipio.split())
                break
        
        # 3. Buscar localidad
        patrones_localidad = [
            r'[Ll]ocalidad\s+de\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)(?:[,\.])',
            r'en\s+la\s+[Ll]ocalidad\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)(?:[,\.])',
            r'[Cc]omunidad\s+de\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)(?:[,\.])'
        ]
        
        for patron in patrones_localidad:
            match = re.search(patron, texto)
            if match:
                localidad = match.group(1).strip()
                ubicacion['localidad'] = ' '.join(word.capitalize() for word in localidad.split())
                break
        
        # 4. Buscar dirección completa
        patrones_direccion = [
            r'[Uu]bicad[oa]\s+en[\s:]+([^,\.\n]+(?:,\s*[^,\.\n]+)*)',
            r'[Dd]omicilio[\s:]+([^,\.\n]+(?:,\s*[^,\.\n]+)*)',
            r'[Dd]irecci[óo]n[\s:]+([^,\.\n]+(?:,\s*[^,\.\n]+)*)',
            r'[Ss]ito\s+en[\s:]+([^,\.\n]+(?:,\s*[^,\.\n]+)*)'
        ]
        
        for patron in patrones_direccion:
            match = re.search(patron, texto)
            if match:
                direccion = match.group(1).strip()
                if len(direccion) > 10 and len(direccion) < 300:
                    ubicacion['direccion'] = direccion
                    
                    # Intentar extraer estado de la dirección si no se ha encontrado
                    if not ubicacion['entidad_federativa']:
                        direccion_upper = direccion.upper()
                        for estado_key, estado_valor in self.estados_mexico.items():
                            if estado_key in direccion_upper:
                                ubicacion['entidad_federativa'] = estado_valor
                                break
                break
        
        return ubicacion
    
    def _extraer_fechas(self, texto: str) -> Dict[str, Optional[str]]:
        """Extrae todas las fechas y las convierte a formato ISO"""
        fechas = {}
        
        for tipo_fecha, patron in self.patrones_fechas.items():
            match = patron.search(texto)
            if match:
                fecha_texto = match.group(1)
                
                # Manejar casos especiales
                if 'No' in fecha_texto or 'aplica' in fecha_texto.lower():
                    fechas[tipo_fecha] = None
                else:
                    fecha_iso = self._convertir_fecha_iso(fecha_texto)
                    fechas[tipo_fecha] = fecha_iso
        
        return fechas
    
    def _convertir_fecha_iso(self, fecha_texto: str) -> Optional[str]:
        """Convierte fecha a formato ISO (YYYY-MM-DD HH:MM:SS)"""
        fecha_texto = fecha_texto.strip()
        
        # Extraer hora si existe
        hora = 0
        minuto = 0
        match_hora = re.search(r'(\d{1,2}):(\d{2})', fecha_texto)
        if match_hora:
            hora = int(match_hora.group(1))
            minuto = int(match_hora.group(2))
            # Remover la hora del texto para procesar la fecha
            fecha_texto = re.sub(r'\s*(?:a\s+las?\s+)?\d{1,2}:\d{2}', '', fecha_texto)
        
        # Formato 1: DD/MM/YYYY o DD-MM-YYYY
        match = re.match(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', fecha_texto)
        if match:
            dia = int(match.group(1))
            mes = int(match.group(2))
            año = int(match.group(3))
            
            try:
                fecha = datetime(año, mes, dia, hora, minuto)
                return fecha.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                logger.warning(f"Fecha inválida: {fecha_texto}")
                return None
        
        # Formato 2: DD de MES de YYYY
        match = re.match(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', fecha_texto, re.IGNORECASE)
        if match:
            dia = int(match.group(1))
            mes_texto = match.group(2).upper()
            año = int(match.group(3))
            
            if mes_texto in self.meses:
                mes = self.meses[mes_texto]
                try:
                    fecha = datetime(año, mes, dia, hora, minuto)
                    return fecha.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    logger.warning(f"Fecha inválida: {fecha_texto}")
                    return None
        
        logger.debug(f"No se pudo convertir fecha: {fecha_texto}")
        return None
    
    def _extraer_informacion_tecnica(self, texto: str) -> Dict[str, Optional[str]]:
        """Extrae información técnica de la licitación"""
        info = {
            'volumen_obra': None,
            'cantidad': None,
            'unidad_medida': None,
            'especificaciones_tecnicas': None,
            'lugar_eventos': None
        }
        
        # Volumen de obra/adquisición
        patrones_volumen = [
            r'[Vv]olumen\s+a?\s*(?:adquirir|contratar)[\s:]+([^\.\n]+)',
            r'[Vv]olumen\s+de\s+(?:la\s+)?(?:obra|licitaci[óo]n)[\s:]+([^\.\n]+)',
            r'[Cc]antidad\s+a?\s*(?:adquirir|contratar)[\s:]+([^\.\n]+)'
        ]
        
        for patron in patrones_volumen:
            match = re.search(patron, texto)
            if match:
                volumen = match.group(1).strip()
                if len(volumen) > 5 and len(volumen) < 500:
                    info['volumen_obra'] = volumen
                    
                    # Intentar extraer cantidad y unidad
                    match_cantidad = re.search(r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*([A-Za-z]+)', volumen)
                    if match_cantidad:
                        info['cantidad'] = match_cantidad.group(1)
                        info['unidad_medida'] = match_cantidad.group(2)
                break
        
        # Especificaciones técnicas
        if 'Los detalles se determinan en la convocatoria' in texto:
            info['especificaciones_tecnicas'] = 'Los detalles se determinan en la convocatoria'
        elif 'especificaciones' in texto.lower():
            match = re.search(r'[Ee]specificaciones[\s:]+([^\.\n]+)', texto)
            if match:
                info['especificaciones_tecnicas'] = match.group(1).strip()[:500]
        
        # Lugar de eventos
        patrones_lugar = [
            r'[Ll]os\s+eventos\s+se\s+(?:llevar[áa]n\s+a\s+cabo|realizar[áa]n)\s+en[\s:]+([^\.\n]+)',
            r'[Ll]ugar\s+de\s+(?:los\s+)?eventos?[\s:]+([^\.\n]+)',
            r'[Dd]omicilio\s+(?:de\s+la\s+)?(?:entidad|dependencia)[\s:]+([^\.\n]+)'
        ]
        
        for patron in patrones_lugar:
            match = re.search(patron, texto)
            if match:
                lugar = match.group(1).strip()
                if len(lugar) > 10 and len(lugar) < 300:
                    info['lugar_eventos'] = lugar
                break
        
        return info


def procesar_archivo_txt(archivo_txt: str) -> List[LicitacionMejorada]:
    """
    Procesa un archivo TXT del DOF y extrae todas las licitaciones
    
    Args:
        archivo_txt: Ruta al archivo TXT del DOF
    
    Returns:
        Lista de objetos LicitacionMejorada
    """
    import os
    
    licitaciones = []
    parser = ParserDOFMejorado()
    
    # Extraer información del ejemplar del nombre del archivo
    nombre_archivo = os.path.basename(archivo_txt)
    
    # Buscar fecha y edición en el nombre (formato: DDMMYYYY_EDICION.txt)
    match = re.search(r'(\d{2})(\d{2})(\d{4})_(MAT|VES)', nombre_archivo)
    
    if match:
        dia, mes, año, edicion = match.groups()
        fecha_ejemplar = f"{año}-{mes}-{dia}"
        edicion_ejemplar = edicion
    else:
        logger.warning(f"No se pudo extraer fecha del archivo: {nombre_archivo}")
        fecha_ejemplar = datetime.now().strftime('%Y-%m-%d')
        edicion_ejemplar = "DESCONOCIDA"
    
    try:
        with open(archivo_txt, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Buscar páginas con marcadores
        patron_pagina = re.compile(r"===== \[PÁGINA (\d+)\] =====")
        matches = list(patron_pagina.finditer(contenido))
        
        # Si hay marcadores de página, procesar por páginas
        if matches:
            for i, match in enumerate(matches):
                num_pagina = int(match.group(1))
                inicio = match.end()
                
                if i < len(matches) - 1:
                    fin = matches[i + 1].start()
                else:
                    fin = len(contenido)
                
                contenido_pagina = contenido[inicio:fin].strip()
                
                # Dividir por patrones de separación de licitaciones
                bloques = re.split(r'\(R\.\-\s*\d+\)', contenido_pagina)
                
                for bloque in bloques:
                    if len(bloque.strip()) < 100:
                        continue
                    
                    licitacion = parser.parsear_bloque(
                        bloque, num_pagina, fecha_ejemplar, 
                        edicion_ejemplar, nombre_archivo
                    )
                    
                    if licitacion:
                        licitaciones.append(licitacion)
        else:
            # Si no hay marcadores, procesar todo como una página
            licitacion = parser.parsear_bloque(
                contenido, 1, fecha_ejemplar, 
                edicion_ejemplar, nombre_archivo
            )
            
            if licitacion:
                licitaciones.append(licitacion)
        
        logger.info(f"Extraídas {len(licitaciones)} licitaciones de {archivo_txt}")
        
    except Exception as e:
        logger.error(f"Error procesando {archivo_txt}: {e}")
    
    return licitaciones


def guardar_json(licitaciones: List[LicitacionMejorada], archivo_salida: str):
    """
    Guarda las licitaciones en formato JSON con estadísticas
    
    Args:
        licitaciones: Lista de licitaciones extraídas
        archivo_salida: Ruta del archivo JSON de salida
    """
    # Calcular estadísticas
    total = len(licitaciones)
    por_estado = {}
    por_tipo = {}
    confianza_promedio = 0
    
    for lic in licitaciones:
        # Por estado
        estado = lic.entidad_federativa or "No especificado"
        por_estado[estado] = por_estado.get(estado, 0) + 1
        
        # Por tipo
        tipo = lic.tipo_contratacion
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        
        # Confianza promedio
        confianza_promedio += lic.confianza_extraccion
    
    if total > 0:
        confianza_promedio /= total
    
    # Preparar datos para JSON
    datos_json = {
        'archivo_procesado': archivo_salida,
        'fecha_procesamiento': datetime.now().isoformat(),
        'total_licitaciones': total,
        'estadisticas': {
            'por_entidad_federativa': por_estado,
            'por_tipo_contratacion': por_tipo,
            'confianza_promedio': round(confianza_promedio, 2)
        },
        'licitaciones': [asdict(lic) for lic in licitaciones]
    }
    
    # Guardar JSON
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        json.dump(datos_json, f, ensure_ascii=False, indent=2)
    
    logger.info(f"JSON guardado en: {archivo_salida}")
    logger.info(f"Total: {total} licitaciones")
    logger.info(f"Confianza promedio: {round(confianza_promedio, 2)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python estructura_dof_mejorado.py <archivo.txt>")
        print("Ejemplo: python estructura_dof_mejorado.py 01082025_MAT.txt")
        sys.exit(1)
    
    archivo_txt = sys.argv[1]
    
    # Procesar archivo
    licitaciones = procesar_archivo_txt(archivo_txt)
    
    if licitaciones:
        # Generar nombre de archivo de salida
        archivo_salida = archivo_txt.replace('.txt', '_mejorado.json')
        
        # Guardar JSON
        guardar_json(licitaciones, archivo_salida)
        
        print(f"\n✅ Procesamiento completado")
        print(f"📊 {len(licitaciones)} licitaciones extraídas")
        print(f"💾 Resultados guardados en: {archivo_salida}")
        
        # Mostrar muestra de resultados
        print("\n📋 Muestra de licitaciones extraídas:")
        for i, lic in enumerate(licitaciones[:3], 1):
            print(f"\n{i}. {lic.numero_licitacion or 'Sin número'}")
            print(f"   Dependencia: {lic.dependencia}")
            print(f"   Estado: {lic.entidad_federativa or 'No especificado'}")
            print(f"   Tipo: {lic.tipo_contratacion}")
            print(f"   Confianza: {lic.confianza_extraccion}")
    else:
        print("❌ No se encontraron licitaciones en el archivo")
