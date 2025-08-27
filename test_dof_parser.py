#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Parser para mejorar extracción de texto del DOF
Archivo de pruebas para analizar y estructurar mejor la información
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import psycopg2
import psycopg2.extras
import yaml

def load_config():
    """Cargar configuración de BD."""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config['database']
    except Exception as e:
        print(f"Error cargando config: {e}")
        return None

def get_dof_samples(limit=5):
    """Obtener muestras de licitaciones del DOF para análisis."""
    db_config = load_config()
    if not db_config:
        return []
    
    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['name'],
            user=db_config['user'],
            password=db_config['password'],
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id,
                numero_procedimiento,
                titulo,
                descripcion,
                entidad_compradora,
                datos_originales,
                fecha_publicacion,
                fecha_apertura
            FROM licitaciones 
            WHERE fuente = 'DOF' 
            ORDER BY fecha_captura DESC 
            LIMIT %s
        """, (limit,))
        
        samples = cursor.fetchall()
        conn.close()
        return samples
        
    except Exception as e:
        print(f"Error obteniendo muestras: {e}")
        return []

class DOFTextParser:
    """Parser mejorado para textos del DOF."""
    
    def __init__(self):
        # Meses en español
        self.meses = {
            'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
            'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
            'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
        }
        
        # Patrones mejorados para cubrir TODOS los formatos encontrados
        self.evento_patterns = {
            'fecha_publicacion_compranet': [
                r'Fecha\s+de\s+publicación\s+en\s+Compranet\s+(\d{1,2}/\d{1,2}/\d{4})',
                r'Fecha\s+de\s+publicación\s+en\s+CompraNet\s+(\d{1,2}/\d{1,2}/\d{4})',
                r'Fecha\s+de\s+publicación\s+en\s+Compras?\s+MX\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
                r'Fecha\s+de\s+publicación\s+en\s+Compras?\s+MX\s+(\d{1,2}/\w+/\d{4})',
            ],
            'junta_aclaraciones': [
                r'Junta\s+de\s+aclaraciones\s+(\d{1,2}/\d{1,2}/\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?)',
                r'Junta\s+de\s+aclaraciones\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?)',
                r'Junta\s+de\s+Aclaraciones\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})',
                r'Junta\s+de\s+aclaraciones\s+(\d{1,2}/\w+/\d{4}\s+\d{1,2}:\d{2})',
            ],
            'presentacion_apertura': [
                r'Presentación\s+y\s+apertura\s+de\s+proposiciones\s+(\d{1,2}/\d{1,2}/\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?)',
                r'Acto\s+de\s+presentación\s+y\s+apertura\s+de\s+proposiciones\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?)',
                r'Presentación\s+y\s+[Aa]pertura\s+de\s+[Pp]roposiciones\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})',
            ],
            'fallo': [
                r'Fallo\s+(\d{1,2}/\d{1,2}/\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?)',
                r'Fallo\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})',
                r'Emisión\s+del\s+Fallo\s+(\d{1,2}\s+DE\s+\w+(?:\s+DE\s+\d{4})?)',
            ],
            'visita_sitio': [
                r'Visita\s+al\s+sitio\s+(?:de\s+los\s+trabajos?\s+)?(\d{1,2}/\d{1,2}/\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?|No\s+habrá\s+visita)',
                r'Visita\s+al\s+sitio\s+(?:de\s+los\s+trabajos?\s+)?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4}(?:,?\s*a?\s*las?\s*\d{1,2}:\d{2})?)',
            ]
        }
    
    def extract_dates_from_text(self, text: str) -> Dict[str, str]:
        """Extraer fechas específicas del texto con múltiples patrones."""
        fechas_encontradas = {}
        
        # Buscar cada tipo de evento con múltiples patrones
        for evento, patterns in self.evento_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    fecha_texto = match.group(1)
                    if "No habrá" in fecha_texto:
                        fechas_encontradas[evento] = "No aplica"
                    else:
                        fecha_normalizada = self.normalize_date(fecha_texto)
                        if fecha_normalizada:
                            fechas_encontradas[evento] = fecha_normalizada
                            break  # Solo tomar la primera coincidencia válida
                        else:
                            fechas_encontradas[evento] = f"Original: {fecha_texto}"
        
        return fechas_encontradas
    
    def normalize_date(self, fecha_texto: str) -> Optional[str]:
        """Normalizar fecha a formato ISO con múltiples patrones."""
        fecha_texto = fecha_texto.strip()
        
        # Patrón 1: "20/08/2025, a las 10:00" o "20/08/2025 10:00"
        match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})(?:,?\s*(?:a?\s*las?\s*)?(\d{1,2}):(\d{2})(?:\s*horas?)?)?', fecha_texto, re.IGNORECASE)
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
        
        # Patrón 2: "12 de agosto de 2025, a las 10:00"
        match = re.match(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})(?:,?\s*(?:a?\s*las?\s*)?(\d{1,2}):(\d{2})(?:\s*horas?)?)?', fecha_texto, re.IGNORECASE)
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
        
        # Patrón 3: "14/agosto/2025 11:00 hrs"
        match = re.match(r'(\d{1,2})/(\w+)/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?:\s*hrs?\.?)?)?', fecha_texto, re.IGNORECASE)
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
        
        # Patrón 4: "12 DE AGOSTO DE 2025 11:00 HORAS"
        match = re.match(r'(\d{1,2})\s+DE\s+(\w+)\s+(?:DE\s+)?(\d{4})(?:\s+(\d{1,2}):(\d{2})(?:\s*HORAS?)?)?', fecha_texto.upper())
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
    
    def extract_location(self, text: str) -> Dict[str, Optional[str]]:
        """Extraer información de ubicación mejorada con manejo de errores."""
        location_info = {
            'localidad': None,
            'municipio': None,
            'estado': None,
            'ciudad': None
        }
        
        # Patrones para ubicación - corregidos con grupos de captura
        patterns = [
            (r'(?:localidad de\s+|localidad\s+)([^,\.]+)', 'localidad'),
            (r'(?:municipio de\s+|municipio\s+)([^,\.]+)', 'municipio'),
            (r'(?:estado de\s+|estado\s+)([^,\.]+)', 'estado'),
            (r'(SALTILLO),\s*(COAHUILA)', 'ciudad'),  # Caso específico
            (r'(CABO\s+SAN\s+LUCAS),\s*(B[^,]*)', 'ciudad'),  # Caso específico
            (r'([A-Z\s]{3,25}),\s*([A-Z\.]{2,15})', 'ciudad'),  # Patrón general CIUDAD, ESTADO
        ]
        
        for pattern, tipo in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if match.lastindex == 1:  # Solo un grupo
                        valor = match.group(1).strip()
                    elif match.lastindex >= 2:  # Múltiples grupos (ciudad, estado)
                        valor = f"{match.group(1).strip()}, {match.group(2).strip()}"
                    else:
                        continue
                    
                    if len(valor) > 2 and len(valor) < 100:  # Validar longitud razonable
                        location_info[tipo] = valor
            except (IndexError, AttributeError) as e:
                # Si hay error en el patrón, continuar con el siguiente
                print(f"Error en patrón de ubicación '{pattern}': {e}")
                continue
        
        return location_info
    
    def clean_title(self, titulo: str, descripcion: str = "") -> str:
        """Limpiar y mejorar el título."""
        if not titulo:
            return ""
            
        # Remover comillas innecesarias
        titulo = titulo.strip('"\'')
        
        # Si contiene "Volumen" como parte del título, separar
        if "Volumen" in titulo and len(titulo) > 100:
            # Cortar en "Volumen" para obtener solo el título principal
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
    
    def extract_technical_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extraer información técnica del texto con mejor validación."""
        info = {
            'volumen_obra': None,
            'cantidad': None,
            'unidad': None,
            'especificaciones': None,
            'detalles_convocatoria': None,
            'visita_requerida': None,
            'caracter_procedimiento': None
        }
        
        # Volumen de obra - mejorado
        volumen_patterns = [
            r'Volumen\s+a?\s*\w*\s*(.*?)(?:Los\s+detalles|Fecha\s+de|$)',
            r'Volumen\s+de\s+(?:la\s+)?(?:obra|licitación)\s+(.*?)(?:Fecha\s+de|$)',
        ]
        
        for pattern in volumen_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                volumen_texto = match.group(1).strip()
                if volumen_texto and len(volumen_texto) > 3:
                    info['volumen_obra'] = volumen_texto[:200]  # Limitar longitud
                    break
        
        # Cantidad específica (ej: "134 pieza") - mejorado para evitar fechas
        cantidad_match = re.search(r'(\d+)\s+(pieza|unidad|equipo|servicio|lote)(?:s)?\b', text, re.IGNORECASE)
        if cantidad_match:
            # Validar que no sea parte de una fecha
            numero = int(cantidad_match.group(1))
            if numero > 31 or numero < 2000:  # No es día ni año
                info['cantidad'] = cantidad_match.group(1)
                info['unidad'] = cantidad_match.group(2)
        
        # Detalles en convocatoria
        if re.search(r'(?:Los\s+)?[Dd]etalles\s+se\s+determinan\s+en\s+la\s+(?:propia\s+)?convocatoria', text, re.IGNORECASE):
            info['detalles_convocatoria'] = "Los detalles se determinan en la convocatoria"
        elif re.search(r'Se\s+(?:detalla|determinan?)\s+en\s+la\s+[Cc]onvocatoria', text, re.IGNORECASE):
            info['detalles_convocatoria'] = "Se detalla en la Convocatoria"
        
        # Visita al sitio
        if re.search(r'No\s+habrá\s+visita\s+al\s+sitio', text, re.IGNORECASE):
            info['visita_requerida'] = False
        elif re.search(r'Visita\s+al\s+sitio', text, re.IGNORECASE):
            info['visita_requerida'] = True
        
        # Carácter del procedimiento
        if re.search(r'carácter\s+Internacional', text, re.IGNORECASE):
            info['caracter_procedimiento'] = "Internacional"
        elif re.search(r'Nacional', text, re.IGNORECASE):
            info['caracter_procedimiento'] = "Nacional"
        
        return info
    
    def split_title_description(self, titulo: str) -> Tuple[str, str]:
        """Separar título de descripción cuando están concatenados."""
        if not titulo:
            return "", ""
        
        # Buscar puntos de corte comunes - ordenados por prioridad
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
    
    def parse_licitacion(self, licitacion_data: dict) -> dict:
        """Parser principal para una licitación."""
        titulo_original = licitacion_data.get('titulo', '') or ''
        descripcion_original = licitacion_data.get('descripcion') or ''
        
        # Combinar título y descripción para análisis completo
        texto_completo = f"{titulo_original} {descripcion_original}"
        
        # Separar título de descripción si están concatenados
        titulo_separado, descripcion_extraida = self.split_title_description(titulo_original)
        
        resultado = {
            'id': licitacion_data.get('id'),
            'numero_procedimiento': licitacion_data.get('numero_procedimiento'),
            'titulo_original': titulo_original,
            'descripcion_original': descripcion_original,
            'titulo_separado': titulo_separado,
            'descripcion_extraida': descripcion_extraida,
            'titulo_limpio': self.clean_title(titulo_original),
            'fechas_extraidas': self.extract_dates_from_text(texto_completo),
            'ubicacion': self.extract_location(texto_completo),
            'info_tecnica': self.extract_technical_info(texto_completo),
            'entidad_original': licitacion_data.get('entidad_compradora'),
        }
        
        return resultado

