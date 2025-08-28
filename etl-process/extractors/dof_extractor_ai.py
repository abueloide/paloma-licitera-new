#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor DOF mejorado con Claude Haiku 3.5
============================================
Versión standalone que funciona independientemente
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import anthropic
except ImportError:
    logger.error("anthropic no instalado. Ejecuta: pip install anthropic")
    exit(1)

class DOFExtractorAI:
    """Extractor mejorado del DOF usando Claude Haiku"""
    
    def __init__(self):
        # Configurar API key desde .env
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key or api_key == 'your_api_key_here':
            raise ValueError(
                "ANTHROPIC_API_KEY no configurada en .env\n"
                "Crea un archivo .env en la raíz del proyecto con:\n"
                "ANTHROPIC_API_KEY=tu_api_key_aqui"
            )
            
        self.client = anthropic.Anthropic(api_key=api_key)
        self.logger = logger
        
        # Detectar rutas del proyecto
        script_dir = Path(__file__).parent
        # Subir hasta la raíz del proyecto (paloma-licitera-new)
        project_root = script_dir.parent.parent  # FIX: Solo 2 niveles arriba
        
        # Rutas de archivos
        self.raw_dir = project_root / "data" / "raw" / "dof"
        self.processed_dir = project_root / "data" / "processed" / "dof"
        
        # Crear directorios si no existen
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Directorio de archivos DOF: {self.raw_dir}")
        logger.info(f"Directorio de salida: {self.processed_dir}")
        
    def extraer_bloques_texto(self, archivo_txt: Path) -> List[str]:
        """
        Extrae bloques de texto de licitaciones del archivo DOF
        """
        try:
            with open(archivo_txt, 'r', encoding='utf-8') as f:
                contenido = f.read()
        except FileNotFoundError:
            self.logger.error(f"Archivo no encontrado: {archivo_txt}")
            return []
        except Exception as e:
            self.logger.error(f"Error leyendo archivo: {e}")
            return []
        
        # Buscar sección de convocatorias
        inicio = contenido.find("CONVOCATORIAS PARA CONCURSOS")
        fin = contenido.find("AVISOS", inicio) if inicio > 0 else -1
        
        if inicio < 0:
            self.logger.warning("No se encontró sección de convocatorias")
            return []
            
        seccion = contenido[inicio:fin] if fin > 0 else contenido[inicio:]
        
        # Dividir por referencias (R.- XXXXXX)
        bloques = re.split(r'\(R\.\-\s*\d+\)', seccion)
        
        # Filtrar bloques válidos
        bloques_validos = []
        for bloque in bloques:
            if len(bloque.strip()) > 100:  # Mínimo 100 caracteres
                bloques_validos.append(bloque.strip())
        
        self.logger.info(f"Encontrados {len(bloques_validos)} bloques de texto")
        return bloques_validos
    
    def procesar_con_ia(self, bloque: str) -> Optional[Dict]:
        """
        Procesa un bloque de texto con Claude Haiku para extraer campos
        """
        prompt = f"""Extrae la información de esta licitación del DOF y responde SOLO con un JSON válido:

TEXTO DE LA LICITACIÓN:
{bloque[:3000]}

FORMATO JSON REQUERIDO:
{{
  "numero_procedimiento": "extraer número exacto, ej: LA-04-812-004000998-N-59-2025",
  "titulo": "objeto o descripción principal",
  "descripcion": "descripción detallada o volumen",
  "entidad_compradora": "SECRETARÍA o institución principal",
  "unidad_compradora": "dirección o unidad específica",
  "tipo_procedimiento": "LICITACIÓN PÚBLICA o INVITACIÓN A CUANDO MENOS TRES o ADJUDICACIÓN DIRECTA",
  "tipo_contratacion": "SERVICIOS o ADQUISICIONES o OBRA PÚBLICA o ARRENDAMIENTO",
  "caracter": "NACIONAL o INTERNACIONAL o INTERNACIONAL BAJO TRATADOS",
  "entidad_federativa": "estado donde se realizará",
  "municipio": "municipio o alcaldía si se menciona",
  "fecha_publicacion": "fecha en formato YYYY-MM-DD",
  "fecha_apertura": "fecha y hora en formato YYYY-MM-DD HH:MM:SS",
  "fecha_fallo": "fecha y hora en formato YYYY-MM-DD HH:MM:SS",
  "fecha_junta_aclaraciones": "fecha y hora en formato YYYY-MM-DD HH:MM:SS"
}}

REGLAS:
- Si no encuentras un campo, usa null
- Normaliza fechas al formato ISO
- Para fechas del año 2025, asegúrate de poner 2025
- Si dice "14 de agosto de 2025" debe ser "2025-08-14"
- Si es "a plazos reducidos", inclúyelo en descripción

RESPONDE SOLO CON EL JSON."""

        try:
            message = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parsear respuesta
            respuesta_texto = message.content[0].text.strip()
            
            # Limpiar markdown si existe
            if respuesta_texto.startswith("```"):
                respuesta_texto = re.sub(r'^```json?\n?', '', respuesta_texto)
                respuesta_texto = re.sub(r'\n?```$', '', respuesta_texto)
            
            return json.loads(respuesta_texto)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parseando JSON: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error con API: {e}")
            return None
    
    def procesar_archivo(self, archivo_txt: Path) -> List[Dict]:
        """
        Procesa un archivo completo del DOF
        """
        self.logger.info(f"Procesando: {archivo_txt.name}")
        
        # Extraer bloques de texto
        bloques = self.extraer_bloques_texto(archivo_txt)
        if not bloques:
            return []
        
        # Procesar cada bloque
        licitaciones = []
        total_bloques = len(bloques)
        
        for i, bloque in enumerate(bloques, 1):
            if i % 5 == 1:  # Log cada 5 bloques
                self.logger.info(f"  Procesando bloque {i}/{total_bloques}")
            
            resultado = self.procesar_con_ia(bloque)
            if resultado:
                # Añadir metadatos
                resultado['fuente'] = 'DOF'
                resultado['estado'] = 'PUBLICADA'
                resultado['moneda'] = 'MXN'
                resultado['datos_originales'] = {
                    'archivo_origen': archivo_txt.name,
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'procesado_con_ia': True,
                    'modelo': 'claude-3-5-haiku-20241022'
                }
                licitaciones.append(resultado)
        
        self.logger.info(f"Extraídas {len(licitaciones)} licitaciones con IA")
        return licitaciones
    
    def extract(self) -> List[Dict]:
        """
        Método principal - extrae todas las licitaciones DOF
        """
        self.logger.info("=== Iniciando extracción DOF con IA ===")
        
        # Verificar que exista el directorio
        if not self.raw_dir.exists():
            self.logger.error(f"No existe el directorio: {self.raw_dir}")
            self.logger.error("Asegúrate de estar en la raíz del proyecto paloma-licitera-new")
            return []
        
        # Buscar archivos TXT del DOF
        archivos_txt = list(self.raw_dir.glob("*.txt"))
        
        if not archivos_txt:
            self.logger.warning(f"No se encontraron archivos .txt en {self.raw_dir}")
            self.logger.info("Archivos disponibles:")
            for archivo in self.raw_dir.iterdir():
                self.logger.info(f"  - {archivo.name}")
            return []
        
        # Filtrar archivos DOF (con MAT o VES en el nombre)
        archivos_dof = [f for f in archivos_txt 
                       if 'MAT' in f.name or 'VES' in f.name]
        
        if not archivos_dof:
            self.logger.warning("No se encontraron archivos DOF (con MAT o VES)")
            self.logger.info("Procesando todos los archivos .txt encontrados...")
            archivos_dof = archivos_txt
        
        self.logger.info(f"Encontrados {len(archivos_dof)} archivos para procesar:")
        for archivo in archivos_dof:
            self.logger.info(f"  - {archivo.name}")
        
        todas_licitaciones = []
        
        # Procesar cada archivo
        for archivo in archivos_dof:
            licitaciones = self.procesar_archivo(archivo)
            
            # Guardar resultado individual
            archivo_salida = self.processed_dir / archivo.name.replace('.txt', '_ai.json')
            with open(archivo_salida, 'w', encoding='utf-8') as f:
                json.dump({
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'archivo_origen': archivo.name,
                    'total_licitaciones': len(licitaciones),
                    'procesado_con_ia': True,
                    'modelo': 'claude-3-5-haiku-20241022',
                    'licitaciones': licitaciones
                }, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"  Guardado: {archivo_salida.name}")
            todas_licitaciones.extend(licitaciones)
        
        self.logger.info(f"=== Total extraído: {len(todas_licitaciones)} licitaciones ===")
        
        # Guardar resumen consolidado
        if todas_licitaciones:
            resumen_archivo = self.processed_dir / f"dof_consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(resumen_archivo, 'w', encoding='utf-8') as f:
                json.dump({
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'total_archivos_procesados': len(archivos_dof),
                    'total_licitaciones': len(todas_licitaciones),
                    'licitaciones': todas_licitaciones
                }, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Resumen guardado en: {resumen_archivo.name}")
        
        return todas_licitaciones


def main():
    """Función principal para pruebas"""
    print("\n🚀 Iniciando extractor DOF con IA...")
    print("="*50)
    
    # Verificar API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("\n❌ ERROR: ANTHROPIC_API_KEY no configurada")
        print("\nPasos para configurar:")
        print("1. Crea un archivo .env en la raíz del proyecto")
        print("2. Añade la siguiente línea:")
        print("   ANTHROPIC_API_KEY=tu_api_key_aqui")
        return
    
    try:
        extractor = DOFExtractorAI()
        licitaciones = extractor.extract()
        
        print(f"\n✅ Proceso completado")
        print(f"Total licitaciones extraídas: {len(licitaciones)}")
        
        if licitaciones:
            print("\n📋 Ejemplo de licitación extraída:")
            lic = licitaciones[0]
            print(f"  • Número: {lic.get('numero_procedimiento', 'N/A')}")
            print(f"  • Título: {lic.get('titulo', 'N/A')[:80]}...")
            print(f"  • Entidad: {lic.get('entidad_compradora', 'N/A')}")
            print(f"  • Fecha apertura: {lic.get('fecha_apertura', 'N/A')}")
            print(f"  • Fecha fallo: {lic.get('fecha_fallo', 'N/A')}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
