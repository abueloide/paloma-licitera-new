#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extractor de Licitaciones del Diario Oficial de la Federación (DOF)
====================================================================

Este script lee archivos TXT del DOF y extrae información estructurada 
de las licitaciones públicas siguiendo el formato exacto del DOF.

Proceso:
1. Lee el archivo TXT del DOF
2. Busca el índice para localizar las páginas de convocatorias
3. Extrae el contenido entre las páginas de inicio y fin
4. Parsea la información de cada licitación
5. Genera un archivo JSON estructurado
"""

import os
import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Licitacion:
    """Estructura de datos para una licitación"""
    # Campos principales
    numero_licitacion: str
    caracter_licitacion: str  # Nacional, Internacional, etc.
    objeto_licitacion: str
    descripcion: str
    dependencia: str
    subdependencia: str
    
    # Volumen y fechas
    volumen_adquirir: str
    fecha_publicacion: str
    fecha_junta_aclaraciones: str
    fecha_visita_instalaciones: str
    fecha_presentacion_apertura: str
    fecha_fallo: str
    
    # Información adicional
    reduccion_plazos: bool
    autoridad_reduccion: str
    lugar_eventos: str
    observaciones: str
    
    # Metadatos
    pagina: int
    referencia: str  # (R.- XXXXXX)
    raw_text: str  # Texto original para debugging
    
    # NUEVO: Información del ejemplar del DOF
    fecha_ejemplar: str  # Fecha del ejemplar del DOF (YYYY-MM-DD)
    edicion_ejemplar: str  # MAT o VES
    archivo_origen: str  # Nombre del archivo del que proviene


class DOFLicitacionesExtractor:
    """Extractor de licitaciones del DOF desde archivos TXT"""
    
    def __init__(self, archivo_txt: str):
        """
        Inicializa el extractor con un archivo TXT del DOF
        
        Args:
            archivo_txt: Ruta al archivo TXT del DOF
        """
        self.archivo_txt = archivo_txt
        self.contenido = ""
        self.paginas = {}
        self.licitaciones = []
        
        # Extraer información del ejemplar del nombre del archivo
        self.fecha_ejemplar, self.edicion_ejemplar = self._extraer_info_ejemplar()
        
        # Patrones regex actualizados para el formato real del DOF
        self.patron_pagina = re.compile(r"===== \[PÁGINA (\d+)\] =====")
        self.patron_indice_convocatorias = re.compile(
            r"CONVOCATORIAS PARA CONCURSOS DE ADQUISICIONES.*?[\.\s]+(\d+)",
            re.IGNORECASE | re.DOTALL
        )
        self.patron_indice_avisos = re.compile(
            r"AVISOS[\s\n]+.*?[\.\s]+(\d+)",
            re.IGNORECASE | re.DOTALL
        )
    
    def _extraer_info_ejemplar(self) -> Tuple[str, str]:
        """
        Extrae la fecha y edición del ejemplar del nombre del archivo.
        
        Returns:
            Tupla (fecha_ejemplar, edicion) en formato (YYYY-MM-DD, MAT/VES)
        """
        nombre_archivo = os.path.basename(self.archivo_txt)
        
        # Buscar patrón DDMMYYYY_EDICION en el nombre del archivo
        # Ejemplos: 01082025_MAT.txt, 31082025_VES.txt
        match = re.search(r'(\d{2})(\d{2})(\d{4})_(MAT|VES)', nombre_archivo)
        
        if match:
            dia, mes, año, edicion = match.groups()
            fecha_ejemplar = f"{año}-{mes}-{dia}"
            return fecha_ejemplar, edicion
        else:
            logger.warning(f"No se pudo extraer fecha del ejemplar del archivo: {nombre_archivo}")
            return "", ""
    
    def cargar_archivo(self) -> bool:
        """Carga el archivo TXT en memoria"""
        try:
            with open(self.archivo_txt, 'r', encoding='utf-8') as f:
                self.contenido = f.read()
            logger.info(f"Archivo cargado: {len(self.contenido)} caracteres")
            logger.info(f"Ejemplar del DOF: {self.fecha_ejemplar} - Edición: {self.edicion_ejemplar}")
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
            
            # Encontrar el final de esta página (inicio de la siguiente)
            if i < len(matches) - 1:
                fin = matches[i + 1].start()
            else:
                fin = len(self.contenido)
            
            self.paginas[num_pagina] = self.contenido[inicio:fin].strip()
        
        logger.info(f"Total de páginas extraídas: {len(self.paginas)}")
        if self.paginas:
            logger.info(f"Rango de páginas: {min(self.paginas.keys())} - {max(self.paginas.keys())}")
    
    def buscar_rango_convocatorias(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Busca en el índice el rango de páginas de las convocatorias
        
        Returns:
            Tupla (página_inicio, página_fin) o (None, None) si no se encuentra
        """
        # Buscar en las primeras páginas (típicamente el índice está en páginas 2-4)
        for num_pag in range(1, min(10, max(self.paginas.keys()) + 1)):
            if num_pag not in self.paginas:
                continue
                
            contenido_pagina = self.paginas[num_pag]
            
            # Buscar "CONVOCATORIAS PARA CONCURSOS..."
            match_conv = self.patron_indice_convocatorias.search(contenido_pagina)
            if match_conv:
                pagina_inicio = int(match_conv.group(1))
                logger.info(f"Encontrado inicio de convocatorias en página {pagina_inicio}")
                
                # Buscar "AVISOS" para determinar el fin
                match_avisos = self.patron_indice_avisos.search(contenido_pagina)
                if match_avisos:
                    pagina_fin = int(match_avisos.group(1)) - 1
                    logger.info(f"Encontrado fin de convocatorias en página {pagina_fin}")
                    return pagina_inicio, pagina_fin
                else:
                    # Si no hay avisos, buscar la última página
                    return pagina_inicio, max(self.paginas.keys())
        
        logger.warning("No se encontró el rango de convocatorias en el índice")
        return None, None
    
    def extraer_licitacion_de_bloque(self, texto: str, num_pagina: int) -> Optional[Licitacion]:
        """
        Extrae información de una licitación de un bloque de texto
        siguiendo el formato exacto del DOF
        
        Args:
            texto: Bloque de texto que contiene la información de la licitación
            num_pagina: Número de página donde se encuentra
            
        Returns:
            Objeto Licitacion o None si no se puede extraer
        """
        # Inicializar datos
        datos = {
            'numero_licitacion': '',
            'caracter_licitacion': '',
            'objeto_licitacion': '',
            'descripcion': '',
            'dependencia': '',
            'subdependencia': '',
            'volumen_adquirir': '',
            'fecha_publicacion': '',
            'fecha_junta_aclaraciones': '',
            'fecha_visita_instalaciones': '',
            'fecha_presentacion_apertura': '',
            'fecha_fallo': '',
            'reduccion_plazos': False,
            'autoridad_reduccion': '',
            'lugar_eventos': '',
            'observaciones': '',
            'pagina': num_pagina,
            'referencia': '',
            'raw_text': texto[:500],
            # NUEVO: Agregar información del ejemplar
            'fecha_ejemplar': self.fecha_ejemplar,
            'edicion_ejemplar': self.edicion_ejemplar,
            'archivo_origen': os.path.basename(self.archivo_txt)
        }
        
        # Patrones mejorados basados en el formato real
        patrones = {
            'numero': [
                r"(?:No\.?\s*de\s*[Ll]icitaci[óo]n|N[úu]mero\s*de\s*[Ll]icitaci[óo]n)[:\s\.]*([LA\-\d\-\w\-\d\w+\-[NIT]\-\d+\-\d{4})",
                r"([LA\-\d+\-\w+\-\d+\w+\-[NIT]\-\d+\-\d{4})"
            ],
            'caracter': [
                r"(?:Car[áa]cter(?:\s+de\s+la\s+[Ll]icitaci[óo]n)?)[:\s]*([\w\s]+)",
                r"(?:Licitaci[óo]n\s+P[úu]blica\s+)(Nacional|Internacional)(?:\s+Electr[óo]nica)?",
            ],
            'objeto': [
                r"(?:Objeto\s*de\s*la\s*[Ll]icitaci[óo]n)[:\s\.]*([\w\s,\.\-]+)",
                r"(?:Descripci[óo]n\s*de\s*la\s*[Ll]icitaci[óo]n)[:\s\.]*([\w\s,\.\-]+)",
                r"(?:Nombre\s*del\s*Procedimiento\s*de\s*contrataci[óo]n)[:\s\.]*([\w\s,\.\-]+)"
            ],
            'volumen': [
                r"(?:Volumen\s*a\s*[Aa]dquirir)[:\s\.]*([\w\s,\.\-]+)",
                r"(?:Cantidad|N[úu]mero\s*de\s*[Ss]ervicios)[:\s\.]*([\w\s,\.\-]+)"
            ],
            'fecha_publicacion': [
                r"(?:Fecha\s*de\s*[Pp]ublicaci[óo]n(?:\s*en\s*Compras?\s*M[Xx])?)[:\s\.]*([\d\/\w\s]+)",
                r"(?:Publicaci[óo]n\s*en\s*Compras?\s*M[Xx])[:\s\.]*([\d\/\w\s]+)"
            ],
            'fecha_junta': [
                r"(?:Junta\s*de\s*[Aa]claraciones?)[:\s\.]*([\d\/\w\s:]+)",
                r"(?:Fecha\s*y\s*hora\s*de\s*junta\s*de\s*aclaraciones)[:\s\.]*([\d\/\w\s:]+)"
            ],
            'fecha_visita': [
                r"(?:Visita\s*a\s*(?:las\s*)?[Ii]nstalaciones?)[:\s\.]*([\d\/\w\s:]+)",
            ],
            'fecha_presentacion': [
                r"(?:Presentaci[óo]n\s*y\s*[Aa]pertura\s*de\s*[Pp]roposiciones?)[:\s\.]*([\d\/\w\s:]+)",
                r"(?:Apertura\s*de\s*[Pp]roposiciones?)[:\s\.]*([\d\/\w\s:]+)"
            ],
            'fecha_fallo': [
                r"(?:Fallo|Emisi[óo]n\s*de\s*[Ff]allo|Fecha\s*(?:y\s*hora\s*)?de\s*[Ff]allo)[:\s\.]*([\d\/\w\s:]+)",
                r"(?:Notificaci[óo]n\s*del?\s*[Ff]allo)[:\s\.]*([\d\/\w\s:]+)"
            ],
            'referencia': [
                r"\(R\.\-\s*(\d+)\)"
            ]
        }
        
        # Extraer dependencia (buscar líneas en mayúsculas al inicio)
        lineas = texto.split('\n')
        for i, linea in enumerate(lineas[:10]):
            linea_limpia = linea.strip()
            # Buscar SECRETARÍA, INSTITUTO, COMISIÓN, etc.
            if re.match(r'^(SECRETAR[ÍI]A|INSTITUTO|COMISI[ÓO]N|ORGANO|HOSPITAL|UNIDAD|SERVICIOS|CONSEJERIA|ADMINISTRACION)', linea_limpia):
                datos['dependencia'] = linea_limpia
                # Buscar subdependencia en las siguientes líneas
                if i + 1 < len(lineas):
                    siguiente = lineas[i + 1].strip()
                    if re.match(r'^[A-Z][A-Z\s]+$', siguiente) and len(siguiente) > 10:
                        datos['subdependencia'] = siguiente
                break
        
        # Extraer campos usando patrones
        for campo, lista_patrones in patrones.items():
            for patron in lista_patrones:
                match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    valor = match.group(1).strip()
                    # Limpiar valor de saltos de línea múltiples
                    valor = re.sub(r'\n+', ' ', valor)
                    valor = re.sub(r'\s+', ' ', valor)
                    
                    if campo == 'numero':
                        datos['numero_licitacion'] = valor
                    elif campo == 'caracter':
                        datos['caracter_licitacion'] = valor
                    elif campo == 'objeto':
                        datos['objeto_licitacion'] = valor[:500]  # Limitar longitud
                    elif campo == 'volumen':
                        datos['volumen_adquirir'] = valor
                    elif campo == 'fecha_publicacion':
                        datos['fecha_publicacion'] = valor
                    elif campo == 'fecha_junta':
                        datos['fecha_junta_aclaraciones'] = valor
                    elif campo == 'fecha_visita':
                        datos['fecha_visita_instalaciones'] = valor
                    elif campo == 'fecha_presentacion':
                        datos['fecha_presentacion_apertura'] = valor
                    elif campo == 'fecha_fallo':
                        datos['fecha_fallo'] = valor
                    elif campo == 'referencia':
                        datos['referencia'] = f"(R.- {valor})"
                    break
        
        # Buscar información de reducción de plazos
        if re.search(r"reducci[óo]n\s+de\s+plazos", texto, re.IGNORECASE):
            datos['reduccion_plazos'] = True
            # Buscar quién autorizó
            match_autoridad = re.search(r"autorizada?\s+por\s+(?:el\s+|la\s+)?([^\n,\.]+)", texto, re.IGNORECASE)
            if match_autoridad:
                datos['autoridad_reduccion'] = match_autoridad.group(1).strip()
        
        # Verificar si tenemos información mínima válida
        if datos['numero_licitacion'] or (datos['objeto_licitacion'] and datos['dependencia']):
            return Licitacion(**datos)
        
        return None
    
    def procesar_paginas_convocatorias(self, pagina_inicio: int, pagina_fin: int):
        """
        Procesa las páginas de convocatorias y extrae las licitaciones
        
        Args:
            pagina_inicio: Primera página de convocatorias
            pagina_fin: Última página de convocatorias
        """
        logger.info(f"Procesando páginas {pagina_inicio} a {pagina_fin}")
        
        for num_pagina in range(pagina_inicio, pagina_fin + 1):
            if num_pagina not in self.paginas:
                logger.warning(f"Página {num_pagina} no encontrada")
                continue
            
            contenido_pagina = self.paginas[num_pagina]
            
            # Dividir por patrones comunes de separación
            # Las licitaciones suelen terminar con (R.- XXXXXX)
            bloques = re.split(r'\(R\.\-\s*\d+\)', contenido_pagina)
            
            # También dividir por encabezados de dependencias
            if len(bloques) == 1:
                # Intentar dividir por RESUMEN DE CONVOCATORIA
                bloques = re.split(r'RESUMEN DE CONVOCATORIA', contenido_pagina)
            
            for i, bloque in enumerate(bloques):
                if len(bloque.strip()) < 50:  # Ignorar bloques muy pequeños
                    continue
                
                # Si el bloque anterior terminó con (R.- XXXXX), agregarlo al principio de este bloque
                if i > 0 and re.search(r'\(R\.\-\s*\d+\)$', bloques[i-1]):
                    continue
                    
                licitacion = self.extraer_licitacion_de_bloque(bloque, num_pagina)
                if licitacion:
                    self.licitaciones.append(licitacion)
                    logger.debug(f"Licitación extraída: {licitacion.numero_licitacion}")
        
        logger.info(f"Total de licitaciones extraídas: {len(self.licitaciones)}")
    
    def guardar_json(self, archivo_salida: str):
        """
        Guarda las licitaciones extraídas en formato JSON
        
        Args:
            archivo_salida: Ruta del archivo JSON de salida
        """
        datos_json = {
            'archivo_origen': os.path.basename(self.archivo_txt),
            'fecha_ejemplar': self.fecha_ejemplar,
            'edicion_ejemplar': self.edicion_ejemplar,
            'fecha_extraccion': datetime.now().isoformat(),
            'total_licitaciones': len(self.licitaciones),
            'licitaciones': [asdict(lic) for lic in self.licitaciones]
        }
        
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Datos guardados en: {archivo_salida}")
        logger.info(f"Fecha del ejemplar DOF: {self.fecha_ejemplar} - Edición: {self.edicion_ejemplar}")
        
        # Generar resumen
        self.generar_resumen()
    
    def generar_resumen(self):
        """Genera un resumen de las licitaciones extraídas"""
        if not self.licitaciones:
            logger.warning("No hay licitaciones para generar resumen")
            return
        
        print("\n" + "="*80)
        print("RESUMEN DE LICITACIONES EXTRAÍDAS")
        print("="*80)
        print(f"📅 Ejemplar del DOF: {self.fecha_ejemplar} - Edición: {self.edicion_ejemplar}")
        
        # Agrupar por dependencia
        dependencias = {}
        for lic in self.licitaciones:
            dep = lic.dependencia or "SIN DEPENDENCIA"
            if dep not in dependencias:
                dependencias[dep] = []
            dependencias[dep].append(lic)
        
        print(f"\nTotal de licitaciones: {len(self.licitaciones)}")
        print(f"Total de dependencias: {len(dependencias)}")
        
        print("\nPor dependencia:")
        for dep, lics in sorted(dependencias.items()):
            print(f"  {dep}: {len(lics)} licitaciones")
        
        # Mostrar tipos de licitación
        tipos = {}
        for lic in self.licitaciones:
            tipo = lic.caracter_licitacion or "NO ESPECIFICADO"
            tipos[tipo] = tipos.get(tipo, 0) + 1
        
        print("\nPor tipo de licitación:")
        for tipo, cantidad in sorted(tipos.items()):
            print(f"  {tipo}: {cantidad}")
        
        print("\n" + "="*80)
    
    def procesar(self) -> bool:
        """
        Ejecuta el proceso completo de extracción
        
        Returns:
            True si el proceso fue exitoso, False en caso contrario
        """
        print(f"\n🔍 Procesando archivo: {self.archivo_txt}")
        print("-" * 50)
        
        # 1. Cargar archivo
        if not self.cargar_archivo():
            return False
        
        # 2. Extraer páginas
        self.extraer_paginas()
        if not self.paginas:
            logger.error("No se pudieron extraer páginas del archivo")
            return False
        
        # 3. Buscar rango de convocatorias
        pagina_inicio, pagina_fin = self.buscar_rango_convocatorias()
        if pagina_inicio is None:
            logger.error("No se pudo determinar el rango de páginas de convocatorias")
            return False
        
        # 4. Procesar páginas de convocatorias
        self.procesar_paginas_convocatorias(pagina_inicio, pagina_fin)
        
        # 5. Guardar resultados
        archivo_salida = self.archivo_txt.replace('.txt', '_licitaciones.json')
        self.guardar_json(archivo_salida)
        
        return True


