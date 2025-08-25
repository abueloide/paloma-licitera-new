#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseWrapper(ABC):
    def __init__(self, config: dict, db_queries):
        self.config = config
        self.db_queries = db_queries
        self.scrapers_dir = Path(__file__).parent.parent.parent / "etl-process" / "extractors"
        
    @abstractmethod
    def should_run(self, modo: str) -> bool:
        pass
        
    @abstractmethod
    def run_scraper(self, modo: str) -> bool:
        pass
        
    def get_generated_files(self, data_dir: str) -> List[Path]:
        """Obtener archivos generados recientemente"""
        dir_path = Path(f"data/raw/{data_dir}")
        if not dir_path.exists():
            return []
        
        # Archivos modificados en las últimas 2 horas
        cutoff = datetime.now() - timedelta(hours=2)
        files = []
        for file_path in dir_path.iterdir():
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime >= cutoff:
                    files.append(file_path)
        return files

class ComprasMXWrapper(BaseWrapper):
    def should_run(self, modo: str) -> bool:
        if modo == "incremental":
            # Verificar si han pasado al menos 6 horas
            last_run = self.db_queries.get_last_processing_date('comprasmx')
            if last_run:
                hours_since = (datetime.now() - last_run).total_seconds() / 3600
                return hours_since >= 6
            return True
        elif modo == "historical":
            return True
        elif modo == "batch":
            return True
        return False
    
    def run_scraper(self, modo: str = "normal", **kwargs) -> bool:
        scraper_path = self.scrapers_dir / "comprasMX" / "ComprasMX_v2Claude.py"
        
        if not scraper_path.exists():
            logger.error(f"Scraper no encontrado: {scraper_path}")
            return False
        
        # Preparar entorno
        env = os.environ.copy()
        
        if modo == "incremental":
            last_expediente = self.db_queries.get_last_comprasmx_expediente()
            if last_expediente:
                env['PALOMA_LAST_EXPEDIENTE'] = last_expediente
                env['PALOMA_MODE'] = 'incremental'
                logger.info(f"Modo incremental: buscando desde expediente {last_expediente}")
        
        elif modo == "historical":
            fecha_desde = kwargs.get('fecha_desde')
            if fecha_desde:
                env['PALOMA_FECHA_DESDE'] = fecha_desde
                env['PALOMA_MODE'] = 'historical'
                logger.info(f"Modo histórico: desde {fecha_desde}")
        
        # Ejecutar scraper
        try:
            logger.info(f"Ejecutando ComprasMX scraper en modo {modo}")
            process = subprocess.run([
                sys.executable, str(scraper_path)
            ], capture_output=True, text=True, env=env, cwd=str(scraper_path.parent))
            
            if process.returncode == 0:
                logger.info("✅ ComprasMX scraper ejecutado exitosamente")
                return True
            else:
                logger.error(f"❌ Error en ComprasMX scraper: {process.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error ejecutando ComprasMX scraper: {e}")
            return False

class DOFWrapper(BaseWrapper):
    def should_run(self, modo: str) -> bool:
        if modo in ["incremental", "batch"]:
            return self.should_run_today()
        elif modo == "historical":
            return True
        return False
    
    def should_run_today(self) -> bool:
        """Verificar si debe ejecutarse DOF hoy"""
        now = datetime.now()
        
        # Verificar si es martes (1) o jueves (3)
        if now.weekday() not in [1, 3]:
            logger.info("DOF: No es martes ni jueves, saltando...")
            return False
        
        # Verificar horarios de publicación - EXACTAMENTE 9:00 AM y 9:00 PM
        current_time = now.time()
        matutino_time = datetime.strptime("09:00", "%H:%M").time()  # 9:00 AM exacto
        vespertino_time = datetime.strptime("21:00", "%H:%M").time()  # 9:00 PM exacto
        
        # Solo ejecutar en los horarios exactos (con ventana de 1 hora)
        matutino_end = datetime.strptime("10:00", "%H:%M").time()
        vespertino_end = datetime.strptime("22:00", "%H:%M").time()
        
        # Verificar si estamos en ventana matutina (9:00-10:00) o vespertina (21:00-22:00)
        in_matutino_window = matutino_time <= current_time < matutino_end
        in_vespertino_window = vespertino_time <= current_time < vespertino_end
        
        if not (in_matutino_window or in_vespertino_window):
            logger.info(f"DOF: Fuera de horarios de ejecución. Hora actual: {current_time.strftime('%H:%M')}")
            return False
        
        # Verificar si ya procesamos hoy
        if self.db_queries.check_dof_processed_today():
            logger.info("DOF: Ya procesado hoy")
            return False
        
        logger.info(f"DOF: Ejecutando en horario {'matutino' if in_matutino_window else 'vespertino'}")
        return True
    
    def run_scraper(self, modo: str = "normal", **kwargs) -> bool:
        scraper_path = self.scrapers_dir / "dof" / "dof_extraccion_estructuracion.py"
        
        if not scraper_path.exists():
            logger.error(f"Scraper no encontrado: {scraper_path}")
            return False
        
        env = os.environ.copy()
        
        if modo == "historical":
            fecha_desde = kwargs.get('fecha_desde')
            if fecha_desde:
                env['DOF_FECHA_DESDE'] = fecha_desde
                env['PALOMA_MODE'] = 'historical'
        
        try:
            logger.info(f"Ejecutando DOF scraper en modo {modo}")
            process = subprocess.run([
                sys.executable, str(scraper_path)
            ], capture_output=True, text=True, env=env, cwd=str(scraper_path.parent))
            
            if process.returncode == 0:
                logger.info("✅ DOF scraper ejecutado exitosamente")
                return True
            else:
                logger.error(f"❌ Error en DOF scraper: {process.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error ejecutando DOF scraper: {e}")
            return False

