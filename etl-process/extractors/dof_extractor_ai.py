#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor DOF mejorado con Claude Haiku 3.5
============================================
Procesa archivos TXT del DOF usando IA para extraer TODAS las licitaciones
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple
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
        project_root = script_dir.parent.parent  # paloma-licitera-new
        
        # Rutas de archivos
        self.raw_dir = project_root / "data" / "raw" / "dof"
        self.processed_dir = project_root / "data" / "processed" / "dof"
        
        # Crear directorios si no existen
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Directorio de archivos DOF: {self.raw_dir}")
        logger.info(f"Directorio de salida: {self.processed_dir}")
    
    def encontrar_seccion_convocatorias(self, contenido: str) -> Tuple[int, int]:
        """
        Encuentra las páginas que contienen convocatorias en el archivo TXT
        Retorna (inicio, fin) de la sección relevante
        """
        lineas = contenido.split('\n')
        
        # Buscar en las primeras líneas el índice
        inicio_convocatorias = None
        fin_convocatorias = None
        
        # Buscar "CONVOCATORIAS PARA CONCURSOS" seguido de página
        patron_convocatorias = re.compile(
            r'CONVOCATORIAS\s+PARA\s+CONCURSOS.*?(\d+)',
            re.IGNORECASE | re.DOTALL
        )
        
        patron_avisos = re.compile(
            r'AVISOS\s+(?:JUDICIALES|GENERALES)?.*?(\d+)',
            re.IGNORECASE | re.DOTALL
        )
        
        # Buscar en las primeras 500 líneas (típicamente el índice está al inicio)
        texto_inicio = '\n'.join(lineas[:500])
        
        match_conv = patron_convocatorias.search(texto_inicio)
        if match_conv:
            try:
                inicio_convocatorias = int(match_conv.group(1))
                logger.info(f"Convocatorias inician en página {inicio_convocatorias}")
            except:
                pass
        
        match_avisos = patron_avisos.search(texto_inicio)
        if match_avisos:
            try:
                fin_convocatorias = int(match_avisos.group(1)) - 1
                logger.info(f"Convocatorias terminan en página {fin_convocatorias}")
            except:
                pass
        
        # Si no encontramos índice, buscar directamente en el contenido
        if inicio_convocatorias is None:
            inicio_idx = contenido.find("CONVOCATORIAS PARA CONCURSOS")
            if inicio_idx > 0:
                inicio_convocatorias = inicio_idx
            else:
                inicio_convocatorias = 0
        
        if fin_convocatorias is None:
            # Buscar donde empiezan los AVISOS
            fin_idx = contenido.find("AVISOS", inicio_convocatorias if inicio_convocatorias else 0)
            if fin_idx > 0:
                fin_convocatorias = fin_idx
            else:
                fin_convocatorias = len(contenido)
        
        return inicio_convocatorias, fin_convocatorias
    
    def extraer_seccion_relevante(self, contenido: str) -> str:
        """
        Extrae solo la sección que contiene las convocatorias
        """
        inicio, fin = self.encontrar_seccion_convocatorias(contenido)
        
        if isinstance(inicio, int) and isinstance(fin, int):
            if inicio < len(contenido) and fin <= len(contenido):
                # Si son índices de caracteres
                if inicio < 1000 and fin < 1000:
                    # Probablemente son números de página, buscar en el contenido
                    patron_pagina = re.compile(rf"PÁGINA\s+{inicio}")
                    match_inicio = patron_pagina.search(contenido)
                    if match_inicio:
                        inicio = match_inicio.start()
                    
                    patron_fin = re.compile(rf"PÁGINA\s+{fin}")
                    match_fin = patron_fin.search(contenido)
                    if match_fin:
                        fin = match_fin.start()
                
                return contenido[inicio:fin]
        
        # Si no pudimos encontrar la sección, buscar patrones directamente
        inicio_idx = contenido.find("CONVOCATORIAS PARA CONCURSOS")
        if inicio_idx < 0:
            inicio_idx = contenido.find("RESUMEN DE CONVOCATORIA")
            if inicio_idx < 0:
                inicio_idx = 0
        
        fin_idx = contenido.find("AVISOS", inicio_idx)
        if fin_idx < 0:
            fin_idx = len(contenido)
        
        return contenido[inicio_idx:fin_idx]
    
    def procesar_con_ia(self, texto: str, num_chunk: int = 1) -> List[Dict]:
        """
        Procesa un fragmento de texto con Claude Haiku para extraer TODAS las licitaciones
        """
        prompt = f"""Analiza este fragmento del Diario Oficial de la Federación y extrae TODAS las licitaciones que encuentres.

TEXTO A ANALIZAR:
{texto[:8000]}  # Claude puede manejar hasta ~100k tokens

INSTRUCCIONES CRÍTICAS:
1. Extrae CADA licitación como un objeto JSON separado
2. Busca patrones como:
   - "LICITACIÓN PÚBLICA NACIONAL"
   - "INVITACIÓN A CUANDO MENOS TRES"
   - "RESUMEN DE CONVOCATORIA"
   - Referencias como "(R.- XXXXX)"
3. Para cada licitación, extrae TODOS estos campos:

FORMATO JSON REQUERIDO para cada licitación:
{{
  "numero_procedimiento": "el código completo, ej: LA-006HHE001-E150-2025",
  "titulo": "objeto de la licitación",
  "descripcion": "descripción detallada",
  "entidad_compradora": "SECRETARÍA o institución",
  "unidad_compradora": "dirección o unidad específica",
  "tipo_procedimiento": "LICITACIÓN PÚBLICA o INVITACIÓN A CUANDO MENOS TRES",
  "tipo_contratacion": "SERVICIOS/ADQUISICIONES/OBRA PÚBLICA/ARRENDAMIENTO",
  "caracter": "NACIONAL/INTERNACIONAL/INTERNACIONAL BAJO TRATADOS",
  "entidad_federativa": "estado donde se realizará",
  "municipio": "municipio o alcaldía",
  "fecha_publicacion": "YYYY-MM-DD",
  "fecha_apertura": "YYYY-MM-DD HH:MM:SS",
  "fecha_fallo": "YYYY-MM-DD HH:MM:SS",
  "fecha_junta_aclaraciones": "YYYY-MM-DD HH:MM:SS",
  "fecha_visita": "YYYY-MM-DD HH:MM:SS si aplica",
  "referencia": "número de referencia (R.- XXXXX) si existe"
}}

REGLAS:
- Extrae TODAS las licitaciones que encuentres
- Si un campo no existe, usa null
- Las fechas deben ser del año 2025
- El numero_procedimiento es CRÍTICO - sin él no se puede guardar

Responde ÚNICAMENTE con un array JSON de licitaciones encontradas: [...]
NO incluyas texto adicional, solo el JSON."""

        try:
            message = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=4000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parsear respuesta
            respuesta_texto = message.content[0].text.strip()
            
            # Buscar el inicio del array JSON
            inicio_json = respuesta_texto.find('[')
            if inicio_json >= 0:
                respuesta_texto = respuesta_texto[inicio_json:]
            
            # Buscar el fin del array JSON
            fin_json = respuesta_texto.rfind(']')
            if fin_json > 0:
                respuesta_texto = respuesta_texto[:fin_json + 1]
            
            # Limpiar markdown si existe
            respuesta_texto = respuesta_texto.replace("```json", "").replace("```", "").strip()
            
            licitaciones = json.loads(respuesta_texto)
            
            if not isinstance(licitaciones, list):
                licitaciones = [licitaciones]
            
            self.logger.info(f"  Chunk {num_chunk}: {len(licitaciones)} licitaciones encontradas")
            return licitaciones
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parseando JSON en chunk {num_chunk}: {e}")
            self.logger.debug(f"Respuesta: {respuesta_texto[:500]}...")
            return []
        except Exception as e:
            self.logger.error(f"Error con API en chunk {num_chunk}: {e}")
            return []
    
    def procesar_archivo(self, archivo_txt: Path) -> List[Dict]:
        """
        Procesa un archivo completo del DOF
        """
        self.logger.info(f"Procesando: {archivo_txt.name}")
        
        try:
            with open(archivo_txt, 'r', encoding='utf-8') as f:
                contenido = f.read()
        except Exception as e:
            self.logger.error(f"Error leyendo archivo: {e}")
            return []
        
        # Extraer solo la sección de convocatorias
        seccion_convocatorias = self.extraer_seccion_relevante(contenido)
        
        if not seccion_convocatorias or len(seccion_convocatorias) < 100:
            self.logger.warning("No se encontró sección de convocatorias válida")
            return []
        
        self.logger.info(f"  Sección de convocatorias: {len(seccion_convocatorias)} caracteres")
        
        # Dividir en chunks si es muy grande (Claude maneja ~100k tokens, ~400k caracteres)
        max_chunk_size = 30000  # ~7500 tokens, dejando espacio para el prompt
        chunks = []
        
        if len(seccion_convocatorias) > max_chunk_size:
            # Dividir inteligentemente por referencias o párrafos
            partes = re.split(r'\(R\.\-\s*\d+\)', seccion_convocatorias)
            
            chunk_actual = ""
            for parte in partes:
                if len(chunk_actual) + len(parte) < max_chunk_size:
                    chunk_actual += parte
                else:
                    if chunk_actual:
                        chunks.append(chunk_actual)
                    chunk_actual = parte
            
            if chunk_actual:
                chunks.append(chunk_actual)
        else:
            chunks = [seccion_convocatorias]
        
        self.logger.info(f"  Dividido en {len(chunks)} chunks para procesar")
        
        # Procesar cada chunk
        todas_licitaciones = []
        for i, chunk in enumerate(chunks, 1):
            licitaciones = self.procesar_con_ia(chunk, i)
            
            # Añadir metadatos
            for lic in licitaciones:
                lic['fuente'] = 'DOF'
                lic['estado'] = 'PUBLICADA'
                lic['moneda'] = 'MXN'
                lic['datos_originales'] = {
                    'archivo_origen': archivo_txt.name,
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'procesado_con_ia': True,
                    'modelo': 'claude-3-5-haiku-20241022',
                    'chunk': f"{i}/{len(chunks)}"
                }
            
            todas_licitaciones.extend(licitaciones)
        
        # Filtrar licitaciones sin numero_procedimiento
        licitaciones_validas = [lic for lic in todas_licitaciones 
                               if lic.get('numero_procedimiento')]
        
        sin_numero = len(todas_licitaciones) - len(licitaciones_validas)
        if sin_numero > 0:
            self.logger.warning(f"  {sin_numero} licitaciones sin numero_procedimiento (descartadas)")
        
        self.logger.info(f"  Total extraído: {len(licitaciones_validas)} licitaciones válidas")
        return licitaciones_validas
    
    def extract(self) -> List[Dict]:
        """
        Método principal - extrae todas las licitaciones DOF
        """
        self.logger.info("=== Iniciando extracción DOF con IA ===")
        
        # Verificar que exista el directorio
        if not self.raw_dir.exists():
            self.logger.error(f"No existe el directorio: {self.raw_dir}")
            return []
        
        # Buscar archivos TXT del DOF
        archivos_txt = list(self.raw_dir.glob("*.txt"))
        
        if not archivos_txt:
            self.logger.warning(f"No se encontraron archivos .txt en {self.raw_dir}")
            return []
        
        # Filtrar archivos DOF (con MAT o VES en el nombre)
        archivos_dof = [f for f in archivos_txt 
                       if 'MAT' in f.name or 'VES' in f.name]
        
        if not archivos_dof:
            self.logger.info("Procesando todos los archivos .txt encontrados...")
            archivos_dof = archivos_txt
        
        self.logger.info(f"Encontrados {len(archivos_dof)} archivos para procesar:")
        for archivo in archivos_dof:
            self.logger.info(f"  - {archivo.name}")
        
        todas_licitaciones = []
        estadisticas = {
            'archivos_procesados': 0,
            'archivos_con_licitaciones': 0,
            'total_licitaciones': 0,
            'licitaciones_sin_numero': 0
        }
        
        # Procesar cada archivo
        for archivo in archivos_dof:
            licitaciones = self.procesar_archivo(archivo)
            estadisticas['archivos_procesados'] += 1
            
            if licitaciones:
                estadisticas['archivos_con_licitaciones'] += 1
                estadisticas['total_licitaciones'] += len(licitaciones)
                
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
                
                self.logger.info(f"  💾 Guardado: {archivo_salida.name}")
                todas_licitaciones.extend(licitaciones)
        
        # Mostrar estadísticas
        self.logger.info("=" * 50)
        self.logger.info("📊 ESTADÍSTICAS FINALES:")
        self.logger.info(f"  • Archivos procesados: {estadisticas['archivos_procesados']}")
        self.logger.info(f"  • Archivos con licitaciones: {estadisticas['archivos_con_licitaciones']}")
        self.logger.info(f"  • Total licitaciones extraídas: {estadisticas['total_licitaciones']}")
        
        # Guardar resumen consolidado
        if todas_licitaciones:
            resumen_archivo = self.processed_dir / f"dof_consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(resumen_archivo, 'w', encoding='utf-8') as f:
                json.dump({
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'estadisticas': estadisticas,
                    'total_licitaciones': len(todas_licitaciones),
                    'licitaciones': todas_licitaciones
                }, f, ensure_ascii=False, indent=2)
            self.logger.info(f"📁 Resumen guardado en: {resumen_archivo.name}")
        
        return todas_licitaciones


def main():
    """Función principal para pruebas"""
    print("\n🚀 Iniciando extractor DOF con IA...")
    print("="*50)
    
    # Verificar API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("\n❌ ERROR: ANTHROPIC_API_KEY no configurada")
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
            titulo = lic.get('titulo', 'N/A')
            if titulo and titulo != 'N/A':
                print(f"  • Título: {titulo[:80]}...")
            print(f"  • Entidad: {lic.get('entidad_compradora', 'N/A')}")
            print(f"  • Fecha apertura: {lic.get('fecha_apertura', 'N/A')}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