def procesar_multiples_archivos(directorio: str = None):
    """
    Procesa múltiples archivos TXT del DOF en un directorio
    
    Args:
        directorio: Directorio con archivos TXT (por defecto el directorio actual)
    """
    if directorio is None:
        directorio = os.path.dirname(os.path.abspath(__file__))
    
    archivos_txt = [f for f in os.listdir(directorio) if f.endswith('.txt') and 'MAT' in f]
    
    if not archivos_txt:
        print(f"No se encontraron archivos TXT del DOF en {directorio}")
        return
    
    print(f"\n📁 Encontrados {len(archivos_txt)} archivos para procesar")
    print("="*80)
    
    resultados = []
    for archivo in sorted(archivos_txt):
        archivo_path = os.path.join(directorio, archivo)
        extractor = DOFLicitacionesExtractor(archivo_path)
        
        if extractor.procesar():
            resultados.append({
                'archivo': archivo,
                'licitaciones': len(extractor.licitaciones),
                'fecha_ejemplar': extractor.fecha_ejemplar,
                'edicion': extractor.edicion_ejemplar,
                'status': 'OK'
            })
        else:
            resultados.append({
                'archivo': archivo,
                'licitaciones': 0,
                'fecha_ejemplar': extractor.fecha_ejemplar,
                'edicion': extractor.edicion_ejemplar,
                'status': 'ERROR'
            })
    
    # Mostrar resumen final
    print("\n" + "="*80)
    print("RESUMEN FINAL DE PROCESAMIENTO")
    print("="*80)
    
    total_licitaciones = sum(r['licitaciones'] for r in resultados)
    archivos_ok = sum(1 for r in resultados if r['status'] == 'OK')
    
    print(f"\nArchivos procesados: {len(resultados)}")
    print(f"Archivos exitosos: {archivos_ok}")
    print(f"Total de licitaciones extraídas: {total_licitaciones}")
    
    print("\nDetalle por archivo:")
    for r in resultados:
        estado = "✅" if r['status'] == 'OK' else "❌"
        print(f"  {estado} {r['archivo']}: {r['licitaciones']} licitaciones - Ejemplar: {r['fecha_ejemplar']} {r['edicion']}")


