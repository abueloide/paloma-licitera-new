#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor DOF con procesamiento directo de PDF usando Claude Haiku
===================================================================
Procesa PDFs completos sin conversión a TXT para mejor precisión
"""

import os
import json
import base64
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

class DOFExtractorPDFAI:
    """Extractor DOF que procesa PDFs directamente con Claude"""
    
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
    
    def procesar_pdf_con_ia(self, pdf_path: Path) -> List[Dict]:
        """
        Procesa un PDF completo con Claude Haiku
        """
        self.logger.info(f"Procesando PDF: {pdf_path.name}")
        
        # Leer y codificar PDF
        try:
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Error leyendo PDF {pdf_path}: {e}")
            return []
        
        # Tamaño del PDF
        size_mb = len(pdf_content) / (1024 * 1024)
        self.logger.info(f"  Tamaño del PDF: {size_mb:.2f} MB")
        
        # Prompt optimizado para extracción completa
        prompt = """Analiza este PDF del Diario Oficial de la Federación y extrae TODAS las licitaciones públicas.

INSTRUCCIONES CRÍTICAS:
1. Busca la sección "CONVOCATORIAS PARA CONCURSOS DE ADQUISICIONES, ARRENDAMIENTOS, OBRAS Y SERVICIOS DEL SECTOR PÚBLICO"
2. Extrae CADA licitación como un objeto JSON separado
3. El numero_procedimiento es OBLIGATORIO - búscalo en formatos como:
   - LA-006HHE001-E150-2025
   - IO-020VST001-E114-2025
   - LPN-006000999-E46-2025
   - Cualquier código que empiece con LA-, IO-, LPN-, LP-, etc.

Para CADA licitación encontrada, extrae:

{
  "numero_procedimiento": "OBLIGATORIO - el código de la licitación",
  "titulo": "objeto de la licitación o descripción principal",
  "descripcion": "descripción detallada, volumen a adquirir, especificaciones",
  "entidad_compradora": "SECRETARÍA o institución convocante",
  "unidad_compradora": "dirección o área específica",
  "tipo_procedimiento": "LICITACIÓN PÚBLICA NACIONAL/INTERNACIONAL o INVITACIÓN A CUANDO MENOS TRES",
  "tipo_contratacion": "ADQUISICIONES/SERVICIOS/OBRA PÚBLICA/ARRENDAMIENTO",
  "caracter": "NACIONAL/INTERNACIONAL/INTERNACIONAL BAJO TRATADOS",
  "entidad_federativa": "estado donde se realizará",
  "municipio": "municipio o delegación si aplica",
  "fecha_publicacion": "fecha del DOF en formato YYYY-MM-DD",
  "fecha_apertura": "fecha de apertura de propuestas YYYY-MM-DD HH:MM:SS",
  "fecha_fallo": "fecha del fallo YYYY-MM-DD HH:MM:SS",
  "fecha_junta_aclaraciones": "fecha de junta de aclaraciones YYYY-MM-DD HH:MM:SS",
  "fecha_visita_lugar": "fecha de visita al sitio YYYY-MM-DD HH:MM:SS si aplica",
  "costo_bases": "costo de las bases en pesos si se menciona",
  "lugar_obtener_bases": "dónde se pueden obtener las bases"
}

REGLAS:
- Si no encuentras un campo, usa null
- Si un PDF contiene múltiples licitaciones, devuelve un array con TODAS
- Extrae fechas del año 2025 correctamente
- Si las bases dicen "sin costo", pon 0 en costo_bases
- El numero_procedimiento NUNCA debe ser null