class TianguisWrapper(BaseWrapper):
    def should_run(self, modo: str) -> bool:
        if modo == "incremental":
            last_run = self.db_queries.get_last_processing_date('tianguis')
            if last_run:
                hours_since = (datetime.now() - last_run).total_seconds() / 3600
                return hours_since >= 6
            return True
        return modo in ["historical", "batch"]
    
    def run_scraper(self, modo: str = "normal", **kwargs) -> bool:
        scraper_path = self.scrapers_dir / "tianguis-digital" / "extractor-tianguis.py"
        
        if not scraper_path.exists():
            logger.error(f"Scraper no encontrado: {scraper_path}")
            return False
        
        env = os.environ.copy()
        
        if modo == "incremental":
            last_uuid = self.db_queries.get_last_tianguis_uuid()
            if last_uuid:
                env['PALOMA_LAST_UUID'] = last_uuid
                env['PALOMA_MODE'] = 'incremental'
        
        elif modo == "historical":
            fecha_desde = kwargs.get('fecha_desde')
            if fecha_desde:
                env['TIANGUIS_FECHA_DESDE'] = fecha_desde
                env['PALOMA_MODE'] = 'historical'
        
        try:
            logger.info(f"Ejecutando Tianguis scraper en modo {modo}")
            process = subprocess.run([
                sys.executable, str(scraper_path)
            ], capture_output=True, text=True, env=env, cwd=str(scraper_path.parent))
            
            if process.returncode == 0:
                logger.info("✅ Tianguis scraper ejecutado exitosamente")
                return True
            else:
                logger.error(f"❌ Error en Tianguis scraper: {process.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error ejecutando Tianguis scraper: {e}")
            return False

class SitiosMasivosWrapper(BaseWrapper):
    def should_run(self, modo: str) -> bool:
        if modo == "weekly":
            return self.should_run_weekly()
        return modo in ["historical", "batch"]
    
    def should_run_weekly(self) -> bool:
        """Verificar si debe ejecutarse semanalmente"""
        now = datetime.now()
        
        # Solo domingos
        if now.weekday() != 6:  # domingo = 6
            return False
        
        # Verificar última ejecución
        last_run = self.db_queries.get_last_processing_date('sitios-masivos')
        if last_run:
            days_since = (now - last_run).days
            return days_since >= 7
        
        return True
    
    def run_scraper(self, modo: str = "normal", **kwargs) -> bool:
        scraper_path = self.scrapers_dir / "sitios-masivos" / "PruebaUnoGPT.py"
        
        if not scraper_path.exists():
            logger.error(f"Scraper no encontrado: {scraper_path}")
            return False
        
        try:
            logger.info(f"Ejecutando SitiosMasivos scraper en modo {modo}")
            process = subprocess.run([
                sys.executable, str(scraper_path)
            ], capture_output=True, text=True, cwd=str(scraper_path.parent))
            
            if process.returncode == 0:
                logger.info("✅ SitiosMasivos scraper ejecutado exitosamente")
                return True
            else:
                logger.error(f"❌ Error en SitiosMasivos scraper: {process.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error ejecutando SitiosMasivos scraper: {e}")
            return False