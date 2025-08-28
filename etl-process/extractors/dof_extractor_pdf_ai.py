#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor DOF con procesamiento de páginas específicas usando Claude Haiku
===========================================================================
Extrae solo las páginas con licitaciones para respetar límite de 100 páginas
"""

import os
import json
import base64
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

try:
    import PyPDF2
except ImportError:
    logger.error("PyPDF2 no instalado. Ejecuta: pip install PyPDF2")
    exit(1)

class DOFExtractorPDFAI:
    """Extractor DOF que procesa PDFs con límite de páginas"""
    
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
        
        logger.info(f"Directorio de PDFs DOF: {self.raw_dir}")
        logger.info(f"Directorio de salida: {self.processed_dir}")
    
    def encontrar_paginas_licitaciones(self, pdf_path: Path) -> Tuple[int, int]:
        """
        Encuentra el rango de páginas que contienen licitaciones
        Busca desde "CONVOCATORIAS" hasta "AVISOS"
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                self.logger.info(f"  PDF tiene {total_pages} páginas totales")
                
                inicio_pagina = None
                fin_pagina = None
                
                # Buscar página de inicio (CONVOCATORIAS)
                for i in range(min(100, total_pages)):  # Buscar en primeras 100 páginas
                    page = pdf_reader.pages[i]
                    text = page.extract_text().upper()
                    
                    if "CONVOCATORIAS PARA CONCURSOS" in text or "CONVOCATORIAS Y AVISOS" in text:
                        inicio_pagina = i
                        self.logger.info(f"  ✓ Sección de convocatorias encontrada en página {i+1}")
                        break
                
                if inicio_pagina is None:
                    self.logger.warning("  ⚠️ No se encontró sección de convocatorias")
                    # Intentar con las primeras 50 páginas como fallback
                    inicio_pagina = 0
                    fin_pagina = min(50, total_pages)
                else:
                    # Buscar página final (AVISOS o final del documento)
                    for i in range(inicio_pagina + 1, min(inicio_pagina + 100, total_pages)):
                        page = pdf_reader.pages[i]
                        text = page.extract_text().upper()
                        
                        if "AVISOS JUDICIALES" in text or "AVISOS GENERALES" in text:
                            fin_pagina = i
                            self.logger.info(f"  ✓ Fin de convocatorias en página {i+1}")
                            break
                    
                    if fin_pagina is None:
                        # Si no encontramos AVISOS, tomar hasta 80 páginas después
                        fin_pagina = min(inicio_pagina + 80, total_pages)
                
                return inicio_pagina, fin_pagina
                
        except Exception as e:
            self.logger.error(f"Error analizando PDF: {e}")
            # Por defecto, tomar primeras 50 páginas
            return 0, 50
    
    def extraer_paginas_pdf(self, pdf_path: Path, inicio: int, fin: int) -> bytes:
        """
        Extrae un rango de páginas del PDF y retorna como bytes
        """
        try:
            with open(pdf_path, 'rb') as input_file:
                pdf_reader = PyPDF2.PdfReader(input_file)
                pdf_writer = PyPDF2.PdfWriter()
                
                # Añadir páginas al writer
                for i in range(inicio, min(fin, len(pdf_reader.pages))):
                    pdf_writer.add_page(pdf_reader.pages[i])
                
                # Escribir a bytes
                import io
                output_buffer = io.BytesIO()
                pdf_writer.write(output_buffer)
                pdf_bytes = output_buffer.getvalue()
                
                self.logger.info(f"  📄 Extrayendo páginas {inicio+1} a {fin} ({fin-inicio} páginas)")
                return pdf_bytes
                
        except Exception as e:
            self.logger.error(f"Error extrayendo páginas: {e}")
            return None
    
    def procesar_pdf_con_ia(self, pdf_path: Path) -> List[Dict]:
        """
        Procesa solo las páginas relevantes del PDF con Claude Haiku
        """
        self.logger.info(f"Procesando PDF: {pdf_path.name}")
        
        # Encontrar páginas con licitaciones
        inicio, fin = self.encontrar_paginas_licitaciones(pdf_path)
        
        # Extraer solo esas páginas
        pdf_bytes = self.extraer_paginas_pdf(pdf_path, inicio, fin)
        if not pdf_bytes:
            return []
        
        # Codificar a base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        size_mb = len(pdf_bytes) / (1024 * 1024)
        self.logger.info(f"  Tamaño del segmento: {size_mb:.2f} MB")
        
        # Prompt optimizado
        prompt = """Analiza este fragmento del Diario Oficial que contiene CONVOCATORIAS DE LICITACIONES.

INSTRUCCIONES CRÍTICAS:
1. Extrae TODAS las licitaciones que encuentres
2. El numero_procedimiento es OBLIGATORIO - búscalo en formatos como:
   - LA-006HHE001-E150-2025
   - IO-020VST001-E114-2025  
   - LPN-006000999-E46-2025
   - LP-INE-XXX/2025
3. Si no encuentras el número, NO incluyas esa licitación

Para CADA licitación, extrae TODOS estos campos:

{
  "numero_procedimiento": "OBLIGATORIO - el código completo",
  "titulo": "objeto de la licitación",
  "descripcion": "descripción detallada",
  "entidad_compradora": "SECRETARÍA o institución",
  "unidad_compradora": "dirección o área",
  "tipo_procedimiento": "LICITACIÓN PÚBLICA NACIONAL/INTERNACIONAL o INVITACIÓN A CUANDO MENOS TRES",
  "tipo_contratacion": "ADQUISICIONES/SERVICIOS/OBRA PÚBLICA/ARRENDAMIENTO",
  "caracter": "NACIONAL/INTERNACIONAL/INTERNACIONAL BAJO TRATADOS",
  "entidad_federativa": "estado",
  "municipio": "municipio si aplica",
  "fecha_publicacion": "YYYY-MM-DD",
  "fecha_apertura": "YYYY-MM-DD HH:MM:SS",
  "fecha_fallo": "YYYY-MM-DD HH:MM:SS",
  "fecha_junta_aclaraciones": "YYYY-MM-DD HH:MM:SS",
  "fecha_visita_lugar": "YYYY-MM-DD HH:MM:SS si aplica",
  "costo_bases": "número o 0 si es sin costo",
  "lugar_obtener_bases": "dónde obtener bases"
}

IMPORTANTE:
- Solo incluye licitaciones CON numero_procedimiento
- Las fechas son del año 2025
- Responde SOLO con el JSON array: [...]
- NO incluyas texto adicional antes o después del JSON"""

        try:
            # Llamada a Claude
            message = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=8000,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
            
            # Parsear respuesta
            respuesta_texto = message.content[0].text.strip()
            
            # Buscar el JSON en la respuesta
            # A veces Claude responde con texto antes del JSON
            inicio_json = respuesta_texto.find('[')
            if inicio_json > 0:
                respuesta_texto = respuesta_texto[inicio_json:]
            
            # Limpiar markdown
            respuesta_texto = respuesta_texto.replace("```json", "").replace("```", "").strip()
            
            # Parsear JSON
            licitaciones = json.loads(respuesta_texto)
            
            if isinstance(licitaciones, dict):
                licitaciones = [licitaciones]
            
            # Añadir metadatos
            for lic in licitaciones:
                lic['fuente'] = 'DOF'
                lic['estado'] = 'PUBLICADA'
                lic['moneda'] = 'MXN'
                lic['datos_originales'] = {
                    'archivo_origen': pdf_path.name,
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'procesado_con_ia': True,
                    'modelo': 'claude-3-5-haiku-20241022',
                    'procesamiento': 'PDF_PARCIAL',
                    'paginas_procesadas': f"{inicio+1}-{fin}"
                }
            
            # Filtrar sin numero_procedimiento
            licitaciones_validas = [lic for lic in licitaciones if lic.get('numero_procedimiento')]
            
            self.logger.info(f"  ✅ Extraídas {len(licitaciones_validas)} licitaciones válidas")
            return licitaciones_validas
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parseando JSON: {e}")
            self.logger.debug(f"Respuesta: {respuesta_texto[:500]}...")
            return []
        except Exception as e:
            self.logger.error(f"Error con API: {e}")
            return []
    
    def extract(self) -> List[Dict]:
        """
        Método principal - extrae todas las licitaciones de PDFs DOF
        """
        self.logger.info("=== Iniciando extracción DOF desde PDFs con IA ===")
        
        # Buscar archivos PDF
        archivos_pdf = list(self.raw_dir.glob("*.pdf"))
        
        if not archivos_pdf:
            self.logger.warning(f"No se encontraron archivos PDF en {self.raw_dir}")
            return []
        
        # Filtrar archivos DOF
        archivos_dof = [f for f in archivos_pdf 
                       if 'MAT' in f.name or 'VES' in f.name]
        
        if not archivos_dof:
            archivos_dof = archivos_pdf
        
        self.logger.info(f"📄 Encontrados {len(archivos_dof)} PDFs para procesar")
        
        todas_licitaciones = []
        estadisticas = {
            'pdfs_procesados': 0,
            'pdfs_con_licitaciones': 0,
            'total_licitaciones': 0
        }
        
        # Procesar cada PDF
        for archivo in archivos_dof:
            licitaciones = self.procesar_pdf_con_ia(archivo)
            estadisticas['pdfs_procesados'] += 1
            
            if licitaciones:
                estadisticas['pdfs_con_licitaciones'] += 1
                estadisticas['total_licitaciones'] += len(licitaciones)
                
                # Guardar resultado individual
                archivo_salida = self.processed_dir / archivo.name.replace('.pdf', '_pdf_ai.json')
                with open(archivo_salida, 'w', encoding='utf-8') as f:
                    json.dump({
                        'fecha_procesamiento': datetime.now().isoformat(),
                        'archivo_origen': archivo.name,
                        'total_licitaciones': len(licitaciones),
                        'procesado_con_ia': True,
                        'modelo': 'claude-3-5-haiku-20241022',
                        'metodo': 'PDF_PARCIAL',
                        'licitaciones': licitaciones
                    }, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"  💾 Guardado: {archivo_salida.name}")
                todas_licitaciones.extend(licitaciones)
        
        # Estadísticas finales
        self.logger.info("=" * 50)
        self.logger.info("📊 ESTADÍSTICAS FINALES:")
        self.logger.info(f"  • PDFs procesados: {estadisticas['pdfs_procesados']}")
        self.logger.info(f"  • PDFs con licitaciones: {estadisticas['pdfs_con_licitaciones']}")
        self.logger.info(f"  • Total licitaciones extraídas: {estadisticas['total_licitaciones']}")
        
        # Guardar consolidado
        if todas_licitaciones:
            resumen_archivo = self.processed_dir / f"dof_pdf_consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(resumen_archivo, 'w', encoding='utf-8') as f:
                json.dump({
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'estadisticas': estadisticas,
                    'licitaciones': todas_licitaciones
                }, f, ensure_ascii=False, indent=2)
            self.logger.info(f"📁 Resumen consolidado: {resumen_archivo.name}")
        
        return todas_licitaciones


def main():
    """Función principal para pruebas"""
    print("\n🚀 Iniciando extractor DOF desde PDFs con IA...")
    print("=" * 60)
    
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("\n❌ ERROR: ANTHROPIC_API_KEY no configurada")
        return
    
    try:
        extractor = DOFExtractorPDFAI()
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
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