def main():
    """Función principal de pruebas."""
    print("🔍 Iniciando análisis de texto del DOF (versión corregida)...\n")
    
    # Obtener muestras
    samples = get_dof_samples(5)
    if not samples:
        print("❌ No se pudieron obtener muestras de la BD")
        return
    
    parser = DOFTextParser()
    
    print(f"📊 Analizando {len(samples)} muestras del DOF:\n")
    
    for i, sample in enumerate(samples, 1):
        print(f"=" * 80)
        print(f"MUESTRA {i} - ID: {sample['id']}")
        print(f"=" * 80)
        
        try:
            resultado = parser.parse_licitacion(sample)
            
            print(f"📝 TÍTULO ORIGINAL:")
            titulo_mostrar = resultado['titulo_original'][:150] + "..." if len(resultado['titulo_original']) > 150 else resultado['titulo_original']
            print(f"   {titulo_mostrar}")
            
            print(f"\n🧹 TÍTULO SEPARADO:")
            print(f"   {resultado['titulo_separado']}")
            
            if resultado['descripcion_extraida']:
                print(f"\n📋 DESCRIPCIÓN EXTRAÍDA DEL TÍTULO:")
                desc_mostrar = resultado['descripcion_extraida'][:200] + "..." if len(resultado['descripcion_extraida']) > 200 else resultado['descripcion_extraida']
                print(f"   {desc_mostrar}")
            
            print(f"\n📅 FECHAS EXTRAÍDAS:")
            if resultado['fechas_extraidas']:
                for evento, fecha in resultado['fechas_extraidas'].items():
                    evento_display = evento.replace('_', ' ').title()
                    print(f"   {evento_display}: {fecha}")
            else:
                print("   ❌ No se encontraron fechas estructuradas")
            
            print(f"\n📍 UBICACIÓN:")
            ubicacion = resultado['ubicacion']
            if any(ubicacion.values()):
                for key, value in ubicacion.items():
                    if value:
                        print(f"   {key}: {value}")
            else:
                print("   ❌ No se encontró información de ubicación")
            
            print(f"\n🔧 INFO TÉCNICA:")
            info_tec = resultado['info_tecnica']
            if any(v for v in info_tec.values() if v is not None):
                for key, value in info_tec.items():
                    if value is not None:
                        if key == 'visita_requerida':
                            print(f"   {key}: {'Sí' if value else 'No'}")
                        else:
                            valor_mostrar = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                            print(f"   {key}: {valor_mostrar}")
            else:
                print("   ❌ No se encontró información técnica")
            
            if resultado['descripcion_original']:
                print(f"\n📋 DESCRIPCIÓN ORIGINAL (primeros 200 chars):")
                desc_original = resultado['descripcion_original'][:200] + "..." if len(resultado['descripcion_original']) > 200 else resultado['descripcion_original']
                print(f"   {desc_original}")
            else:
                print(f"\n📋 DESCRIPCIÓN ORIGINAL: ❌ No disponible")
            
            print("\n")
            
        except Exception as e:
            print(f"❌ Error procesando muestra {i}: {e}")
            print("   Continuando con la siguiente muestra...\n")

if __name__ == "__main__":
    main()
