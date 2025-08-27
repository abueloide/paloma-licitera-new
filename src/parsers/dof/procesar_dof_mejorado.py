#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Procesador Masivo DOF Mejorado
==============================

Script para procesar múltiples archivos TXT del DOF y generar JSONs mejorados
con estadísticas detalladas y reporte consolidado.
"""

import os
import sys
import json
import glob
from typing import List, Dict, Any
from datetime import datetime
import logging
from dataclasses import asdict

# Importar el parser mejorado
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from estructura_dof_mejorado import ParserDOFMejorado, LicitacionMejorada, procesar_archivo_txt

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('procesamiento_dof.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProcesadorDOFMasivo:
    """Procesador masivo para archivos TXT del DOF"""
    
    def __init__(self, directorio_entrada: str, directorio_salida: str = None):
        """
        Inicializa el procesador masivo
        
        Args:
            directorio_entrada: Directorio con archivos TXT del DOF
            directorio_salida: Directorio donde guardar los JSON (por defecto el mismo)
        """
        self.directorio_entrada = directorio_entrada
        self.directorio_salida = directorio_salida or directorio_entrada
        
        # Crear directorio de salida si no existe
        if not os.path.exists(self.directorio_salida):
            os.makedirs(self.directorio_salida)
            logger.info(f"Creado directorio de salida: {self.directorio_salida}")
        
        self.resultados = []
        self.estadisticas_globales = {
            'total_archivos': 0,
            'archivos_procesados': 0,
            'archivos_error': 0,
            'total_licitaciones': 0,
            'licitaciones_con_numero': 0,
            'licitaciones_con_ubicacion': 0,
            'por_entidad': {},
            'por_tipo': {},
            'por_caracter': {},
            'por_fecha_ejemplar': {},
            'confianza_promedio': 0.0,
            'tiempo_procesamiento': None
        }
    
    def buscar_archivos_txt(self) -> List[str]:
        """
        Busca archivos TXT del DOF en el directorio de entrada
        
        Returns:
            Lista de rutas a archivos TXT
        """
        # Patrones comunes de archivos DOF
        patrones = [
            os.path.join(self.directorio_entrada, '*_MAT.txt'),
            os.path.join(self.directorio_entrada, '*_VES.txt'),
            os.path.join(self.directorio_entrada, 'DOF_*.txt'),
            os.path.join(self.directorio_entrada, '*.txt')
        ]
        
        archivos_encontrados = set()
        
        for patron in patrones:
            archivos = glob.glob(patron)
            archivos_encontrados.update(archivos)
        
        # Filtrar archivos que ya son JSON o de salida
        archivos_validos = []
        for archivo in archivos_encontrados:
            nombre = os.path.basename(archivo)
            if not any(x in nombre for x in ['_mejorado.json', '_licitaciones.json', '.log']):
                archivos_validos.append(archivo)
        
        return sorted(archivos_validos)
    
    def procesar_archivo(self, archivo_txt: str) -> Dict[str, Any]:
        """
        Procesa un archivo TXT individual
        
        Args:
            archivo_txt: Ruta al archivo TXT
        
        Returns:
            Diccionario con resultados del procesamiento
        """
        nombre_archivo = os.path.basename(archivo_txt)
        logger.info(f"\n{'='*60}")
        logger.info(f"Procesando: {nombre_archivo}")
        logger.info(f"{'='*60}")
        
        resultado = {
            'archivo': nombre_archivo,
            'ruta': archivo_txt,
            'fecha_procesamiento': datetime.now().isoformat(),
            'status': 'PENDIENTE',
            'licitaciones': 0,
            'archivo_salida': None,
            'error': None,
            'estadisticas': {}
        }
        
        try:
            # Procesar con el parser mejorado
            licitaciones = procesar_archivo_txt(archivo_txt)
            
            if licitaciones:
                # Generar nombre de archivo de salida
                nombre_salida = nombre_archivo.replace('.txt', '_mejorado.json')
                archivo_salida = os.path.join(self.directorio_salida, nombre_salida)
                
                # Calcular estadísticas del archivo
                estadisticas = self._calcular_estadisticas_archivo(licitaciones)
                
                # Preparar datos JSON
                datos_json = {
                    'archivo_origen': nombre_archivo,
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'total_licitaciones': len(licitaciones),
                    'estadisticas': estadisticas,
                    'licitaciones': [asdict(lic) for lic in licitaciones]
                }
                
                # Guardar JSON
                with open(archivo_salida, 'w', encoding='utf-8') as f:
                    json.dump(datos_json, f, ensure_ascii=False, indent=2)
                
                # Actualizar resultado
                resultado['status'] = 'EXITOSO'
                resultado['licitaciones'] = len(licitaciones)
                resultado['archivo_salida'] = archivo_salida
                resultado['estadisticas'] = estadisticas
                
                logger.info(f"✅ Procesado exitosamente: {len(licitaciones)} licitaciones")
                logger.info(f"   Guardado en: {nombre_salida}")
                
                # Actualizar estadísticas globales
                self._actualizar_estadisticas_globales(licitaciones)
                
            else:
                resultado['status'] = 'SIN_DATOS'
                resultado['error'] = 'No se encontraron licitaciones'
                logger.warning(f"⚠️ No se encontraron licitaciones en {nombre_archivo}")
        
        except Exception as e:
            resultado['status'] = 'ERROR'
            resultado['error'] = str(e)
            logger.error(f"❌ Error procesando {nombre_archivo}: {e}")
            self.estadisticas_globales['archivos_error'] += 1
        
        return resultado
    
    def _calcular_estadisticas_archivo(self, licitaciones: List[LicitacionMejorada]) -> Dict:
        """Calcula estadísticas detalladas de las licitaciones de un archivo"""
        estadisticas = {
            'total': len(licitaciones),
            'con_numero_completo': 0,
            'con_ubicacion': 0,
            'con_fechas_completas': 0,
            'confianza_promedio': 0.0,
            'campos_promedio': 0,
            'por_entidad': {},
            'por_tipo': {},
            'por_caracter': {},
            'por_dependencia': {},
            'rango_fechas': {'min': None, 'max': None}
        }
        
        confianza_total = 0
        campos_total = 0
        fechas_publicacion = []
        
        for lic in licitaciones:
            # Número completo
            if lic.numero_licitacion_completo:
                estadisticas['con_numero_completo'] += 1
            
            # Ubicación
            if lic.entidad_federativa:
                estadisticas['con_ubicacion'] += 1
                entidad = lic.entidad_federativa
                estadisticas['por_entidad'][entidad] = estadisticas['por_entidad'].get(entidad, 0) + 1
            
            # Tipo de contratación
            tipo = lic.tipo_contratacion
            estadisticas['por_tipo'][tipo] = estadisticas['por_tipo'].get(tipo, 0) + 1
            
            # Carácter del procedimiento
            caracter = lic.caracter_procedimiento
            estadisticas['por_caracter'][caracter] = estadisticas['por_caracter'].get(caracter, 0) + 1
            
            # Dependencia
            if lic.dependencia:
                dep = lic.dependencia[:50]  # Truncar para evitar claves muy largas
                estadisticas['por_dependencia'][dep] = estadisticas['por_dependencia'].get(dep, 0) + 1
            
            # Fechas completas
            fechas_presentes = sum(1 for f in [
                lic.fecha_publicacion, lic.fecha_junta_aclaraciones,
                lic.fecha_presentacion_apertura, lic.fecha_fallo
            ] if f)
            if fechas_presentes >= 3:
                estadisticas['con_fechas_completas'] += 1
            
            # Fecha de publicación para rango
            if lic.fecha_publicacion:
                fechas_publicacion.append(lic.fecha_publicacion)
            
            # Confianza y campos
            confianza_total += lic.confianza_extraccion
            campos_total += lic.campos_extraidos
        
        # Promedios
        if len(licitaciones) > 0:
            estadisticas['confianza_promedio'] = round(confianza_total / len(licitaciones), 2)
            estadisticas['campos_promedio'] = round(campos_total / len(licitaciones), 1)
        
        # Rango de fechas
        if fechas_publicacion:
            estadisticas['rango_fechas']['min'] = min(fechas_publicacion)
            estadisticas['rango_fechas']['max'] = max(fechas_publicacion)
        
        return estadisticas
    
    def _actualizar_estadisticas_globales(self, licitaciones: List[LicitacionMejorada]):
        """Actualiza las estadísticas globales con las licitaciones procesadas"""
        self.estadisticas_globales['total_licitaciones'] += len(licitaciones)
        
        confianza_suma = 0
        for lic in licitaciones:
            # Con número
            if lic.numero_licitacion_completo:
                self.estadisticas_globales['licitaciones_con_numero'] += 1
            
            # Con ubicación
            if lic.entidad_federativa:
                self.estadisticas_globales['licitaciones_con_ubicacion'] += 1
                entidad = lic.entidad_federativa
                self.estadisticas_globales['por_entidad'][entidad] = \
                    self.estadisticas_globales['por_entidad'].get(entidad, 0) + 1
            
            # Por tipo
            tipo = lic.tipo_contratacion
            self.estadisticas_globales['por_tipo'][tipo] = \
                self.estadisticas_globales['por_tipo'].get(tipo, 0) + 1
            
            # Por carácter
            caracter = lic.caracter_procedimiento
            self.estadisticas_globales['por_caracter'][caracter] = \
                self.estadisticas_globales['por_caracter'].get(caracter, 0) + 1
            
            # Por fecha ejemplar
            if lic.fecha_ejemplar:
                fecha_ej = lic.fecha_ejemplar
                self.estadisticas_globales['por_fecha_ejemplar'][fecha_ej] = \
                    self.estadisticas_globales['por_fecha_ejemplar'].get(fecha_ej, 0) + 1
            
            confianza_suma += lic.confianza_extraccion
        
        # Actualizar confianza promedio global
        if self.estadisticas_globales['total_licitaciones'] > 0:
            self.estadisticas_globales['confianza_promedio'] = round(
                confianza_suma / len(licitaciones), 2
            )
    
    def procesar_todos(self) -> bool:
        """
        Procesa todos los archivos TXT encontrados
        
        Returns:
            True si el proceso fue exitoso
        """
        tiempo_inicio = datetime.now()
        
        # Buscar archivos
        archivos = self.buscar_archivos_txt()
        
        if not archivos:
            logger.warning(f"No se encontraron archivos TXT en {self.directorio_entrada}")
            return False
        
        self.estadisticas_globales['total_archivos'] = len(archivos)
        
        logger.info(f"\n📁 Encontrados {len(archivos)} archivos para procesar")
        logger.info(f"📂 Directorio entrada: {self.directorio_entrada}")
        logger.info(f"💾 Directorio salida: {self.directorio_salida}")
        
        # Procesar cada archivo
        for i, archivo in enumerate(archivos, 1):
            logger.info(f"\n[{i}/{len(archivos)}] Procesando archivo...")
            resultado = self.procesar_archivo(archivo)
            self.resultados.append(resultado)
            
            if resultado['status'] == 'EXITOSO':
                self.estadisticas_globales['archivos_procesados'] += 1
        
        # Calcular tiempo total
        tiempo_fin = datetime.now()
        self.estadisticas_globales['tiempo_procesamiento'] = str(tiempo_fin - tiempo_inicio)
        
        # Guardar reporte consolidado
        self.guardar_reporte_consolidado()
        
        # Mostrar resumen
        self.mostrar_resumen()
        
        return self.estadisticas_globales['archivos_procesados'] > 0
    
    def guardar_reporte_consolidado(self):
        """Guarda un reporte consolidado con todas las estadísticas"""
        archivo_reporte = os.path.join(
            self.directorio_salida, 
            f'reporte_procesamiento_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        
        # Ordenar estadísticas para mejor legibilidad
        if self.estadisticas_globales['por_entidad']:
            self.estadisticas_globales['por_entidad'] = dict(
                sorted(self.estadisticas_globales['por_entidad'].items(), 
                       key=lambda x: x[1], reverse=True)
            )
        
        reporte = {
            'fecha_generacion': datetime.now().isoformat(),
            'directorio_procesado': self.directorio_entrada,
            'directorio_salida': self.directorio_salida,
            'estadisticas_globales': self.estadisticas_globales,
            'resultados_por_archivo': self.resultados
        }
        
        with open(archivo_reporte, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📊 Reporte consolidado guardado en: {archivo_reporte}")
    
    def mostrar_resumen(self):
        """Muestra un resumen del procesamiento en consola"""
        print("\n" + "="*80)
        print("RESUMEN DE PROCESAMIENTO DOF MEJORADO")
        print("="*80)
        
        print(f"\n📈 ESTADÍSTICAS GENERALES:")
        print(f"   • Archivos procesados: {self.estadisticas_globales['archivos_procesados']}/{self.estadisticas_globales['total_archivos']}")
        print(f"   • Archivos con error: {self.estadisticas_globales['archivos_error']}")
        print(f"   • Total licitaciones extraídas: {self.estadisticas_globales['total_licitaciones']}")
        print(f"   • Tiempo de procesamiento: {self.estadisticas_globales['tiempo_procesamiento']}")
        
        print(f"\n📊 CALIDAD DE EXTRACCIÓN:")
        print(f"   • Confianza promedio: {self.estadisticas_globales['confianza_promedio']:.2f}/1.00")
        print(f"   • Licitaciones con número completo: {self.estadisticas_globales['licitaciones_con_numero']}")
        print(f"   • Licitaciones con ubicación: {self.estadisticas_globales['licitaciones_con_ubicacion']}")
        
        if self.estadisticas_globales['total_licitaciones'] > 0:
            pct_numero = (self.estadisticas_globales['licitaciones_con_numero'] / 
                         self.estadisticas_globales['total_licitaciones'] * 100)
            pct_ubicacion = (self.estadisticas_globales['licitaciones_con_ubicacion'] / 
                           self.estadisticas_globales['total_licitaciones'] * 100)
            print(f"   • Porcentaje con número: {pct_numero:.1f}%")
            print(f"   • Porcentaje con ubicación: {pct_ubicacion:.1f}%")
        
        # Top 5 entidades
        if self.estadisticas_globales['por_entidad']:
            print(f"\n🗺️ TOP 5 ENTIDADES FEDERATIVAS:")
            entidades_top = list(self.estadisticas_globales['por_entidad'].items())[:5]
            for entidad, cantidad in entidades_top:
                print(f"   • {entidad}: {cantidad} licitaciones")
        
        # Tipos de contratación
        if self.estadisticas_globales['por_tipo']:
            print(f"\n📋 TIPOS DE CONTRATACIÓN:")
            for tipo, cantidad in self.estadisticas_globales['por_tipo'].items():
                print(f"   • {tipo}: {cantidad}")
        
        # Carácter del procedimiento
        if self.estadisticas_globales['por_caracter']:
            print(f"\n🏷️ CARÁCTER DEL PROCEDIMIENTO:")
            for caracter, cantidad in self.estadisticas_globales['por_caracter'].items():
                print(f"   • {caracter}: {cantidad}")
        
        # Resultados por archivo
        print(f"\n📄 DETALLE POR ARCHIVO:")
        for resultado in self.resultados:
            estado = "✅" if resultado['status'] == 'EXITOSO' else "❌"
            lics = resultado['licitaciones']
            archivo = resultado['archivo']
            print(f"   {estado} {archivo}: {lics} licitaciones")
            
            if resultado['status'] == 'EXITOSO' and resultado['estadisticas']:
                stats = resultado['estadisticas']
                print(f"      - Confianza: {stats['confianza_promedio']:.2f}")
                print(f"      - Con ubicación: {stats['con_ubicacion']}/{stats['total']}")
        
        print("\n" + "="*80)


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Procesador masivo de archivos TXT del DOF'
    )
    parser.add_argument(
        'directorio',
        nargs='?',
        default='.',
        help='Directorio con archivos TXT del DOF (por defecto: directorio actual)'
    )
    parser.add_argument(
        '-o', '--output',
        dest='directorio_salida',
        help='Directorio de salida para los JSON (por defecto: mismo que entrada)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mostrar información detallada de procesamiento'
    )
    
    args = parser.parse_args()
    
    # Configurar nivel de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validar directorio de entrada
    if not os.path.exists(args.directorio):
        print(f"❌ Error: El directorio {args.directorio} no existe")
        sys.exit(1)
    
    # Crear procesador
    procesador = ProcesadorDOFMasivo(
        directorio_entrada=args.directorio,
        directorio_salida=args.directorio_salida
    )
    
    # Procesar todos los archivos
    print("\n🚀 Iniciando procesamiento masivo de archivos DOF...")
    print("="*80)
    
    exito = procesador.procesar_todos()
    
    if exito:
        print("\n✅ Procesamiento completado exitosamente")
    else:
        print("\n⚠️ Procesamiento completado con advertencias")
        print("   Revise el archivo de log para más detalles")
    
    return 0 if exito else 1


if __name__ == "__main__":
    sys.exit(main())
