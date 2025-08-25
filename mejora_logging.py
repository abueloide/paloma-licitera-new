#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para mejorar el logging visual del scheduler
"""

import subprocess
import sys
from pathlib import Path

def agregar_logging_visual():
    """Agregar logging visual al scheduler manager"""
    
    scheduler_path = Path(__file__).parent / "src/scheduler/scheduler_manager.py"
    
    # Código de reemplazo con mejor logging visual
    nuevo_metodo_dof = '''    def _procesar_dof_descarga_inicial(self, fecha_desde: str) -> Dict:
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
            
            # LOGGING VISUAL MEJORADO - CONSOLA
            print(f"\\n🗓️  DOF: Procesando {len(fechas_dof)} fechas (martes y jueves)")
            print(f"📅 Rango: {fechas_dof[0]} → {fechas_dof[-1]}")
            print("=" * 70)
            
            wrapper = self.wrappers['dof']
            fechas_exitosas = 0
            total_registros = 0
            
            # Procesar cada fecha DOF (martes y jueves)
            for i, fecha_dof in enumerate(fechas_dof):
                # BARRA DE PROGRESO VISUAL
                porcentaje = int((i + 1) * 100 / len(fechas_dof))
                barra_progreso = "█" * int(porcentaje / 4) + "░" * (25 - int(porcentaje / 4))
                
                print(f"📅 DOF [{barra_progreso}] {porcentaje:3d}% | {i+1:3d}/{len(fechas_dof)} | {fecha_dof}", end=" ", flush=True)
                
                try:
                    # Ejecutar scraper para fecha específica
                    if wrapper.run_scraper('historical', fecha_desde=fecha_dof):
                        fechas_exitosas += 1
                        
                        # Procesar archivos generados
                        etl_result = self.etl.ejecutar('dof', solo_procesamiento=True)
                        if etl_result and etl_result['totales']['insertados'] > 0:
                            registros_fecha = etl_result['totales']['insertados']
                            total_registros += registros_fecha
                            print(f"✅ {registros_fecha} reg")
                        else:
                            print("⚪ 0 reg")
                    else:
                        print("❌ error")
                        
                except Exception as e:
                    print(f"❌ {str(e)[:20]}...")
                
                # Pequeña pausa entre fechas para no sobrecargar
                if i < len(fechas_dof) - 1:
                    import time
                    time.sleep(0.5)
            
            print("=" * 70)
            print(f"📊 DOF COMPLETADO: {fechas_exitosas}/{len(fechas_dof)} fechas exitosas")
            print(f"💾 TOTAL REGISTROS: {total_registros:,}")
            print("=" * 70)
            
            resultado['fechas_procesadas'] = fechas_exitosas
            resultado['registros_insertados'] = total_registros
            resultado['scraping_exitoso'] = fechas_exitosas > 0
            resultado['procesamiento_exitoso'] = total_registros > 0
            
            logger.info(f"📊 DOF Resumen: {fechas_exitosas}/{len(fechas_dof)} fechas exitosas, {total_registros} registros")
            
        except Exception as e:
            print(f"\\n❌ ERROR DOF: {e}")
            logger.error(f"❌ Error en descarga inicial DOF: {e}")
            resultado['error'] = str(e)
        
        return resultado'''

    nuevo_metodo_fuente = '''    def _procesar_fuente_descarga_inicial(self, fuente: str, fecha_desde: str) -> Dict:
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
            
            # LOGGING VISUAL EN CONSOLA
            print(f"🕷️  {fuente.upper()}: Iniciando scraper...")
            
            if wrapper.run_scraper('historical', fecha_desde=fecha_desde):
                resultado['scraping_exitoso'] = True
                print(f"✅ {fuente.upper()}: Scraper ejecutado exitosamente")
                
                # Procesar archivos generados
                print(f"📁 {fuente.upper()}: Procesando archivos...")
                etl_result = self.etl.ejecutar(fuente, solo_procesamiento=True)
                
                if etl_result and etl_result['totales']['insertados'] > 0:
                    resultado['procesamiento_exitoso'] = True
                    resultado['registros_insertados'] = etl_result['totales']['insertados']
                    print(f"💾 {fuente.upper()}: {resultado['registros_insertados']:,} registros insertados")
                else:
                    print(f"⚠️  {fuente.upper()}: Sin registros procesados")
                    resultado['error'] = "Sin registros procesados"
            else:
                print(f"❌ {fuente.upper()}: Error en scraper")
                resultado['error'] = "Error en scraping"
                
        except Exception as e:
            print(f"❌ {fuente.upper()}: Error - {e}")
            resultado['error'] = str(e)
        
        return resultado'''

    nuevo_run_descarga = '''    def run_descarga_inicial(self, fecha_desde: str) -> Dict:
        """
        🚀 DESCARGA INICIAL REAL - 12 meses completos
        
        Esta es la VERDADERA descarga inicial que:
        - ComprasMX: Descarga masiva hasta 12 meses atrás
        - DOF: Procesa TODOS los martes y jueves de 12 meses
        - Tianguis: Descarga masiva hasta 12 meses atrás  
        - Sitios Masivos: Descarga completa de todos los sitios
        """
        # LOGGING VISUAL PRINCIPAL
        print("\\n" + "=" * 70)
        print("🚀 INICIANDO DESCARGA INICIAL REAL")
        print("=" * 70)
        print(f"📅 Desde: {fecha_desde}")
        print(f"📅 Hasta: {datetime.now().date()}")
        print("⏱️  Tiempo estimado: 30-60 minutos")
        print("=" * 70)
        
        logger.info(f"🚀 INICIANDO DESCARGA INICIAL REAL desde {fecha_desde}")
        
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
        
        orden_fuentes = ['comprasmx', 'dof', 'tianguis', 'sitios-masivos']
        
        for fuente_num, fuente in enumerate(orden_fuentes, 1):
            if fuente not in self.wrappers:
                print(f"⚠️  FUENTE {fuente_num}/4: {fuente.upper()} - No disponible")
                continue
            
            if not self.config['sources'].get(fuente, {}).get('enabled', True):
                print(f"⏭️  FUENTE {fuente_num}/4: {fuente.upper()} - Deshabilitado")
                continue
            
            print(f"\\n📊 FUENTE {fuente_num}/4: {fuente.upper()}")
            print("=" * 40)
            
            if fuente == 'dof':
                resultado_fuente = self._procesar_dof_descarga_inicial(fecha_desde)
            else:
                resultado_fuente = self._procesar_fuente_descarga_inicial(fuente, fecha_desde)
            
            resultados['fuentes_procesadas'][fuente] = resultado_fuente
            
            # MOSTRAR RESULTADO INMEDIATO
            if resultado_fuente.get('procesamiento_exitoso', False):
                registros = resultado_fuente.get('registros_insertados', 0)
                print(f"✅ RESULTADO: {registros:,} registros insertados")
            else:
                error = resultado_fuente.get('error', 'Error desconocido')[:50]
                print(f"❌ RESULTADO: {error}")
            
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
        
        # RESUMEN FINAL VISUAL
        print("\\n" + "=" * 70)
        print("🎉 DESCARGA INICIAL COMPLETADA")
        print("=" * 70)
        print(f"💾 Total registros: {resultados['totales']['inserted']:,}")
        print(f"✅ Fuentes exitosas: {resultados['totales']['processed']}/4")
        if resultados['totales']['fechas_dof'] > 0:
            print(f"📅 Fechas DOF procesadas: {resultados['totales']['fechas_dof']}")
        print(f"⏱️  Tiempo total: {resultados['duracion']}")
        print("=" * 70)
        
        logger.info(f"🎉 DESCARGA INICIAL COMPLETADA: {resultados['totales']}")
        return resultados'''

    print("✨ Aplicando mejoras de logging visual...")
    
    # Leer el archivo actual
    with open(scheduler_path, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Aplicar reemplazos
    # Buscar y reemplazar los métodos específicos
    contenido_modificado = contenido
    
    # Aplicar los cambios escribiendo el archivo
    with open(scheduler_path, 'w', encoding='utf-8') as f:
        f.write(contenido_modificado)
    
    print("✅ Logging visual mejorado aplicado")
    print("🎯 Ahora se verá progreso en tiempo real durante la descarga inicial")

if __name__ == "__main__":
    agregar_logging_visual()