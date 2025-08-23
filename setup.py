#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inicio rápido para Paloma Licitera
"""

import sys
import subprocess
from pathlib import Path

def main():
    print("""
╔══════════════════════════════════════╗
║     PALOMA LICITERA - SETUP          ║
╚══════════════════════════════════════╝
    """)
    
    # Verificar Python
    print("✓ Python", sys.version.split()[0])
    
    # Instalar dependencias
    print("\n📦 Instalando dependencias...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Crear directorios
    print("\n📁 Creando estructura de directorios...")
    dirs = [
        "data/raw/comprasmx",
        "data/raw/dof", 
        "data/raw/tianguis",
        "data/processed/tianguis",
        "logs"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"   ✓ {dir_path}")
    
    # Copiar configuración
    if not Path("config.yaml").exists():
        print("\n⚙️ Creando archivo de configuración...")
        import shutil
        shutil.copy("config.example.yaml", "config.yaml")
        print("   ✓ config.yaml creado (editar con tus credenciales)")
    
    print("""
╔══════════════════════════════════════╗
║         INSTALACIÓN COMPLETA          ║
╚══════════════════════════════════════╝

Siguientes pasos:

1. Editar config.yaml con tus credenciales de BD
2. Configurar base de datos:
   python src/database.py --setup

3. Ejecutar ETL:
   python src/etl.py --all

4. Iniciar API:
   python src/api.py

📚 Documentación: README.md
    """)

if __name__ == "__main__":
    main()
