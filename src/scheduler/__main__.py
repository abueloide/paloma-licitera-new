#!/usr/bin/env python3
import argparse
import json
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Agregar path
sys.path.insert(0, str(Path(__file__).parent.parent))

from .scheduler_manager import SchedulerManager

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/scheduler.log')
        ]
    )

def print_results(results: dict, format: str = "json"):
    if format == "json":
        print(json.dumps(results, indent=2, default=str))
    elif format == "summary":
        print(f"\n📊 RESUMEN DE EJECUCIÓN")
        print(f"Modo: {results.get('modo', 'N/A')}")
        print(f"Duración: {results.get('duracion', 'N/A')}")
        
        totales = results.get('totales', {})
        print(f"Scraped: {totales.get('scraped', 0)}")
        print(f"Processed: {totales.get('processed', 0)}")
        print(f"Inserted: {totales.get('inserted', 0)}")
        print(f"Errors: {totales.get('errors', 0)}")
        print(f"Skipped: {totales.get('skipped', 0)}")

def main():
    parser = argparse.ArgumentParser(description="Paloma Licitera - Scheduler Automatizado")
    
    # Comandos principales
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')
    
    # 🚀 NUEVO: Comando descarga inicial
    inicial_parser = subparsers.add_parser('descarga-inicial', help='🚀 Descarga inicial REAL de 12 meses')
    inicial_parser.add_argument('--desde', required=True, help='Fecha desde (YYYY-MM-DD)')
    
    # Comando histórico
    hist_parser = subparsers.add_parser('historico', help='Descarga histórica')
    hist_parser.add_argument('--fuente', required=True, choices=['all', 'comprasmx', 'dof', 'tianguis', 'sitios-masivos'])
    hist_parser.add_argument('--desde', required=True, help='Fecha desde (YYYY-MM-DD)')
    
    # Comando incremental
    inc_parser = subparsers.add_parser('incremental', help='Actualización incremental')
    inc_parser.add_argument('--fuente', default='all', choices=['all', 'comprasmx', 'dof', 'tianguis'])
    
    # Comando batch
    batch_parser = subparsers.add_parser('batch', help='Ejecución batch')
    batch_parser.add_argument('modo', choices=['diario', 'cada_6h', 'semanal'])
    
    # Comando status
    subparsers.add_parser('status', help='Estado del sistema')
    
    # Comando stats
    stats_parser = subparsers.add_parser('stats', help='Estadísticas')
    stats_parser.add_argument('--dias', type=int, default=30, help='Días hacia atrás')
    
    # Comando daemon
    daemon_parser = subparsers.add_parser('daemon', help='Modo daemon')
    daemon_parser.add_argument('--interval', type=int, default=3600, help='Intervalo en segundos')
    
    # Opciones globales
    parser.add_argument('--config', default='config.yaml', help='Archivo de configuración')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--output', default='summary', choices=['json', 'summary'], help='Formato de salida')
    
    args = parser.parse_args()
    
    # Configurar logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Inicializar scheduler
        scheduler = SchedulerManager(args.config)
        
        # Ejecutar comando
        if args.command == 'descarga-inicial':
            print("\n🚀 INICIANDO DESCARGA INICIAL COMPLETA DE 12 MESES")
            print("=" * 60)
            print("📊 Esta es la VERDADERA descarga inicial que obtiene:")
            print("   • ComprasMX: ~50,000-100,000 licitaciones")
            print("   • DOF: Todos los martes y jueves (~5,000-10,000)")
            print("   • Tianguis Digital: ~10,000-20,000 licitaciones")
            print("   • Sitios Masivos: ~5,000-15,000 licitaciones")
            print("   • Tiempo estimado: 30-60 minutos")
            print("=" * 60)
            print()
            
            results = scheduler.run_descarga_inicial(args.desde)
            
            # Mostrar resultado especial para descarga inicial
            if args.output == 'summary':
                print("\n🎉 DESCARGA INICIAL COMPLETADA")
                print("=" * 40)
                totales = results.get('totales', {})
                print(f"📊 Total insertado: {totales.get('inserted', 0):,} licitaciones")
                print(f"📋 Fuentes procesadas: {totales.get('processed', 0)}/4")
                print(f"🗓️ Fechas DOF procesadas: {totales.get('fechas_dof', 0)}")
                print(f"⏱️ Duración: {results.get('duracion', 'N/A')}")
                
                if totales.get('errors', 0) > 0:
                    print(f"⚠️ Errores: {totales.get('errors', 0)}")
                
                print("\n📈 DESGLOSE POR FUENTE:")
                for fuente, detalle in results.get('fuentes_procesadas', {}).items():
                    registros = detalle.get('registros_insertados', 0)
                    if fuente == 'dof':
                        fechas_info = f" ({detalle.get('fechas_procesadas', 0)} fechas)"
                    else:
                        fechas_info = ""
                    
                    status = "✅" if detalle.get('procesamiento_exitoso') else "❌"
                    print(f"   {status} {fuente.upper()}: {registros:,} registros{fechas_info}")
                
                print("\n🎯 SIGUIENTE PASO:")
                print("   Usa './run-scheduler.sh incremental' para actualizaciones")
                print("   Usa './run-scheduler.sh status' para ver estadísticas")
            else:
                print_results(results, args.output)
            
        elif args.command == 'historico':
            results = scheduler.run_historical(args.fuente, args.desde)
            print_results(results, args.output)
            
        elif args.command == 'incremental':
            fuentes = ['comprasmx', 'dof', 'tianguis'] if args.fuente == 'all' else [args.fuente]
            results = scheduler.run_incremental(fuentes)
            print_results(results, args.output)
            
        elif args.command == 'batch':
            results = scheduler.run_batch(args.modo)
            print_results(results, args.output)
            
        elif args.command == 'status':
            status = scheduler.get_status()
            print(json.dumps(status, indent=2, default=str))
            
        elif args.command == 'stats':
            # Implementar estadísticas
            print("📊 Estadísticas no implementadas aún")
            
        elif args.command == 'daemon':
            import time
            logger.info(f"Iniciando modo daemon, intervalo: {args.interval}s")
            
            while True:
                try:
                    # Ejecutar incremental cada intervalo
                    logger.info("🔄 Ejecutando ciclo daemon")
                    results = scheduler.run_incremental()
                    
                    if results['totales']['inserted'] > 0:
                        logger.info(f"✅ Daemon: {results['totales']['inserted']} nuevos registros")
                    else:
                        logger.info("⏭️ Daemon: Sin nuevos registros")
                        
                except KeyboardInterrupt:
                    logger.info("🛑 Daemon interrumpido por usuario")
                    break
                except Exception as e:
                    logger.error(f"❌ Error en daemon: {e}")
                
                time.sleep(args.interval)
        
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()