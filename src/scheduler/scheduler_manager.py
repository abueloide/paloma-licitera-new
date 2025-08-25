#!/usr/bin/env python3
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import sys
from pathlib import Path
import calendar

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
    
    def _generar_fechas_dof_12_meses(self, fecha_desde: str) -> List[str]:
        """Generar todas las fechas de martes y jueves desde fecha_desde hasta hoy"""
        logger.info(f"🗓️ Generando fechas DOF desde {fecha_desde}")
        
        fecha_inicio = datetime.fromisoformat(fecha_desde).date()
        fecha_fin = datetime.now().date()
        
        fechas_dof = []
        fecha_actual = fecha_inicio
        
        while fecha_actual <= fecha_fin:
            # Martes = 1, Jueves = 3
            if fecha_actual.weekday() in [1, 3]:
                fechas_dof.append(fecha_actual.strftime('%Y-%m-%d'))
            fecha_actual += timedelta(days=1)
        
        logger.info(f"📋 Generadas {len(fechas_dof)} fechas DOF (martes y jueves)")
        logger.info(f"📅 Primera fecha: {fechas_dof[0] if fechas_dof else 'N/A'}")
        logger.info(f"📅 Última fecha: {fechas_dof[-1] if fechas_dof else 'N/A'}")
        
        return fechas_dof
    
    def run_descarga_inicial(self, fecha_desde: str) -> Dict:
        """
        🚀 DESCARGA INICIAL REAL - 12 meses completos
        
        Esta es la VERDADERA descarga inicial que:
        - ComprasMX: Descarga masiva hasta 12 meses atrás
        - DOF: Procesa TODOS los martes y jueves de 12 meses
        - Tianguis: Descarga masiva hasta 12 meses atrás  
        - Sitios Masivos: Descarga completa de todos los sitios
        """
        logger.info(f"🚀 INICIANDO DESCARGA INICIAL REAL desde {fecha_desde}")
        logger.info("📊 Esta descarga puede tomar 30-60 minutos...")
        
        resultados = {
            'inicio': datetime.now(),
            'modo': 'descarga_inicial',
            'fecha_desde': fecha_desde,
            'fuentes_procesadas': {},
            'totales': {'scraped': 0, 'processed': 0, 'inserted': 0, 'errors': 0, 'fechas_dof': 0},
            'estimaciones': {
                'comprasmx': '50,000-100,000 registros esperados',
                'dof': '5,000-10,000 registros esperados',
                'tianguis': '10,000-20,000 registros esperados',  
                'sitios-masivos': '5,000-15,000 registros esperados'
            }
        }
        
        # ORDEN DE PRIORIDAD para descarga inicial:
        # 1. ComprasMX (máxima prioridad - portal federal principal)
        # 2. DOF (alta prioridad - pero requiere procesamiento especial)
        # 3. Tianguis Digital (prioridad media - CDMX)
        # 4. Sitios Masivos (menor prioridad - múltiples sitios)
        
        orden_fuentes = ['comprasmx', 'dof', 'tianguis', 'sitios-masivos']
        
        for fuente in orden_fuentes:
            if fuente not in self.wrappers:
                logger.warning(f"⚠️ Fuente no disponible: {fuente}")
                continue
            
            if not self.config['sources'].get(fuente, {}).get('enabled', True):
                logger.info(f"⏭️ Fuente deshabilitada: {fuente}")
                continue
            
            logger.info(f"📊 PROCESANDO FUENTE PRIORITARIA: {fuente.upper()}")
            
            if fuente == 'dof':
                # DOF requiere procesamiento especial con fechas específicas
                resultado_fuente = self._procesar_dof_descarga_inicial(fecha_desde)
            else:
                # ComprasMX, Tianguis, Sitios Masivos: descarga masiva
                resultado_fuente = self._procesar_fuente_descarga_inicial(fuente, fecha_desde)
            
            resultados['fuentes_procesadas'][fuente] = resultado_fuente
            
            # Actualizar totales
            if resultado_fuente.get('scraping_exitoso', False):
                resultados['totales']['scraped'] += 1
            if resultado_fuente.get('procesamiento_exitoso', False):
                resultados['totales']['processed'] += 1
                resultados['totales']['inserted'] += resultado_fuente.get('registros_insertados', 0)
            if resultado_fuente.get('error'):
                resultados['totales']['errors'] += 1
            if fuente == 'dof' and resultado_fuente.get('fechas_procesadas'):
                resultados['totales']['fechas_dof'] = resultado_fuente['fechas_procesadas']
        
        resultados['fin'] = datetime.now()
        resultados['duracion'] = str(resultados['fin'] - resultados['inicio'])
        
        logger.info(f"🎉 DESCARGA INICIAL COMPLETADA: {resultados['totales']}")
        return resultados
    
    def _procesar_dof_descarga_inicial(self, fecha_desde: str) -> Dict:
        """Procesar DOF con fechas específicas de martes y jueves"""
        logger.info("📋 PROCESANDO DOF - Modo descarga inicial")
        
        resultado = {
            'scraping_exitoso': False,
            'procesamiento_exitoso': False,
            'registros_insertados': 0,
            'fechas_procesadas': 0,
            'fechas_total': 0,
            'error': None
        }
        
        try:
            # Generar todas las fechas DOF de los últimos 12 meses
            fechas_dof = self._generar_fechas_dof_12_meses(fecha_desde)
            resultado['fechas_total'] = len(fechas_dof)
            
            if not fechas_dof:
                resultado['error'] = "No se generaron fechas DOF válidas"
                return resultado
            
            logger.info(f"🗓️ Procesando {len(fechas_dof)} fechas DOF...")
            
            wrapper = self.wrappers['dof']
            fechas_exitosas = 0
            total_registros = 0
            
            # Procesar cada fecha DOF (martes y jueves)
            for i, fecha_dof in enumerate(fechas_dof):
                logger.info(f"📅 Procesando DOF {i+1}/{len(fechas_dof)}: {fecha_dof}")
                
                try:
                    # Ejecutar scraper para fecha específica
                    if wrapper.run_scraper('historical', fecha_desde=fecha_dof):
                        fechas_exitosas += 1
                        
                        # Procesar archivos generados
                        etl_result = self.etl.ejecutar('dof', solo_procesamiento=True)
                        if etl_result and etl_result['totales']['insertados'] > 0:
                            registros_fecha = etl_result['totales']['insertados']
                            total_registros += registros_fecha
                            logger.info(f"✅ DOF {fecha_dof}: {registros_fecha} registros insertados")
                        else:
                            logger.warning(f"⚠️ DOF {fecha_dof}: Sin registros encontrados")
                    else:
                        logger.warning(f"❌ DOF {fecha_dof}: Error en scraping")
                        
                except Exception as e:
                    logger.error(f"❌ Error procesando DOF {fecha_dof}: {e}")
                
                # Pequeña pausa entre fechas para no sobrecargar
                if i < len(fechas_dof) - 1:
                    import time
                    time.sleep(1)
            
            resultado['fechas_procesadas'] = fechas_exitosas
            resultado['registros_insertados'] = total_registros
            resultado['scraping_exitoso'] = fechas_exitosas > 0
            resultado['procesamiento_exitoso'] = total_registros > 0
            
            logger.info(f"📊 DOF Resumen: {fechas_exitosas}/{len(fechas_dof)} fechas exitosas, {total_registros} registros")
            
        except Exception as e:
            logger.error(f"❌ Error en descarga inicial DOF: {e}")
            resultado['error'] = str(e)
        
        return resultado
    
    def _procesar_fuente_descarga_inicial(self, fuente: str, fecha_desde: str) -> Dict:
        """Procesar fuente en modo descarga inicial masiva"""
        logger.info(f"📊 PROCESANDO {fuente.upper()} - Modo descarga inicial")
        
        resultado = {
            'scraping_exitoso': False,
            'procesamiento_exitoso': False,
            'registros_insertados': 0,
            'error': None
        }
        
        try:
            wrapper = self.wrappers[fuente]
            
            # Ejecutar scraper en modo histórico masivo
            logger.info(f"🕷️ Iniciando scraper {fuente} (descarga masiva)...")
            
            if wrapper.run_scraper('historical', fecha_desde=fecha_desde):
                resultado['scraping_exitoso'] = True
                logger.info(f"✅ {fuente} scraper ejecutado exitosamente")
                
                # Procesar archivos generados
                logger.info(f"📁 Procesando archivos generados por {fuente}...")
                etl_result = self.etl.ejecutar(fuente, solo_procesamiento=True)
                
                if etl_result and etl_result['totales']['insertados'] > 0:
                    resultado['procesamiento_exitoso'] = True
                    resultado['registros_insertados'] = etl_result['totales']['insertados']
                    logger.info(f"💾 {fuente}: {resultado['registros_insertados']} registros insertados")
                else:
                    logger.warning(f"⚠️ {fuente}: Sin registros procesados")
                    resultado['error'] = "Sin registros procesados"
            else:
                logger.error(f"❌ Error en scraper {fuente}")
                resultado['error'] = "Error en scraping"
                
        except Exception as e:
            logger.error(f"❌ Error procesando {fuente}: {e}")
            resultado['error'] = str(e)
        
        return resultado
    
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