Responde ÚNICAMENTE con un JSON array de licitaciones: [...]"""

        try:
            # Llamada a Claude con el PDF
            message = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=8000,  # Más tokens para PDFs grandes
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
            
            # Limpiar markdown si existe
            if respuesta_texto.startswith("```"):
                respuesta_texto = respuesta_texto.replace("```json", "").replace("```", "").strip()
            
            # Parsear JSON
            licitaciones = json.loads(respuesta_texto)
            
            # Asegurar que es una lista
            if isinstance(licitaciones, dict):
                licitaciones = [licitaciones]
            
            # Añadir metadatos a cada licitación
            for lic in licitaciones:
                lic['fuente'] = 'DOF'
                lic['estado'] = 'PUBLICADA'
                lic['moneda'] = 'MXN'
                lic['datos_originales'] = {
                    'archivo_origen': pdf_path.name,
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'procesado_con_ia': True,
                    'modelo': 'claude-3-5-haiku-20241022',
                    'procesamiento': 'PDF_DIRECTO'
                }
            
            # Filtrar licitaciones sin numero_procedimiento
            licitaciones_validas = [lic for lic in licitaciones if lic.get('numero_procedimiento')]
            licitaciones_sin_numero = len(licitaciones) - len(licitaciones_validas)
            
            if licitaciones_sin_numero > 0:
                self.logger.warning(f"  ⚠️ {licitaciones_sin_numero} licitaciones sin numero_procedimiento (descartadas)")
            
            self.logger.info(f"  ✅ Extraídas {len(licitaciones_validas)} licitaciones válidas del PDF")
            return licitaciones_validas
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parseando JSON de Claude: {e}")
            self.logger.error(f"Respuesta: {respuesta_texto[:500]}...")
            return []
        except Exception as e:
            self.logger.error(f"Error con API de Claude: {e}")
            return []
    
    def extract(self) -> List[Dict]:
        """
        Método principal - extrae todas las licitaciones de PDFs DOF
        """
        self.logger.info("=== Iniciando extracción DOF desde PDFs con IA ===")
        
        # Buscar archivos PDF del DOF
        archivos_pdf = list(self.raw_dir.glob("*.pdf"))
        
        if not archivos_pdf:
            self.logger.warning(f"No se encontraron archivos PDF en {self.raw_dir}")
            self.logger.info("Ejecuta primero el descargador de PDFs del DOF")
            return []
        
        # Filtrar archivos DOF (con MAT o VES en el nombre)
        archivos_dof = [f for f in archivos_pdf 
                       if 'MAT' in f.name or 'VES' in f.name]
        
        if not archivos_dof:
            self.logger.info("Procesando todos los PDFs encontrados...")
            archivos_dof = archivos_pdf
        
        self.logger.info(f"📄 Encontrados {len(archivos_dof)} PDFs para procesar:")
        for archivo in archivos_dof:
            self.logger.info(f"  - {archivo.name}")
        
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
                        'metodo': 'PDF_DIRECTO',
                        'licitaciones': licitaciones
                    }, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"  💾 Guardado: {archivo_salida.name}")
                todas_licitaciones.extend(licitaciones)
        
        # Mostrar estadísticas
        self.logger.info("=" * 50)
        self.logger.info("📊 ESTADÍSTICAS FINALES:")
        self.logger.info(f"  • PDFs procesados: {estadisticas['pdfs_procesados']}")
        self.logger.info(f"  • PDFs con licitaciones: {estadisticas['pdfs_con_licitaciones']}")
        self.logger.info(f"  • Total licitaciones extraídas: {estadisticas['total_licitaciones']}")
        
        # Guardar resumen consolidado
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
    
    # Verificar API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("\n❌ ERROR: ANTHROPIC_API_KEY no configurada")
        print("\nPasos para configurar:")
        print("1. Crea un archivo .env en la raíz del proyecto")
        print("2. Añade la siguiente línea:")
        print("   ANTHROPIC_API_KEY=tu_api_key_aqui")
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
            else:
                print(f"  • Título: N/A")
            print(f"  • Entidad: {lic.get('entidad_compradora', 'N/A')}")
            print(f"  • Fecha apertura: {lic.get('fecha_apertura', 'N/A')}")
            print(f"  • Fecha fallo: {lic.get('fecha_fallo', 'N/A')}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
