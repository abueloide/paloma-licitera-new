#!/usr/bin/env python3
"""
Script directo para ejecutar DOF con IA
Solo necesitas ANTHROPIC_API_KEY en .env
"""

import os
import sys
from pathlib import Path

# Agregar rutas necesarias
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "etl-process"))

# Cargar .env
from dotenv import load_dotenv
load_dotenv()

# Verificar API key
if not os.getenv('ANTHROPIC_API_KEY'):
    print("❌ ERROR: ANTHROPIC_API_KEY no configurada en .env")
    print("\nCrea un archivo .env con:")
    print("ANTHROPIC_API_KEY=tu_api_key_aqui")
    sys.exit(1)

# Importar y ejecutar
try:
    from extractors.dof_extractor_ai import DOFExtractorAI
    from database import Database
    
    print("🚀 Iniciando extracción DOF con Claude Haiku...")
    
    # Ejecutar extractor
    extractor = DOFExtractorAI()
    licitaciones = extractor.extract()
    
    if licitaciones:
        print(f"\n✅ Extraídas {len(licitaciones)} licitaciones")
        
        # Insertar en BD
        print("💾 Insertando en base de datos...")
        db = Database("config.yaml")
        
        insertadas = 0
        for lic in licitaciones:
            try:
                if db.insertar_licitacion(lic):
                    insertadas += 1
            except Exception as e:
                pass  # Ya existe o error menor
        
        print(f"✅ {insertadas} nuevas licitaciones insertadas")
        print(f"Total en BD: {db.contar_registros()}")
    else:
        print("⚠️ No se extrajeron licitaciones")
        
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("\nInstala las dependencias:")
    print("pip install anthropic python-dotenv psycopg2-binary")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
