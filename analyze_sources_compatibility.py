#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis comparativo de datos entre fuentes: DOF, ComprasMX y Tianguis Digital
Verificar qué información está disponible en cada fuente para estandarizar el modelo
"""

import psycopg2
import psycopg2.extras
import yaml
import json
from collections import defaultdict

def load_config():
    """Cargar configuración de BD."""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config['database']
    except Exception as e:
        print(f"Error cargando config: {e}")
        return None

def analyze_data_by_source():
    """Analizar datos disponibles por cada fuente."""
    db_config = load_config()
    if not db_config:
        return
    
    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['name'],
            user=db_config['user'],
            password=db_config['password'],
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        
        cursor = conn.cursor()
        
        print("🔍 ANÁLISIS COMPARATIVO DE FUENTES DE DATOS")
        print("=" * 80)
        
        # Obtener estadísticas generales por fuente
        cursor.execute("""
            SELECT 
                fuente,
                COUNT(*) as total_registros,
                COUNT(DISTINCT entidad_compradora) as entidades_unicas,
                COUNT(CASE WHEN titulo IS NOT NULL AND LENGTH(titulo) > 0 THEN 1 END) as con_titulo,
                COUNT(CASE WHEN descripcion IS NOT NULL AND LENGTH(descripcion) > 0 THEN 1 END) as con_descripcion,
                COUNT(CASE WHEN fecha_publicacion IS NOT NULL THEN 1 END) as con_fecha_publicacion,
                COUNT(CASE WHEN fecha_apertura IS NOT NULL THEN 1 END) as con_fecha_apertura,
                COUNT(CASE WHEN monto_estimado IS NOT NULL AND monto_estimado > 0 THEN 1 END) as con_monto,
                COUNT(CASE WHEN tipo_contratacion IS NOT NULL THEN 1 END) as con_tipo_contratacion,
                COUNT(CASE WHEN tipo_procedimiento IS NOT NULL THEN 1 END) as con_tipo_procedimiento,
                COUNT(CASE WHEN estado IS NOT NULL THEN 1 END) as con_estado,
                COUNT(CASE WHEN url_original IS NOT NULL THEN 1 END) as con_url
            FROM licitaciones
            WHERE fuente IS NOT NULL
            GROUP BY fuente
            ORDER BY total_registros DESC;
        """)
        
        stats = cursor.fetchall()
        
        print(f"📊 ESTADÍSTICAS GENERALES POR FUENTE:")
        print(f"{'Fuente':<15} {'Total':<8} {'Títulos':<8} {'Descrip':<8} {'F.Pub':<8} {'F.Apert':<8} {'Monto':<8} {'URL':<8}")
        print("-" * 80)
        
        for stat in stats:
            print(f"{stat['fuente']:<15} {stat['total_registros']:<8} {stat['con_titulo']:<8} {stat['con_descripcion']:<8} {stat['con_fecha_publicacion']:<8} {stat['con_fecha_apertura']:<8} {stat['con_monto']:<8} {stat['con_url']:<8}")
        
        # Análizar muestras específicas de cada fuente
        print(f"\n📋 ANÁLISIS DETALLADO POR FUENTE:")
        
        fuentes = ['DOF', 'ComprasMX', 'TIANGUIS_DIGITAL']
        
        for fuente in fuentes:
            print(f"\n" + "=" * 60)
            print(f"🔎 FUENTE: {fuente}")
            print(f"=" * 60)
            
            cursor.execute("""
                SELECT 
                    id,
                    numero_procedimiento,
                    titulo,
                    descripcion,
                    entidad_compradora,
                    tipo_contratacion,
                    tipo_procedimiento,
                    estado,
                    fecha_publicacion,
                    fecha_apertura,
                    fecha_fallo,
                    monto_estimado,
                    moneda,
                    url_original,
                    datos_originales
                FROM licitaciones 
                WHERE fuente = %s 
                ORDER BY fecha_captura DESC 
                LIMIT 3
            """, (fuente,))
            
            samples = cursor.fetchall()
            
            if not samples:
                print(f"❌ No se encontraron registros para {fuente}")
                continue
            
            print(f"📊 {len(samples)} muestras encontradas:")
            
            for i, sample in enumerate(samples, 1):
                print(f"\n--- MUESTRA {i} ---")
                print(f"ID: {sample['id']}")
                print(f"Número: {sample['numero_procedimiento'] or 'No disponible'}")
                
                # Analizar título
                titulo = sample['titulo'] or ''
                if titulo:
                    print(f"Título: {titulo[:100]}{'...' if len(titulo) > 100 else ''}")
                    print(f"  - Longitud: {len(titulo)} caracteres")
                    print(f"  - Contiene fechas: {'Sí' if any(x in titulo.upper() for x in ['2024', '2025', 'AGOSTO', 'SEPTIEMBRE']) else 'No'}")
                    print(f"  - Contiene 'Volumen': {'Sí' if 'volumen' in titulo.lower() else 'No'}")
                else:
                    print("Título: ❌ No disponible")
                
                # Analizar descripción
                desc = sample['descripcion'] or ''
                if desc:
                    print(f"Descripción: {desc[:100]}{'...' if len(desc) > 100 else ''}")
                    print(f"  - Longitud: {len(desc)} caracteres")
                else:
                    print("Descripción: ❌ No disponible")
                
                # Analizar entidad
                print(f"Entidad: {sample['entidad_compradora'] or 'No disponible'}")
                
                # Analizar fechas disponibles
                fechas_disponibles = []
                if sample['fecha_publicacion']:
                    fechas_disponibles.append(f"Publicación: {sample['fecha_publicacion']}")
                if sample['fecha_apertura']:
                    fechas_disponibles.append(f"Apertura: {sample['fecha_apertura']}")
                if sample['fecha_fallo']:
                    fechas_disponibles.append(f"Fallo: {sample['fecha_fallo']}")
                
                print(f"Fechas: {'; '.join(fechas_disponibles) if fechas_disponibles else '❌ No disponibles'}")
                
                # Analizar monto
                if sample['monto_estimado']:
                    print(f"Monto: {sample['monto_estimado']} {sample['moneda'] or 'MXN'}")
                else:
                    print("Monto: ❌ No disponible")
                
                # Analizar tipos
                print(f"Tipo Contratación: {sample['tipo_contratacion'] or 'No disponible'}")
                print(f"Tipo Procedimiento: {sample['tipo_procedimiento'] or 'No disponible'}")
                print(f"Estado: {sample['estado'] or 'No disponible'}")
                
                # Analizar datos_originales si existen
                if sample['datos_originales']:
                    try:
                        if isinstance(sample['datos_originales'], str):
                            datos_orig = json.loads(sample['datos_originales'])
                        else:
                            datos_orig = sample['datos_originales']
                        
                        print(f"Datos originales: {len(datos_orig)} campos")
                        print(f"  - Campos: {', '.join(list(datos_orig.keys())[:5])}{'...' if len(datos_orig) > 5 else ''}")
                    except:
                        print("Datos originales: Formato no válido")
                else:
                    print("Datos originales: ❌ No disponibles")
        
        # Análisis de compatibilidad entre fuentes
        print(f"\n" + "=" * 80)
        print(f"🔍 ANÁLISIS DE COMPATIBILIDAD ENTRE FUENTES")
        print(f"=" * 80)
        
        # Verificar qué campos están disponibles consistentemente
        cursor.execute("""
            SELECT 
                fuente,
                AVG(CASE WHEN titulo IS NOT NULL AND LENGTH(titulo) > 0 THEN 1.0 ELSE 0.0 END) * 100 as pct_titulo,
                AVG(CASE WHEN descripcion IS NOT NULL AND LENGTH(descripcion) > 0 THEN 1.0 ELSE 0.0 END) * 100 as pct_descripcion,
                AVG(CASE WHEN fecha_publicacion IS NOT NULL THEN 1.0 ELSE 0.0 END) * 100 as pct_fecha_pub,
                AVG(CASE WHEN fecha_apertura IS NOT NULL THEN 1.0 ELSE 0.0 END) * 100 as pct_fecha_apert,
                AVG(CASE WHEN monto_estimado IS NOT NULL AND monto_estimado > 0 THEN 1.0 ELSE 0.0 END) * 100 as pct_monto,
                AVG(CASE WHEN tipo_contratacion IS NOT NULL THEN 1.0 ELSE 0.0 END) * 100 as pct_tipo_contrat,
                AVG(CASE WHEN entidad_compradora IS NOT NULL THEN 1.0 ELSE 0.0 END) * 100 as pct_entidad
            FROM licitaciones
            WHERE fuente IS NOT NULL
            GROUP BY fuente
            ORDER BY fuente;
        """)
        
        compatibility = cursor.fetchall()
        
        print("Porcentaje de registros con datos completos por fuente:")
        print(f"{'Fuente':<15} {'Título':<8} {'Descrip':<8} {'F.Pub':<8} {'F.Apert':<9} {'Monto':<8} {'Tipo':<8} {'Entidad':<8}")
        print("-" * 80)
        
        for comp in compatibility:
            print(f"{comp['fuente']:<15} {comp['pct_titulo']:<8.1f} {comp['pct_descripcion']:<8.1f} {comp['pct_fecha_pub']:<8.1f} {comp['pct_fecha_apert']:<9.1f} {comp['pct_monto']:<8.1f} {comp['pct_tipo_contrat']:<8.1f} {comp['pct_entidad']:<8.1f}")
        
        # Recomendaciones
        print(f"\n" + "=" * 80)
        print(f"💡 RECOMENDACIONES PARA MODELO ESTÁNDAR")
        print(f"=" * 80)
        
        recomendaciones = [
            "✅ CAMPOS UNIVERSALES (disponibles en todas las fuentes):",
            "  - titulo (con diferentes niveles de estructura)",
            "  - entidad_compradora",
            "  - fecha_publicacion (en diferentes formatos)",
            "",
            "⚠️  CAMPOS PARCIALES (no disponibles en todas las fuentes):",
            "  - descripcion (menos común en ComprasMX/Tianguis)",
            "  - fecha_apertura (más común en DOF)",
            "  - monto_estimado (variable por fuente)",
            "",
            "🔧 ESTRATEGIA DE PARSING DIFERENCIADA:",
            "  - DOF: Parsing avanzado de texto (fechas, ubicación, volumen)",
            "  - ComprasMX: Estructura más estándar, menos parsing requerido",
            "  - Tianguis: Verificar estructura específica",
            "",
            "📋 PROPUESTA DE MODELO HÍBRIDO:",
            "  - Campos base comunes a todas las fuentes",
            "  - Campos específicos por fuente en JSONB",
            "  - Parser diferenciado por tipo de fuente"
        ]
        
        for rec in recomendaciones:
            print(rec)
        
        conn.close()
        
    except Exception as e:
        print(f"Error en análisis: {e}")

def main():
    print("🔍 Iniciando análisis comparativo de fuentes de datos...\n")
    analyze_data_by_source()
    
    print(f"\n" + "=" * 80)
    print("🎯 CONCLUSIÓN")
    print("=" * 80)
    print("Antes de implementar un parser estándar, necesitamos:")
    print("1. Verificar la estructura real de ComprasMX y Tianguis Digital")
    print("2. Identificar qué información está disponible consistentemente")
    print("3. Diseñar parsers específicos por fuente según su estructura")
    print("4. Crear un modelo híbrido que mantenga compatibilidad")

if __name__ == "__main__":
    main()
