#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extractor Mejorado de Licitaciones del Diario Oficial de la Federación (DOF)
=============================================================================

MEJORAS PRINCIPALES:
- Extrae correctamente el objeto de la licitación (sin mezclar otros campos)
- Parsea fechas a formato ISO (YYYY-MM-DD) con hora separada
- Evita duplicados al procesar bloques
- Extrae campos adicionales: lugar de eventos, autoridad firmante
- Mejor separación entre título y descripción

Actualización: 28/12/2024
"""

import os
import re
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class FechaEstructurada:
    """Estructura para fechas parseadas"""
    fecha: str  # YYYY-MM-DD
    hora: str   # HH:MM
    texto_original: str
    
    def to_dict(self) -> Dict:
        return {
            'fecha': self.fecha,
            'hora': self.hora,
            'texto_original': self.texto_original
        }


@dataclass 
class LicitacionMejorada:
    """Estructura mejorada de datos para una licitación"""
    # Identificación
    numero_licitacion: str
    titulo: str  # Objeto corto y limpio
    descripcion: str  # Si el objeto es muy largo, el resto va aquí
    
    # Caracterización
    caracter_licitacion: str  # Nacional, Internacional, etc.
    tipo_procedimiento: str  # Licitación Pública, Invitación, etc.
    
    # Entidades
    dependencia: str
    subdependencia: str
    unidad_responsable: str
    
    # Detalles de contratación
    objeto_contratacion: str  # Objeto completo original
    volumen_adquirir: str
    
    # Fechas estructuradas
    fecha_publicacion: Dict[str, Any]
    fecha_junta_aclaraciones: Dict[str, Any]
    fecha_visita_instalaciones: Dict[str, Any]
    fecha_presentacion_apertura: Dict[str, Any]
    fecha_fallo: Dict[str, Any]
    
    # Información adicional
    lugar_eventos: str
    autoridad_firmante: str
    reduccion_plazos: bool
    autoridad_reduccion: str
    observaciones: str
    
    # Metadatos
    pagina: int
    referencia: str  # (R.- XXXXXX)
    
    # Información del ejemplar
    fecha_ejemplar: str  # YYYY-MM-DD
    edicion_ejemplar: str  # MAT o VES
    archivo_origen: str
    
    # Control de calidad
    confianza_extraccion: float = 0.0  # 0-1, qué tan confiable es la extracción
    campos_faltantes: List[str] = field(default_factory=list)


class ExtractorDOFMejorado:
    """Extractor mejorado de licitaciones del DOF"""
    
    # Meses en español para parseo
    MESES_ES = {
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12',
        'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'ago': '08', 'agos': '08',
        'sep': '09', 'sept': '09', 'oct': '10', 'nov': '11', 'dic': '12'
    }
    
    def __init__(self, archivo_txt: str):
        self.archivo_txt = archivo_txt
        self.contenido = ""
        self.paginas = {}
        self.licitaciones = []
        self.bloques_procesados = set()  # Para evitar duplicados
        
        # Extraer información del ejemplar
        self.fecha_ejemplar, self.edicion_ejemplar = self._extraer_info_ejemplar()
        
        # Compilar patrones una sola vez
        self._compilar_patrones()
    
    def _compilar_patrones(self):
        """Compila todos los patrones regex para mejor rendimiento"""
        self.patron_pagina = re.compile(r"===== \[PÁGINA (\d+)\] =====")
        self.patron_indice_convocatorias = re.compile(
            r"CONVOCATORIAS PARA CONCURSOS DE ADQUISICIONES.*?[\.\s]+(\d+)",
            re.IGNORECASE | re.DOTALL
        )
        self.patron_indice_avisos = re.compile(
            r"AVISOS[\s\n]+.*?[\.\s]+(\d+)",
            re.IGNORECASE | re.DOTALL
        )
        
        # Patrones para detectar fin del objeto
        self.patron_fin_objeto = re.compile(
            r"(?:Volumen\s+a\s+[Aa]dquirir|Fecha\s+de\s+[Pp]ublicaci|Junta\s+de|Visita\s+a|Presentaci|Apertura|Fallo)",
            re.IGNORECASE
        )
        
        # Patrón para detectar firmas/autoridades
        self.patron_firma = re.compile(
            r"(?:SUFRAGIO\s+EFECTIVO|ATENTAMENTE|EL\s+(?:JEFE|DIRECTOR|TITULAR)|LA\s+(?:JEFA|DIRECTORA|TITULAR))",
            re.IGNORECASE
        )
    
    def _extraer_info_ejemplar(self) -> Tuple[str, str]:
        """Extrae fecha y edición del nombre del archivo"""
        nombre_archivo = os.path.basename(self.archivo_txt)
        match = re.search(r'(\d{2})(\d{2})(\d{4})_(MAT|VES)', nombre_archivo)
        
        if match:
            dia, mes, año, edicion = match.groups()
            fecha_ejemplar = f"{año}-{mes}-{dia}"
            return fecha_ejemplar, edicion
        
        return "", ""
    
    def _parsear_fecha(self, fecha_str: str) -> Dict[str, Any]:
        """
        Parsea una fecha del DOF a formato estructurado
        
        Formatos soportados:
        - DD/MM/YYYY, HH:MM horas
        - DD de mes de YYYY
        - HH:MM horas, DD Mes. YYYY  
        - DD-MM-YYYY HH:MM
        """
        if not fecha_str or fecha_str == "No aplica":
            return None
            
        fecha_str = fecha_str.strip()
        fecha = ""
        hora = ""
        
        try:
            # Formato: DD/MM/YYYY, HH:MM horas
            match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?:,?\s*(\d{1,2}):(\d{2}))?', fecha_str)
            if match:
                dia, mes, año = match.groups()[:3]
                fecha = f"{año}-{mes.zfill(2)}-{dia.zfill(2)}"
                if match.group(4):
                    hora = f"{match.group(4).zfill(2)}:{match.group(5)}"
                return {
                    'fecha': fecha,
                    'hora': hora,
                    'texto_original': fecha_str
                }
            
            # Formato: HH:MM horas, DD Mes. YYYY
            match = re.search(r'(\d{1,2}):(\d{2})\s*(?:horas?|hrs?)?,?\s*(\d{1,2})\s+(\w{3,})\s*\.?\s*(\d{4})', fecha_str, re.IGNORECASE)
            if match:
                hora_h, hora_m, dia, mes_str, año = match.groups()
                mes = self.MESES_ES.get(mes_str.lower(), '01')
                fecha = f"{año}-{mes}-{dia.zfill(2)}"
                hora = f"{hora_h.zfill(2)}:{hora_m}"
                return {
                    'fecha': fecha,
                    'hora': hora,
                    'texto_original': fecha_str
                }
            
            # Formato: DD de mes de YYYY
            match = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de(?:l?)?\s+(\d{4})', fecha_str, re.IGNORECASE)
            if match:
                dia, mes_str, año = match.groups()
                mes = self.MESES_ES.get(mes_str.lower(), '01')
                fecha = f"{año}-{mes}-{dia.zfill(2)}"
                
                # Buscar hora separada
                hora_match = re.search(r'(\d{1,2}):(\d{2})', fecha_str)
                if hora_match:
                    hora = f"{hora_match.group(1).zfill(2)}:{hora_match.group(2)}"
                
                return {
                    'fecha': fecha,
                    'hora': hora,
                    'texto_original': fecha_str
                }
            
            # Formato: DD Mes YYYY
            match = re.search(r'(\d{1,2})\s+(\w{3,})\.?\s+(\d{4})', fecha_str, re.IGNORECASE)
            if match:
                dia, mes_str, año = match.groups()
                mes = self.MESES_ES.get(mes_str.lower(), '01')
                fecha = f"{año}-{mes}-{dia.zfill(2)}"
                
                # Buscar hora
                hora_match = re.search(r'(\d{1,2}):(\d{2})', fecha_str)
                if hora_match:
                    hora = f"{hora_match.group(1).zfill(2)}:{hora_match.group(2)}"
                
                return {
                    'fecha': fecha,
                    'hora': hora,
                    'texto_original': fecha_str
                }
            
        except Exception as e:
            logger.debug(f"Error parseando fecha '{fecha_str}': {e}")
        
        # Si no se pudo parsear, devolver el texto original
        return {
            'fecha': '',
            'hora': '',
            'texto_original': fecha_str
        }
    
    def _extraer_objeto_limpio(self, texto: str) -> Tuple[str, str]:
        """
        Extrae el objeto de licitación limpio, separando título de descripción
        
        Returns:
            (titulo, descripcion)
        """
        # Buscar donde comienza el objeto
        match_objeto = re.search(
            r"(?:Objeto\s*de\s*la\s*[Ll]icitaci[óo]n|Descripci[óo]n)[:\s\.]*(.+)",
            texto,
            re.IGNORECASE | re.DOTALL
        )
        
        if not match_objeto:
            return "", ""
        
        objeto_completo = match_objeto.group(1)
        
        # Buscar donde termina el objeto (antes de Volumen, Fecha, etc.)
        fin_match = self.patron_fin_objeto.search(objeto_completo)
        if fin_match:
            objeto_completo = objeto_completo[:fin_match.start()]
        
        # Limpiar el objeto
        objeto_completo = re.sub(r'\s+', ' ', objeto_completo).strip()
        
        # Si el objeto es muy largo, dividir en título y descripción
        if len(objeto_completo) > 200:
            # Buscar primer punto o primera oración completa
            punto = objeto_completo.find('.')
            if punto > 0 and punto < 200:
                titulo = objeto_completo[:punto].strip()
                descripcion = objeto_completo[punto+1:].strip()
            else:
                titulo = objeto_completo[:200].strip()
                descripcion = objeto_completo[200:].strip()
        else:
            titulo = objeto_completo
            descripcion = ""
        
        # Limpiar comillas innecesarias
        titulo = titulo.strip('"').strip("'")
        
        return titulo, descripcion
    
    def _extraer_lugar_y_autoridad(self, texto: str) -> Tuple[str, str]:
        """Extrae el lugar de los eventos y la autoridad firmante"""
        lugar = ""
        autoridad = ""
        
        # Buscar patrón de firma (usualmente al final)
        match_firma = self.patron_firma.search(texto)
        if match_firma:
            # El texto antes de la firma suele tener el lugar
            texto_antes = texto[:match_firma.start()]
            
            # Buscar lugar (ciudad, estado)
            match_lugar = re.search(
                r"([A-Z][A-Z\s,\.]+(?:CIUDAD DE MEXICO|CD\.\s*MEX\.|MEXICO|[A-Z]+))",
                texto_antes[-200:],  # Buscar en los últimos 200 caracteres
                re.IGNORECASE
            )
            if match_lugar:
                lugar = match_lugar.group(1).strip()
                lugar = re.sub(r'\s+', ' ', lugar)
            
            # Buscar autoridad después de la firma
            texto_despues = texto[match_firma.end():]
            lineas = texto_despues.split('\n')
            for linea in lineas[:5]:  # Revisar las primeras 5 líneas
                if re.match(r'^(EL|LA)\s+', linea.strip()):
                    autoridad = linea.strip()
                    break
        
        return lugar, autoridad
    
    def _extraer_licitacion_mejorada(self, texto: str, num_pagina: int) -> Optional[LicitacionMejorada]:
        """Extrae una licitación con parseo mejorado"""
        
        # Generar hash del bloque para evitar duplicados
        bloque_hash = hash(texto[:100])
        if bloque_hash in self.bloques_procesados:
            return None
        self.bloques_procesados.add(bloque_hash)
        
        # Extraer objeto limpio (título y descripción)
        titulo, descripcion = self._extraer_objeto_limpio(texto)
        
        # Si no hay objeto, probablemente no es una licitación válida
        if not titulo:
            return None
        
        # Extraer campos básicos
        datos = {
            'numero_licitacion': self._extraer_campo(texto, 
                [r"No\.?\s*de\s*[Ll]icitaci[óo]n[:\s\.]*([LA\-\d\-\w\-\d\w+\-[NIT]\-\d+\-\d{4})",
                 r"([LA\-\d+\-\w+\-\d+\w+\-[NIT]\-\d+\-\d{4})",
                 r"([LI][A-Z]?\-\d+\-\d+)",
                 r"N[úu]mero[:\s]*([A-Z0-9\-]+)"]),
            
            'titulo': titulo,
            'descripcion': descripcion,
            'objeto_contratacion': titulo + (f". {descripcion}" if descripcion else ""),
            
            'caracter_licitacion': self._extraer_campo(texto,
                [r"Car[áa]cter[:\s]*([^\n]+)",
                 r"(Nacional|Internacional)(?:\s+Abierta)?(?:\s+Electr[óo]nica)?"]),
            
            'tipo_procedimiento': self._detectar_tipo_procedimiento(texto),
            
            'dependencia': self._extraer_dependencia(texto),
            'subdependencia': self._extraer_subdependencia(texto),
            'unidad_responsable': self._extraer_campo(texto,
                [r"Unidad\s+[Rr]esponsable[:\s]*([^\n]+)"]),
            
            'volumen_adquirir': self._extraer_campo(texto,
                [r"Volumen\s*a\s*[Aa]dquirir[:\s\.]*([^\n]+)",
                 r"Cantidad[:\s]*([^\n]+)"]),
            
            # Fechas parseadas
            'fecha_publicacion': self._parsear_fecha(
                self._extraer_campo(texto, 
                    [r"Fecha\s*de\s*[Pp]ublicaci[óo]n[:\s\.]*([^\n]+)",
                     r"Publicaci[óo]n\s*en\s*Compras?\s*M[Xx][:\s\.]*([^\n]+)"])),
            
            'fecha_junta_aclaraciones': self._parsear_fecha(
                self._extraer_campo(texto,
                    [r"Junta\s*de\s*[Aa]claraciones?[:\s\.]*([^\n]+)",
                     r"Fecha\s*y\s*hora\s*de\s*junta[:\s\.]*([^\n]+)"])),
            
            'fecha_visita_instalaciones': self._parsear_fecha(
                self._extraer_campo(texto,
                    [r"Visita\s*a\s*(?:las\s*)?[Ii]nstalaciones?[:\s\.]*([^\n]+)"])),
            
            'fecha_presentacion_apertura': self._parsear_fecha(
                self._extraer_campo(texto,
                    [r"Presentaci[óo]n\s*y\s*[Aa]pertura[:\s\.]*([^\n]+)",
                     r"Apertura\s*de\s*[Pp]roposiciones?[:\s\.]*([^\n]+)"])),
            
            'fecha_fallo': self._parsear_fecha(
                self._extraer_campo(texto,
                    [r"Fallo[:\s\.]*([^\n]+)",
                     r"Notificaci[óo]n\s*del?\s*[Ff]allo[:\s\.]*([^\n]+)",
                     r"Emisi[óo]n\s*de\s*[Ff]allo[:\s\.]*([^\n]+)"])),
            
            # Información adicional
            'lugar_eventos': '',
            'autoridad_firmante': '',
            'reduccion_plazos': bool(re.search(r"reducci[óo]n\s+de\s+plazos", texto, re.IGNORECASE)),
            'autoridad_reduccion': '',
            'observaciones': '',
            
            # Metadatos
            'pagina': num_pagina,
            'referencia': self._extraer_campo(texto, [r"\(R\.\-\s*(\d+)\)"]),
            
            # Información del ejemplar
            'fecha_ejemplar': self.fecha_ejemplar,
            'edicion_ejemplar': self.edicion_ejemplar,
            'archivo_origen': os.path.basename(self.archivo_txt),
            
            # Control de calidad
            'confianza_extraccion': 0.0,
            'campos_faltantes': []
        }
        
        # Extraer lugar y autoridad
        lugar, autoridad = self._extraer_lugar_y_autoridad(texto)
        datos['lugar_eventos'] = lugar
        datos['autoridad_firmante'] = autoridad
        
        # Si hay reducción de plazos, buscar autoridad
        if datos['reduccion_plazos']:
            match_autoridad = re.search(
                r"autorizada?\s+por\s+(?:el\s+|la\s+)?([^\n,\.]+)",
                texto,
                re.IGNORECASE
            )
            if match_autoridad:
                datos['autoridad_reduccion'] = match_autoridad.group(1).strip()
        
        # Calcular confianza y campos faltantes
        campos_importantes = ['numero_licitacion', 'titulo', 'dependencia', 
                             'fecha_publicacion', 'fecha_presentacion_apertura']
        campos_presentes = sum(1 for c in campos_importantes if datos.get(c))
        datos['confianza_extraccion'] = campos_presentes / len(campos_importantes)
        
        datos['campos_faltantes'] = [c for c in campos_importantes if not datos.get(c)]
        
        # Solo crear licitación si tiene información mínima
        if datos['confianza_extraccion'] >= 0.4:  # Al menos 2 de 5 campos importantes
            return LicitacionMejorada(**datos)
        
        return None
    
    def _extraer_campo(self, texto: str, patrones: List[str]) -> str:
        """Extrae un campo usando múltiples patrones"""
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                valor = match.group(1) if len(match.groups()) > 0 else match.group(0)
                return re.sub(r'\s+', ' ', valor).strip()
        return ""
    
    def _extraer_dependencia(self, texto: str) -> str:
        """Extrae la dependencia del texto"""
        lineas = texto.split('\n')
        for linea in lineas[:15]:  # Buscar en las primeras líneas
            linea_limpia = linea.strip()
            if re.match(r'^SECRETAR[ÍI]A\s+[A-Z\s]+$', linea_limpia):
                return linea_limpia
            elif re.match(r'^(INSTITUTO|COMISI[ÓO]N|ORGANO|HOSPITAL)\s+[A-Z\s]+$', linea_limpia):
                return linea_limpia
        return ""
    
    def _extraer_subdependencia(self, texto: str) -> str:
        """Extrae la subdependencia del texto"""
        lineas = texto.split('\n')
        encontro_dependencia = False
        
        for linea in lineas[:20]:
            linea_limpia = linea.strip()
            
            # Si ya encontramos la dependencia, la siguiente línea en mayúsculas puede ser subdependencia
            if encontro_dependencia:
                if re.match(r'^[A-Z][A-Z\s]+$', linea_limpia) and len(linea_limpia) > 10:
                    if not re.match(r'^(SECRETAR|INSTITUTO|COMISI)', linea_limpia):
                        return linea_limpia
            
            # Marcar que encontramos dependencia
            if re.match(r'^(SECRETAR|INSTITUTO|COMISI|ORGANO|HOSPITAL)', linea_limpia):
                encontro_dependencia = True
        
        return ""
    
    def _detectar_tipo_procedimiento(self, texto: str) -> str:
        """Detecta el tipo de procedimiento de la licitación"""
        texto_upper = texto.upper()
        
        if 'INVITACIÓN' in texto_upper or 'INVITACION' in texto_upper:
            if 'TRES' in texto_upper or '3' in texto_upper:
                return "INVITACION_3_PERSONAS"
            return "INVITACION"
        elif 'ADJUDICACIÓN DIRECTA' in texto_upper or 'ADJUDICACION DIRECTA' in texto_upper:
            return "ADJUDICACION_DIRECTA"
        else:
            return "LICITACION_PUBLICA"
    
    def cargar_archivo(self) -> bool:
        """Carga el archivo TXT en memoria"""
        try:
            with open(self.archivo_txt, 'r', encoding='utf-8') as f:
                self.contenido = f.read()
            logger.info(f"Archivo cargado: {len(self.contenido)} caracteres")
            return True
        except Exception as e:
            logger.error(f"Error al cargar archivo: {e}")
            return False
    
    def extraer_paginas(self):
        """Extrae y organiza el contenido por páginas"""
        matches = list(self.patron_pagina.finditer(self.contenido))
        
        for i, match in enumerate(matches):
            num_pagina = int(match.group(1))
            inicio = match.end()
            
            if i < len(matches) - 1:
                fin = matches[i + 1].start()
            else:
                fin = len(self.contenido)
            
            self.paginas[num_pagina] = self.contenido[inicio:fin].strip()
        
        logger.info(f"Total de páginas extraídas: {len(self.paginas)}")
    
    def buscar_rango_convocatorias(self) -> Tuple[Optional[int], Optional[int]]:
        """Busca el rango de páginas de convocatorias"""
        for num_pag in range(1, min(10, max(self.paginas.keys()) + 1)):
            if num_pag not in self.paginas:
                continue
                
            contenido_pagina = self.paginas[num_pag]
            
            match_conv = self.patron_indice_convocatorias.search(contenido_pagina)
            if match_conv:
                pagina_inicio = int(match_conv.group(1))
                
                match_avisos = self.patron_indice_avisos.search(contenido_pagina)
                if match_avisos:
                    pagina_fin = int(match_avisos.group(1)) - 1
                    return pagina_inicio, pagina_fin
                else:
                    return pagina_inicio, max(self.paginas.keys())
        
        return None, None
    
    def procesar_paginas_convocatorias(self, pagina_inicio: int, pagina_fin: int):
        """Procesa las páginas de convocatorias con extracción mejorada"""
        logger.info(f"Procesando páginas {pagina_inicio} a {pagina_fin}")
        self.bloques_procesados.clear()  # Limpiar para este procesamiento
        
        for num_pagina in range(pagina_inicio, pagina_fin + 1):
            if num_pagina not in self.paginas:
                continue
            
            contenido_pagina = self.paginas[num_pagina]
            
            # Mejorar la división de bloques
            # 1. Por referencias (R.- XXXXX)
            bloques = re.split(r'\(R\.\-\s*\d+\)', contenido_pagina)
            
            # 2. Si no hay suficientes bloques, dividir por RESUMEN DE CONVOCATORIA
            if len(bloques) <= 2:
                bloques = re.split(r'RESUMEN DE (?:LA\s+)?CONVOCATORIA', contenido_pagina)
            
            # 3. También considerar división por SECRETARÍA
            if len(bloques) <= 2:
                bloques = re.split(r'(?=^SECRETAR[ÍI]A\s+)', contenido_pagina, flags=re.MULTILINE)
            
            for bloque in bloques:
                if len(bloque.strip()) < 100:  # Ignorar bloques muy pequeños
                    continue
                
                licitacion = self._extraer_licitacion_mejorada(bloque, num_pagina)
                if licitacion:
                    self.licitaciones.append(licitacion)
                    logger.debug(f"Licitación extraída: {licitacion.numero_licitacion} - Confianza: {licitacion.confianza_extraccion:.2f}")
        
        logger.info(f"Total de licitaciones extraídas: {len(self.licitaciones)}")
        
        # Mostrar estadísticas de calidad
        confianza_promedio = sum(l.confianza_extraccion for l in self.licitaciones) / len(self.licitaciones) if self.licitaciones else 0
        logger.info(f"Confianza promedio de extracción: {confianza_promedio:.2%}")
    
    def guardar_json(self, archivo_salida: str):
        """Guarda las licitaciones en formato JSON mejorado"""
        # Convertir licitaciones a diccionarios
        licitaciones_dict = []
        for lic in self.licitaciones:
            lic_dict = asdict(lic)
            # No incluir campos de control en el JSON final
            lic_dict.pop('confianza_extraccion', None)
            lic_dict.pop('campos_faltantes', None)
            licitaciones_dict.append(lic_dict)
        
        datos_json = {
            'archivo_origen': os.path.basename(self.archivo_txt),
            'fecha_ejemplar': self.fecha_ejemplar,
            'edicion_ejemplar': self.edicion_ejemplar,
            'fecha_extraccion': datetime.now().isoformat(),
            'version_extractor': '2.0',
            'total_licitaciones': len(self.licitaciones),
            'estadisticas': {
                'confianza_promedio': sum(l.confianza_extraccion for l in self.licitaciones) / len(self.licitaciones) if self.licitaciones else 0,
                'licitaciones_alta_confianza': sum(1 for l in self.licitaciones if l.confianza_extraccion >= 0.8),
                'licitaciones_media_confianza': sum(1 for l in self.licitaciones if 0.5 <= l.confianza_extraccion < 0.8),
                'licitaciones_baja_confianza': sum(1 for l in self.licitaciones if l.confianza_extraccion < 0.5)
            },
            'licitaciones': licitaciones_dict
        }
        
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Datos guardados en: {archivo_salida}")
        self.generar_resumen()
    
    def generar_resumen(self):
        """Genera un resumen detallado de las licitaciones extraídas"""
        if not self.licitaciones:
            logger.warning("No hay licitaciones para generar resumen")
            return
        
        print("\n" + "="*80)
        print("RESUMEN DE EXTRACCIÓN MEJORADA")
        print("="*80)
        print(f"📅 Ejemplar: {self.fecha_ejemplar} - Edición: {self.edicion_ejemplar}")
        print(f"📊 Total de licitaciones: {len(self.licitaciones)}")
        
        # Estadísticas de calidad
        confianza_alta = sum(1 for l in self.licitaciones if l.confianza_extraccion >= 0.8)
        confianza_media = sum(1 for l in self.licitaciones if 0.5 <= l.confianza_extraccion < 0.8)
        confianza_baja = sum(1 for l in self.licitaciones if l.confianza_extraccion < 0.5)
        
        print(f"\n📈 Calidad de extracción:")
        print(f"  ✅ Alta confianza (≥80%): {confianza_alta}")
        print(f"  ⚠️  Media confianza (50-79%): {confianza_media}")
        print(f"  ❌ Baja confianza (<50%): {confianza_baja}")
        
        # Estadísticas de fechas parseadas
        fechas_parseadas = sum(1 for l in self.licitaciones 
                              if l.fecha_publicacion and l.fecha_publicacion.get('fecha'))
        print(f"\n📅 Fechas parseadas correctamente: {fechas_parseadas}/{len(self.licitaciones)}")
        
        # Por dependencia
        dependencias = {}
        for lic in self.licitaciones:
            dep = lic.dependencia or "SIN DEPENDENCIA"
            dependencias[dep] = dependencias.get(dep, 0) + 1
        
        print(f"\n🏛️ Por dependencia ({len(dependencias)} total):")
        for dep, count in sorted(dependencias.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {dep}: {count}")
        
        print("\n" + "="*80)
    
    def procesar(self) -> bool:
        """Ejecuta el proceso completo de extracción mejorada"""
        print(f"\n🔍 Procesando archivo: {self.archivo_txt}")
        print("-" * 50)
        
        if not self.cargar_archivo():
            return False
        
        self.extraer_paginas()
        if not self.paginas:
            logger.error("No se pudieron extraer páginas")
            return False
        
        pagina_inicio, pagina_fin = self.buscar_rango_convocatorias()
        if pagina_inicio is None:
            logger.error("No se encontró el rango de convocatorias")
            return False
        
        self.procesar_paginas_convocatorias(pagina_inicio, pagina_fin)
        
        archivo_salida = self.archivo_txt.replace('.txt', '_licitaciones_mejorado.json')
        self.guardar_json(archivo_salida)
        
        return True


def main():
    """Función principal para testing"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python estructura_dof_mejorado.py <archivo.txt>")
        sys.exit(1)
    
    archivo_txt = sys.argv[1]
    
    if not os.path.exists(archivo_txt):
        print(f"Error: El archivo {archivo_txt} no existe")
        sys.exit(1)
    
    extractor = ExtractorDOFMejorado(archivo_txt)
    
    if extractor.procesar():
        print(f"\n✅ Proceso completado exitosamente")
        print(f"Total de licitaciones: {len(extractor.licitaciones)}")
    else:
        print("\n❌ Error en el procesamiento")
        sys.exit(1)


if __name__ == "__main__":
    main()
