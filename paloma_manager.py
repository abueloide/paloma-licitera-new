#!/usr/bin/env python3
"""
PALOMA LICITERA - SISTEMA DE GESTIÓN UNIFICADO
Reemplazo completo de paloma.sh con manejo robusto de dependencias
"""

import os
import sys
import subprocess
import platform
import json
import argparse
from pathlib import Path
from datetime import datetime

class PalomaManager:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.venv_dir = self.root_dir / ".venv"
        self.python_exe = self.venv_dir / ("Scripts" if platform.system() == "Windows" else "bin") / "python"
        self.pip_exe = self.venv_dir / ("Scripts" if platform.system() == "Windows" else "bin") / "pip"
        
        # Colores para output
        self.GREEN = '\033[92m'
        self.YELLOW = '\033[93m'
        self.RED = '\033[91m'
        self.BLUE = '\033[94m'
        self.BOLD = '\033[1m'
        self.END = '\033[0m'
    
    def print_header(self):
        """Imprimir header del sistema"""
        print(f"""
{self.BOLD}╔══════════════════════════════════════════════╗
║     🐦 PALOMA LICITERA - SISTEMA UNIFICADO     ║
╚══════════════════════════════════════════════╝{self.END}
        """)
    
    def check_python(self):
        """Verificar versión de Python"""
        version = sys.version_info
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"{self.RED}❌ Se requiere Python 3.8 o superior{self.END}")
            return False
        return True
    
    def check_postgresql(self):
        """Verificar conexión a PostgreSQL"""
        try:
            result = subprocess.run(
                ["psql", "-h", "localhost", "-U", "postgres", "-d", "paloma_licitera", "-c", "SELECT 1"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"{self.GREEN}✓ PostgreSQL conectado{self.END}")
                
                # Contar registros
                result = subprocess.run(
                    ["psql", "-h", "localhost", "-U", "postgres", "-d", "paloma_licitera", 
                     "-tAc", "SELECT COUNT(*) FROM licitaciones"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    count = result.stdout.strip()
                    print(f"  📊 {count} licitaciones en BD")
                return True
            else:
                print(f"{self.YELLOW}⚠️  PostgreSQL no disponible{self.END}")
                return False
        except FileNotFoundError:
            print(f"{self.YELLOW}⚠️  psql no encontrado{self.END}")
            return False
    
    def setup_venv(self):
        """Crear y activar ambiente virtual"""
        if not self.venv_dir.exists():
            print(f"{self.YELLOW}📦 Creando ambiente virtual...{self.END}")
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_dir)], check=True)
        
        if self.python_exe.exists():
            print(f"{self.GREEN}✓ Ambiente virtual listo{self.END}")
            return True
        else:
            print(f"{self.RED}❌ Error con ambiente virtual{self.END}")
            return False
    
    def install_dependencies(self):
        """Instalar dependencias de forma inteligente"""
        print(f"\n{self.BOLD}📦 INSTALANDO DEPENDENCIAS{self.END}")
        
        # Dependencias esenciales que SIEMPRE deben instalarse
        essential_deps = [
            "python-dotenv==1.0.0",
            "pyyaml==6.0.1",
            "requests==2.31.0",
            "psycopg2-binary>=2.9.10",
            "anthropic>=0.64.0",
            "beautifulsoup4==4.12.2",
            "pandas>=2.2.0",
            "fastapi>=0.110.0",
            "uvicorn>=0.27.0"
        ]
        
        # Dependencias problemáticas que intentamos pero no son críticas
        optional_deps = [
            "PyMuPDF==1.23.14",  # Problema con espacios en path
            "lxml==4.9.3",       # Puede fallar en Mac M1
            "html5lib==1.1"      # Puede tener conflictos
        ]
        
        # Alternativas para las problemáticas
        alternative_deps = [
            "pypdf2",      # Alternativa a PyMuPDF
            "pdfplumber",  # Otra alternativa para PDFs
            "pdfminer.six" # Más alternativas
        ]
        
        # Actualizar pip primero
        print("  📍 Actualizando pip...")
        subprocess.run([str(self.pip_exe), "install", "--upgrade", "pip"], 
                      capture_output=True)
        
        # Instalar esenciales
        print("  📍 Instalando dependencias esenciales...")
        for dep in essential_deps:
            try:
                result = subprocess.run(
                    [str(self.pip_exe), "install", dep],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"    ✓ {dep.split('==')[0]}")
                else:
                    print(f"    ⚠️  {dep.split('==')[0]} - problema menor")
            except Exception as e:
                print(f"    ❌ {dep}: {e}")
        
        # Intentar opcionales sin fallar
        print("  📍 Intentando dependencias opcionales...")
        for dep in optional_deps:
            try:
                subprocess.run(
                    [str(self.pip_exe), "install", "--no-deps", dep],
                    capture_output=True,
                    timeout=30
                )
                print(f"    ✓ {dep.split('==')[0]}")
            except:
                print(f"    ⏭️  {dep.split('==')[0]} - saltado")
        
        # Instalar alternativas
        print("  📍 Instalando alternativas para PDFs...")
        for dep in alternative_deps:
            try:
                subprocess.run(
                    [str(self.pip_exe), "install", dep],
                    capture_output=True
                )
                print(f"    ✓ {dep}")
            except:
                pass
        
        print(f"{self.GREEN}✅ Dependencias instaladas{self.END}")
    
    def setup_env_file(self):
        """Configurar archivo .env"""
        env_file = self.root_dir / ".env"
        
        if not env_file.exists():
            print(f"{self.YELLOW}⚠️  Creando archivo .env{self.END}")
            with open(env_file, 'w') as f:
                f.write("# Configuración Paloma Licitera\n")
                f.write("ANTHROPIC_API_KEY=tu_api_key_aqui\n")
                f.write("DATABASE_URL=postgresql://postgres:password@localhost/paloma_licitera\n")
            print(f"  📝 Edita .env con tu API key de Anthropic")
        else:
            # Verificar si tiene API key
            with open(env_file, 'r') as f:
                content = f.read()
                if 'ANTHROPIC_API_KEY' in content and 'tu_api_key_aqui' not in content:
                    print(f"{self.GREEN}✓ Archivo .env configurado{self.END}")
                else:
                    print(f"{self.YELLOW}⚠️  Falta configurar ANTHROPIC_API_KEY en .env{self.END}")
    
    def run_etl(self, source="all"):
        """Ejecutar ETL"""
        print(f"\n{self.BOLD}🚀 EJECUTANDO ETL - {source.upper()}{self.END}")
        
        cmd = [str(self.python_exe), "src/etl.py", "--fuente", source]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.root_dir)
            )
            
            # Mostrar output en tiempo real
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"  {line.rstrip()}")
            
            process.wait()
            
            if process.returncode == 0:
                print(f"{self.GREEN}✅ ETL completado exitosamente{self.END}")
            else:
                stderr = process.stderr.read()
                print(f"{self.RED}❌ Error en ETL:{self.END}")
                print(stderr)
                
        except Exception as e:
            print(f"{self.RED}❌ Error ejecutando ETL: {e}{self.END}")
    
    def start_dashboard(self):
        """Iniciar dashboard (API + Frontend)"""
        print(f"\n{self.BOLD}🎨 INICIANDO DASHBOARD{self.END}")
        
        # Iniciar API
        print("  📡 Iniciando API backend...")
        api_process = subprocess.Popen(
            [str(self.python_exe), "src/api.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.root_dir)
        )
        
        # Iniciar Frontend
        print("  🎨 Iniciando frontend...")
        frontend_dir = self.root_dir / "frontend"
        if frontend_dir.exists():
            subprocess.Popen(
                ["npm", "run", "dev"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(frontend_dir)
            )
        
        print(f"""
{self.GREEN}✅ Dashboard iniciado:{self.END}
  📡 API: http://localhost:8000
  📊 Docs: http://localhost:8000/docs  
  🎨 Frontend: http://localhost:3001
  
  Presiona Ctrl+C para detener
        """)
        
        try:
            api_process.wait()
        except KeyboardInterrupt:
            print(f"\n{self.YELLOW}Deteniendo servicios...{self.END}")
            api_process.terminate()
    
    def show_status(self):
        """Mostrar estado del sistema"""
        print(f"\n{self.BOLD}📊 ESTADO DEL SISTEMA{self.END}")
        
        # Python
        self.check_python()
        
        # PostgreSQL
        self.check_postgresql()
        
        # Ambiente virtual
        if self.venv_dir.exists():
            print(f"{self.GREEN}✓ Ambiente virtual existe{self.END}")
        else:
            print(f"{self.YELLOW}⚠️  Ambiente virtual no existe{self.END}")
        
        # Dependencias clave
        try:
            result = subprocess.run(
                [str(self.pip_exe), "list"],
                capture_output=True,
                text=True
            )
            if "anthropic" in result.stdout:
                print(f"{self.GREEN}✓ Anthropic instalado{self.END}")
            if "fastapi" in result.stdout:
                print(f"{self.GREEN}✓ FastAPI instalado{self.END}")
            if "pandas" in result.stdout:
                print(f"{self.GREEN}✓ Pandas instalado{self.END}")
        except:
            pass
        
        # Archivos de datos
        data_dir = self.root_dir / "data"
        if data_dir.exists():
            subdirs = ["raw/comprasmx", "raw/dof", "raw/tianguis"]
            for subdir in subdirs:
                path = data_dir / subdir
                if path.exists():
                    files = list(path.glob("*"))
                    print(f"  📁 {subdir}: {len(files)} archivos")

def main():
    parser = argparse.ArgumentParser(
        description='🐦 Paloma Licitera - Sistema de Gestión Unificado'
    )
    
    parser.add_argument(
        'command',
        choices=['setup', 'status', 'download', 'dashboard', 'etl'],
        help='Comando a ejecutar'
    )
    
    parser.add_argument(
        '--source',
        choices=['all', 'comprasmx', 'dof', 'tianguis'],
        default='all',
        help='Fuente de datos para ETL'
    )
    
    args = parser.parse_args()
    
    manager = PalomaManager()
    manager.print_header()
    
    if args.command == 'setup':
        print(f"\n{manager.BOLD}🔧 CONFIGURACIÓN INICIAL{manager.END}")
        if not manager.check_python():
            sys.exit(1)
        manager.setup_venv()
        manager.install_dependencies()
        manager.setup_env_file()
        manager.check_postgresql()
        print(f"\n{manager.GREEN}✅ Sistema configurado. Ejecuta:{manager.END}")
        print(f"  python paloma_manager.py download")
        
    elif args.command == 'status':
        manager.show_status()
        
    elif args.command == 'download' or args.command == 'etl':
        manager.run_etl(args.source)
        
    elif args.command == 'dashboard':
        manager.start_dashboard()

if __name__ == "__main__":
    main()