def main():
    """Función principal"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python estructura_dof.py <archivo.txt>")
        print("  o: python estructura_dof.py --all")
        print("\nOpciones:")
        print("  <archivo.txt>  Procesar un archivo específico")
        print("  --all          Procesar todos los archivos TXT en el directorio actual")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        procesar_multiples_archivos()
    else:
        archivo_txt = sys.argv[1]
        
        if not os.path.exists(archivo_txt):
            print(f"Error: El archivo {archivo_txt} no existe")
            sys.exit(1)
        
        # Crear extractor y procesar
        extractor = DOFLicitacionesExtractor(archivo_txt)
        
        if extractor.procesar():
            print(f"\n✅ Proceso completado exitosamente")
            print(f"Total de licitaciones extraídas: {len(extractor.licitaciones)}")
            print(f"📅 Ejemplar del DOF: {extractor.fecha_ejemplar} - Edición: {extractor.edicion_ejemplar}")
            
            # Mostrar algunas licitaciones de ejemplo
            if extractor.licitaciones:
                print("\nEjemplos de licitaciones encontradas:")
                print("-" * 50)
                for i, lic in enumerate(extractor.licitaciones[:3], 1):
                    print(f"\n{i}. Licitación: {lic.numero_licitacion}")
                    print(f"   Carácter: {lic.caracter_licitacion}")
                    print(f"   Dependencia: {lic.dependencia}")
                    if lic.subdependencia:
                        print(f"   Subdependencia: {lic.subdependencia}")
                    print(f"   Objeto: {lic.objeto_licitacion[:100]}...")
                    print(f"   Página: {lic.pagina}")
                    print(f"   Fecha Ejemplar DOF: {lic.fecha_ejemplar}")
                    print(f"   Edición: {lic.edicion_ejemplar}")
                    if lic.referencia:
                        print(f"   Referencia: {lic.referencia}")
        else:
            print("\n❌ Error en el procesamiento")
            sys.exit(1)


if __name__ == "__main__":
    main()
