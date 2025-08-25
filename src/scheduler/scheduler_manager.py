#!/usr/bin/env python3
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import sys
from pathlib import Path

# Agregar paths necesarios
sys.path.insert(0, str(Path(__file__).parent.parent))

from .database_queries import DatabaseQueries
from .scraper_wrappers import ComprasMXWrapper, DOFWrapper, TianguisWrapper, SitiosMasivosWrapper
from ..etl import ETL

logger = logging.getLogger(__name__)

class SchedulerManager:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Expandir variables de entorno en configuración
        self._expand_env_vars()
        
        self.db_queries = DatabaseQueries(self.config)
        self.etl = ETL(config_path)
        
        # Inicializar wrappers
        self.wrappers = {
            'comprasmx': ComprasMXWrapper(self.config, self.db_queries),
            'dof': DOFWrapper(self.config, self.db_queries),
            'tianguis': TianguisWrapper(self.config, self.db_queries),
            'sitios-masivos': SitiosMasivosWrapper(self.config, self.db_queries)
        }
    
    def _expand_env_vars(self):
        """Expandir variables de entorno en config"""
        import os
        db_config = self.config['database']
        
        for key in db_config:
            value = db_config[key]
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_expr = value[2:-1]  # Remover ${ }
                if ':-' in env_expr:
                    env_var, default = env_expr.split(':-')
                    db_config[key] = os.environ.get(env_var, default)
                else:
                    db_config[key] = os.environ.get(env_expr, value)
    
    def run_historical(self, fuente: str, fecha_desde: str) -> Dict:
        """Ejecutar descarga histórica desde fecha específica"""
        logger.info(f"🕰️ Iniciando descarga histórica: {fuente} desde {fecha_desde}")
        
        resultados = {
            'inicio': datetime.now(),
            'modo': 'historical',
            'fuente': fuente,
            'fecha_desde': fecha_desde,
            'fuentes_procesadas': {},
            'totales': {'scraped': 0, 'processed': 0, 'inserted': 0, 'errors': 0}
        }
        
        # Validar fecha
        try:
            datetime.fromisoformat(fecha_desde)
        except ValueError:
            resultados['error'] = f"Fecha inválida: {fecha_desde}. Usar formato YYYY-MM-DD"
            return resultados
        
        # Determinar fuentes a procesar
        fuentes = [fuente] if fuente != 'all' else list(self.wrappers.keys())
        
        for fuente_actual in fuentes:
            if fuente_actual not in self.wrappers:
                logger.warning(f"Fuente desconocida: {fuente_actual}")
                continue
                
            logger.info(f"📊 Procesando fuente: {fuente_actual}")
            wrapper = self.wrappers[fuente_actual]
            
            resultado_fuente = {
                'scraping_exitoso': False,
                'archivos_generados': 0,
                'procesamiento_exitoso': False,
                'registros_insertados': 0,
                'error': None
            }
            
            try:
                # 1. Ejecutar scraper
                if wrapper.run_scraper('historical', fecha_desde=fecha_desde):
                    resultado_fuente['scraping_exitoso'] = True
                    resultados['totales']['scraped'] += 1
                    
                    # 2. Procesar archivos generados
                    etl_result = self.etl.ejecutar(fuente_actual, solo_procesamiento=True)
                    
                    if etl_result and etl_result['totales']['insertados'] > 0:
                        resultado_fuente['procesamiento_exitoso'] = True
                        resultado_fuente['registros_insertados'] = etl_result['totales']['insertados']
                        resultados['totales']['processed'] += 1
                        resultados['totales']['inserted'] += etl_result['totales']['insertados']
                    
                else:
                    resultado_fuente['error'] = "Error en scraping"
                    resultados['totales']['errors'] += 1
                    
            except Exception as e:
                logger.error(f"Error procesando {fuente_actual}: {e}")
                resultado_fuente['error'] = str(e)
                resultados['totales']['errors'] += 1
            
            resultados['fuentes_procesadas'][fuente_actual] = resultado_fuente
        
        resultados['fin'] = datetime.now()
        resultados['duracion'] = str(resultados['fin'] - resultados['inicio'])
        
        logger.info(f"✅ Descarga histórica completada: {resultados['totales']}")
        return resultados
    
    def run_incremental(self, fuentes: List[str] = None) -> Dict:
        """Ejecutar actualización incremental"""
        if fuentes is None:
            fuentes = ['comprasmx', 'dof', 'tianguis']
            
        logger.info(f"🔄 Iniciando actualización incremental: {fuentes}")
        
        resultados = {
            'inicio': datetime.now(),
            'modo': 'incremental',
            'fuentes_solicitadas': fuentes,
            'fuentes_procesadas': {},
            'totales': {'scraped': 0, 'processed': 0, 'inserted': 0, 'skipped': 0, 'errors': 0}
        }
        
        for fuente in fuentes:
            if fuente not in self.wrappers:
                logger.warning(f"Fuente desconocida: {fuente}")
                continue
                
            wrapper = self.wrappers[fuente]
            
            resultado_fuente = {
                'should_run': False,
                'scraping_exitoso': False,
                'procesamiento_exitoso': False,
                'registros_insertados': 0,
                'razon_skip': None,
                'error': None
            }
            
            try:
                # Verificar si debe ejecutarse
                if wrapper.should_run('incremental'):
                    resultado_fuente['should_run'] = True
                    
                    logger.info(f"🔄 Ejecutando incremental para {fuente}")
                    
                    # Ejecutar scraper
                    if wrapper.run_scraper('incremental'):
                        resultado_fuente['scraping_exitoso'] = True
                        resultados['totales']['scraped'] += 1
                        
                        # Procesar archivos
                        etl_result = self.etl.ejecutar(fuente, solo_procesamiento=True)
                        
                        if etl_result and etl_result['totales']['insertados'] > 0:
                            resultado_fuente['procesamiento_exitoso'] = True
                            resultado_fuente['registros_insertados'] = etl_result['totales']['insertados']
                            resultados['totales']['processed'] += 1
                            resultados['totales']['inserted'] += etl_result['totales']['insertados']
                        
                    else:
                        resultado_fuente['error'] = "Error en scraping"
                        resultados['totales']['errors'] += 1
                        
                else:
                    # Determinar razón del skip
                    if fuente == 'dof':
                        if not wrapper.should_run_today():
                            resultado_fuente['razon_skip'] = "No es martes/jueves o ya procesado"
                    else:
                        last_run = self.db_queries.get_last_processing_date(fuente)
                        if last_run:
                            hours_since = (datetime.now() - last_run).total_seconds() / 3600
                            resultado_fuente['razon_skip'] = f"Ejecutado hace {hours_since:.1f}h (< 6h)"
                        else:
                            resultado_fuente['razon_skip'] = "Primera ejecución"
                    
                    resultados['totales']['skipped'] += 1
                    logger.info(f"⏭️ Saltando {fuente}: {resultado_fuente['razon_skip']}")
                    
            except Exception as e:
                logger.error(f"Error en incremental {fuente}: {e}")
                resultado_fuente['error'] = str(e)
                resultados['totales']['errors'] += 1
            
            resultados['fuentes_procesadas'][fuente] = resultado_fuente
        
        resultados['fin'] = datetime.now()
        resultados['duracion'] = str(resultados['fin'] - resultados['inicio'])
        
        logger.info(f"✅ Actualización incremental completada: {resultados['totales']}")
        return resultados
    
    def run_batch(self, modo: str) -> Dict:
        """Ejecutar lote programado"""
        logger.info(f"📅 Iniciando ejecución batch: {modo}")
        
        batch_config = self.config.get('automation', {}).get('batch_config', {})
        
        if modo not in batch_config:
            return {'error': f"Modo batch desconocido: {modo}"}
        
        config_modo = batch_config[modo]
        fuentes = config_modo.get('fuentes', [])
        
        resultados = {
            'inicio': datetime.now(),
            'modo': f'batch_{modo}',
            'fuentes_programadas': fuentes,
            'config': config_modo
        }
        
        # Ejecutar según el modo
        if modo == 'diario':
            resultados.update(self.run_incremental(fuentes))
        elif modo == 'cada_6h':
            resultados.update(self.run_incremental(fuentes))
        elif modo == 'semanal':
            # Para semanal, ejecutar sitios masivos
            if 'sitios-masivos' in fuentes:
                wrapper = self.wrappers['sitios-masivos']
                if wrapper.should_run('weekly'):
                    resultados.update(self.run_incremental(['sitios-masivos']))
                else:
                    resultados.update({'totales': {'skipped': 1}, 'razon': 'No es domingo o ya ejecutado'})
        
        logger.info(f"✅ Ejecución batch {modo} completada")
        return resultados
    
    def get_status(self) -> Dict:
        """Obtener estado actual del sistema"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'database': self._check_database_status(),
            'fuentes': self._get_sources_status(),
            'ultimo_procesamiento': self._get_last_processing_info(),
            'scheduler_config': self.config.get('automation', {})
        }
        
        return status
    
    def _check_database_status(self) -> Dict:
        """Verificar estado de la base de datos"""
        try:
            counts = self.db_queries.count_records_by_source()
            return {
                'connected': True,
                'total_records': sum(counts.values()),
                'by_source': counts
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def _get_sources_status(self) -> Dict:
        """Obtener estado de las fuentes"""
        sources_status = {}
        
        for fuente, wrapper in self.wrappers.items():
            try:
                last_run = self.db_queries.get_last_processing_date(fuente)
                should_run_incremental = wrapper.should_run('incremental')
                
                sources_status[fuente] = {
                    'enabled': self.config['sources'].get(fuente, {}).get('enabled', True),
                    'last_run': last_run.isoformat() if last_run else None,
                    'should_run_incremental': should_run_incremental,
                    'hours_since_last_run': ((datetime.now() - last_run).total_seconds() / 3600) if last_run else None
                }
                
                # Info específica por fuente
                if fuente == 'dof':
                    sources_status[fuente]['should_run_today'] = wrapper.should_run_today()
                elif fuente == 'sitios-masivos':
                    sources_status[fuente]['should_run_weekly'] = wrapper.should_run_weekly()
                    
            except Exception as e:
                sources_status[fuente] = {'error': str(e)}
        
        return sources_status
    
    def _get_last_processing_info(self) -> Dict:
        """Obtener información del último procesamiento"""
        info = {}
        
        for fuente in self.wrappers.keys():
            try:
                last_date = self.db_queries.get_last_processing_date(fuente)
                if last_date:
                    # Contar registros añadidos en las últimas 24 horas
                    last_24h = datetime.now() - timedelta(hours=24)
                    new_records = self.db_queries.get_records_added_since(fuente, last_24h)
                    
                    info[fuente] = {
                        'last_processing': last_date.isoformat(),
                        'records_last_24h': new_records
                    }
            except Exception as e:
                info[fuente] = {'error': str(e)}
        
        return info