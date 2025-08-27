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
        self.fecha_patterns = [
            r'(\d{1,2})\s+DE\s+([A-Z]+)\s+DE\s+(\d{4})\s+(\d{1,2}):(\d{2})\s+HORAS?',
            r'(\d{1,2})\s+DE\s+([A-Z]+)\s+DE\s+(\d{4})',
            r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})'
        ]
        
        self.meses = {
            'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
            'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
            'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
        }
        
        self.evento_patterns = {
            'visita': r'Visita\s+al\s+sitio[^\d]*(\d{1,2}\s+DE\s+[A-Z]+\s+DE\s+\d{4}[^\d]*\d{1,2}:\d{2}\s+HORAS?)',
            'apertura': r'(?:Presentación\s+y\s+)?[Aa]pertura\s+de\s+proposiciones[^\d]*(\d{1,2}\s+DE\s+[A-Z]+\s+DE\s+\d{4}[^\d]*\d{1,2}:\d{2}\s+HORAS?)',
            'junta_aclaraciones': r'Junta\s+de\s+Aclaraciones[^\d]*(\d{1,2}\s+DE\s+[A-Z]+\s+DE\s+\d{4}[^\d]*\d{1,2}:\d{2}\s+HORAS?)',
            'fallo': r'Emisión\s+del\s+Fallo[^\d]*(\d{1,2}\s+DE\s+[A-Z]+(?:\s+DE\s+\d{4})?)',
            'fallo_alt': r'Fallo[^\d]*(\d{1,2}\s+DE\s+[A-Z]+(?:\s+DE\s+\d{4})?)'
        }
    
    def extract_dates_from_text(self, text: str) -> Dict[str, str]:
        """Extraer fechas específicas del texto."""
        fechas_encontradas = {}
        
        # Buscar cada tipo de evento
        for evento, pattern in self.evento_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fecha_texto = match.group(1)
                fecha_normalizada = self.normalize_date(fecha_texto)
                if fecha_normalizada:
                    fechas_encontradas[evento] = fecha_normalizada
        
        return fechas_encontradas
    
    def normalize_date(self, fecha_texto: str) -> Optional[str]:
        """Normalizar fecha a formato ISO."""
        # Patrón: "12 DE AGOSTO DE 2025 11:00 HORAS"
        match = re.match(r'(\d{1,2})\s+DE\s+([A-Z]+)\s+(?:DE\s+)?(\d{4})(?:\s+(\d{1,2}):(\d{2}))?', fecha_texto.upper())
        if match:
            dia = int(match.group(1))
            mes_texto = match.group(2)
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
        """Extraer información de ubicación."""
        location_info = {
            'localidad': None,
            'municipio': None,
            'estado': None
        }
        
        # Patrones para ubicación
        localidad_pattern = r'(?:localidad de\s+|localidad\s+)([^,\.]+)'
        municipio_pattern = r'(?:municipio de\s+|municipio\s+)([^,\.]+)'
        estado_pattern = r'(?:estado de\s+|estado\s+)([^,\.]+)'
        
        localidad_match = re.search(localidad_pattern, text, re.IGNORECASE)
        if localidad_match:
            location_info['localidad'] = localidad_match.group(1).strip()
        
        municipio_match = re.search(municipio_pattern, text, re.IGNORECASE)
        if municipio_match:
            location_info['municipio'] = municipio_match.group(1).strip()
        
        estado_match = re.search(estado_pattern, text, re.IGNORECASE)
        if estado_match:
            location_info['estado'] = estado_match.group(1).strip()
        
        return location_info
    
    def clean_title(self, titulo: str, descripcion: str = "") -> str:
        """Limpiar y mejorar el título."""
        # Remover comillas innecesarias
        titulo = titulo.strip('"\'')
        
        # Si el título está muy largo, intentar extraer solo la parte principal
        if len(titulo) > 200:
            # Buscar punto, dos puntos o "EN EL" como separador
            for separator in ['. EN EL', '. EN LA', ': ', '.']:
                if separator in titulo:
                    titulo = titulo.split(separator)[0]
                    break
        
        return titulo.strip()
    
    def extract_technical_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extraer información técnica del texto."""
        info = {
            'volumen_obra': None,
            'especificaciones': None,
            'detalles_convocatoria': None
        }
        
        # Volumen de obra
        volumen_match = re.search(r'Volumen\s+de\s+la\s+Obra[:\s]*(.*?)(?:\.|Visita|Presentación|$)', text, re.IGNORECASE)
        if volumen_match:
            info['volumen_obra'] = volumen_match.group(1).strip()
        
        # Detalles en convocatoria
        if 'LOS DETALLES SE DETERMINAN EN LA CONVOCATORIA' in text.upper():
            info['detalles_convocatoria'] = True
        
        return info
    
    def parse_licitacion(self, licitacion_data: dict) -> dict:
        """Parser principal para una licitación."""
        titulo_original = licitacion_data.get('titulo', '')
        descripcion_original = licitacion_data.get('descripcion', '')
        
        # Combinar título y descripción para análisis completo
        texto_completo = f"{titulo_original} {descripcion_original}"
        
        resultado = {
            'id': licitacion_data.get('id'),
            'numero_procedimiento': licitacion_data.get('numero_procedimiento'),
            'titulo_original': titulo_original,
            'descripcion_original': descripcion_original,
            'titulo_limpio': self.clean_title(titulo_original, descripcion_original),
            'fechas_extraidas': self.extract_dates_from_text(texto_completo),
            'ubicacion': self.extract_location(texto_completo),
            'info_tecnica': self.extract_technical_info(texto_completo),
            'entidad_original': licitacion_data.get('entidad_compradora'),
        }
        
        return resultado

def main():
    """Función principal de pruebas."""
    print("🔍 Iniciando análisis de texto del DOF...\n")
    
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
        
        resultado = parser.parse_licitacion(sample)
        
        print(f"📝 TÍTULO ORIGINAL:")
        print(f"   {resultado['titulo_original'][:100]}...")
        
        print(f"\n🧹 TÍTULO LIMPIO:")
        print(f"   {resultado['titulo_limpio']}")
        
        print(f"\n📅 FECHAS EXTRAÍDAS:")
        if resultado['fechas_extraidas']:
            for evento, fecha in resultado['fechas_extraidas'].items():
                print(f"   {evento}: {fecha}")
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
        if any(v for v in info_tec.values() if v):
            for key, value in info_tec.items():
                if value:
                    print(f"   {key}: {value}")
        else:
            print("   ❌ No se encontró información técnica")
        
        print(f"\n📋 DESCRIPCIÓN ORIGINAL (primeros 200 chars):")
        print(f"   {resultado['descripcion_original'][:200]}...")
        
        print("\n")

if __name__ == "__main__":
    main()
