#!/usr/bin/env python3
"""
DOF Extractor - Cornerstone
Extractor del Diario Oficial de la Federación
"""

import os
import sys
import logging
import requests
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DOFExtractor:
    """Extractor de licitaciones del Diario Oficial de la Federación"""
    
    def __init__(self):
        self.base_url = "https://www.dof.gob.mx"
        self.data_dir = Path("data/raw/dof")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_dof_dates(self, start_date: str, end_date: str = None) -> List[str]:
        """Genera fechas de martes y jueves entre start_date y end_date"""
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        dates = []
        current = start
        
        while current <= end:
            # 1=Lunes, 2=Martes, 3=Miércoles, 4=Jueves, 5=Viernes, 6=Sábado, 0=Domingo
            if current.weekday() in [1, 3]:  # Martes y Jueves
                dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
            
        return dates
        
    def download_dof_date(self, date: str) -> bool:
        """Descarga el DOF de una fecha específica"""
        try:
            # Convertir fecha para URL del DOF
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            date_formatted = date_obj.strftime("%d/%m/%Y")
            
            # URL del DOF para esa fecha
            url = f"{self.base_url}/nota_detalle.php?codigo=5000000&fecha={date_formatted}"
            
            logger.info(f"Descargando DOF para {date}...")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Guardar contenido
            filename = f"dof_{date.replace('-', '_')}.txt"
            filepath = self.data_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(response.text)
                
            logger.info(f"✅ DOF guardado: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error descargando DOF {date}: {e}")
            return False
            
    def extract_licitaciones_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extrae licitaciones del texto del DOF"""
        licitaciones = []
        
        # Patrones comunes para licitaciones
        patterns = [
            r'LICITACIÓN.*?PÚBLICA.*?(?=LICITACIÓN|$)',
            r'INVITACIÓN.*?(?=INVITACIÓN|$)',
            r'ADJUDICACIÓN.*?(?=ADJUDICACIÓN|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                # Extraer información básica
                licitacion = {
                    'titulo': self._extract_titulo(match),
                    'descripcion': match[:500],  # Primeros 500 caracteres
                    'entidad_compradora': self._extract_entidad(match),
                    'tipo_procedimiento': self._extract_tipo(pattern),
                    'fuente': 'dof',
                    'url_original': '',
                    'datos_originales': {'texto_completo': match}
                }
                
                licitaciones.append(licitacion)
                
        return licitaciones
        
    def _extract_titulo(self, text: str) -> str:
        """Extrae el título de una licitación"""
        # Buscar líneas que parezcan títulos
        lines = text.split('\n')[:5]  # Primeras 5 líneas
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:
                return line
        return "Licitación DOF"
        
    def _extract_entidad(self, text: str) -> str:
        """Extrae la entidad compradora"""
        # Buscar patrones de instituciones
        patterns = [
            r'SECRETARÍA\s+DE\s+\w+',
            r'INSTITUTO\s+\w+',
            r'COMISIÓN\s+\w+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
                
        return "Entidad DOF"
        
    def _extract_tipo(self, pattern: str) -> str:
        """Determina el tipo de procedimiento basado en el patrón"""
        if 'LICITACIÓN' in pattern:
            return 'Licitación Pública'
        elif 'INVITACIÓN' in pattern:
            return 'Invitación'
        elif 'ADJUDICACIÓN' in pattern:
            return 'Adjudicación Directa'
        return 'Otro'
        
    def run_extraction(self, start_date: str = None, days_back: int = 30):
        """Ejecuta la extracción completa"""
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            
        logger.info(f"🚀 Iniciando extracción DOF desde {start_date}")
        
        # Generar fechas
        dates = self.generate_dof_dates(start_date)
        logger.info(f"📅 Fechas a procesar: {len(dates)}")
        
        downloaded = 0
        total_licitaciones = 0
        
        # Descargar archivos
        for date in dates:
            if self.download_dof_date(date):
                downloaded += 1
                
        logger.info(f"✅ Descarga completada: {downloaded}/{len(dates)} archivos")
        
        # Procesar archivos descargados
        for txt_file in self.data_dir.glob("dof_*.txt"):
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                licitaciones = self.extract_licitaciones_from_text(content)
                total_licitaciones += len(licitaciones)
                
                # Guardar JSON procesado
                json_file = txt_file.with_suffix('.json')
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(licitaciones, f, ensure_ascii=False, indent=2)
                    
                logger.info(f"📄 {txt_file.name}: {len(licitaciones)} licitaciones")
                
            except Exception as e:
                logger.error(f"❌ Error procesando {txt_file}: {e}")
                
        logger.info(f"🎯 Extracción completada: {total_licitaciones} licitaciones totales")
        return total_licitaciones

def main():
    """Función principal"""
    extractor = DOFExtractor()
    
    # Permitir parámetros de línea de comandos
    start_date = None
    days_back = 30
    
    if len(sys.argv) > 1:
        start_date = sys.argv[1]
    if len(sys.argv) > 2:
        days_back = int(sys.argv[2])
        
    extractor.run_extraction(start_date, days_back)

if __name__ == "__main__":
    main()
